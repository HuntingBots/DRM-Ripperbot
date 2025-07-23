#!/data/data/com.termux/files/usr/bin/bash

# Termux Script for DRM Ripper Bot Dependencies
# Installs: ffmpeg, aria2, wget, curl, N_m3u8DL-RE, mp4decrypt, gdrive
# For use with your Python Telegram DRM ripper bot

set -e

echo "Updating Termux packages..."
pkg update -y && pkg upgrade -y

echo "Installing Python and required tools..."
pkg install -y python ffmpeg aria2 wget curl tar git unzip

echo "Installing pip requirements (if requirements.txt exists)..."
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
else
    pip install python-telegram-bot pyrogram tgcrypto
fi

# Download and install N_m3u8DL-RE (Android ARM64 build)
mkdir -p ~/tools && cd ~/tools
echo "Fetching latest N_m3u8DL-RE release..."
N_RE_URL=$(curl -s https://api.github.com/repos/nilaoda/N_m3u8DL-RE/releases/latest | grep "browser_download_url.*android-bionic-arm64.*tar.gz" | cut -d '"' -f 4 | head -n 1)
wget "$N_RE_URL" -O N_m3u8DL-RE.tar.gz
tar -xzf N_m3u8DL-RE.tar.gz
chmod +x N_m3u8DL-RE

# Download Bento4 mp4decrypt static binary (Android ARM64)
echo "Downloading mp4decrypt (Bento4)..."
wget -O mp4decrypt https://github.com/DavidMuhammad/bento4-static-builds/raw/main/android/mp4decrypt-arm64
chmod +x mp4decrypt

# Download gdrive CLI for uploads (Linux ARM64)
echo "Downloading gdrive CLI..."
wget -O gdrive https://github.com/prasmussen/gdrive/releases/download/2.1.1/gdrive-linux-arm64
chmod +x gdrive

# Add ~/tools to PATH for current and future sessions
if ! grep -q 'export PATH=$HOME/tools:$PATH' ~/.bashrc; then
    echo 'export PATH=$HOME/tools:$PATH' >> ~/.bashrc
fi
export PATH=$HOME/tools:$PATH

cd ~

echo -e "\n✅ All tools are installed! Please RESTART your Termux session or run:"
echo "source ~/.bashrc"
echo -e "\nTo verify, run: N_m3u8DL-RE --version ; mp4decrypt --version ; gdrive version ; ffmpeg -version"

echo -e "\nYou can now run your bot normally. All tools are in your PATH."
