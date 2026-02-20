# Telegram Music Downloader Bot 🎵

A professional asynchronous Telegram bot that searches for music on YouTube and allows users to download tracks in MP3 format.

## Features
- 🔍 **Search:** Find any track by name using `yt-dlp`.
- ⚡ **Asynchronous:** Built with `aiogram 3.x` for high performance.
- 📥 **MP3 Conversion:** High-quality audio extraction (192kbps).
- 🛠 **Clean Code:** Structured with logging, type hinting, and error handling.

## Installation

1. Clone the repository:
   ```bash
   git clone [https://github.com/YOUR_USERNAME/music-downloader-bot.git](https://github.com/YOUR_USERNAME/music-downloader-bot.git)

2. Install dependencies:
    pip install -r requirements.txt

3. Install FFmpeg on your system (required for MP3 conversion).

4. Create a .env file and add your Telegram Bot Token:
    BOT_TOKEN=your_token_here

Usage

    Run the bot:
    python main.py
    Send the name of a song to the bot, and it will provide a link and a download button.