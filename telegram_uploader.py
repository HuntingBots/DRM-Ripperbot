import asyncio
from pyrogram import Client
import config

API_ID = config.API_ID
API_HASH = config.API_HASH

app = Client("tghrip_userbot", api_id=API_ID, api_hash=API_HASH)

async def upload_file(file_path, target_chat_id):
    async with app:
        await app.send_document(chat_id=target_chat_id, document=file_path)
