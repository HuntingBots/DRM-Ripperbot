import os

class Config(object):
    # Bot configuration
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "1719450568:AAFs2Rtl1vroH0IBL91QFQuuBc5DYiX-M48")
    API_ID = int(os.environ.get("API_ID", 3975570))
    API_HASH = os.environ.get("API_HASH", "680b62f2844aa1954216f6cb99d2f3d9")
    SESSION_NAME = os.environ.get("SESSION_NAME", "AQA7eRMAW_96_U1qa-YSfOdhgRx5hZVeTwuAHxICB7wDK_UNM315-tNnijR7ziedbM76uWTvXn_-pEszyU2vaF9zQOGf1odhUq4deOlTdt4nk2Yleya3gMO6usFfDcug6a_LK2vHc_vpRHfxrG97htNqSd-A12XVBxqCIjQXBA279fciB99kVwhNDzbP9MZyDAxvIPMaejPJZZdT0aCJ96D_OkO5L2ZbATZe7dksGkel1G3GdVCVumrDtCFODSoGOBqSjYQjLUl3_RLkiNOAojSZwQIzZ-jMDFvfMzqAfPyfnbdUIFMCDDn58bJJbTx7tdq84V_q19Jb3GtGyhRCV31h-CocYQAAAABNeVDBAA")
    LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "-1002773421244"))
    OWNER_ID = int(os.environ.get("OWNER_ID", 1606221784))
    BOT_USERNAME = os.environ.get("BOT_USERNAME", "@urltofile00bo)

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
