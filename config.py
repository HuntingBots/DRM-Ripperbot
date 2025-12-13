# config.py - Configuration for DRM-RipperBot with MPD support

import os
from pathlib import Path

# Bot Configuration
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # From @BotFather
ADMIN_IDS = [123456789, 987654321]  # Telegram user IDs
MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024  # 2GB
MAX_CONCURRENT_TASKS = 3

# DRM Configuration
WVD_FILE_PATH = "/path/to/your/cdm.wvd"  # Required for DRM decryption
MP4DECRYPT_PATH = "/usr/local/bin/mp4decrypt"  # Or just 'mp4decrypt' if in PATH

# Download Configuration
TEMP_DIR = "/tmp/drm_ripperbot"
MAX_RETRIES = 3
DOWNLOAD_TIMEOUT = 3600  # 1 hour
CHUNK_SIZE = 1024 * 1024  # 1MB

# MPD/DASH Specific
MPD_MAX_BITRATE = 10000000  # 10 Mbps max
MPD_AUDIO_FORMAT = "best"  # or "m4a", "mp3", "opus"
MPD_MERGE_FORMAT = "mp4"
MPD_USE_ARIA2 = True  # Use aria2c for faster downloads
MPD_CONCURRENT_FRAGMENTS = 16

# Streaming Protocols
ALLOWED_PROTOCOLS = [
    "http", "https", "ftp"
]
BLOCKED_DOMAINS = [
    "malicious.com",
    "piracy-site.org"
]

# Quality Presets
QUALITY_PRESETS = {
    "best": "bestvideo+bestaudio/best",
    "1080p": "bestvideo[height<=1080]+bestaudio/best",
    "720p": "bestvideo[height<=720]+bestaudio/best",
    "480p": "bestvideo[height<=480]+bestaudio/best",
    "360p": "bestvideo[height<=360]+bestaudio/best",
    "audio_only": "bestaudio"
}

# Upload Configuration
ENABLE_GDRIVE = True
GDRIVE_CREDENTIALS_PATH = "auth/client_secrets.json"
GDRIVE_FOLDER_ID = "YOUR_GOOGLE_DRIVE_FOLDER_ID"

TELEGRAM_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB (Telegram limit)
SPLIT_LARGE_FILES = True  # Split files > 50MB
SPLIT_SIZE = 45 * 1024 * 1024  # 45MB chunks

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = "drm_ripperbot.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Performance
CACHE_SIZE = 100
CACHE_TTL = 3600  # 1 hour
USE_PROXY = False
PROXY_URL = "http://user:pass@proxy:port"

# Security
REQUIRE_AUTH = True
ALLOW_PUBLIC_FORMATS = True  # Allow /formats without auth
RATE_LIMIT_PER_USER = 10  # Max requests per minute
RATE_LIMIT_PER_IP = 30  # Max requests per minute per IP

# Create required directories
for directory in [TEMP_DIR, "downloads", "logs", "cache"]:
    Path(directory).mkdir(parents=True, exist_ok=True)

# Validate WVD file
if WVD_FILE_PATH and not os.path.exists(WVD_FILE_PATH):
    print(f"⚠️ Warning: WVD file not found at {WVD_FILE_PATH}")
    print("DRM decryption will not work without a valid .wvd file")

# Validate mp4decrypt
try:
    import subprocess
    result = subprocess.run(["which", "mp4decrypt"], capture_output=True, text=True)
    if result.returncode != 0:
        print("⚠️ Warning: mp4decrypt not found in PATH")
except:
    print("⚠️ Warning: Could not verify mp4decrypt installation")
