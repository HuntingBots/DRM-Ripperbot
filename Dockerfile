FROM python:3.9-slim

# Install dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    aria2 \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Bento4
RUN wget https://www.bento4.com/downloads/Bento4-SDK-1-6-0-641.x86_64-unknown-linux.zip \
    && unzip Bento4-SDK-*.zip \
    && cp Bento4-SDK-*/bin/mp4decrypt /usr/local/bin/ \
    && rm -rf Bento4-SDK-*

# Setup app
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN pip install -U https://github.com/aarubui/yt-dlp-mp4decrypt/archive/master.zip

COPY . .

# Run bot
CMD ["python3", "bot.py"]
