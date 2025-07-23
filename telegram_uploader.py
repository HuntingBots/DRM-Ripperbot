import asyncio
from pyrogram import Client
import config

API_ID = config.Config.API_ID
API_HASH = config.Config.API_HASH

app = Client("tghrip_userbot", api_id=API_ID, api_hash=API_HASH)

async def upload_file(file_path, target_chat_id):
    max_size = config.Config.get_max_tg_upload_size()
    if os.path.getsize(file_path) > max_size:
        raise Exception(f"File size exceeds Telegram upload limit ({max_size // (1024*1024)} MB)")
    async with app:
        await app.send_document(chat_id=target_chat_id, document=file_path)
