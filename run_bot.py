"""
run_bot.py – Main automation loop for the YoutubeAI pipeline.

Runs continuously, generating and uploading YouTube Shorts at the interval
configured by UPLOADS_PER_DAY (default 12 = every 2 hours).

Usage:
    python run_bot.py

Optional flags:
    --once          Run only one iteration then exit (useful for testing).
    --type TYPE     Force content type: "curiosity", "suspense", or "random".
    --dry-run       Generate and compose the video but skip the YouTube upload.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
import traceback
import uuid
from pathlib import Path

# ---------------------------------------------------------------------------
# Logging setup (must happen before config import)
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pipeline imports
# ---------------------------------------------------------------------------

from config import config
from generate_script import generate_script
from generate_video import generate_video
from generate_voice import generate_narration
from compose_video import compose_short
from upload_video import upload_to_youtube, build_description


# ---------------------------------------------------------------------------
# Single-video production pipeline
# ---------------------------------------------------------------------------

def produce_and_upload(content_type: str = "random", dry_run: bool = False) -> dict:
    """
    Run the full pipeline for one YouTube Short.

    Steps:
      1. Generate script (idea + narration + visual prompt)
      2. Generate AI video scene
      3. Generate AI voice narration
      4. Compose final 1080×1920 short (video + audio + subtitles)
      5. Upload to YouTube (unless dry_run=True)

    Returns
    -------
    dict with pipeline results including 'video_id' (if uploaded) and 'output_path'.
    """
    run_id = uuid.uuid4().hex[:6]
    logger.info("═══ Starting production run %s (type=%s) ═══", run_id, content_type)

    # ── Step 1: Script ──────────────────────────────────────────────────
    logger.info("[%s] Step 1/5 – Generating script…", run_id)
    script = generate_script(content_type)
    logger.info(
        "[%s] Script: type=%s, title='%s', duration=%ds",
        run_id,
        script.get("type"),
        script.get("title"),
        script.get("duration_seconds", 0),
    )

    # ── Step 2: AI Video ─────────────────────────────────────────────────
    logger.info("[%s] Step 2/5 – Generating AI video scene…", run_id)
    raw_video_path = generate_video(
        prompt=script["visual_prompt"],
        duration_seconds=script.get("duration_seconds", 10),
    )

    # ── Step 3: AI Voice ─────────────────────────────────────────────────
    logger.info("[%s] Step 3/5 – Generating AI voice narration…", run_id)
    audio_path = generate_narration(script["narration"])

    # ── Step 4: Compose ──────────────────────────────────────────────────
    logger.info("[%s] Step 4/5 – Composing final short…", run_id)
    final_video_path = compose_short(
        video_path=raw_video_path,
        audio_path=audio_path,
        script=script,
    )

    result = {
        "run_id": run_id,
        "script": script,
        "raw_video_path": str(raw_video_path),
        "audio_path": str(audio_path),
        "output_path": str(final_video_path),
        "video_id": None,
    }

    # ── Step 5: Upload ───────────────────────────────────────────────────
    if dry_run:
        logger.info("[%s] Step 5/5 – DRY RUN: skipping YouTube upload.", run_id)
    else:
        logger.info("[%s] Step 5/5 – Uploading to YouTube…", run_id)
        video_id = upload_to_youtube(
            video_path=final_video_path,
            title=script["title"],
            description=build_description(script),
            tags=[t.lstrip("#") for t in script.get("hashtags", [])],
        )
        result["video_id"] = video_id
        logger.info(
            "[%s] ✓ Short published: https://youtu.be/%s", run_id, video_id
        )

    logger.info("═══ Run %s complete ═══", run_id)
    return result


# ---------------------------------------------------------------------------
# Continuous loop
# ---------------------------------------------------------------------------

def run_loop(content_type: str = "random", dry_run: bool = False) -> None:
    """
    Run the pipeline in a continuous loop, respecting the configured schedule.

    The interval between uploads is:
        86400 / UPLOADS_PER_DAY  seconds

    Errors in individual runs are caught and logged; the loop always continues.
    """
    interval = config.seconds_between_uploads
    logger.info(
        "Starting YoutubeAI bot – %d shorts/day, interval=%.0fs, dry_run=%s",
        config.uploads_per_day,
        interval,
        dry_run,
    )

    consecutive_failures = 0
    max_consecutive_failures = 5

    while True:
        try:
            produce_and_upload(content_type=content_type, dry_run=dry_run)
            consecutive_failures = 0
        except KeyboardInterrupt:
            logger.info("Interrupted by user – shutting down.")
            sys.exit(0)
        except (RuntimeError, ValueError, OSError, IOError, ConnectionError):
            consecutive_failures += 1
            logger.error(
                "Pipeline run failed (consecutive failures: %d/%d):\n%s",
                consecutive_failures,
                max_consecutive_failures,
                traceback.format_exc(),
            )
            if consecutive_failures >= max_consecutive_failures:
                logger.critical(
                    "Too many consecutive failures (%d). Exiting.",
                    consecutive_failures,
                )
                sys.exit(1)

        logger.info("Sleeping %.0f seconds until next run…", interval)
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            logger.info("Interrupted during sleep – shutting down.")
            sys.exit(0)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="YoutubeAI – Autonomous YouTube Shorts production bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_bot.py                      # run forever (12 shorts/day)
  python run_bot.py --once               # produce & upload one short, then exit
  python run_bot.py --once --dry-run     # produce one short without uploading
  python run_bot.py --type curiosity     # force curiosity-facts content type
        """,
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Produce and upload exactly one Short then exit.",
    )
    parser.add_argument(
        "--type",
        dest="content_type",
        choices=["curiosity", "suspense", "random"],
        default=config.content_type,
        help="Content type to generate (default: %(default)s).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Generate and compose the video but skip the YouTube upload.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    if args.once:
        produce_and_upload(content_type=args.content_type, dry_run=args.dry_run)
    else:
        run_loop(content_type=args.content_type, dry_run=args.dry_run)
