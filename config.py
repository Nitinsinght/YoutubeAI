"""Configuration management for the AI YouTube Shorts production system."""

import os
from dotenv import load_dotenv

load_dotenv()


# --- API Keys ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
RUNWAY_API_KEY = os.getenv("RUNWAY_API_KEY", "")
PIKA_API_KEY = os.getenv("PIKA_API_KEY", "")

# --- YouTube OAuth ---
YOUTUBE_CLIENT_SECRETS_FILE = os.getenv(
    "YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json"
)
YOUTUBE_TOKEN_FILE = os.getenv("YOUTUBE_TOKEN_FILE", "youtube_token.json")

# --- Video settings ---
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
VIDEO_FPS = 24

# --- Content settings ---
CONTENT_TYPES = ["curiosity_fact", "suspense_story"]

# Curiosity / Mind-Blowing Facts: 6-10 seconds
CURIOSITY_DURATION_MIN = 6
CURIOSITY_DURATION_MAX = 10

# Suspense Micro-Stories: 10-20 seconds
SUSPENSE_DURATION_MIN = 10
SUSPENSE_DURATION_MAX = 20

# --- Video generation provider ---
# Options: "runway", "pika", "stable_video_diffusion"
VIDEO_PROVIDER = os.getenv("VIDEO_PROVIDER", "stable_video_diffusion")

# --- Voice settings ---
VOICE_NAME = os.getenv("VOICE_NAME", "en-US-GuyNeural")
VOICE_RATE = os.getenv("VOICE_RATE", "+0%")

# --- Subtitle settings ---
SUBTITLE_FONT_SIZE = 60
SUBTITLE_FONT_COLOR = "white"
SUBTITLE_STROKE_COLOR = "black"
SUBTITLE_STROKE_WIDTH = 3
SUBTITLE_POSITION = "center"

# --- Output directories ---
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output")
AUDIO_DIR = os.path.join(OUTPUT_DIR, "audio")
VIDEO_DIR = os.path.join(OUTPUT_DIR, "videos")
TEMP_DIR = os.path.join(OUTPUT_DIR, "temp")

# --- Scheduling ---
# Delay between video productions in seconds (default: 1 hour)
PRODUCTION_DELAY_SECONDS = int(os.getenv("PRODUCTION_DELAY_SECONDS", "3600"))
# Maximum videos per day
MAX_VIDEOS_PER_DAY = int(os.getenv("MAX_VIDEOS_PER_DAY", "20"))

# --- OpenAI model ---
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")


def ensure_directories():
    """Create output directories if they don't exist."""
    for directory in [OUTPUT_DIR, AUDIO_DIR, VIDEO_DIR, TEMP_DIR]:
        os.makedirs(directory, exist_ok=True)
