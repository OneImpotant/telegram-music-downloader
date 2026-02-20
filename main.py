import asyncio
import os
import logging
import yt_dlp
from typing import Optional, Dict, Any

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import FSInputFile
from dotenv import load_dotenv

# --- Configuration & Logging ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Setup professional logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Verify token existence
if not BOT_TOKEN:
    exit("Error: BOT_TOKEN not found in environment variables.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Output directory for temporary files
DOWNLOAD_DIR = "downloads"

# --- YouTube Downloader Settings ---
YDL_SEARCH_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'extract_flat': True,
}

YDL_DOWNLOAD_OPTIONS = {
    'format': 'bestaudio/best',
    'outtmpl': f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'quiet': True,
}

# --- Core Functions ---

async def search_youtube(query: str) -> Optional[Dict[str, Any]]:
    """
    Search for a video on YouTube and return metadata.
    Returns None if no results found or on error.
    """
    with yt_dlp.YoutubeDL(YDL_SEARCH_OPTIONS) as ydl:
        try:
            # Use ytsearch1 prefix to get the top result
            result = await asyncio.to_thread(ydl.extract_info, f"ytsearch1:{query}", download=False)
            
            if not result or 'entries' not in result or not result['entries']:
                return None
            
            info = result['entries'][0]
            return {
                'id': info.get('id'),
                'title': info.get('title'),
                'url': f"https://www.youtube.com/watch?v={info.get('id')}"
            }
        except Exception as e:
            logger.error(f"Search error: {e}")
            return None

# --- Message Handlers ---

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    """Handles the /start command."""
    await message.answer(
        f"Hello, {message.from_user.first_name}! 🎵\n"
        "Send me a track name and I will find it on YouTube for you."
    )

@dp.message(F.text)
async def search_handler(message: types.Message):
    """Handles text queries for music search."""
    processing_msg = await message.answer(f"🔍 Searching for: <b>{message.text}</b>", parse_mode="HTML")
    
    track = await search_youtube(message.text)
    
    if track and track.get('id'):
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(
            text="📥 Download MP3", 
            callback_data=f"dl_{track['id']}")
        )
        
        response_text = (
            f"✅ <b>Found:</b> {track['title']}\n"
            f"🔗 <b>Link:</b> {track['url']}\n\n"
            f"Do you want to download this track as MP3?"
        )
        
        await processing_msg.edit_text(
            response_text,
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )
    else:
        await processing_msg.edit_text("❌ Nothing found. Please try a different name.")

# --- Callback Handlers ---

@dp.callback_query(F.data.startswith("dl_"))
async def download_callback(callback: types.CallbackQuery):
    """Processes MP3 download requests when the button is clicked."""
    video_id = callback.data.split("_")[1]
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    await callback.message.edit_text("⏳ Processing audio... Please wait.")

    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    try:
        # Download and convert using yt-dlp
        with yt_dlp.YoutubeDL(YDL_DOWNLOAD_OPTIONS) as ydl:
            # Run blocking extract_info in a thread to keep bot responsive
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            file_path = ydl.prepare_filename(info).rsplit('.', 1)[0] + ".mp3"
            
            # Send the file to user
            audio_file = FSInputFile(file_path)
            await callback.message.answer_audio(
                audio_file, 
                caption=f"🎶 {info.get('title', 'Your Music')}"
            )
            
            # Cleanup: delete status message and local file
            await callback.message.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
            
    except Exception as e:
        logger.error(f"Download error: {e}")
        await callback.message.answer("❌ Sorry, an error occurred while downloading.")

# --- Main Entry Point ---

async def main():
    """Application entry point."""
    logger.info("Starting bot...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")