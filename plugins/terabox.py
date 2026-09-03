"""TeraBox share-link downloader for the /t command."""

import asyncio
import logging
import os
import shutil
import time
from datetime import datetime
from urllib.parse import urlparse

import aiohttp
from pyrogram import Client, enums, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions

from plugins.config import Config
from plugins.database.add import AddUser
from plugins.database.database import db
from plugins.functions.display_progress import humanbytes, progress_for_pyrogram
from plugins.functions.forcesub import handle_force_subscribe
from plugins.functions.verify import check_verification, get_token
from plugins.script import Translation
from plugins.thumbnail import Gthumb01, Gthumb02, Mdata01

logger = logging.getLogger(__name__)
QUALITY_PREFERENCE = ("1080p", "720p", "480p", "360p")
TERABOX_DOMAINS = ("terabox.com", "1024terabox.com", "terabox.app")


def select_stream_url(api_response):
    """Return the highest supported stream URL and its file metadata."""
    if api_response.get("status") != "success":
        return None, None, None
    for item in api_response.get("list", []):
        streams = item.get("fast_stream_url") or {}
        for quality in QUALITY_PREFERENCE:
            url = streams.get(quality)
            if isinstance(url, str) and url.startswith(("https://", "http://")):
                return url, item, quality
    return None, None, None


def is_terabox_url(url):
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    return parsed.scheme in {"http", "https"} and any(
        hostname == domain or hostname.endswith("." + domain)
        for domain in TERABOX_DOMAINS
    )


def safe_filename(name):
    return os.path.basename(name or "terabox_video.mp4").replace("\x00", "") or "terabox_video.mp4"


async def edit_status(message, text):
    try:
        await message.edit_text(text, parse_mode=enums.ParseMode.HTML)
    except Exception as error:
        logger.debug("Could not update TeraBox status: %s", error)


@Client.on_message(filters.private & filters.command("t", ["/", "."]))
async def terabox_download(bot, message):
    if len(message.command) != 2:
        await message.reply_text("Usage: <code>/t https://terabox.com/s/your-share-link</code>")
        return

    share_url = message.command[1].strip()
    if not is_terabox_url(share_url):
        await message.reply_text("Please send a valid TeraBox share URL with <code>/t</code>.")
        return
    if not Config.TERABOX_API_KEY:
        await message.reply_text("TeraBox downloading is not configured. Ask the bot owner to set <code>TERABOX_API_KEY</code>.")
        return
    if message.from_user.id != Config.OWNER_ID and Config.TRUE_OR_FALSE:
        if not await check_verification(bot, message.from_user.id):
            buttons = InlineKeyboardMarkup([[InlineKeyboardButton(
                "✓⃝ Vᴇʀɪꜰʏ ✓⃝", url=await get_token(
                    bot, message.from_user.id, f"https://telegram.me/{Config.BOT_USERNAME}?start="
                ), style=enums.ButtonStyle.SUCCESS,
            )]])
            await message.reply_text("<b>Pʟᴇᴀsᴇ Vᴇʀɪꜰʏ Fɪʀsᴛ Tᴏ Usᴇ Mᴇ</b>", reply_markup=buttons)
            return

    await AddUser(bot, message)
    if Config.UPDATES_CHANNEL and await handle_force_subscribe(bot, message) == 400:
        return
    status = await message.reply_text("<b>Getting TeraBox download link…</b>", link_preview_options=LinkPreviewOptions(is_disabled=True))

    try:
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(Config.TERABOX_API_URL, json={"url": share_url}, headers={"xAPIverse-Key": Config.TERABOX_API_KEY}) as response:
                if response.status != 200:
                    logger.warning("TeraBox API returned HTTP %s", response.status)
                    await edit_status(status, "<b>TeraBox API is unavailable. Please try again later.</b>")
                    return
                payload = await response.json(content_type=None)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
        logger.warning("TeraBox API request failed: %s", error)
        await edit_status(status, "<b>Could not get a TeraBox download link. Please try again later.</b>")
        return

    stream_url, file_info, quality = select_stream_url(payload)
    if not stream_url:
        await edit_status(status, "<b>No supported video stream was found in this TeraBox link.</b>")
        return

    filename = safe_filename(file_info.get("name"))
    temp_dir = os.path.join(Config.DOWNLOAD_LOCATION, f"terabox_{message.from_user.id}_{int(time.time())}")
    os.makedirs(temp_dir, exist_ok=True)
    command = [
        "yt-dlp", "--no-warnings", "--no-playlist", "--hls-prefer-ffmpeg",
        "--max-filesize", str(Config.TG_MAX_FILE_SIZE), "-o", os.path.join(temp_dir, filename), stream_url,
    ]
    if Config.HTTP_PROXY:
        command.extend(["--proxy", Config.HTTP_PROXY])

    started = datetime.now()
    thumbnail = None
    await edit_status(status, f"<b>Downloading TeraBox video ({quality})…</b>")
    try:
        process = await asyncio.create_subprocess_exec(*command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        _, stderr = await process.communicate()
        if process.returncode:
            logger.error("TeraBox yt-dlp failed: %s", stderr.decode(errors="replace"))
            await edit_status(status, "<b>Unable to download this TeraBox video.</b>")
            return
        downloaded_files = [os.path.join(temp_dir, file) for file in os.listdir(temp_dir) if os.path.isfile(os.path.join(temp_dir, file))]
        if not downloaded_files:
            await edit_status(status, "<b>Downloaded file was not found.</b>")
            return
        downloaded_file = max(downloaded_files, key=os.path.getsize)
        file_size = os.path.getsize(downloaded_file)
        if file_size > Config.TG_MAX_FILE_SIZE:
            await edit_status(status, f"<b>File is too large for Telegram: {humanbytes(file_size)}</b>")
            return

        download_seconds = (datetime.now() - started).seconds
        await edit_status(status, "<b>Uploading video to Telegram…</b>")
        upload_started = time.time()
        if await db.get_upload_as_doc(message.from_user.id):
            width, height, duration = await Mdata01(downloaded_file)
            thumbnail = await Gthumb02(bot, message, duration, downloaded_file)
            await message.reply_video(downloaded_file, caption=Translation.CUSTOM_CAPTION_UL_FILE, duration=duration, width=width, height=height, supports_streaming=True, thumb=thumbnail, progress=progress_for_pyrogram, progress_args=(Translation.UPLOAD_START, status, upload_started))
        else:
            thumbnail = await Gthumb01(bot, message)
            await message.reply_document(downloaded_file, thumb=thumbnail, caption=Translation.CUSTOM_CAPTION_UL_FILE, progress=progress_for_pyrogram, progress_args=(Translation.UPLOAD_START, status, upload_started))
        upload_seconds = (datetime.now() - started).seconds - download_seconds
        await edit_status(status, Translation.AFTER_SUCCESSFUL_UPLOAD_MSG_WITH_TS.format(download_seconds, upload_seconds))
    except Exception as error:
        logger.exception("TeraBox download/upload failed")
        await edit_status(status, f"<b>TeraBox download failed:</b> <code>{str(error)[:300]}</code>")
    finally:
        if thumbnail and os.path.exists(thumbnail):
            try:
                os.remove(thumbnail)
            except OSError:
                logger.debug("Could not remove TeraBox thumbnail: %s", thumbnail)
        shutil.rmtree(temp_dir, ignore_errors=True)
