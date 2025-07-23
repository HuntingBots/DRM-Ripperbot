import config

OWNER_ID = config.Config.OWNER_ID
SUDO_USERS = config.Config.SUDO_USERS
AUTHORIZED_GROUPS = config.Config.AUTHORIZED_GROUPS

def is_authorized(user_id: int, chat_id: int) -> bool:
    """Return True if user is OWNER, SUDO, or message is in an authorized group."""
    return (
        user_id == OWNER_ID or
        user_id in SUDO_USERS or
        chat_id in AUTHORIZED_GROUPS
    )
