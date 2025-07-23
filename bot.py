import os
import subprocess
import shlex
import threading
import asyncio
import uuid

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler
)
from telegram.error import Forbidden

import config
from access_control import is_authorized

TELEGRAM_BOT_TOKEN = config.Config.BOT_TOKEN
DOWNLOAD_DIR = os.path.abspath(config.Config.DOWNLOAD_LOCATION)
MAX_TG_SIZE = config.Config.get_max_tg_upload_size()  # For userbot uploads (2GB/4GB)

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ========== TASK MANAGEMENT ==========
tasks = {}  # task_id: Task

class Task:
    def __init__(self, user_id, url, key_kid, upload_type, chat_id, message_id):
        self.task_id = str(uuid.uuid4())[:8]
        self.user_id = user_id
        self.url = url
        self.key_kid = key_kid
        self.upload_type = upload_type  # 'tg' or 'gdrive'
        self.chat_id = chat_id
        self.message_id = message_id
        self.status = "Queued"
        self.cancelled = False
        self.progress = 0
        self.filename = None
        self.thread = None

    def cancel(self):
        self.cancelled = True
        self.status = "Cancelled"

    def save(self):
        with open(f"{DOWNLOAD_DIR}/{self.task_id}.task", "w") as f:
            f.write(f"{self.url}\n{self.key_kid or ''}\n{self.upload_type}\n{self.status}\n")

    @staticmethod
    def load(task_id):
        try:
            with open(f"{DOWNLOAD_DIR}/{task_id}.task", "r") as f:
                url, key_kid, upload_type, status = f.read().splitlines()
                return url, key_kid or None, upload_type, status
        except Exception:
            return None

# ========== UTILS ==========
def detect_extension(url: str) -> str:
    if ".m3u8" in url:
        return "m3u8"
    if ".mpd" in url:
        return "mpd"
    if ".ts" in url:
        return "ts"
    return "mp4"

def run_cmd_status(command, task: Task, shell=False):
    process = subprocess.Popen(
        command if shell else shlex.split(command),
        shell=shell,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    output_lines = []
    while True:
        if task.cancelled:
            process.terminate()
            return output_lines, "Cancelled"
        line = process.stdout.readline()
        if not line:
            break
        output_lines.append(line)
        if "Segment" in line or "%" in line:
            try:
                pct = int(''.join(filter(str.isdigit, line)))
                task.progress = pct
            except:
                pass
    process.wait()
    return output_lines, process.returncode

async def send_status_bar(context, task: Task):
    while task.status not in ["Done", "Cancelled", "Error"]:
        bar = f"[{'=' * (task.progress // 10)}{' ' * (10 - (task.progress // 10))}] {task.progress}%\nStatus: {task.status}"
        keyboard = [
            [InlineKeyboardButton("Cancel", callback_data=f"cancel_{task.task_id}"),
             InlineKeyboardButton("Save Task", callback_data=f"save_{task.task_id}")]
        ]
        try:
            await context.bot.edit_message_text(
                chat_id=task.chat_id,
                message_id=task.message_id,
                text=f"🔄 Ripping Task {task.task_id}\nURL: {task.url}\n" + bar,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception:
            pass
        await asyncio.sleep(2)

async def process_task(context, task: Task):
    ext = detect_extension(task.url)
    base = os.path.join(DOWNLOAD_DIR, f"{task.user_id}_{task.task_id}")
    raw_file = f"{base}.{ext}"
    decrypted_file = f"{base}_decrypted.mp4"
    final_file = f"{base}_final.mp4"
    task.status = "Downloading"
    if ext == "mpd":
        dl_cmd = f"N_m3u8DL-RE '{task.url}' -M format=mp4 -o '{raw_file}'"
    else:
        dl_cmd = f"N_m3u8DL-RE '{task.url}' -o '{raw_file}'"

    _, code = run_cmd_status(dl_cmd, task, shell=True)
    if code != 0 or not os.path.exists(raw_file):
        task.status = "Error"
        return

    src_file = raw_file
    if task.key_kid:
        kid, key = task.key_kid.split(':')
        task.status = "Decrypting"
        dec_cmd = f"mp4decrypt --key {kid}:{key} '{raw_file}' '{decrypted_file}'"
        _, code = run_cmd_status(dec_cmd, task, shell=True)
        if code != 0 or not os.path.exists(decrypted_file):
            task.status = "Error"
            return
        src_file = decrypted_file

    if not src_file.endswith(".mp4"):
        task.status = "Remuxing"
        ffmpeg_cmd = f"ffmpeg -y -i '{src_file}' -c copy '{final_file}'"
        _, code = run_cmd_status(ffmpeg_cmd, task, shell=True)
        if code != 0 or not os.path.exists(final_file):
            task.status = "Error"
            return
    else:
        final_file = src_file

    task.filename = final_file
    task.status = "Uploading"

    if task.upload_type == "tg":
        size = os.path.getsize(final_file)
        if size < MAX_TG_SIZE:
            try:
                await context.bot.send_message(
                    chat_id=task.chat_id,
                    text=f"Download complete. Uploading to Telegram..."
                )
                with open(final_file, "rb") as f:
                    await context.bot.send_document(
                        chat_id=task.chat_id,
                        document=f,
                        filename=os.path.basename(final_file),
                        caption=f"Task {task.task_id} completed!"
                    )
            except Forbidden:
                pass
            except Exception as e:
                task.status = "Error"
                await context.bot.send_message(
                    chat_id=task.chat_id,
                    text=f"❌ Failed to upload to Telegram: {e}"
                )
        else:
            # Split the file into parts and upload each
            task.status = "Splitting large file for Telegram upload"
            part_prefix = os.path.join(DOWNLOAD_DIR, f"{os.path.basename(final_file)}.part_")
            split_size = MAX_TG_SIZE  # In bytes

            # Use split command (Linux/macOS)
            split_cmd = f"split -b {split_size} '{final_file}' '{part_prefix}'"
            subprocess.run(split_cmd, shell=True, check=True)

            # List all parts
            part_files = sorted([os.path.join(DOWNLOAD_DIR, f) for f in os.listdir(DOWNLOAD_DIR) if f.startswith(os.path.basename(final_file) + ".part_")])

            await context.bot.send_message(
                chat_id=task.chat_id,
                text=f"📦 File is larger than Telegram's limit. Uploading in {len(part_files)} parts. After download, join parts with:\n\ncat {os.path.basename(final_file)}.part_* > {os.path.basename(final_file)}"
            )

            for i, part in enumerate(part_files, start=1):
                with open(part, "rb") as f:
                    try:
                        await context.bot.send_document(
                            chat_id=task.chat_id,
                            document=f,
                            filename=os.path.basename(part),
                            caption=f"Part {i} of {len(part_files)} for task {task.task_id}"
                        )
                    except Forbidden:
                        pass
                    except Exception as e:
                        await context.bot.send_message(
                            chat_id=task.chat_id,
                            text=f"❌ Failed to upload part {i}: {e}"
                        )

            # Optional: clean up part files after upload
            for part in part_files:
                try:
                    os.remove(part)
                except Exception:
                    pass
    elif task.upload_type == "gdrive":
        task.status = "Uploading to Google Drive"
        gdrive_cmd = f"gdrive upload --share '{final_file}'"
        process = subprocess.Popen(
            shlex.split(gdrive_cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        out, err = process.communicate()
        link = ""
        for line in out.splitlines():
            if "https://drive.google.com" in line:
                link = line.strip()
                break
        try:
            if link:
                await context.bot.send_message(
                    chat_id=task.chat_id,
                    text=f"✅ Uploaded to Google Drive:\n{link}"
                )
            else:
                await context.bot.send_message(
                    chat_id=task.chat_id,
                    text="Failed to upload to Google Drive."
                )
        except Forbidden:
            pass
    task.status = "Done"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    if not is_authorized(user_id, chat_id):
        try:
            await update.message.reply_text("⛔ Not authorized.")
        except Forbidden:
            pass
        return
    await update.message.reply_text(
        "Send /rip <url> [KID:KEY] [tg|gdrive]\n"
        "Examples:\n"
        "  /rip https://site/playlist.m3u8\n"
        "  /rip https://site/manifest.mpd 87d...:dc4... gdrive\n"
        "Supports m3u8, ts, mpd/dash (with or without DRM), uploads to Telegram or Google Drive.\n"
        "You can cancel or save a task during processing."
    )

async def rip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    if not is_authorized(user_id, chat_id):
        try:
            await update.message.reply_text("⛔ Not authorized.")
        except Forbidden:
            pass
        return

    args = context.args
    if not args:
        await update.message.reply_text("Usage: /rip <stream_url> [KID:KEY] [tg|gdrive]")
        return
    url = args[0]
    key_kid = None
    upload_type = "tg"
    if len(args) > 1 and ':' in args[1]:
        key_kid = args[1]
        if len(args) > 2:
            upload_type = args[2].lower()
    elif len(args) > 1:
        upload_type = args[1].lower()
    if upload_type not in ["tg", "gdrive"]:
        upload_type = "tg"

    msg = await update.message.reply_text(
        "Ripping started...",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel", callback_data="cancel_pending"),
             InlineKeyboardButton("Save Task", callback_data="save_pending")]
        ])
    )
    task = Task(
        user_id=user_id,
        url=url,
        key_kid=key_kid,
        upload_type=upload_type,
        chat_id=chat_id,
        message_id=msg.message_id
    )
    tasks[task.task_id] = task

    loop = asyncio.get_event_loop()
    task.thread = threading.Thread(target=lambda: asyncio.run_coroutine_threadsafe(
        process_task(context, task), loop).result()
    )
    task.thread.start()
    asyncio.create_task(send_status_bar(context, task))
    await context.bot.edit_message_reply_markup(
        chat_id=task.chat_id,
        message_id=task.message_id,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Cancel", callback_data=f"cancel_{task.task_id}"),
             InlineKeyboardButton("Save Task", callback_data=f"save_{task.task_id}")]
        ])
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("cancel_"):
        task_id = data.split("_", 1)[1]
        if task_id in tasks:
            tasks[task_id].cancel()
            try:
                await query.edit_message_text(f"❌ Task {task_id} cancelled.")
            except Forbidden:
                pass
    elif data.startswith("save_"):
        task_id = data.split("_", 1)[1]
        if task_id in tasks:
            tasks[task_id].save()
            try:
                await query.edit_message_text(f"💾 Task {task_id} saved.")
            except Forbidden:
                pass

async def tasks_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    if not is_authorized(user_id, chat_id):
        try:
            await update.message.reply_text("⛔ Not authorized.")
        except Forbidden:
            pass
        return
    msg = ""
    for tid, task in tasks.items():
        msg += f"{tid}: {task.url} | Status: {task.status}\n"
    if not msg:
        msg = "No active tasks."
    await update.message.reply_text(msg)

async def error_handler(update, context):
    try:
        raise context.error
    except Forbidden:
        pass
    except Exception as e:
        print(f"Unhandled exception: {e}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rip", rip))
    app.add_handler(CommandHandler("tasks", tasks_list))
    app.add_handler(CallbackQueryHandler(button))
    app.add_error_handler(error_handler)
    print("Bot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
