#!/bin/bash
# setup_drm_ripperbot.sh - Enhanced for key support

set -e

echo "🚀 Setting up DRM-RipperBot with MPD Key Support..."
echo "=================================================="

# Update system
echo "🔄 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install Python dependencies
echo "🐍 Installing Python and pip..."
sudo apt-get install -y python3 python3-pip python3-venv

# Create virtual environment
echo "📁 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python packages
echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Install yt-dlp-mp4decrypt plugin
echo "🔌 Installing yt-dlp-mp4decrypt plugin..."
pip install -U https://github.com/aarubui/yt-dlp-mp4decrypt/archive/master.zip

# Install additional packages for key support
echo "🔑 Installing key support packages..."
pip install cryptography pycryptodome

# Install Bento4 (mp4decrypt)
echo "🔐 Installing Bento4 for mp4decrypt..."
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "📥 Downloading Bento4 for Linux..."
    wget -q https://www.bento4.com/downloads/Bento4-SDK-1-6-0-641.x86_64-unknown-linux.zip
    unzip -q Bento4-SDK-*.zip
    sudo cp Bento4-SDK-*/bin/mp4decrypt /usr/local/bin/
    sudo cp Bento4-SDK-*/bin/mp4info /usr/local/bin/
    sudo chmod +x /usr/local/bin/mp4decrypt
    rm -rf Bento4-SDK-*
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo "📥 Installing Bento4 via Homebrew..."
    brew install bento4
else
    echo "⚠️ Unsupported OS. Please install Bento4 manually:"
    echo "   https://www.bento4.com/downloads/"
fi

# Install aria2 for faster downloads
echo "⚡ Installing aria2 for faster downloads..."
sudo apt-get install -y aria2

# Install ffmpeg
echo "🎬 Installing ffmpeg..."
sudo apt-get install -y ffmpeg

# Create directories
echo "📂 Creating directories..."
mkdir -p downloads logs cache temp temp_keys
mkdir -p auth

# Set permissions
echo "🔒 Setting permissions..."
chmod +x bot.py
chmod +x setup_drm_ripperbot.sh
chmod 700 temp_keys  # Secure directory for keys

# Create example config
if [ ! -f config.py ]; then
    echo "⚙️ Creating config.py.example..."
    cat > config.py.example << 'EOF'
# Bot Configuration
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
ADMIN_IDS = [123456789]

# DRM Configuration
WVD_FILE_PATH = "/path/to/your/cdm.wvd"  # Optional for mp4decrypt plugin

# MPD/DASH Key Support
ALLOW_DIRECT_KEYS = True
KEY_VALIDATION = True
AUTO_EXTRACT_KEYS = True

# Quality Presets
QUALITY_PRESETS = {
    "best": "bestvideo+bestaudio/best",
    "1080p": "bestvideo[height<=1080]+bestaudio/best",
    "720p": "bestvideo[height<=720]+bestaudio/best",
    "480p": "bestvideo[height<=480]+bestaudio/best",
}

# Upload Configuration
ENABLE_GDRIVE = False
GDRIVE_CREDENTIALS_PATH = "auth/client_secrets.json"

# Security
REQUIRE_AUTH = True
MAX_KEYS_PER_REQUEST = 5
EOF
    echo "⚠️ Please copy config.py.example to config.py and edit it"
fi

echo ""
echo "✅ **Setup Complete!**"
echo ""
echo "📋 **Key Features Installed:**"
echo "   • yt-dlp with mp4decrypt plugin"
echo "   • Bento4 (mp4decrypt binary)"
echo "   • Direct key support (kid:key format)"
echo "   • Key extraction from URLs"
echo ""
echo "🚀 **Start the bot:**"
echo "   source venv/bin/activate && python bot.py"
echo ""
echo "🔑 **Test Key Format:**"
echo "   /testkey 87d54d841e2348b2969a66137522aedd:dc4df1cd96827c90fd05829ef8ed0a0f"
echo ""
echo "📚 **Example Usage:**"
echo "   /mpdkey https://example.com/stream.mpd 87d54d841e2348b2969a66137522aedd:dc4df1cd96827c90fd05829ef8ed0a0f 720p"
