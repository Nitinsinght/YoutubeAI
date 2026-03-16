# YoutubeAI

**Autonomous AI YouTube Shorts Production System**

A fully automated pipeline that generates, produces, and uploads high-quality YouTube Shorts videos without human intervention. The system creates original AI-generated videos, adds subtitles and narration, and uploads them automatically to YouTube.

## Features

- **AI Script Generation** — Generates viral video ideas, scripts, titles, and hashtags using OpenAI
- **AI Video Generation** — Creates original video scenes using Runway Gen, Pika, or Stable Video Diffusion
- **AI Voice Narration** — Natural-sounding narration using Microsoft Edge TTS
- **Video Composition** — Combines scenes with synchronized subtitles and narration
- **YouTube Upload** — Automated upload with titles, descriptions, and hashtags
- **Continuous Operation** — Runs as a bot producing 10–20 Shorts per day

## Content Types

### 1. Curiosity / Mind-Blowing Facts (6–10 seconds)

- Attention-grabbing hook
- AI-generated visual scene
- Surprising fact
- Optimized for looping

### 2. Suspense Micro-Stories (10–20 seconds)

- Hook that sets the scene
- Rising tension
- Resolution
- Unexpected twist

## Architecture

```
YoutubeAI/
├── config.py            # Configuration and environment settings
├── generate_script.py   # Script/idea generation using OpenAI
├── generate_video.py    # AI video generation (Runway/Pika/SVD)
├── generate_voice.py    # Voice narration with edge-tts
├── compose_video.py     # Video composition with subtitles
├── upload_video.py      # YouTube upload automation
├── run_bot.py           # Main automation loop
├── requirements.txt     # Python dependencies
├── .env.example         # Environment configuration template
└── tests/
    └── test_pipeline.py # Unit tests
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file and fill in your API keys:

```bash
cp .env.example .env
```

Required API keys:

| Key | Purpose |
|-----|---------|
| `OPENAI_API_KEY` | Script generation (required) |
| `RUNWAY_API_KEY` | Video generation with Runway (if using Runway) |
| `PIKA_API_KEY` | Video generation with Pika (if using Pika) |
| `SVD_API_URL` | Stable Video Diffusion endpoint (if using SVD) |

### 3. Set Up YouTube OAuth

1. Create a project in the [Google Cloud Console](https://console.cloud.google.com/)
2. Enable the YouTube Data API v3
3. Create OAuth 2.0 credentials (Desktop application)
4. Download the client secrets JSON file
5. Save it as `client_secrets.json` in the project root

### 4. Choose a Video Provider

Set `VIDEO_PROVIDER` in your `.env` file:

- `runway` — Runway Gen API
- `pika` — Pika API
- `stable_video_diffusion` — Local or remote SVD endpoint

## Usage

### Run the Bot

```bash
python run_bot.py
```

The bot will continuously:
1. Generate a video idea and script
2. Create AI video scenes from the script
3. Generate voice narration
4. Compose the final video with subtitles
5. Upload to YouTube
6. Wait the configured delay and repeat

### Configuration Options

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `PRODUCTION_DELAY_SECONDS` | `3600` | Seconds between video productions |
| `MAX_VIDEOS_PER_DAY` | `20` | Maximum videos to produce per day |
| `VOICE_NAME` | `en-US-GuyNeural` | TTS voice for narration |
| `VOICE_RATE` | `+0%` | Speech rate adjustment |
| `OUTPUT_DIR` | `output` | Directory for generated files |
| `OPENAI_MODEL` | `gpt-4` | OpenAI model for script generation |

## Testing

```bash
python -m unittest tests.test_pipeline -v
```

## Pipeline Flow

```
generate_script.py    →  Video idea + script + prompts
        ↓
generate_video.py     →  AI-generated video scenes
        ↓
generate_voice.py     →  Voice narration audio
        ↓
compose_video.py      →  Final video with subtitles + narration
        ↓
upload_video.py       →  Upload to YouTube Shorts
        ↓
run_bot.py            →  Wait → Repeat
```
