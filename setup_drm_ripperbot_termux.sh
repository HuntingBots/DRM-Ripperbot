#!/data/data/com.termux/files/usr/bin/bash

set -e

echo "========= 1. Update Termux and install system dependencies ========="
pkg update -y && pkg upgrade -y
pkg install -y python ffmpeg aria2 wget curl tar git unzip

echo "========= 2. Clone or update DRM-Ripperbot ========="
if [ ! -d "$HOME/DRM-Ripperbot" ]; then
    git clone https://github.com/HuntingBots4/DRM-Ripperbot.git ~/DRM-Ripperbot
else
    cd ~/DRM-Ripperbot && git pull
fi
cd ~/DRM-Ripperbot

echo "========= 3. Install Python dependencies ========="
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
else
    pip install python-telegram-bot pyrogram tgcrypto
fi

echo "========= 4. Setting up tools directory ========="
mkdir -p ~/tools && cd ~/tools

echo "========= 5. Download latest N_m3u8DL-RE (Android ARM64/Termux) ========="
N_RE_URL=$(curl -s https://api.github.com/repos/nilaoda/N_m3u8DL-RE/releases/latest | grep "browser_download_url.*android-bionic-arm64.*tar.gz" | cut -d '"' -f 4 | head -n 1)
if [ -z "$N_RE_URL" ]; then
    echo "Could not find N_m3u8DL-RE ARM64 build. Exiting."
    exit 1
fi
wget -O N_m3u8DL-RE.tar.gz "$N_RE_URL"
tar -xzf N_m3u8DL-RE.tar.gz
chmod +x N_m3u8DL-RE

echo "========= 6. Download mp4decrypt (Bento4, ARM64) ========="
wget -O mp4decrypt https://github.com/DavidMuhammad/bento4-static-builds/raw/main/android/mp4decrypt-arm64
chmod +x mp4decrypt

echo "========= 7. Download gdrive CLI (ARM64) ========="
wget -O gdrive https://github.com/prasmussen/gdrive/releases/download/2.1.1/gdrive-linux-arm64
chmod +x gdrive

echo "========= 8. Add ~/tools to PATH ========="
if ! grep -q 'export PATH=$HOME/tools:$PATH' ~/.bashrc; then
    echo 'export PATH=$HOME/tools:$PATH' >> ~/.bashrc
fi
export PATH=$HOME/tools:$PATH

echo "========= 9. Final instructions ========="
echo -e "\n✅ All tools and bot source are installed!"
echo "To reload your shell with the new PATH, run: source ~/.bashrc"
echo "To verify tools, run: N_m3u8DL-RE --version ; mp4decrypt --version ; gdrive version ; ffmpeg -version"
echo ""
echo "Now edit your bot config in ~/DRM-Ripperbot/config.py (put your bot token, etc)."
echo "To start your bot: cd ~/DRM-Ripperbot && python bot.py"
echo ""
echo "If you want to update the bot: cd ~/DRM-Ripperbot && git pull"
echo "If you need to re-run this setup, just bash setup_drm_ripperbot_termux.sh"
echo ""
echo "Enjoy your DRM-Ripperbot!"
