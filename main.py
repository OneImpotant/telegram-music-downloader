import asyncio
import os
import logging
import yt_dlp
from typing import Optional, List, Dict, Any

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import FSInputFile
from dotenv import load_dotenv

# --- Configuration & Logging ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

if not BOT_TOKEN:
    exit("Error: BOT_TOKEN not found in environment variables.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

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

async def search_youtube(query: str, limit: int = 1) -> List[Dict[str, Any]]:
    """
    Search for videos on YouTube. 
    limit: number of results to return.
    """
    with yt_dlp.YoutubeDL(YDL_SEARCH_OPTIONS) as ydl:
        try:
            # Using ytsearchN prefix to get multiple results
            search_query = f"ytsearch{limit}:{query}"
            result = await asyncio.to_thread(ydl.extract_info, search_query, download=False)
            
            if not result or 'entries' not in result:
                return []
            
            tracks = []
            for entry in result['entries']:
                if entry:
                    tracks.append({
                        'id': entry.get('id'),
                        'title': entry.get('title'),
                        'url': f"https://www.youtube.com/watch?v={entry.get('id')}"
                    })
            return tracks
        except Exception as e:
            logger.error(f"Search error: {e}")
            return []

# --- Message Handlers ---

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    """Handles the /start command."""
    await message.answer(
        f"Hello, {message.from_user.first_name}! 🎵\n\n"
        "Commands:\n"
        "🔍 /search <name> - Find music by name\n"
        "🔥 /top - Get top 5 music hits of today"
    )

@dp.message(Command("search"))
async def search_command(message: types.Message, command: CommandObject):
    """Handles /search <query> command."""
    if not command.args:
        return await message.answer("Please provide a song name. Example: <code>/search Eminem</code>", parse_mode="HTML")
    
    query = command.args
    processing_msg = await message.answer(f"🔍 Searching for: <b>{query}</b>...", parse_mode="HTML")
    
    tracks = await search_youtube(query, limit=1)
    
    if tracks:
        track = tracks[0]
        builder = InlineKeyboardBuilder()
        builder.button(text="📥 Download MP3", callback_data=f"dl_{track['id']}")
        builder.button(text="❌ No, thanks", callback_data="cancel_search")
        builder.adjust(1)
        
        await processing_msg.edit_text(
            f"✅ <b>Found:</b> {track['title']}\n🔗 <a href='{track['url']}'>Link to YouTube</a>\n\nDo you want to download MP3?",
            parse_mode="HTML",
            reply_markup=builder.as_markup(),
            disable_web_page_preview=True # Keep chat clean
        )
    else:
        await processing_msg.edit_text("❌ Nothing found.")

@dp.message(Command("top"))
async def top_songs_handler(message: types.Message):
    """Handles /top command - finds 5 trending songs."""
    processing_msg = await message.answer("🔥 Fetching today's top 5 hits...")
    
    # Searching for today's music hits
    top_tracks = await search_youtube("today's top music hits", limit=5)
    
    if not top_tracks:
        return await processing_msg.edit_text("❌ Could not fetch top hits.")
    
    builder = InlineKeyboardBuilder()
    response_text = "<b>🔥 Today's Top 5 Hits:</b>\n\n"
    
    for i, track in enumerate(top_tracks, 1):
        response_text += f"{i}. {track['title']}\n"
        # Each button will trigger the download of that specific track
        builder.button(text=f"Download #{i}", callback_data=f"dl_{track['id']}")
    
    builder.button(text="❌ Close", callback_data="cancel_search")
    builder.adjust(2, 2, 1, 1) # Professional grid layout for buttons
    
    await processing_msg.edit_text(
        response_text,
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )

# --- Callback Handlers ---

@dp.callback_query(F.data == "cancel_search")
async def cancel_callback(callback: types.CallbackQuery):
    """Handles the 'No, thanks' / 'Close' button click."""
    await callback.answer("Action cancelled")
    await callback.message.delete() # Simply remove the message to clean up

@dp.callback_query(F.data.startswith("dl_"))
async def download_callback(callback: types.CallbackQuery):
    """Processes MP3 download requests."""
    video_id = callback.data.split("_")[1]
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Change message to show progress
    await callback.message.edit_text("⏳ Converting to MP3... Please wait.")

    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)

    try:
        with yt_dlp.YoutubeDL(YDL_DOWNLOAD_OPTIONS) as ydl:
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            file_path = ydl.prepare_filename(info).rsplit('.', 1)[0] + ".mp3"
            
            audio_file = FSInputFile(file_path)
            await callback.message.answer_audio(
                audio_file, 
                caption=f"🎶 {info.get('title', 'Your Music')}\nvia @YourBot"
            )
            
            await callback.message.delete()
            if os.path.exists(file_path):
                os.remove(file_path)
            
    except Exception as e:
        logger.error(f"Download error: {e}")
        await callback.message.answer("❌ Error during download. The video might be too long or restricted.")

# --- Main Entry Point ---

async def main():
    logger.info("Bot started and ready for commands.")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")