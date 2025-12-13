# config.py - Configuration for DRM-RipperBot with MPD support

import os
from pathlib import Path

# Bot Configuration
import os

class Config(object):
    # Bot configuration
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "1719450568:AAFs2Rtl1vroH0IBL91QFQuuBc5DYiX-M48")
    API_ID = int(os.environ.get("API_ID", 3975570))
    API_HASH = os.environ.get("API_HASH", "680b62f2844aa1954216f6cb99d2f3d9")
    SESSION_NAME = os.environ.get("SESSION_NAME", "AQA7eRMAW_96_U1qa-YSfOdhgRx5hZVeTwuAHxICB7wDK_UNM315-tNnijR7ziedbM76uWTvXn_-pEszyU2vaF9zQOGf1odhUq4deOlTdt4nk2Yleya3gMO6usFfDcug6a_LK2vHc_vpRHfxrG97htNqSd-A12XVBxqCIjQXBA279fciB99kVwhNDzbP9MZyDAxvIPMaejPJZZdT0aCJ96D_OkO5L2ZbATZe7dksGkel1G3GdVCVumrDtCFODSoGOBqSjYQjLUl3_RLkiNOAojSZwQIzZ-jMDFvfMzqAfPyfnbdUIFMCDDn58bJJbTx7tdq84V_q19Jb3GtGyhRCV31h-CocYQAAAABNeVDBAA")
    LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "-1002773421244"))
    OWNER_ID = int(os.environ.get("OWNER_ID", 1606221784))
    BOT_USERNAME = os.environ.get("BOT_USERNAME", "@urltofile00bot")
    
    # Only allow commands from these group(s)
    # Comma separated list of group IDs (use negative numbers for supergroups/channels)
    AUTHORIZED_GROUPS = [
        int(x) for x in os.environ.get("AUTHORIZED_GROUPS", "-1001234567890").split(",") if x
    ]

    # Sudo users (admins, helpers etc.)
    try:
        SUDO_USERS = [int(x) for x in os.environ.get("SUDO_USERS", "").split(",") if x]
    except ValueError:
        SUDO_USERS = []
    # Always add owner to sudo users
    if OWNER_ID not in SUDO_USERS:
        SUDO_USERS.append(OWNER_ID)

    # Google Drive credentials
    Credentials = os.environ.get("GDRIVE_CREDENTIALS", "auth/client_secrets.json")
    DRIVE_ID = os.environ.get("DRIVE_ID", "")

    # Other configurations
    DOWNLOAD_LOCATION = "./DOWNLOADS"
    # Hard limit for any file handled by the bot
    MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", 4 * 1024 * 1024 * 1024))  # 4GB
    # For Telegram uploads:
    # 2GB for regular, 4GB for premium
    TG_USER_MAX_FILE_SIZE = 2 * 1024 * 1024 * 1024       # 2GB (non-premium)
    TG_PREMIUM_MAX_FILE_SIZE = 4 * 1024 * 1024 * 1024    # 4GB (premium)
    # Use this to control which account is premium for uploads
    IS_TG_PREMIUM = os.environ.get("IS_TG_PREMIUM", "false").lower() == "true"

    # Use correct Telegram upload limit for userbot uploads
    @classmethod
    def get_max_tg_upload_size(cls):
        return cls.TG_PREMIUM_MAX_FILE_SIZE if cls.IS_TG_PREMIUM else cls.TG_USER_MAX_FILE_SIZE

    # For Bot API (not userbot, i.e. not pyrogram), the max is 50MB (Telegram restriction)
    TG_BOT_API_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

    SESSION_STR = os.environ.get("SESSION_STR", "")
    DATABASE_URL = os.environ.get("DATABASE_URL", "")
    FREE_USER_MAX_FILE_SIZE = int(os.environ.get("FREE_USER_MAX_FILE_SIZE", 2097152000))
    MAX_SPLIT_SIZE = int(os.environ.get("MAX_SPLIT_SIZE", 4187407334))
    CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", 128))
    DEF_THUMB_NAIL_VID_S = os.environ.get("DEF_THUMB_NAIL_VID_S", "")
    HTTP_PROXY = os.environ.get("HTTP_PROXY", "")
    DEF_WATER_MARK_FILE = os.environ.get("DEF_WATER_MARK_FILE", "@urltofile00bon")
    MAX_MESSAGE_LENGTH = 4096
    PROCESS_MAX_TIMEOUT = int(os.environ.get("PROCESS_MAX_TIMEOUT", 3600))

    # Helper: check if a user is authorized
    @classmethod
    def is_user_authorized(cls, user_id: int, chat_id: int) -> bool:
        """Check if the user is owner, sudo, or in an authorized group."""
        return (
            user_id == cls.OWNER_ID
            or user_id in cls.SUDO_USERS
            or chat_id in cls.AUTHORIZED_GROUPS
        )
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

