"""
compose_video.py – Combine AI video, narration, and subtitles into a final Short.

Pipeline:
  1. Resize / pad the raw AI video clip to 1080×1920 (vertical).
  2. Mix in the AI narration audio track.
  3. Burn subtitle captions onto the video (centred, bold, high-contrast).
  4. Export the final MP4 ready for upload.

Dependencies: moviepy, Pillow, numpy
  pip install moviepy Pillow numpy
"""

from __future__ import annotations

import logging
import math
import textwrap
import uuid
from pathlib import Path
from typing import Optional

from config import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Font / subtitle settings
# ---------------------------------------------------------------------------

SUBTITLE_FONT = "DejaVu-Sans-Bold"  # must be installed; fallback = "Arial"
SUBTITLE_FONT_SIZE = 72
SUBTITLE_COLOR = "white"
SUBTITLE_STROKE_COLOR = "black"
SUBTITLE_STROKE_WIDTH = 3
SUBTITLE_Y_POSITION = 0.75   # fraction of frame height from top
SUBTITLE_MAX_CHARS_PER_LINE = 28


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _final_output_path() -> Path:
    name = f"short_{uuid.uuid4().hex[:8]}.mp4"
    return Path(config.output_dir) / name


def _build_subtitle_clips(narration_text: str, total_duration: float, size: tuple):
    """
    Split the narration into subtitle segments and return a list of
    moviepy TextClip objects timed evenly across the video.
    """
    from moviepy.editor import TextClip

    words = narration_text.split()
    if not words:
        return []

    # Split into chunks of ~SUBTITLE_MAX_CHARS_PER_LINE characters
    lines: list[str] = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 <= SUBTITLE_MAX_CHARS_PER_LINE:
            current = (current + " " + word).strip()
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    if not lines:
        return []

    segment_duration = total_duration / len(lines)
    clips = []

    for i, line in enumerate(lines):
        start = i * segment_duration
        try:
            txt_clip = (
                TextClip(
                    line,
                    font=SUBTITLE_FONT,
                    fontsize=SUBTITLE_FONT_SIZE,
                    color=SUBTITLE_COLOR,
                    stroke_color=SUBTITLE_STROKE_COLOR,
                    stroke_width=SUBTITLE_STROKE_WIDTH,
                    method="caption",
                    size=(size[0] - 80, None),
                    align="center",
                )
                .set_start(start)
                .set_duration(segment_duration)
                .set_position(("center", SUBTITLE_Y_POSITION), relative=True)
            )
            clips.append(txt_clip)
        except (OSError, RuntimeError, AttributeError) as exc:  # pragma: no cover
            logger.warning("Could not render subtitle line '%s': %s", line, exc)

    return clips


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compose_short(
    video_path: Path,
    audio_path: Optional[Path],
    script: dict,
    output_path: Optional[Path] = None,
) -> Path:
    """
    Compose the final YouTube Short.

    Parameters
    ----------
    video_path:
        Path to the raw AI-generated video clip (any resolution / orientation).
    audio_path:
        Path to the narration MP3, or None to keep the original audio track.
    script:
        The script dict from generate_script – used for subtitle text and duration.
    output_path:
        Where to save the final video. If None, a unique path is generated.

    Returns
    -------
    Path to the composed 1080×1920 MP4 short.
    """
    try:
        from moviepy.editor import (
            VideoFileClip,
            AudioFileClip,
            CompositeVideoClip,
            CompositeAudioClip,
            concatenate_videoclips,
        )
    except ImportError as exc:
        raise ImportError(
            "moviepy is required for video composition. "
            "Install with: pip install moviepy"
        ) from exc

    target_w = config.video_width
    target_h = config.video_height
    target_duration: int = script.get("duration_seconds", 10)
    narration_text: str = script.get("narration", "")

    if output_path is None:
        output_path = _final_output_path()

    logger.info("Composing short from %s …", video_path.name)

    # ── 1. Load video ───────────────────────────────────────────────────
    clip = VideoFileClip(str(video_path))

    # ── 2. Resize to vertical 1080×1920 while preserving aspect ratio ──
    clip_aspect = clip.w / clip.h
    target_aspect = target_w / target_h

    if clip_aspect > target_aspect:
        # wider than needed → scale to height, crop sides
        clip = clip.resize(height=target_h)
        x_center = clip.w / 2
        clip = clip.crop(
            x1=x_center - target_w / 2,
            x2=x_center + target_w / 2,
            y1=0,
            y2=target_h,
        )
    else:
        # taller / narrower than needed → scale to width, crop top/bottom
        clip = clip.resize(width=target_w)
        y_center = clip.h / 2
        clip = clip.crop(
            x1=0,
            x2=target_w,
            y1=y_center - target_h / 2,
            y2=y_center + target_h / 2,
        )

    # ── 3. Loop or trim to target duration ──────────────────────────────
    if clip.duration < target_duration:
        # Loop the clip to fill the target duration
        n_loops = math.ceil(target_duration / clip.duration)
        clip = concatenate_videoclips([clip] * n_loops)
    clip = clip.subclip(0, target_duration)

    # ── 4. Audio: narration replaces original track ──────────────────────
    if audio_path and audio_path.exists():
        narration = AudioFileClip(str(audio_path))
        # Trim narration to video length if it overshoots
        if narration.duration > target_duration:
            narration = narration.subclip(0, target_duration)
        clip = clip.set_audio(narration)
    # else: keep original video audio (or silence)

    # ── 5. Burn subtitles ────────────────────────────────────────────────
    subtitle_clips = _build_subtitle_clips(
        narration_text,
        total_duration=target_duration,
        size=(target_w, target_h),
    )
    if subtitle_clips:
        final = CompositeVideoClip([clip] + subtitle_clips, size=(target_w, target_h))
    else:
        final = clip

    # ── 6. Export ────────────────────────────────────────────────────────
    final.write_videofile(
        str(output_path),
        codec="libx264",
        audio_codec="aac",
        fps=30,
        preset="fast",
        ffmpeg_params=["-crf", "23"],
        logger=None,
    )

    logger.info("Final short saved: %s", output_path)
    return output_path
