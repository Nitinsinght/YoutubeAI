# YoutubeAI — Complete Guide

This document explains **what was built**, **how to use it**, and **what to do next**.

---

## Table of Contents

- [What Was Built](#what-was-built)
  - [System Overview](#system-overview)
  - [Module-by-Module Breakdown](#module-by-module-breakdown)
  - [How the Pipeline Works](#how-the-pipeline-works)
- [How to Use This](#how-to-use-this)
  - [Prerequisites](#prerequisites)
  - [Step 1 — Install Dependencies](#step-1--install-dependencies)
  - [Step 2 — Get Your API Keys](#step-2--get-your-api-keys)
  - [Step 3 — Configure the Environment](#step-3--configure-the-environment)
  - [Step 4 — Set Up YouTube OAuth](#step-4--set-up-youtube-oauth)
  - [Step 5 — Run the Bot](#step-5--run-the-bot)
  - [Step 6 — Monitor and Verify](#step-6--monitor-and-verify)
  - [Running Individual Modules](#running-individual-modules)
  - [Running Tests](#running-tests)
- [What To Do Next](#what-to-do-next)
  - [Immediate Next Steps](#immediate-next-steps)
  - [Short-Term Improvements](#short-term-improvements)
  - [Advanced Features Roadmap](#advanced-features-roadmap)

---

## What Was Built

### System Overview

YoutubeAI is a **fully autonomous AI YouTube Shorts production system**. It is a Python pipeline that:

1. **Generates video ideas and scripts** using OpenAI (GPT-4)
2. **Creates AI video scenes** using Runway Gen, Pika, or Stable Video Diffusion
3. **Generates voice narration** using Microsoft Edge TTS (free, no API key needed)
4. **Composes final videos** with subtitles, narration, and vertical formatting (1080×1920)
5. **Uploads to YouTube** automatically via the YouTube Data API v3
6. **Loops continuously** — producing up to 20 Shorts per day on a schedule

The system produces two types of content:

| Type | Duration | Structure |
|------|----------|-----------|
| **Curiosity / Mind-Blowing Facts** | 6–10 seconds | Hook → Visual → Fact → Loop |
| **Suspense Micro-Stories** | 10–20 seconds | Hook → Tension → Resolution → Twist |

### Module-by-Module Breakdown

Here is every file in the project and exactly what it does:

#### `config.py` — Configuration Hub

Central configuration for the entire system. All settings come from environment variables (via a `.env` file) with sensible defaults.

**What it manages:**
- API keys (OpenAI, Runway, Pika)
- YouTube OAuth file paths
- Video dimensions (1080×1920), FPS (24), and duration ranges
- Voice settings (voice name, speaking rate)
- Subtitle styling (font size, colors, stroke)
- Output directory paths
- Scheduling (delay between videos, daily max)

**Key function:**
- `ensure_directories()` — creates `output/`, `output/audio/`, `output/videos/`, and `output/temp/` folders

#### `generate_script.py` — Script & Idea Generation

Uses the OpenAI API to generate complete video scripts. Sends carefully crafted system prompts that instruct GPT-4 to return structured JSON.

**What it generates:**
- Video title (max 70 characters, catchy)
- Hashtags (5–8 relevant tags)
- Script segments (hook, fact/tension/resolution/twist)
- AI video generation prompts (cinematic scene descriptions)
- Target duration

**Key functions:**
- `generate_script(content_type)` — generates a full script dict. Pass `"curiosity_fact"` or `"suspense_story"`, or `None` for random
- `generate_title_and_hashtags(script_data)` — extracts title and formatted hashtag string
- `build_narration_text(script_data)` — assembles all script segments into narration text

**Topic categories it picks from:** nature/animals, space, human body, history, ocean/deep sea, technology, psychology, ancient civilizations, weather, survival stories.

#### `generate_video.py` — AI Video Scene Generation

Creates video clips from the text prompts in the script. Supports three video generation providers:

| Provider | How it works | API Key needed |
|----------|-------------|---------------|
| **Runway Gen** | Cloud API — sends prompt, polls for completion, downloads result | `RUNWAY_API_KEY` |
| **Pika** | Cloud API — same pattern as Runway | `PIKA_API_KEY` |
| **Stable Video Diffusion** | Local/remote API endpoint — sends prompt, gets video back | `SVD_API_URL` (default: `localhost:7860`) |

**Key functions:**
- `generate_video(prompt, duration, output_path)` — generates one video clip from a text prompt
- `generate_video_scenes(script_data)` — generates all scenes for a script (1 scene for curiosity facts, 3 scenes for suspense stories)

For Runway/Pika, it uses async polling — submits the job, then polls every 10 seconds until done (up to 10 minutes timeout).

#### `generate_voice.py` — Voice Narration

Uses `edge-tts` (Microsoft Edge Text-to-Speech) to create natural-sounding voice narration. This is **free** and requires **no API key**.

**Key functions:**
- `generate_voice(text, output_path)` — generates an MP3 narration file from text
- `generate_voice_with_timestamps(text, output_path)` — same, but also returns word-level timestamps (useful for precise subtitle sync)
- `list_available_voices(language)` — lists all available TTS voices for a language

**Default voice:** `en-US-GuyNeural` (a natural-sounding male voice). Configurable via `VOICE_NAME` env var.

#### `compose_video.py` — Video Composition

Uses MoviePy v2 to combine everything into the final YouTube Short. This is where scenes, audio, and subtitles all come together.

**What it does:**
1. Loads all video scene clips
2. Resizes each to vertical format (1080×1920) — preserving aspect ratio with center-crop
3. Concatenates scenes (or loops a single scene to match audio length)
4. Overlays the narration audio
5. Creates subtitle text overlays positioned at 70% from top
6. Exports the final MP4 with H.264 video + AAC audio

**Key functions:**
- `compose_video(scene_paths, audio_path, script_data)` — standard composition with evenly-timed subtitles
- `compose_video_with_timestamps(scene_paths, audio_path, timestamps)` — precise subtitle timing using word-level timestamps

**Subtitle styling:** White text, black stroke, 60px font size, center-aligned, wrapped at 25 characters per line.

#### `upload_video.py` — YouTube Upload

Handles authentication and uploading to YouTube via the official YouTube Data API v3.

**What it does:**
1. Authenticates via OAuth 2.0 (first run opens a browser for consent, then caches the token)
2. Builds the video metadata (title, description, tags, category, privacy)
3. Uploads using resumable upload (10MB chunks) with exponential backoff retry (up to 5 retries)

**Key functions:**
- `get_youtube_service()` — authenticates and returns a YouTube API client
- `upload_video(video_path, title, description, tags)` — uploads a video file
- `build_description(script_data, hashtag_str)` — formats the YouTube description

#### `run_bot.py` — Main Automation Loop

The orchestrator that ties everything together and runs continuously.

**What it does:**
1. Calls `generate_script()` to get a script
2. Calls `generate_video_scenes()` to create AI video clips
3. Calls `generate_voice()` to create narration
4. Calls `compose_video()` to assemble the final video
5. Calls `upload_video()` to upload to YouTube
6. Waits the configured delay (default: 1 hour)
7. Repeats — up to 20 videos per day

**Error handling:** If any step fails, it logs the error, waits 60 seconds, and retries. The bot won't crash from a single failure.

**Daily limit:** Resets the video counter at midnight each day.

#### `tests/test_pipeline.py` — Unit Tests

25 unit tests covering all modules. All tests use mocking (no real API calls needed):

- **4 config tests** — directories, content types, dimensions, durations
- **7 script tests** — title/hashtag generation, narration text assembly, OpenAI integration
- **5 video tests** — provider validation, error handling, scene generation for both content types
- **3 upload tests** — file validation, description formatting
- **4 composition tests** — word grouping, subtitle creation
- **2 bot tests** — full pipeline integration

### How the Pipeline Works

Here is the exact data flow for one video production cycle:

```
┌─────────────────────────────────────────────────────────┐
│  run_bot.py — produce_and_upload_short()                │
│                                                         │
│  1. generate_script("curiosity_fact")                   │
│     └─→ OpenAI GPT-4 → returns JSON:                   │
│         {title, hashtags, hook, fact,                   │
│          visual_prompt, duration}                       │
│                                                         │
│  2. generate_video_scenes(script_data)                  │
│     └─→ Video API (Runway/Pika/SVD) → returns:         │
│         ["/output/videos/scene_abc123.mp4"]             │
│                                                         │
│  3. generate_voice(narration_text)                      │
│     └─→ edge-tts → returns:                            │
│         "/output/audio/voice_def456.mp3"                │
│                                                         │
│  4. compose_video(scenes, audio, script)                │
│     └─→ MoviePy → returns:                             │
│         "/output/videos/short_ghi789.mp4"               │
│                                                         │
│  5. upload_video(video_path, title, description)        │
│     └─→ YouTube API → returns:                         │
│         {"id": "youtube_video_id"}                      │
│                                                         │
│  6. Wait 1 hour → repeat                               │
└─────────────────────────────────────────────────────────┘
```

---

## How to Use This

### Prerequisites

- **Python 3.9+** installed
- **An OpenAI API key** (required — for script generation)
- **A video generation API** — at least one of:
  - Runway Gen API key (`RUNWAY_API_KEY`)
  - Pika API key (`PIKA_API_KEY`)
  - A running Stable Video Diffusion server (`SVD_API_URL`)
- **A Google Cloud project** with YouTube Data API v3 enabled (for uploading)
- **ffmpeg** installed on your system (used by MoviePy for video encoding)

### Step 1 — Install Dependencies

```bash
# Clone the repository
git clone https://github.com/Nitinsinght/YoutubeAI.git
cd YoutubeAI

# (Recommended) Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python packages
pip install -r requirements.txt
```

**Also install ffmpeg** (needed by MoviePy):
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows — download from https://ffmpeg.org/download.html
```

### Step 2 — Get Your API Keys

#### OpenAI (Required)
1. Go to https://platform.openai.com/api-keys
2. Create a new API key
3. Copy it — you'll need it in Step 3

#### Video Generation (Pick One)

**Option A: Runway Gen** (recommended for quality)
1. Sign up at https://runwayml.com/
2. Get your API key from the dashboard
3. Set `VIDEO_PROVIDER=runway` in your `.env`

**Option B: Pika**
1. Sign up at https://pika.art/
2. Get your API key
3. Set `VIDEO_PROVIDER=pika` in your `.env`

**Option C: Stable Video Diffusion** (free, self-hosted)
1. Set up a local SVD server (e.g., using ComfyUI or a custom API wrapper)
2. Make sure it's running at `http://localhost:7860/api/generate-video`
3. Set `VIDEO_PROVIDER=stable_video_diffusion` in your `.env`

#### YouTube Upload
1. Go to https://console.cloud.google.com/
2. Create a new project
3. Enable "YouTube Data API v3"
4. Go to Credentials → Create Credentials → OAuth 2.0 Client ID
5. Choose "Desktop application"
6. Download the JSON file and save it as `client_secrets.json` in the project root

### Step 3 — Configure the Environment

```bash
# Copy the template
cp .env.example .env

# Edit with your keys
nano .env  # or use any text editor
```

Fill in your `.env` file:

```ini
# Required
OPENAI_API_KEY=sk-your-actual-openai-key-here
OPENAI_MODEL=gpt-4

# Pick your video provider
VIDEO_PROVIDER=runway
RUNWAY_API_KEY=your-runway-key-here

# Scheduling
PRODUCTION_DELAY_SECONDS=3600   # 1 hour between videos
MAX_VIDEOS_PER_DAY=20           # target 10-20 per day

# Voice (optional — defaults work well)
VOICE_NAME=en-US-GuyNeural
VOICE_RATE=+0%
```

### Step 4 — Set Up YouTube OAuth

The first time you upload a video, the bot will open a browser window asking you to authorize access to your YouTube account.

1. Make sure `client_secrets.json` is in the project root
2. Run the bot (Step 5)
3. A browser window will open — sign in with the Google account that owns your YouTube channel
4. Click "Allow" to grant upload permissions
5. The bot saves the token to `youtube_token.json` — subsequent runs won't need the browser

> **Note:** If running on a server without a browser, you can run the auth flow once on your local machine, then copy the `youtube_token.json` file to the server.

### Step 5 — Run the Bot

```bash
python run_bot.py
```

You'll see output like:

```
2026-03-16 01:00:00,000 [INFO] Starting AI YouTube Shorts Bot
2026-03-16 01:00:00,001 [INFO] Max videos per day: 20, Delay between videos: 3600s
2026-03-16 01:00:00,002 [INFO] === Starting new Short production ===
2026-03-16 01:00:00,003 [INFO] Step 1: Generating script...
2026-03-16 01:00:02,500 [INFO] Script generated: Did You Know Sharks Are Older Than Trees?
2026-03-16 01:00:02,501 [INFO] Step 2: Generating video scenes...
2026-03-16 01:02:30,000 [INFO] Generated 1 scene(s)
2026-03-16 01:02:30,001 [INFO] Step 3: Generating voice narration...
2026-03-16 01:02:32,000 [INFO] Voice narration saved to: output/audio/voice_abc123.mp3
2026-03-16 01:02:32,001 [INFO] Step 4: Composing final video...
2026-03-16 01:02:45,000 [INFO] Final video saved to: output/videos/short_def456.mp4
2026-03-16 01:02:45,001 [INFO] Step 5: Uploading to YouTube...
2026-03-16 01:02:50,000 [INFO] Upload complete: https://youtube.com/shorts/AbCdEf12345
2026-03-16 01:02:50,001 [INFO] Videos produced today: 1 / 20
2026-03-16 01:02:50,002 [INFO] Waiting 3600 seconds before next production...
```

The bot will keep running, producing a new Short every hour until it hits the daily limit.

**To stop the bot:** Press `Ctrl+C`.

### Step 6 — Monitor and Verify

- **Check `bot.log`** for the full production log
- **Check `output/videos/`** for the generated video files
- **Check `output/audio/`** for the narration audio files
- **Check your YouTube Studio** to verify uploads

### Running Individual Modules

You can also run each step individually (useful for testing):

```python
# Generate just a script
from generate_script import generate_script, build_narration_text
script = generate_script(content_type="curiosity_fact")
print(script)

# Generate just the voice narration
from generate_voice import generate_voice
audio_path = generate_voice("Did you know sharks are older than trees?")

# List available voices
from generate_voice import list_available_voices
voices = list_available_voices("en")
for v in voices:
    print(f"{v['name']} ({v['gender']})")
```

### Running Tests

```bash
# Run all 25 tests
python -m unittest tests.test_pipeline -v

# Run tests for a specific module
python -m unittest tests.test_pipeline.TestGenerateScript -v
python -m unittest tests.test_pipeline.TestGenerateVideo -v
python -m unittest tests.test_pipeline.TestComposeVideo -v
python -m unittest tests.test_pipeline.TestUploadVideo -v
python -m unittest tests.test_pipeline.TestRunBot -v
```

---

## What To Do Next

### Immediate Next Steps

These are things you should do **right now** to get the bot running:

#### 1. Get API Keys and Test Each Module

Before running the full bot, test each module individually:

```bash
# Test script generation (requires OPENAI_API_KEY)
python -c "
from generate_script import generate_script
script = generate_script('curiosity_fact')
print(script)
"
```

```bash
# Test voice generation (no API key needed)
python -c "
from generate_voice import generate_voice
path = generate_voice('Did you know sharks are older than trees?')
print(f'Audio saved to: {path}')
"
```

```bash
# Test video generation (requires your chosen provider key)
python -c "
from generate_video import generate_video
path = generate_video('Cinematic shot of a shark swimming in a dark ocean', duration=6)
print(f'Video saved to: {path}')
"
```

#### 2. Do a Dry Run Without YouTube Upload

Modify `run_bot.py` temporarily to skip the upload step, so you can verify the generated videos look good before going live:

```python
# In run_bot.py, in produce_and_upload_short(), comment out Step 5:
# response = upload_video(...)
# Instead:
logger.info("SKIPPING UPLOAD — video ready at: %s", video_path)
```

#### 3. Set Up YouTube OAuth

Follow Step 4 above to get `client_secrets.json`. Run the bot once to complete the OAuth flow and generate `youtube_token.json`.

#### 4. Start with `privacy="unlisted"`

Before going fully public, change the default privacy in `upload_video.py`:

```python
def upload_video(video_path, title, description, tags=None,
                 category_id="22", privacy="unlisted"):  # Changed from "public"
```

Review your first few uploads in YouTube Studio, then switch to `"public"` when you're satisfied with the quality.

### Short-Term Improvements

These are improvements to make the system more robust:

#### 1. Add Analytics Tracking

Create a simple database (SQLite) to track what was produced:

```python
# Future: analytics.py
# Track: video_id, title, content_type, topic, upload_time, views, likes
```

This lets you see which topics and content types perform best.

#### 2. Add Content Deduplication

The script generator currently picks topics randomly. Add a history file to avoid repeating topics:

```python
# Future: Keep a log of previously used topics/titles
# Check before generating a new script to ensure variety
```

#### 3. Add Thumbnail Generation

YouTube Shorts benefit from custom thumbnails. Add a module that uses Pillow to create eye-catching thumbnails:

```python
# Future: generate_thumbnail.py
# Use Pillow to create a 1080x1920 thumbnail with:
# - A frame from the video
# - Large, bold text overlay
# - Eye-catching colors
```

#### 4. Add Error Recovery for Partial Failures

If video generation succeeds but upload fails, the current system loses the video. Add checkpointing:

```python
# Future: Save progress after each step
# If step 5 (upload) fails, don't redo steps 1-4
# Just retry the upload with the existing video file
```

#### 5. Add a Configuration Validation Check

Add a startup check that verifies all required API keys are set and valid before starting the bot loop.

### Advanced Features Roadmap

These are larger features for the future:

#### 1. Performance Analytics Integration

Connect to the YouTube Analytics API to track which videos perform best, then feed that data back into the script generator to optimize for views and engagement.

#### 2. A/B Testing for Hooks

Generate multiple hook variants for each video, upload them at different times, and track which hooks get the most views in the first hour.

#### 3. Trend-Based Topic Selection

Use Google Trends API or Twitter/X trending topics to generate videos about what people are currently interested in, instead of picking from a static topic list.

#### 4. Multi-Channel Support

Support uploading to multiple YouTube channels simultaneously, each with different content strategies (e.g., one for facts, one for stories).

#### 5. Web Dashboard

Build a simple web UI (Flask/FastAPI) that shows:
- Production queue and status
- Upload history with YouTube links
- Analytics and performance metrics
- Configuration controls

#### 6. Content Quality Scoring

Before uploading, run the generated video through a quality check:
- Is the video visually coherent?
- Does the narration match the visuals?
- Is the subtitle timing correct?
- Score the video and only upload if it passes a threshold.

#### 7. Automated Scheduling Optimization

Instead of uploading at fixed intervals, use YouTube Analytics to determine the best posting times for your audience and schedule uploads accordingly.

---

## File Quick Reference

| File | Purpose | Dependencies |
|------|---------|-------------|
| `config.py` | All settings | `python-dotenv` |
| `generate_script.py` | Script generation | `openai` |
| `generate_video.py` | Video generation | `requests` |
| `generate_voice.py` | Voice narration | `edge-tts` |
| `compose_video.py` | Video composition | `moviepy`, `Pillow` |
| `upload_video.py` | YouTube upload | `google-api-python-client`, `google-auth-oauthlib` |
| `run_bot.py` | Orchestration loop | All above modules |
| `tests/test_pipeline.py` | Unit tests (25) | `unittest`, `unittest.mock` |

## Environment Variables Quick Reference

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `OPENAI_API_KEY` | **Yes** | — | Script generation |
| `VIDEO_PROVIDER` | No | `stable_video_diffusion` | Which video AI to use |
| `RUNWAY_API_KEY` | If using Runway | — | Runway Gen API |
| `PIKA_API_KEY` | If using Pika | — | Pika API |
| `SVD_API_URL` | If using SVD | `http://localhost:7860/...` | SVD endpoint |
| `OPENAI_MODEL` | No | `gpt-4` | Which GPT model |
| `VOICE_NAME` | No | `en-US-GuyNeural` | TTS voice |
| `VOICE_RATE` | No | `+0%` | Speech speed |
| `PRODUCTION_DELAY_SECONDS` | No | `3600` | Seconds between videos |
| `MAX_VIDEOS_PER_DAY` | No | `20` | Daily upload cap |
| `OUTPUT_DIR` | No | `output` | Where files are saved |
