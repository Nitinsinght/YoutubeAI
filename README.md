# YoutubeAI – Autonomous AI YouTube Shorts Factory

An end-to-end pipeline that **generates, produces, and uploads YouTube Shorts automatically** using AI video generation models, GPT-4o scripts, and AI voice narration — with no human intervention required.

---

## Features

| Capability | Details |
|---|---|
| **Script generation** | GPT-4o writes punchy curiosity-fact or suspense micro-story scripts with viral hooks |
| **AI video generation** | Runway ML Gen-3, Pika 1.0, or local Stable Video Diffusion |
| **AI voice narration** | OpenAI TTS or ElevenLabs |
| **Subtitle burning** | Centred captions auto-timed to narration |
| **Vertical format** | All output is 1080 × 1920 (YouTube Shorts / TikTok) |
| **Auto-upload** | YouTube Data API v3 with OAuth 2.0 |
| **Scheduling** | Configurable cadence (default 12 Shorts per day) |
| **Continuous loop** | Runs forever, recovering from transient errors |

---

## Repository Structure

```
YoutubeAI/
├── config.py            # Centralised configuration (reads .env)
├── generate_script.py   # AI script generation (curiosity & suspense)
├── generate_video.py    # AI video scene generation (Runway / Pika / SVD)
├── generate_voice.py    # AI voice narration (OpenAI TTS / ElevenLabs)
├── compose_video.py     # Video composition: resize → loop → audio → subtitles
├── upload_video.py      # YouTube Data API v3 upload
├── run_bot.py           # Main automation loop
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
└── tests/               # Unit tests (no API keys required)
    ├── test_config.py
    ├── test_generate_script.py
    └── test_upload_video.py
```

---

## Quick Start

### 1. Clone and install dependencies

```bash
git clone https://github.com/Nitinsinght/YoutubeAI.git
cd YoutubeAI
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in your API keys (see Configuration section below)
```

### 3. Set up YouTube OAuth

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a project and enable the **YouTube Data API v3**.
3. Create an **OAuth 2.0 Client ID** (Desktop app type).
4. Download the JSON file and save it as `client_secrets.json` (or the path set in `YOUTUBE_CLIENT_SECRETS_FILE`).

### 4. Run the bot

```bash
# Run continuously (default: 12 Shorts/day)
python run_bot.py

# Produce and upload exactly one Short, then exit
python run_bot.py --once

# Generate and compose without uploading (useful for testing)
python run_bot.py --once --dry-run

# Force a specific content type
python run_bot.py --type curiosity
python run_bot.py --type suspense
```

---

## Content Types

### Curiosity / Mind-Blowing Facts (6–10 s)

```
HOOK   → "Did you know sharks existed before trees?"
VISUAL → AI-generated prehistoric ocean scene
FACT   → "Sharks have existed for over 400 million years."
LOOP   → "Watch again – did you catch that?"
```

### Suspense Micro-Stories (10–20 s)

```
HOOK       → "Two girls were driving through a safari road."
TENSION    → "A lion suddenly started walking toward their car."
VISUAL     → Cinematic lion-approaching-car scene
RESOLUTION → "They stayed calm and locked the doors."
TWIST      → "The lion circled the car… then walked away."
```

---

## Configuration

Copy `.env.example` to `.env` and set the following variables:

### Required

| Variable | Description |
|---|---|
| `OPENAI_API_KEY` | OpenAI API key (GPT-4o + TTS) |

### Video Generation (choose one backend)

| Variable | Description |
|---|---|
| `VIDEO_BACKEND` | `runway` (default), `pika`, or `stable_video` |
| `RUNWAY_API_KEY` | Runway ML API key (required if `VIDEO_BACKEND=runway`) |
| `PIKA_API_KEY` | Pika API key (required if `VIDEO_BACKEND=pika`) |
| `SVD_MODEL_PATH` | HuggingFace model ID for SVD (required if `VIDEO_BACKEND=stable_video`) |

### Voice / TTS (choose one backend)

| Variable | Description |
|---|---|
| `TTS_BACKEND` | `openai` (default) or `elevenlabs` |
| `OPENAI_TTS_VOICE` | `onyx`, `alloy`, `echo`, `fable`, `nova`, `shimmer` |
| `ELEVENLABS_API_KEY` | ElevenLabs API key (required if `TTS_BACKEND=elevenlabs`) |
| `ELEVENLABS_VOICE_ID` | ElevenLabs voice ID |

### YouTube

| Variable | Description |
|---|---|
| `YOUTUBE_CLIENT_SECRETS_FILE` | Path to OAuth 2.0 client secrets JSON |
| `YOUTUBE_TOKEN_FILE` | Where to cache the OAuth token (auto-created) |
| `YOUTUBE_CATEGORY_ID` | Category ID (`22`=People & Blogs, `24`=Entertainment) |

### Scheduling & Output

| Variable | Default | Description |
|---|---|---|
| `UPLOADS_PER_DAY` | `12` | Shorts to upload per day (10–20 recommended) |
| `CONTENT_TYPE` | `random` | `curiosity`, `suspense`, or `random` |
| `OUTPUT_DIR` | `output` | Directory for generated files |

---

## Optional: Stable Video Diffusion (local GPU)

To run fully offline with a local GPU:

```bash
pip install torch diffusers transformers accelerate "imageio[ffmpeg]"
# Then set in .env:
# VIDEO_BACKEND=stable_video
# SVD_MODEL_PATH=stabilityai/stable-video-diffusion-img2vid-xt
```

Requires a GPU with at least 12 GB VRAM for float16 inference.

---

## Running Tests

```bash
pip install pytest
python -m pytest tests/ -v
```

Tests are fully mocked — no API keys are needed to run them.

---

## Pipeline Overview

```
generate_script()        # GPT-4o → structured script dict
      ↓
generate_video()         # Runway/Pika/SVD → raw MP4 scene
      ↓
generate_narration()     # OpenAI TTS/ElevenLabs → MP3 audio
      ↓
compose_short()          # resize → loop → merge audio → burn subtitles → 1080×1920 MP4
      ↓
upload_to_youtube()      # YouTube Data API v3 → public Short
      ↓
sleep(86400 / UPLOADS_PER_DAY)
      ↓
repeat ∞
```

---

## License

MIT
