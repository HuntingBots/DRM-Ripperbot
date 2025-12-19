import asyncio
import logging
import os
import sys
import re
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, UserNotParticipant
import json
from database import Database
from record import M3U8Recorder
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Bot configuration
API_ID = int(os.getenv("API_ID", ""))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MONGO_URI = os.getenv("MONGO_URI", "")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split()))
LOG_CHANNEL = int(os.getenv("LOG_CHANNEL", "")) if os.getenv("LOG_CHANNEL") else None
PREMIUM = True
# Initialize bot and database
app = Client("m3u8_recorder_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
db = Database(MONGO_URI)
recorder = M3U8Recorder()

# Global variables for tracking
active_recordings = {}
user_sessions = {}
waiting_for_duration = set()  # Track users waiting for custom duration input

@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Handle start command"""
    try:
        user_id = message.from_user.id
        user_data = await db.get_user(user_id)
        
        if not user_data:
            await db.add_user(user_id, message.from_user.first_name, message.from_user.username)
        
        welcome_text = (
            "🎬 **M3U8 Stream Recorder Bot**\n\n"
            "⚠️ **Use A stable m3u8 link other wise lead to premature recording stops**\n\n"
            "📹 **Features:**\n"
            "• Record M3U8 streams with custom duration\n"
            "• Auto-upload with thumbnails and metadata\n"
            "• Split large files automatically\n"
            "• Screenshot generation\n\n"
            "🚀 **Commands:**\n"
            "• `/record <url>` - Record M3U8 stream\n"
            "• `/settings` - Configure bot settings\n"
            "• `/help` - Show help message\n\n"
            "💡 **Usage:** Send `/record` followed by your M3U8 URL"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📖 Help", callback_data="help"),
             InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
        ])
        
        await message.reply_text(welcome_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.reply_text("❌ An error occurred. Please try again.")

@app.on_message(filters.command("record"))
async def record_command(client: Client, message: Message):
    """Handle record command"""
    try:
        user_id = message.from_user.id
        
        # Check if user is banned
        if await db.is_banned(user_id):
            await message.reply_text("❌ You are banned from using this bot.")
            return
        
        # Check subscription
        if PREMIUM and not await db.is_premium(user_id) and user_id not in ADMIN_IDS:
            await message.reply_text(
                "🔒 **Premium Required**\n\n"
                "This bot requires a premium subscription to record streams.\n"
                "Contact admin for subscription details."
            )
            return
        
        # Check if user has active recording
       # if user_id in active_recordings:
            #await message.reply_text("⚠️ You already have an active recording. Please wait for it to complete.")
            #return
        
        # Extract URL from command
        command_parts = message.text.split(maxsplit=1)
        if len(command_parts) < 2:
            await message.reply_text(
                "📝 **Usage:** `/record <url>`\n\n"
                "**Example:**\n"
                "`/record http://example.com/stream.m3u8`"
            )
            return
        
        url = command_parts[1].strip()
        
        # Validate URL
        if not (url.startswith("http://") or url.startswith("https://")):
            await message.reply_text("❌ Invalid URL. Please provide a valid HTTP/HTTPS URL.")
            return
        
        # Store session data
        user_sessions[user_id] = {
            "url": url,
            "message_id": message.id,
            "chat_id": message.chat.id
        }
        
        # Duration selection keyboard
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏱️ 30 Minutes", callback_data="duration_30m"),
             InlineKeyboardButton("⏱️ 60 Minutes", callback_data="duration_60m")],
            [InlineKeyboardButton("⏱️ 300 Minutes", callback_data="duration_300m"),
             InlineKeyboardButton("🕐 Custom Duration", callback_data="duration_custom")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_record")]
        ])
        
        await message.reply_text(
            f"🎯 **Recording URL:** `{url}`\n\n"
            "⏰ **Select Duration:**",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in record command: {e}")
        await message.reply_text("❌ An error occurred while processing your request.")

@app.on_message(filters.command("settings"))
async def settings_command(client: Client, message: Message):
    """Handle settings command"""
    try:
        user_id = message.from_user.id
        settings = await db.get_user_settings(user_id)
        
        upload_mode = "📹 Video" if settings.get("upload_mode") == "video" else "📁 File"
        split_mode = "✅ On" if settings.get("split_mode", True) else "❌ Off"
        screenshot_mode = "✅ On" if settings.get("screenshot_mode", True) else "❌ Off"
        
        settings_text = (
            "⚙️ **Bot Settings**\n\n"
            f"📤 **Upload Mode:** {upload_mode}\n"
            f"✂️ **Split Mode:** {split_mode}\n"
            f"📸 **Screenshots:** {screenshot_mode}\n\n"
            "💡 **Split Mode:** Splits files larger than 1.90GB\n"
            "📸 **Screenshots:** Generates 10 screenshots when enabled"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Upload Mode", callback_data="set_upload_mode"),
             InlineKeyboardButton("✂️ Split Mode", callback_data="set_split_mode")],
            [InlineKeyboardButton("📸 Screenshots", callback_data="set_screenshot_mode")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
        ])
        
        await message.reply_text(settings_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in settings command: {e}")
        await message.reply_text("❌ An error occurred while loading settings.")


@app.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    """Handle help command"""
    help_text = (
        "📖 **Help & Commands**\n\n"
        "🎬 **Recording Commands:**\n"
        "• `/record <url>` - Record M3U8/TS stream\n"
        "⚙️ **Settings Commands:**\n"
        "• `/settings` - Configure bot settings\n\n"
        "👨‍💼 **Admin Commands:**\n"
        "• `/paid <user_id> <days>` - Grant premium access\n"
        "• `/broadcast <message>` - Broadcast message\n"
        "• `/ban <user_id>` - Ban user\n"
        "• `/unban <user_id>` - Unban user\n\n"
        "💡 **Usage Examples:**\n"
        "• `/record http://example.com/stream.m3u8`\n"
        "• `/paid 123456789 30d`\n\n"
        "🔧 **Features:**\n"
        "• Custom duration recording\n"
        "• Auto file splitting (>1.90GB)\n"
        "• Screenshot generation (10 screenshots)\n"
        "• Thumbnail support\n"
        "• Progress tracking"
    )
    
    await message.reply_text(help_text)

# Admin Commands
@app.on_message(filters.command("paid") & filters.user(ADMIN_IDS))
async def paid_command(client: Client, message: Message):
    """Handle paid subscription command"""
    try:
        command_parts = message.text.split()
        if len(command_parts) < 3:
            await message.reply_text("📝 **Usage:** `/paid <user_id> <days>`\n\n**Example:** `/paid 123456789 30d`")
            return
        
        user_id = int(command_parts[1])
        duration_str = command_parts[2]
        
        # Parse duration
        if duration_str.endswith('d'):
            days = int(duration_str[:-1])
        else:
            days = int(duration_str)
        
        expiry_date = datetime.now() + timedelta(days=days)
        await db.set_premium(user_id, expiry_date)
        
        await message.reply_text(f"✅ **Premium Access Granted**\n\nUser: `{user_id}`\nDuration: {days} days\nExpiry: {expiry_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Notify user
        try:
            await app.send_message(
                user_id,
                f"🎉 **Premium Access Granted!**\n\n"
                f"⏰ **Duration:** {days} days\n"
                f"📅 **Expires:** {expiry_date.strftime('%Y-%m-%d')}\n\n"
                f"You can now use all bot features!"
            )
        except:
            pass
            
    except Exception as e:
        logger.error(f"Error in paid command: {e}")
        await message.reply_text("❌ Error granting premium access. Please check the user ID and duration format.")

@app.on_message(filters.command("broadcast") & filters.user(ADMIN_IDS))
async def broadcast_command(client: Client, message: Message):
    """Handle broadcast command"""
    try:
        command_parts = message.text.split(maxsplit=1)
        if len(command_parts) < 2:
            await message.reply_text("📝 **Usage:** `/broadcast <message>`")
            return
        
        broadcast_message = command_parts[1]
        users = await db.get_all_users()
        
        success_count = 0
        failed_count = 0
        
        status_msg = await message.reply_text("📡 **Broadcasting...**\n\n⏳ Starting broadcast...")
        
        for user in users:
            try:
                await app.send_message(user["user_id"], broadcast_message)
                success_count += 1
                await asyncio.sleep(0.1)  # Rate limiting
            except:
                failed_count += 1
            
            # Update status every 50 users
            if (success_count + failed_count) % 50 == 0:
                await status_msg.edit_text(
                    f"📡 **Broadcasting...**\n\n"
                    f"✅ Sent: {success_count}\n"
                    f"❌ Failed: {failed_count}\n"
                    f"📊 Total: {success_count + failed_count}/{len(users)}"
                )
        
        await status_msg.edit_text(
            f"📡 **Broadcast Complete**\n\n"
            f"✅ Successfully sent: {success_count}\n"
            f"❌ Failed: {failed_count}\n"
            f"📊 Total users: {len(users)}"
        )
        
    except Exception as e:
        logger.error(f"Error in broadcast command: {e}")
        await message.reply_text("❌ Error during broadcast.")

@app.on_message(filters.command("ban") & filters.user(ADMIN_IDS))
async def ban_command(client: Client, message: Message):
    """Handle ban command"""
    try:
        command_parts = message.text.split()
        if len(command_parts) < 2:
            await message.reply_text("📝 **Usage:** `/ban <user_id>`")
            return
        
        user_id = int(command_parts[1])
        await db.ban_user(user_id)
        
        await message.reply_text(f"🚫 **User Banned**\n\nUser ID: `{user_id}`")
        
    except Exception as e:
        logger.error(f"Error in ban command: {e}")
        await message.reply_text("❌ Error banning user. Please check the user ID.")

@app.on_message(filters.command("unban") & filters.user(ADMIN_IDS))
async def unban_command(client: Client, message: Message):
    """Handle unban command"""
    try:
        command_parts = message.text.split()
        if len(command_parts) < 2:
            await message.reply_text("📝 **Usage:** `/unban <user_id>`")
            return
        
        user_id = int(command_parts[1])
        await db.unban_user(user_id)
        
        await message.reply_text(f"✅ **User Unbanned**\n\nUser ID: `{user_id}`")
        
    except Exception as e:
        logger.error(f"Error in unban command: {e}")
        await message.reply_text("❌ Error unbanning user. Please check the user ID.")

# Callback handlers
@app.on_callback_query()
async def callback_handler(client: Client, callback_query: CallbackQuery):
    """Handle callback queries"""
    try:
        data = callback_query.data
        user_id = callback_query.from_user.id
        
        # Always answer the callback first
        await callback_query.answer()
        
        if data.startswith("duration_"):
            await handle_duration_selection(client, callback_query)
        elif data.startswith("set_"):
            await handle_settings_callback(client, callback_query)
        elif data == "cancel_record":
            if user_id in user_sessions:
                del user_sessions[user_id]
            if user_id in waiting_for_duration:
                waiting_for_duration.remove(user_id)
            await callback_query.message.edit_text("❌ **Recording Cancelled**")
        elif data == "help":
            await callback_query.message.edit_text(
                "📖 **Help & Commands**\n\n"
                "🎬 **Recording Commands:**\n"
                "• `/record <url>` - Record M3U8/TS stream\n"
                "• `/status` - Check current recording status\n\n"
                "⚙️ **Settings Commands:**\n"
                "• `/settings` - Configure bot settings\n\n"
                "👨‍💼 **Admin Commands:**\n"
                "• `/paid <user_id> <days>` - Grant premium access\n"
                "• `/broadcast <message>` - Broadcast message\n"
                "• `/ban <user_id>` - Ban user\n"
                "• `/unban <user_id>` - Unban user\n\n"
                "💡 **Usage Examples:**\n"
                "• `/record http://example.com/stream.m3u8`\n"
                "• `/paid 123456789 30d`\n\n"
                "🔧 **Features:**\n"
                "• Custom duration recording\n"
                "• Auto file splitting (>1.90GB)\n"
                "• Screenshot generation (10 screenshots)\n"
                "• Thumbnail support\n"
                "• Progress tracking",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
                ])
            )
        elif data == "settings":
            await refresh_settings_display(client, callback_query.message, user_id)
        elif data == "back_to_main":
            welcome_text = (
                "🎬 **M3U8 Stream Recorder Bot**\n\n"
                "📹 **Features:**\n"
                "• Record M3U8/TS streams with custom duration\n"
                "• Auto-upload with thumbnails and metadata\n"
                "• Split large files automatically\n"
                "• Screenshot generation\n\n"
                "🚀 **Commands:**\n"
                "• `/record <url>` - Record M3U8/TS stream\n"
                "• `/settings` - Configure bot settings\n"
                "• `/status` - Check recording status\n"
                "• `/help` - Show help message\n\n"
                "💡 **Usage:** Send `/record` followed by your M3U8 URL"
            )
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📖 Help", callback_data="help"),
                 InlineKeyboardButton("⚙️ Settings", callback_data="settings")]
            ])
            
            await callback_query.message.edit_text(welcome_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in callback handler: {e}")
        try:
            await callback_query.answer("❌ An error occurred.", show_alert=True)
        except:
            pass

async def handle_dfffuration_selection(client: Client, callback_query: CallbackQuery):
    """Handle duration selection callbacks"""
    try:
        user_id = callback_query.from_user.id
        data = callback_query.data
        
        if user_id not in user_sessions:
            await callback_query.message.edit_text("❌ Session expired. Please start again with `/record`")
            return
        
        session = user_sessions[user_id]
        url = session["url"]
        
        if data == "duration_custom":
            # Add user to waiting list
            waiting_for_duration.add(user_id)
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_record")]
            ])
            
            await callback_query.message.edit_text(
                "⏰ **Custom Duration**\n\n"
                "Please send the duration in format: `hh:mm:ss`\n\n"
                "**Examples:**\n"
                "• `00:05:00` for 5 minutes\n"
                "• `01:30:00` for 1 hour 30 minutes\n"
                "• `02:00:00` for 2 hours\n"
                "• `12:00:00` for 12 hours (maximum)\n\n"
                "📝 **Send your custom duration:**",
                reply_markup=keyboard
            )
            return
        
        # Parse duration
        duration_map = {
            "duration_30m": 1800,   # 30 minutes
            "duration_60m": 3600,   # 60 minutes
            "duration_300m": 18000  # 300 minutes (5 hours)
        }
        
        duration_seconds = duration_map.get(data)
        if not duration_seconds:
            return
        
        # Start recording
        await start_recording(client, callback_query.message, user_id, url, duration_seconds)
        
    except Exception as e:
        logger.error(f"Error handling duration selection: {e}")
        await callback_query.message.edit_text("❌ An error occurred while processing duration.")

async def handle_settings_callback(client: Client, callback_query: CallbackQuery):
    """Handle settings callbacks"""
    try:
        user_id = callback_query.from_user.id
        data = callback_query.data
        
        if data == "set_upload_mode":
            current_mode = await db.get_user_setting(user_id, "upload_mode", "video")
            new_mode = "file" if current_mode == "video" else "video"
            await db.set_user_setting(user_id, "upload_mode", new_mode)
            
        elif data == "set_split_mode":
            current_mode = await db.get_user_setting(user_id, "split_mode", True)
            new_mode = not current_mode
            await db.set_user_setting(user_id, "split_mode", new_mode)
            
        elif data == "set_screenshot_mode":
            current_mode = await db.get_user_setting(user_id, "screenshot_mode", True)
            new_mode = not current_mode
            await db.set_user_setting(user_id, "screenshot_mode", new_mode)
        
        # Refresh settings display
        await refresh_settings_display(client, callback_query.message, user_id)
        
    except Exception as e:
        logger.error(f"Error handling settings callback: {e}")
        await callback_query.message.edit_text("❌ An error occurred while updating settings.")

async def refresh_settings_display(client: Client, message: Message, user_id: int):
    """Refresh the settings display"""
    try:
        settings = await db.get_user_settings(user_id)
        
        upload_mode = "📹 Video" if settings.get("upload_mode") == "video" else "📁 File"
        split_mode = "✅ On" if settings.get("split_mode", True) else "❌ Off"
        screenshot_mode = "✅ On" if settings.get("screenshot_mode", True) else "❌ Off"
        
        settings_text = (
            "⚙️ **Bot Settings**\n\n"
            f"📤 **Upload Mode:** {upload_mode}\n"
            f"✂️ **Split Mode:** {split_mode}\n"
            f"📸 **Screenshots:** {screenshot_mode}\n\n"
            "💡 **Split Mode:** Splits files larger than 1.90GB\n"
            "📸 **Screenshots:** Generates 10 screenshots when enabled"
        )
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Upload Mode", callback_data="set_upload_mode"),
             InlineKeyboardButton("✂️ Split Mode", callback_data="set_split_mode")],
            [InlineKeyboardButton("📸 Screenshots", callback_data="set_screenshot_mode")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
        ])
        
        await message.edit_text(settings_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error refreshing settings display: {e}")

async def start_recording(client: Client, message: Message, user_id: int, url: str, duration: int):
    """Start the recording process"""
    try:
        # Mark user as having active recording
        active_recordings[user_id] = {
            "url": url,
            "duration": duration,
            "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "Initializing",
            "progress": 0
        }
        
        # Convert duration to readable format
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60
        
        if hours > 0:
            duration_text = f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            duration_text = f"{minutes}m {seconds}s"
        else:
            duration_text = f"{seconds}s"
        
        # Update message
        await message.edit_text(
            f"🎬 **Recording Started**\n\n"
            f"🔗 **URL:** `{url}`\n"
            f"⏰ **Duration:** {duration_text}\n"
            f"📊 **Status:** Initializing...\n\n"
            f"⏳ Please wait while we process your stream..."
        )
        
        # Get user settings
        settings = await db.get_user_settings(user_id)
        
        # Start recording task
        asyncio.create_task(
            recorder.record_stream(
                client, message, user_id, url, duration, settings, active_recordings
            )
        )
        
        # Clean up session
        if user_id in user_sessions:
            del user_sessions[user_id]
        
        # Remove from waiting list
        if user_id in waiting_for_duration:
            waiting_for_duration.remove(user_id)
        
    except Exception as e:
        logger.error(f"Error starting recording: {e}")
        await message.edit_text("❌ Failed to start recording. Please try again.")
        if user_id in active_recordings:
            del active_recordings[user_id]

def parse_duration(duration_str: str) -> int:
    """Parse duration string in format hh:mm:ss and return total seconds"""
    try:
        # Remove any extra whitespace
        duration_str = duration_str.strip()
        
        # Check if format matches hh:mm:ss using regex
        pattern = r'^(\d{1,2}):(\d{1,2}):(\d{1,2})$'
        match = re.match(pattern, duration_str)
        
        if not match:
            raise ValueError("Invalid format")
        
        hours, minutes, seconds = map(int, match.groups())
        
        # Validate ranges
        if minutes >= 60 or seconds >= 60:
            raise ValueError("Minutes and seconds must be less than 60")
        
        if hours > 12:
            raise ValueError("Maximum duration is 12 hours")
        
        total_seconds = hours * 3600 + minutes * 60 + seconds
        
        if total_seconds <= 0:
            raise ValueError("Duration must be greater than 0")
        
        return total_seconds
        
    except ValueError as e:
        raise e
    except Exception as e:
        raise ValueError("Invalid duration format")

# Handle custom duration input
@app.on_message(filters.text)
async def handle_custom_duration(client: Client, message: Message):
    """Handle custom duration input"""
    try:
        user_id = message.from_user.id
        
        # Check if user is waiting for custom duration input
        if user_id in waiting_for_duration and user_id in user_sessions:
            text = message.text.strip()
            
            try:
                # Parse duration
                total_seconds = parse_duration(text)
                
                session = user_sessions[user_id]
                url = session["url"]
                chat_id = session["chat_id"]
                
                # Remove from waiting list
                waiting_for_duration.remove(user_id)
                
                # Delete the user's duration input message
                try:
                    await message.delete()
                except:
                    pass
                
                # Find the original message (the one with duration selection)
                # We need to edit that message, not create a new one
                try:
                    # Get the original message from session
                    original_message_id = session.get("duration_message_id")
                    if original_message_id:
                        # Try to get the original message
                        try:
                            original_message = await client.get_messages(chat_id, original_message_id)
                        except:
                            # If we can't get the original message, send a new one
                            original_message = await client.send_message(
                                chat_id,
                                f"🎯 **Recording URL:** `{url}`\n\n⏰ **Custom Duration Set**"
                            )
                    else:
                        # Send a new message if we don't have the original message ID
                        original_message = await client.send_message(
                            chat_id,
                            f"🎯 **Recording URL:** `{url}`\n\n⏰ **Custom Duration Set**"
                        )
                    
                    # Start recording with the original/new message
                    await start_recording(client, original_message, user_id, url, total_seconds)
                    
                except Exception as e:
                    logger.error(f"Error getting original message: {e}")
                    # Fallback: send a new message
                    new_message = await client.send_message(
                        chat_id,
                        f"🎯 **Recording URL:** `{url}`\n\n⏰ **Starting Recording...**"
                    )
                    await start_recording(client, new_message, user_id, url, total_seconds)
                
            except ValueError as e:
                error_msg = str(e)
                if "Invalid format" in error_msg:
                    await message.reply_text(
                        "❌ **Invalid Format**\n\n"
                        "Please use the exact format: `hh:mm:ss`\n\n"
                        "**Valid Examples:**\n"
                        "• `00:05:00` for 5 minutes\n"
                        "• `01:30:00` for 1 hour 30 minutes\n"
                        "• `02:00:00` for 2 hours\n\n"
                        "**Invalid Examples:**\n"
                        "• `5:00` (missing hours)\n"
                        "• `1:30:0` (single digit seconds)\n"
                        "• `90:00:00` (hours > 12)\n"
                        "• `01:70:00` (minutes >= 60)"
                    )
                elif "Minutes and seconds must be less than 60" in error_msg:
                    await message.reply_text(
                        "❌ **Invalid Time Values**\n\n"
                        "Minutes and seconds must be less than 60.\n\n"
                        "**Examples:**\n"
                        "• `01:59:59` ✅ Valid\n"
                        "• `01:60:00` ❌ Invalid (60 minutes)\n"
                        "• `01:30:60` ❌ Invalid (60 seconds)"
                    )
                elif "Maximum duration is 12 hours" in error_msg:
                    await message.reply_text(
                        "❌ **Duration Too Long**\n\n"
                        "Maximum recording duration is 12 hours.\n\n"
                        "**Maximum:** `12:00:00`"
                    )
                elif "Duration must be greater than 0" in error_msg:
                    await message.reply_text(
                        "❌ **Invalid Duration**\n\n"
                        "Duration must be greater than 0 seconds.\n\n"
                        "**Minimum:** `00:00:01`"
                    )
                else:
                    await message.reply_text(
                        "❌ **Invalid Duration**\n\n"
                        "Please use format: `hh:mm:ss`\n"
                        "Example: `01:30:00` for 1 hour 30 minutes"
                    )
            
            except Exception as e:
                logger.error(f"Error parsing custom duration: {e}")
                await message.reply_text(
                    "❌ **Error Processing Duration**\n\n"
                    "Please try again with format: `hh:mm:ss`"
                )
    
    except Exception as e:
        logger.error(f"Error handling custom duration: {e}")


# Also update the handle_duration_selection function to store the message ID
async def handle_duration_selection(client: Client, callback_query: CallbackQuery):
    """Handle duration selection callbacks"""
    try:
        user_id = callback_query.from_user.id
        data = callback_query.data
        
        if user_id not in user_sessions:
            await callback_query.message.edit_text("❌ Session expired. Please start again with `/record`")
            return
        
        session = user_sessions[user_id]
        url = session["url"]
        
        if data == "duration_custom":
            # Add user to waiting list
            waiting_for_duration.add(user_id)
            
            # Store the message ID for later reference
            user_sessions[user_id]["duration_message_id"] = callback_query.message.id
            
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_record")]
            ])
            
            await callback_query.message.edit_text(
                "⏰ **Custom Duration**\n\n"
                "Please send the duration in format: `hh:mm:ss`\n\n"
                "**Examples:**\n"
                "• `00:05:00` for 5 minutes\n"
                "• `01:30:00` for 1 hour 30 minutes\n"
                "• `02:00:00` for 2 hours\n"
                "• `12:00:00` for 12 hours (maximum)\n\n"
                "📝 **Send your custom duration:**",
                reply_markup=keyboard
            )
            return
        
        # Parse duration
        duration_map = {
            "duration_30m": 1800,   # 30 minutes
            "duration_60m": 3600,   # 60 minutes
            "duration_300m": 18000  # 300 minutes (5 hours)
        }
        
        duration_seconds = duration_map.get(data)
        if not duration_seconds:
            return
        
        # Start recording
        await start_recording(client, callback_query.message, user_id, url, duration_seconds)
        
    except Exception as e:
        logger.error(f"Error handling duration selection: {e}")
        await callback_query.message.edit_text("❌ An error occurred while processing duration.")

# Handle custom duration input
@app.on_message(filters.text & filters.private)
async def handle_cuffffstom_duration(client: Client, message: Message):
    """Handle custom duration input"""
    try:
        user_id = message.from_user.id
        
        # Check if user is waiting for custom duration input
        if user_id in waiting_for_duration and user_id in user_sessions:
            text = message.text.strip()
            
            try:
                # Parse duration
                total_seconds = parse_duration(text)
                
                session = user_sessions[user_id]
                url = session["url"]
                
                # Remove from waiting list
                waiting_for_duration.remove(user_id)
                
                # Start recording with custom duration
                await start_recording(client, message, user_id, url, total_seconds)
                
            except ValueError as e:
                error_msg = str(e)
                if "Invalid format" in error_msg:
                    await message.reply_text(
                        "❌ **Invalid Format**\n\n"
                        "Please use the exact format: `hh:mm:ss`\n\n"
                        "**Valid Examples:**\n"
                        "• `00:05:00` for 5 minutes\n"
                        "• `01:30:00` for 1 hour 30 minutes\n"
                        "• `02:00:00` for 2 hours\n\n"
                        "**Invalid Examples:**\n"
                        "• `5:00` (missing hours)\n"
                        "• `1:30:0` (single digit seconds)\n"
                        "• `90:00:00` (hours > 12)\n"
                        "• `01:70:00` (minutes >= 60)"
                    )
                elif "Minutes and seconds must be less than 60" in error_msg:
                    await message.reply_text(
                        "❌ **Invalid Time Values**\n\n"
                        "Minutes and seconds must be less than 60.\n\n"
                        "**Examples:**\n"
                        "• `01:59:59` ✅ Valid\n"
                        "• `01:60:00` ❌ Invalid (60 minutes)\n"
                        "• `01:30:60` ❌ Invalid (60 seconds)"
                    )
                elif "Maximum duration is 12 hours" in error_msg:
                    await message.reply_text(
                        "❌ **Duration Too Long**\n\n"
                        "Maximum recording duration is 12 hours.\n\n"
                        "**Maximum:** `12:00:00`"
                    )
                elif "Duration must be greater than 0" in error_msg:
                    await message.reply_text(
                        "❌ **Invalid Duration**\n\n"
                        "Duration must be greater than 0 seconds.\n\n"
                        "**Minimum:** `00:00:01`"
                    )
                else:
                    await message.reply_text(
                        "❌ **Invalid Duration**\n\n"
                        "Please use format: `hh:mm:ss`\n"
                        "Example: `01:30:00` for 1 hour 30 minutes"
                    )
            
            except Exception as e:
                logger.error(f"Error parsing custom duration: {e}")
                await message.reply_text(
                    "❌ **Error Processing Duration**\n\n"
                    "Please try again with format: `hh:mm:ss`"
                )
    
    except Exception as e:
        logger.error(f"Error handling custom duration: {e}")


async def main():
    await app.start()
    await db.connect()
    logger.info("Bot started")
    
    try:
        # Keep the bot running
        await idle()
    finally:
        await app.stop()
        await db.close()
        logger.info("Bot stopped")

if __name__ == "__main__":
    from pyrogram import idle
    
    # Set up async event loop
    loop = asyncio.get_event_loop()
    
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
