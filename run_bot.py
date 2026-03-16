"""Main automation loop for the AI YouTube Shorts production system.

Orchestrates the full pipeline:
  1. Generate video idea and script
  2. Generate AI video scenes
  3. Generate voice narration
  4. Compose final video with subtitles
  5. Upload to YouTube
  6. Wait and repeat

Run with: python run_bot.py
"""

import logging
import sys
import time
import traceback
from datetime import datetime, timedelta

import config
from compose_video import compose_video
from generate_script import (
    build_narration_text,
    generate_script,
    generate_title_and_hashtags,
)
from generate_video import generate_video_scenes
from generate_voice import generate_voice
from upload_video import build_description, upload_video

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", mode="a"),
    ],
)
logger = logging.getLogger(__name__)


def produce_and_upload_short(content_type=None):
    """Run the full production pipeline for one YouTube Short.

    Args:
        content_type: Either 'curiosity_fact' or 'suspense_story'.
            If None, a random type is chosen.

    Returns:
        dict: Upload response from YouTube API, or None on failure.
    """
    logger.info("=== Starting new Short production ===")

    # Step 1: Generate script
    logger.info("Step 1: Generating script...")
    script_data = generate_script(content_type=content_type)
    title, hashtag_str = generate_title_and_hashtags(script_data)
    logger.info("Script generated: %s", title)

    # Step 2: Generate video scenes
    logger.info("Step 2: Generating video scenes...")
    scene_paths = generate_video_scenes(script_data)
    logger.info("Generated %d scene(s)", len(scene_paths))

    # Step 3: Generate voice narration
    logger.info("Step 3: Generating voice narration...")
    narration_text = build_narration_text(script_data)
    audio_path = generate_voice(narration_text)
    logger.info("Voice narration saved to: %s", audio_path)

    # Step 4: Compose final video
    logger.info("Step 4: Composing final video...")
    video_path = compose_video(scene_paths, audio_path, script_data)
    logger.info("Final video saved to: %s", video_path)

    # Step 5: Upload to YouTube
    logger.info("Step 5: Uploading to YouTube...")
    description = build_description(script_data, hashtag_str)
    tags = [
        tag.lstrip("#")
        for tag in script_data.get("hashtags", ["shorts", "viral"])
    ]

    response = upload_video(
        video_path=video_path,
        title=title,
        description=description,
        tags=tags,
    )

    video_id = response.get("id", "unknown")
    logger.info(
        "Upload complete: https://youtube.com/shorts/%s", video_id
    )

    return response


def run_bot():
    """Run the main bot loop continuously.

    Produces and uploads YouTube Shorts on a schedule, respecting
    the daily maximum video limit and configured delay between
    productions.
    """
    logger.info("Starting AI YouTube Shorts Bot")
    logger.info(
        "Max videos per day: %d, Delay between videos: %ds",
        config.MAX_VIDEOS_PER_DAY,
        config.PRODUCTION_DELAY_SECONDS,
    )

    config.ensure_directories()

    videos_today = 0
    day_start = datetime.now().date()

    while True:
        current_date = datetime.now().date()

        if current_date != day_start:
            videos_today = 0
            day_start = current_date
            logger.info("New day started, resetting video count")

        if videos_today >= config.MAX_VIDEOS_PER_DAY:
            tomorrow = datetime.combine(
                current_date + timedelta(days=1),
                datetime.min.time(),
            )
            wait_seconds = (tomorrow - datetime.now()).total_seconds()
            logger.info(
                "Daily limit reached (%d videos). Waiting %.0f seconds "
                "until tomorrow.",
                videos_today,
                wait_seconds,
            )
            time.sleep(max(wait_seconds, 60))
            continue

        try:
            produce_and_upload_short()
            videos_today += 1
            logger.info(
                "Videos produced today: %d / %d",
                videos_today,
                config.MAX_VIDEOS_PER_DAY,
            )
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
        except Exception:
            logger.error(
                "Error during production: %s", traceback.format_exc()
            )
            logger.info("Waiting 60 seconds before retrying...")
            time.sleep(60)
            continue

        if videos_today < config.MAX_VIDEOS_PER_DAY:
            logger.info(
                "Waiting %d seconds before next production...",
                config.PRODUCTION_DELAY_SECONDS,
            )
            time.sleep(config.PRODUCTION_DELAY_SECONDS)


if __name__ == "__main__":
    run_bot()
