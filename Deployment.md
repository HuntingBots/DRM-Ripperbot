echo ""
echo "========= 7. Final instructions ========="
echo "✅ All tools and bot source are installed!"

## 🔐 MPD/DASH with Key Support

### Key Format
The bot supports keys in the following formats:
- **Hex format**: `kid:key` (32 hex characters each)
  Example: `87d54d841e2348b2969a66137522aedd:dc4df1cd96827c90fd05829ef8ed0a0f`
- **Alternative**: `kid=key`
- **URL parameters**: `?key=87d54d841e2348b2969a66137522aedd:dc4df1cd96827c90fd05829ef8ed0a0f`

### Commands
```bash
# Download with explicit key
/mpdkey <url> <key> [quality]

# Test key format
/testkey 87d54d841e2348b2969a66137522aedd:dc4df1cd96827c90fd05829ef8ed0a0f

# Extract keys from URL
/extractkey https://example.com/stream.mpd?key=87d54d841e2348b2969a66137522aedd:dc4df1cd96827c90fd05829ef8ed0a0f

# Regular MPD download (uses WVD if available)
/mpd <url> [quality]

echo ""
echo "1. Edit your bot config file and set your Telegram bot token and other settings:"
echo "   nano ~/DRM-Ripperbot/config.py"
echo ""
echo "2. Start your bot:"
echo "   cd ~/DRM-Ripperbot && python3 bot.py && git token - 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 && Username - HuntingBots"
echo ""
echo "To verify tools, run: N_m3u8DL-RE --version ; mp4decrypt --version ; gdrive version ; ffmpeg -version"
echo ""
echo "If you want to update the bot: cd ~/DRM-Ripperbot && git pull"
echo ""
echo "Enjoy your DRM-Ripperbot Telegram bot!"
