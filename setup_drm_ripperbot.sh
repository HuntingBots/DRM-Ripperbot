#!/bin/bash

set -e

echo "========= 1. Update packages and install system dependencies ========="
sudo apt update && sudo apt install -y python3 python3-pip ffmpeg aria2 wget curl git unzip

echo "========= 2. Clone or update DRM-Ripperbot ========="
if [ ! -d "$HOME/DRM-Ripperbot" ]; then
    git clone https://github.com/HuntingBots4/DRM-Ripperbot.git ~/DRM-Ripperbot
else
    cd ~/DRM-Ripperbot && git pull
fi
cd ~/DRM-Ripperbot

echo "========= 3. Install Python dependencies ========="
if [ -f requirements.txt ]; then
    pip3 install -r requirements.txt
else
    pip3 install python-telegram-bot pyrogram tgcrypto
fi

echo "========= 4. Download and install N_m3u8DL-RE (linux-x64) ========="
cd ~
wget -O N_m3u8DL-RE-linux-x64.tar.gz https://github.com/nilaoda/N_m3u8DL-RE/releases/latest/download/N_m3u8DL-RE-linux-x64.tar.gz
tar -xzf N_m3u8DL-RE-linux-x64.tar.gz
sudo mv N_m3u8DL-RE /usr/local/bin/
sudo chmod +x /usr/local/bin/N_m3u8DL-RE
rm N_m3u8DL-RE-linux-x64.tar.gz

echo "========= 5. Download and install mp4decrypt (Bento4, Linux x86_64) ========="
wget -O mp4decrypt https://github.com/DavidMuhammad/bento4-static-builds/raw/main/linux/mp4decrypt
sudo mv mp4decrypt /usr/local/bin/
sudo chmod +x /usr/local/bin/mp4decrypt

echo "========= 6. Download and install gdrive CLI (Linux x64) ========="
wget -O gdrive-linux-x64 https://github.com/prasmussen/gdrive/releases/download/2.1.1/gdrive-linux-x64
sudo mv gdrive-linux-x64 /usr/local/bin/gdrive
sudo chmod +x /usr/local/bin/gdrive

echo ""
echo "========= 7. Final instructions ========="
echo "✅ All tools and bot source are installed!"
echo ""
echo "1. Edit your bot config file and set your Telegram bot token and other settings:"
echo "   nano ~/DRM-Ripperbot/config.py"
echo ""
echo "2. Start your bot:"
echo "   cd ~/DRM-Ripperbot && python3 bot.py"
echo ""
echo "To verify tools, run: N_m3u8DL-RE --version ; mp4decrypt --version ; gdrive version ; ffmpeg -version"
echo ""
echo "If you want to update the bot: cd ~/DRM-Ripperbot && git pull"
echo ""
echo "Enjoy your DRM-Ripperbot Telegram bot!"
