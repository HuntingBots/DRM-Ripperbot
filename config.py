import os

class Config(object):
    # Bot configuration
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    API_ID = int(os.environ.get("API_ID", 123456))
    API_HASH = os.environ.get("API_HASH", "YOUR_API_HASH_HERE")
    SESSION_NAME = os.environ.get("SESSION_NAME", "YOUR_SESSION_STRING_HERE")
    LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "-1001234567890"))
    OWNER_ID = int(os.environ.get("OWNER_ID", 123456789))
    BOT_USERNAME = os.environ.get("BOT_USERNAME", "@yourbotusername")

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
    MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE", 2097152000))
    TG_MAX_FILE_SIZE = int(os.environ.get("TG_MAX_FILE_SIZE", 2097152000))
    SESSION_STR = os.environ.get("SESSION_STR", "")
    DATABASE_URL = os.environ.get("DATABASE_URL", "")
    FREE_USER_MAX_FILE_SIZE = int(os.environ.get("FREE_USER_MAX_FILE_SIZE", 2097152000))
    MAX_SPLIT_SIZE = int(os.environ.get("MAX_SPLIT_SIZE", 4187407334))
    CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", 128))
    DEF_THUMB_NAIL_VID_S = os.environ.get("DEF_THUMB_NAIL_VID_S", "")
    HTTP_PROXY = os.environ.get("HTTP_PROXY", "")
    DEF_WATER_MARK_FILE = os.environ.get("DEF_WATER_MARK_FILE", "@yourbotusername")
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
