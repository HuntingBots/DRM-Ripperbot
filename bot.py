#!/usr/bin/env python3
# bot.py - Enhanced with direct key support for MPD/DASH

import os
import sys
import asyncio
import logging
import tempfile
import subprocess
import json
import re
import base64
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse, parse_qs, urlencode

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Telegram imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# Local imports
import config
from access_control import AccessControl
from task_manager import TaskManager
from telegram_uploader import TelegramUploader
from gdrive_uploader import GDriveUploader
from ffmpeg_convert import FFmpegConverter
from inline_keyboard import InlineKeyboard

# Initialize components
access_control = AccessControl()
task_manager = TaskManager()
telegram_uploader = TelegramUploader()
gdrive_uploader = GDriveUploader(config.GDRIVE_CREDENTIALS_PATH) if config.ENABLE_GDRIVE else None
ffmpeg_converter = FFmpegConverter()
inline_keyboard = InlineKeyboard()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class MPDRipper:
    """MPD/DASH Ripper with support for direct keys and yt-dlp-mp4decrypt"""
    
    def __init__(self):
        self.wvd_path = config.WVD_FILE_PATH
        self.temp_dir = config.TEMP_DIR
        os.makedirs(self.temp_dir, exist_ok=True)
        self.keys_file = os.path.join(self.temp_dir, "drm_keys.txt")
        
    def validate_key_format(self, key_string: str) -> bool:
        """Validate if key is in correct kid:key format"""
        # Accept two formats:
        # 1. kid:key (hex:hex)
        # 2. kid=key (sometimes used)
        pattern1 = r'^[0-9a-fA-F]{32}:[0-9a-fA-F]{32}$'  # 32 hex chars:32 hex chars
        pattern2 = r'^[0-9a-fA-F]{32}=[0-9a-fA-F]{32}$'  # 32 hex chars=32 hex chars
        
        key_string = key_string.strip()
        return bool(re.match(pattern1, key_string) or re.match(pattern2, key_string))
    
    def format_key_for_ytdlp(self, key_string: str) -> str:
        """Convert key to yt-dlp compatible format"""
        key_string = key_string.strip()
        
        # Convert = to : if needed
        if '=' in key_string and ':' not in key_string:
            key_string = key_string.replace('=', ':')
        
        # Ensure proper hex format
        parts = key_string.split(':')
        if len(parts) == 2:
            kid, key = parts
            # Pad if needed
            kid = kid.zfill(32)
            key = key.zfill(32)
            return f"{kid}:{key}"
        
        return key_string
    
    def create_keys_file(self, keys: list) -> str:
        """Create a temporary keys file for yt-dlp"""
        with open(self.keys_file, 'w') as f:
            for key in keys:
                formatted_key = self.format_key_for_ytdlp(key)
                f.write(f"{formatted_key}\n")
        return self.keys_file
    
    def extract_keys_from_url(self, url: str) -> list:
        """Extract keys from URL parameters or fragments"""
        parsed = urlparse(url)
        keys = []
        
        # Check query parameters
        query_params = parse_qs(parsed.query)
        for param, values in query_params.items():
            if param.lower() in ['key', 'drmkey', 'widevinekey']:
                for value in values:
                    if self.validate_key_format(value):
                        keys.append(value)
        
        # Check fragment
        if parsed.fragment:
            fragment_params = parse_qs(parsed.fragment)
            for param, values in fragment_params.items():
                if param.lower() in ['key', 'drmkey', 'widevinekey']:
                    for value in values:
                        if self.validate_key_format(value):
                            keys.append(value)
        
        return keys
    
    async def check_mpd_encryption(self, url: str) -> dict:
        """Check if MPD requires encryption and try to detect key"""
        try:
            # Try to get info without downloading
            cmd = ['yt-dlp', '--dump-json', '--skip-download', url]
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                info = json.loads(stdout)
                
                result = {
                    'has_drm': False,
                    'encrypted': False,
                    'key_sources': [],
                    'formats_encrypted': 0,
                    'formats_total': 0
                }
                
                if 'formats' in info:
                    result['formats_total'] = len(info['formats'])
                    for fmt in info['formats']:
                        if fmt.get('has_drm') or fmt.get('drm') or 'encrypted' in fmt.get('format_note', '').lower():
                            result['encrypted'] = True
                            result['formats_encrypted'] += 1
                
                # Check for DRM in description
                if 'description' in info:
                    desc = info['description'].lower()
                    if 'drm' in desc or 'encrypted' in desc or 'widevine' in desc:
                        result['has_drm'] = True
                
                return result
            else:
                # Try a different approach - check MPD content
                cmd = ['curl', '-s', url]
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate()
                mpd_content = stdout.decode('utf-8', errors='ignore')
                
                return {
                    'has_drm': 'ContentProtection' in mpd_content or 'drm' in mpd_content.lower(),
                    'encrypted': 'cenc' in mpd_content.lower() or 'encryption' in mpd_content.lower(),
                    'key_sources': [],
                    'formats_encrypted': 0,
                    'formats_total': 0
                }
                
        except Exception as e:
            logger.error(f"Error checking MPD encryption: {e}")
            return {'has_drm': False, 'encrypted': False, 'error': str(e)}
    
    async def download_with_key(self, url: str, key_string: str = None, quality: str = 'best', 
                               method: str = 'auto') -> dict:
        """
        Download MPD with provided key
        Methods: auto, ytdlp_keys, mp4decrypt_plugin, external_mp4decrypt
        """
        download_dir = tempfile.mkdtemp(prefix='mpd_key_', dir=self.temp_dir)
        
        try:
            # Extract keys from URL if not provided
            keys = []
            if key_string:
                keys.append(key_string)
            
            url_keys = self.extract_keys_from_url(url)
            keys.extend(url_keys)
            
            # Remove duplicate keys
            keys = list(set(keys))
            
            logger.info(f"Using keys: {keys}")
            
            if not keys and method != 'mp4decrypt_plugin':
                return {
                    'success': False,
                    'error': 'No decryption key provided. Use /mpdkey <url> <key> format.',
                    'suggestion': 'Format: 87d54d841e2348b2969a66137522aedd:dc4df1cd96827c90fd05829ef8ed0a0f'
                }
            
            # Method 1: yt-dlp with --allow-unplayable-formats and --video-password (if key is in URL)
            if method == 'auto' or method == 'ytdlp_keys':
                if keys:
                    return await self._download_with_ytdlp_keys(url, keys, quality, download_dir)
            
            # Method 2: yt-dlp with mp4decrypt plugin (requires .wvd)
            if method == 'auto' or method == 'mp4decrypt_plugin':
                if self.wvd_path and os.path.exists(self.wvd_path):
                    return await self._download_with_mp4decrypt_plugin(url, quality, download_dir)
            
            # Method 3: Download encrypted and decrypt with mp4decrypt separately
            if method == 'auto' or method == 'external_mp4decrypt':
                if keys:
                    return await self._download_and_decrypt_separate(url, keys, quality, download_dir)
            
            return {
                'success': False,
                'error': 'No valid decryption method available',
                'details': f'Keys provided: {len(keys)}, WVD exists: {os.path.exists(self.wvd_path) if self.wvd_path else False}'
            }
            
        except Exception as e:
            logger.error(f"Download with key error: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'download_dir': download_dir
            }
    
    async def _download_with_ytdlp_keys(self, url: str, keys: list, quality: str, download_dir: str) -> dict:
        """Download using yt-dlp with --video-password or key file"""
        output_template = f'{download_dir}/%(title)s.%(ext)s'
        
        # Create keys file
        keys_file = self.create_keys_file(keys)
        
        # Build command
        cmd = [
            'yt-dlp',
            '--allow-unplayable-formats',
            '--no-check-certificate',
            '--verbose',
            '--newline',
            '--progress',
            '-o', output_template,
        ]
        
        # Add format/quality selection
        if quality in config.QUALITY_PRESETS:
            cmd.extend(['-f', config.QUALITY_PRESETS[quality]])
        else:
            cmd.extend(['-f', 'best'])
        
        # Add decryption keys
        # Try different approaches for key specification
        for key in keys:
            formatted_key = self.format_key_for_ytdlp(key)
            cmd.extend(['--add-header', f'X-Key: {formatted_key}'])
        
        # Add MPD specific options
        cmd.extend([
            '--ignore-errors',
            '--no-part',
            '--hls-prefer-native',
            '--merge-output-format', 'mp4',
            '--cookies-from-browser', 'chrome',  # Optional: for sites requiring login
            url
        ])
        
        logger.info(f"Executing yt-dlp with keys: {' '.join(cmd)}")
        
        # Execute
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        
        return await self._monitor_download_process(process, download_dir, "ytdlp_keys")
    
    async def _download_with_mp4decrypt_plugin(self, url: str, quality: str, download_dir: str) -> dict:
        """Download using yt-dlp-mp4decrypt plugin"""
        if not self.wvd_path or not os.path.exists(self.wvd_path):
            return {
                'success': False,
                'error': 'WVD file not found. Required for mp4decrypt plugin.'
            }
        
        output_template = f'{download_dir}/%(title)s.%(ext)s'
        
        cmd = [
            'yt-dlp',
            '--use-postprocessor', f'Mp4Decrypt:when=before_dl;devicepath={self.wvd_path}',
            '--allow-unplayable-formats',
            '--no-check-certificate',
            '--verbose',
            '--newline',
            '--progress',
            '-o', output_template,
        ]
        
        # Add format/quality selection
        if quality in config.QUALITY_PRESETS:
            cmd.extend(['-f', config.QUALITY_PRESETS[quality]])
        else:
            cmd.extend(['-f', 'best'])
        
        # Add MPD specific options
        cmd.extend([
            '--ignore-errors',
            '--no-part',
            '--hls-prefer-native',
            '--merge-output-format', 'mp4',
            url
        ])
        
        logger.info(f"Executing yt-dlp with mp4decrypt plugin: {' '.join(cmd)}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        
        return await self._monitor_download_process(process, download_dir, "mp4decrypt_plugin")
    
    async def _download_and_decrypt_separate(self, url: str, keys: list, quality: str, download_dir: str) -> dict:
        """Download encrypted file then decrypt with mp4decrypt"""
        # Step 1: Download encrypted
        encrypted_dir = os.path.join(download_dir, 'encrypted')
        os.makedirs(encrypted_dir, exist_ok=True)
        
        output_template = f'{encrypted_dir}/enc_%(title)s_%(format_id)s.%(ext)s'
        
        cmd_download = [
            'yt-dlp',
            '--allow-unplayable-formats',
            '--no-check-certificate',
            '--verbose',
            '-o', output_template,
            '--no-exec',  # Don't run any post-processing
        ]
        
        if quality in config.QUALITY_PRESETS:
            cmd_download.extend(['-f', config.QUALITY_PRESETS[quality]])
        else:
            cmd_download.extend(['-f', 'bestvideo+bestaudio/best'])
        
        cmd_download.append(url)
        
        logger.info(f"Downloading encrypted: {' '.join(cmd_download)}")
        
        process = await asyncio.create_subprocess_exec(
            *cmd_download,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )
        
        download_result = await self._monitor_download_process(process, encrypted_dir, "download_encrypted")
        
        if not download_result['success']:
            return download_result
        
        # Step 2: Find downloaded files
        encrypted_files = list(Path(encrypted_dir).glob('*'))
        
        if not encrypted_files:
            return {
                'success': False,
                'error': 'No encrypted files downloaded',
                'download_dir': download_dir
            }
        
        # Step 3: Decrypt each file
        decrypted_files = []
        for enc_file in encrypted_files:
            dec_file = os.path.join(download_dir, f'dec_{enc_file.name}')
            
            for key in keys:
                formatted_key = self.format_key_for_ytdlp(key)
                cmd_decrypt = ['mp4decrypt', '--key', formatted_key, str(enc_file), dec_file]
                
                try:
                    process = await asyncio.create_subprocess_exec(
                        *cmd_decrypt,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode == 0 and os.path.exists(dec_file):
                        decrypted_files.append(dec_file)
                        logger.info(f"Successfully decrypted: {enc_file.name}")
                        break
                    else:
                        logger.warning(f"Decryption failed for {enc_file.name}: {stderr.decode()}")
                except Exception as e:
                    logger.error(f"Error during decryption: {e}")
        
        if not decrypted_files:
            return {
                'success': False,
                'error': 'Failed to decrypt any files',
                'download_dir': download_dir
            }
        
        # Step 4: Merge if multiple files
        if len(decrypted_files) >= 2:
            # Assume first is video, second is audio
            video_file = decrypted_files[0]
            audio_file = decrypted_files[1]
            final_file = os.path.join(download_dir, 'final_merged.mp4')
            
            cmd_merge = [
                'ffmpeg', '-i', video_file, '-i', audio_file,
                '-c', 'copy', '-map', '0:v:0', '-map', '1:a:0',
                final_file
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd_merge,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            await process.communicate()
            
            if process.returncode == 0 and os.path.exists(final_file):
                return {
                    'success': True,
                    'file_path': final_file,
                    'download_dir': download_dir,
                    'size': os.path.getsize(final_file),
                    'method': 'external_mp4decrypt'
                }
        
        # If merging failed or only one file, return first decrypted file
        return {
            'success': True,
            'file_path': decrypted_files[0],
            'download_dir': download_dir,
            'size': os.path.getsize(decrypted_files[0]),
            'method': 'external_mp4decrypt'
        }
    
    async def _monitor_download_process(self, process, download_dir: str, method: str) -> dict:
        """Monitor download process and collect output"""
        output_lines = []
        downloaded_file = None
        
        while True:
            line = await process.stdout.readline()
            if not line:
                break
                
            line_text = line.decode().strip()
            output_lines.append(line_text)
            
            # Check for downloaded file
            if 'Merging formats into' in line_text:
                parts = line_text.split("'")
                if len(parts) >= 2:
                    potential_file = parts[1]
                    if os.path.exists(potential_file):
                        downloaded_file = potential_file
            
            # Check for completion
            if '[ExtractAudio]' in line_text or '[Merger]' in line_text:
                if '[Merger] Merging formats into "' in line_text:
                    parts = line_text.split('"')
                    if len(parts) >= 2:
                        final_file = parts[1]
                        if os.path.exists(final_file):
                            downloaded_file = final_file
        
        await process.wait()
        
        # If no file found via stdout, search directory
        if not downloaded_file:
            files = list(Path(download_dir).glob('*'))
            if files:
                # Get largest file (likely the video)
                files.sort(key=lambda x: x.stat().st_size, reverse=True)
                downloaded_file = str(files[0])
        
        if downloaded_file and os.path.exists(downloaded_file) and os.path.getsize(downloaded_file) > 0:
            return {
                'success': True,
                'file_path': downloaded_file,
                'download_dir': download_dir,
                'size': os.path.getsize(downloaded_file),
                'log': '\n'.join(output_lines[-20:]),
                'method': method
            }
        else:
            return {
                'success': False,
                'error': f'Download failed using {method}',
                'log': '\n'.join(output_lines[-20:]),
                'download_dir': download_dir
            }

# Initialize MPD ripper
mpd_ripper = MPDRipper()

# Command Handlers
async def mpdkey_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mpdkey command for MPD with explicit keys"""
    user_id = update.effective_user.id
    
    if not access_control.check_access(user_id):
        await update.message.reply_text("❌ Access denied. Contact admin.")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "Usage: `/mpdkey <url> [key] [quality]`\n\n"
            "**Key Format:** `kid:key` (32 hex chars each)\n"
            "**Example:** `87d54d841e2348b2969a66137522aedd:dc4df1cd96827c90fd05829ef8ed0a0f`\n\n"
            "**Quality options:**\n"
            "• `best` - Best quality (default)\n"
            "• `1080p` - 1080p or lower\n"
            "• `720p` - 720p or lower\n\n"
            "**Examples:**\n"
            "`/mpdkey https://example.com/stream.mpd 87d54d841e2348b2969a66137522aedd:dc4df1cd96827c90fd05829ef8ed0a0f 720p`\n"
            "`/mpdkey https://example.com/stream.mpd?key=87d54d841e2348b2969a66137522aedd:dc4df1cd96827c90fd05829ef8ed0a0f`",
            parse_mode='Markdown'
        )
        return
    
    # Parse arguments
    url = context.args[0]
    key = None
    quality = 'best'
    method = 'auto'
    
    if len(context.args) >= 2:
        # Check if second arg is a key or quality
        if mpd_ripper.validate_key_format(context.args[1]):
            key = context.args[1]
            if len(context.args) >= 3:
                quality = context.args[2]
        else:
            quality = context.args[1]
    
    # Check if key is in URL
    url_keys = mpd_ripper.extract_keys_from_url(url)
    if not key and url_keys:
        key = url_keys[0]
    
    # Create task
    task_id = task_manager.create_task(
        user_id=user_id,
        task_type='mpdkey_download',
        url=url,
        key=key,
        quality=quality,
        method=method
    )
    
    # Send initial status
    status_msg = await update.message.reply_text(
        f"🔐 **MPD with Key Download**\n\n"
        f"🔗 URL: `{url[:80]}...`\n"
        f"🔑 Key: `{'Provided' if key else 'Extracting from URL...'}`\n"
        f"🎚️ Quality: `{quality}`\n"
        f"📝 Task ID: `{task_id}`\n"
        f"⏳ Status: `Initializing...`",
        parse_mode='Markdown'
    )
    
    # Process in background
    asyncio.create_task(process_mpdkey_download(task_id, update, context, status_msg))

async def process_mpdkey_download(task_id: str, update: Update, context: ContextTypes.DEFAULT_TYPE, status_msg):
    """Process MPD with key download"""
    task = task_manager.get_task(task_id)
    if not task:
        return
    
    url = task['url']
    key = task.get('key')
    quality = task.get('quality', 'best')
    method = task.get('method', 'auto')
    
    try:
        # Step 1: Analyze MPD
        await status_msg.edit_text(
            f"🔍 **Analyzing MPD...**\n"
            f"URL: `{url[:60]}...`\n"
            f"Key: `{key[:40] + '...' if key and len(key) > 40 else key or 'Not provided'}`",
            parse_mode='Markdown'
        )
        
        # Check encryption
        encryption_info = await mpd_ripper.check_mpd_encryption(url)
        
        if not encryption_info.get('encrypted') and not encryption_info.get('has_drm'):
            await status_msg.edit_text(
                f"⚠️ **MPD Analysis**\n\n"
                f"This MPD doesn't appear to be encrypted.\n"
                f"DRM detected: `{encryption_info.get('has_drm', False)}`\n"
                f"Encrypted formats: `{encryption_info.get('formats_encrypted', 0)}/{encryption_info.get('formats_total', 0)}`\n\n"
                f"Trying download anyway...",
                parse_mode='Markdown'
            )
        else:
            await status_msg.edit_text(
                f"🔐 **Encrypted MPD Detected**\n\n"
                f"DRM: `{encryption_info.get('has_drm', True)}`\n"
                f"Encrypted formats: `{encryption_info.get('formats_encrypted', 0)}/{encryption_info.get('formats_total', 0)}`\n"
                f"Key provided: `{'Yes' if key else 'No'}`",
                parse_mode='Markdown'
            )
        
        # Step 2: Determine best method
        if not key and not config.WVD_FILE_PATH:
            await status_msg.edit_text(
                f"❌ **No Decryption Method Available**\n\n"
                f"No key provided and no WVD file configured.\n"
                f"Please provide a key or configure WVD file in config.py",
                parse_mode='Markdown'
            )
            task_manager.update_task(task_id, {'status': 'failed', 'error': 'No decryption method'})
            return
        
        # Auto-select method
        if method == 'auto':
            if key:
                method = 'ytdlp_keys'
            elif config.WVD_FILE_PATH and os.path.exists(config.WVD_FILE_PATH):
                method = 'mp4decrypt_plugin'
            else:
                method = 'external_mp4decrypt'
        
        await status_msg.edit_text(
            f"⚙️ **Starting Download**\n\n"
            f"Method: `{method}`\n"
            f"Quality: `{quality}`\n"
            f"Key: `{'Using provided key' if key else 'Using WVD file' if config.WVD_FILE_PATH else 'No key/WVD'}`",
            parse_mode='Markdown'
        )
        
        task_manager.update_task(task_id, {'status': 'downloading', 'progress': 10, 'method': method})
        
        # Download
        result = await mpd_ripper.download_with_key(url, key, quality, method)
        
        if result['success']:
            task_manager.update_task(task_id, {'status': 'processing', 'progress': 90})
            
            # Update status
            file_size_mb = result['size'] / (1024 * 1024)
            await status_msg.edit_text(
                f"✅ **Download Complete!**\n\n"
                f"📁 File: `{os.path.basename(result['file_path'])}`\n"
                f"📦 Size: `{file_size_mb:.2f} MB`\n"
                f"🔓 Method: `{result.get('method', 'unknown')}`\n"
                f"⚙️ Processing...",
                parse_mode='Markdown'
            )
            
            # Convert if needed
            if not result['file_path'].endswith('.mp4'):
                converted_file = await ffmpeg_converter.convert_to_mp4(
                    result['file_path'],
                    result['file_path'].rsplit('.', 1)[0] + '.mp4'
                )
                if converted_file:
                    result['file_path'] = converted_file
            
            # Upload to Telegram
            await status_msg.edit_text(
                f"📤 **Uploading to Telegram...**\n\n"
                f"File: `{os.path.basename(result['file_path'])}`\n"
                f"Size: `{file_size_mb:.2f} MB`",
                parse_mode='Markdown'
            )
            
            upload_success = await telegram_uploader.upload_file(
                file_path=result['file_path'],
                chat_id=update.effective_chat.id,
                caption=f"🔐 MPD with Key Download Complete\nQuality: {quality}\nSize: {file_size_mb:.2f} MB\nMethod: {result.get('method', 'unknown')}"
            )
            
            if upload_success:
                # Optional Google Drive upload
                if config.ENABLE_GDRIVE and gdrive_uploader:
                    await status_msg.edit_text("☁️ Uploading to Google Drive...")
                    gdrive_url = await gdrive_uploader.upload_to_drive(result['file_path'])
                    if gdrive_url:
                        await update.message.reply_text(f"📁 Google Drive: {gdrive_url}")
                
                # Cleanup
                try:
                    import shutil
                    shutil.rmtree(result['download_dir'], ignore_errors=True)
                    
                    # Clean keys file
                    if os.path.exists(mpd_ripper.keys_file):
                        os.remove(mpd_ripper.keys_file)
                except:
                    pass
                
                task_manager.update_task(task_id, {'status': 'completed', 'progress': 100})
                await status_msg.edit_text(
                    f"🎉 **Task Completed Successfully!**\n\n"
                    f"✅ Download: Complete\n"
                    f"✅ Decryption: Complete\n"
                    f"✅ Upload: Complete\n\n"
                    f"Task ID: `{task_id}`",
                    parse_mode='Markdown'
                )
            else:
                task_manager.update_task(task_id, {'status': 'failed', 'error': 'Upload failed'})
                await status_msg.edit_text("❌ Upload failed. File saved locally.")
        
        else:
            task_manager.update_task(task_id, {'status': 'failed', 'error': result.get('error')})
            
            error_details = result.get('details', '')
            error_log = result.get('log', '')[:800]
            
            error_msg = f"❌ **Download Failed**\n\nError: `{result.get('error', 'Unknown error')}`"
            
            if error_details:
                error_msg += f"\nDetails: `{error_details}`"
            
            if error_log:
                error_msg += f"\n\n**Log excerpt:**\n```\n{error_log}\n```"
            
            await status_msg.edit_text(error_msg, parse_mode='Markdown')
    
    except Exception as e:
        logger.error(f"MPD key download error: {e}", exc_info=True)
        task_manager.update_task(task_id, {'status': 'failed', 'error': str(e)})
        
        await status_msg.edit_text(
            f"💥 **Critical Error**\n\n"
            f"Error: `{str(e)}`\n\n"
            f"Task ID: `{task_id}`",
            parse_mode='Markdown'
        )

async def test_key_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Test if a key is in valid format"""
    if not context.args:
        await update.message.reply_text(
            "Usage: `/testkey <key>`\n\n"
            "**Valid Formats:**\n"
            "• `kid:key` (32 hex chars each)\n"
            "• `kid=key` (32 hex chars each)\n\n"
            "**Example:**\n"
            "`/testkey 87d54d841e2348b2969a66137522aedd:dc4df1cd96827c90fd05829ef8ed0a0f`",
            parse_mode='Markdown'
        )
        return
    
    key_string = ' '.join(context.args)
    
    is_valid = mpd_ripper.validate_key_format(key_string)
    
    if is_valid:
        formatted = mpd_ripper.format_key_for_ytdlp(key_string)
        await update.message.reply_text(
            f"✅ **Valid Key Format**\n\n"
            f"Original: `{key_string}`\n"
            f"Formatted: `{formatted}`\n\n"
            f"Ready to use with `/mpdkey` command!",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"❌ **Invalid Key Format**\n\n"
            f"Key: `{key_string}`\n\n"
            f"**Expected Format:**\n"
            f"• 32 hex characters\n"
            f"• Separated by `:` or `=`\n"
            f"• Example: `87d54d841e2348b2969a66137522aedd:dc4df1cd96827c90fd05829ef8ed0a0f`",
            parse_mode='Markdown'
        )

async def extract_key_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Extract keys from URL"""
    if not context.args:
        await update.message.reply_text("Usage: `/extractkey <url>`")
        return
    
    url = context.args[0]
    
    keys = mpd_ripper.extract_keys_from_url(url)
    
    if keys:
        keys_text = "\n".join([f"• `{key}`" for key in keys])
        await update.message.reply_text(
            f"🔑 **Keys Found in URL**\n\n"
            f"URL: `{url[:80]}...`\n\n"
            f"**Keys:**\n{keys_text}\n\n"
            f"Use with: `/mpdkey {url} {keys[0]}`",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"🔍 **No Keys Found**\n\n"
            f"URL: `{url[:80]}...`\n\n"
            f"No decryption keys found in URL parameters.\n"
            f"You need to provide a key manually.",
            parse_mode='Markdown'
        )

# Update start command to include new features
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Enhanced start command with key support"""
    welcome_text = """
🚀 **DRM-RipperBot with MPD/DASH & Key Support**

**🎬 MPD/DASH with Keys:**
- Direct key support: `kid:key` format
- URL parameter extraction
- Multiple decryption methods

**🔑 Key Commands:**
`/mpdkey <url> [key] [quality]` - Download with key
`/testkey <key>` - Validate key format
`/extractkey <url>` - Extract keys from URL
`/mpd <url> [quality]` - Regular MPD download

**🔧 Example:**
