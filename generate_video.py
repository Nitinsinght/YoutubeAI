"""
generate_video.py – AI video scene generation for YouTube Shorts.

Supports three backends selected via the VIDEO_BACKEND environment variable:
  • "runway"        – Runway ML Gen-3 Alpha (cloud API)
  • "pika"          – Pika 1.0 (cloud API)
  • "stable_video"  – Stable Video Diffusion (local / HuggingFace)

The public interface is a single function:

    video_path = generate_video(prompt, duration_seconds)

The result is a vertical (1080×1920) MP4 clip saved to the output directory.
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from pathlib import Path
from typing import Optional

import requests

from config import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _output_path(suffix: str = "") -> Path:
    name = f"scene_{uuid.uuid4().hex[:8]}{suffix}.mp4"
    return Path(config.output_dir) / name


# ---------------------------------------------------------------------------
# Runway ML backend
# ---------------------------------------------------------------------------

_RUNWAY_API_BASE = "https://api.dev.runwayml.com/v1"
_RUNWAY_POLL_INTERVAL = 5   # seconds between status polls
_RUNWAY_TIMEOUT = 300       # maximum wait time in seconds


def _generate_runway(prompt: str, duration: int) -> Path:
    """
    Generate a video clip using the Runway ML Gen-3 Alpha API.

    Runway Gen-3 Alpha Turbo supports 5 s and 10 s durations.
    We snap the requested duration to the nearest supported value.
    """
    api_key = config.runway_api_key
    if not api_key:
        raise EnvironmentError(
            "RUNWAY_API_KEY is required when VIDEO_BACKEND='runway'."
        )

    # Runway supports 5 s or 10 s; clamp to nearest
    runway_duration = 5 if duration <= 7 else 10

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Runway-Version": "2024-11-06",
    }

    # Create generation task
    payload = {
        "model": "gen3a_turbo",
        "promptText": prompt,
        "duration": runway_duration,
        "ratio": "768:1344",  # closest 9:16 Runway supports
    }
    resp = requests.post(
        f"{_RUNWAY_API_BASE}/image_to_video",
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    task_id = resp.json()["id"]
    logger.info("Runway task created: %s", task_id)

    # Poll until complete
    deadline = time.time() + _RUNWAY_TIMEOUT
    while time.time() < deadline:
        time.sleep(_RUNWAY_POLL_INTERVAL)
        status_resp = requests.get(
            f"{_RUNWAY_API_BASE}/tasks/{task_id}",
            headers=headers,
            timeout=15,
        )
        status_resp.raise_for_status()
        data = status_resp.json()
        status = data.get("status")
        logger.debug("Runway task %s status: %s", task_id, status)

        if status == "SUCCEEDED":
            video_url = data["output"][0]
            return _download_video(video_url)
        elif status in {"FAILED", "CANCELLED"}:
            raise RuntimeError(
                f"Runway generation failed for task {task_id}: {data.get('failure', '')}"
            )

    raise TimeoutError(f"Runway task {task_id} did not complete within {_RUNWAY_TIMEOUT}s")


# ---------------------------------------------------------------------------
# Pika backend
# ---------------------------------------------------------------------------

_PIKA_API_BASE = "https://api.pika.art/v1"
_PIKA_POLL_INTERVAL = 5
_PIKA_TIMEOUT = 300


def _generate_pika(prompt: str, duration: int) -> Path:
    """Generate a video clip using the Pika 1.0 API."""
    api_key = config.pika_api_key
    if not api_key:
        raise EnvironmentError(
            "PIKA_API_KEY is required when VIDEO_BACKEND='pika'."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "options": {
            "aspectRatio": "9:16",
            "frameRate": 24,
            "duration": min(max(duration, 3), 15),  # Pika supports 3–15 s
        },
    }
    resp = requests.post(
        f"{_PIKA_API_BASE}/generate",
        headers=headers,
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    job_id = resp.json()["id"]
    logger.info("Pika job created: %s", job_id)

    deadline = time.time() + _PIKA_TIMEOUT
    while time.time() < deadline:
        time.sleep(_PIKA_POLL_INTERVAL)
        status_resp = requests.get(
            f"{_PIKA_API_BASE}/jobs/{job_id}",
            headers=headers,
            timeout=15,
        )
        status_resp.raise_for_status()
        data = status_resp.json()
        status = data.get("status")
        logger.debug("Pika job %s status: %s", job_id, status)

        if status == "completed":
            video_url = data["result"]["url"]
            return _download_video(video_url)
        elif status == "failed":
            raise RuntimeError(
                f"Pika generation failed for job {job_id}: {data.get('error', '')}"
            )

    raise TimeoutError(f"Pika job {job_id} did not complete within {_PIKA_TIMEOUT}s")


# ---------------------------------------------------------------------------
# Stable Video Diffusion (local) backend
# ---------------------------------------------------------------------------

def _generate_stable_video(prompt: str, duration: int) -> Path:
    """
    Generate a video using Stable Video Diffusion locally via diffusers.

    The pipeline works in two stages:
      1. Generate a still image from the text prompt with SDXL.
      2. Animate the image with SVD-XT.

    Requires: torch, diffusers, transformers, accelerate, Pillow
    """
    try:
        import torch
        from diffusers import StableVideoDiffusionPipeline, DiffusionPipeline
        from PIL import Image
    except ImportError as exc:
        raise ImportError(
            "The 'stable_video' backend requires: torch, diffusers, transformers, "
            "accelerate, Pillow. Install them with:\n"
            "  pip install torch diffusers transformers accelerate Pillow"
        ) from exc

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    # Stage 1 – text-to-image with SDXL
    logger.info("Generating seed image with SDXL (device=%s)…", device)
    sdxl_pipe = DiffusionPipeline.from_pretrained(
        "stabilityai/stable-diffusion-xl-base-1.0",
        torch_dtype=dtype,
        use_safetensors=True,
        variant="fp16" if device == "cuda" else None,
    ).to(device)
    sdxl_pipe.set_progress_bar_config(disable=True)

    image: Image.Image = sdxl_pipe(
        prompt=prompt,
        num_inference_steps=30,
        height=1024,
        width=576,
    ).images[0]

    del sdxl_pipe
    if device == "cuda":
        torch.cuda.empty_cache()

    # Stage 2 – image-to-video with SVD-XT
    logger.info("Animating image with Stable Video Diffusion…")
    svd_pipe = StableVideoDiffusionPipeline.from_pretrained(
        config.svd_model_path,
        torch_dtype=dtype,
        variant="fp16" if device == "cuda" else None,
    ).to(device)
    svd_pipe.set_progress_bar_config(disable=True)

    # SVD-XT produces 25 base frames at 6 fps ≈ 4 s of video.
    # For each additional second beyond 4 s we add 6 more frames (1 s × 6 fps),
    # capped at 50 frames to stay within GPU memory limits.
    num_frames = min(25 + (duration - 4) * 6, 50)

    frames = svd_pipe(
        image,
        num_frames=num_frames,
        num_inference_steps=25,
        decode_chunk_size=8,
    ).frames[0]

    out_path = _output_path()
    _save_frames_as_video(frames, out_path, fps=6)
    logger.info("SVD video saved: %s", out_path)
    return out_path


def _save_frames_as_video(frames: list, out_path: Path, fps: int = 6) -> None:
    """Convert a list of PIL Images to an MP4 using imageio."""
    try:
        import imageio
        import numpy as np
    except ImportError as exc:
        raise ImportError(
            "imageio and numpy are required to save SVD frames. "
            "Install with: pip install imageio[ffmpeg] numpy"
        ) from exc

    with imageio.get_writer(str(out_path), fps=fps, codec="libx264") as writer:
        for frame in frames:
            writer.append_data(np.array(frame))


# ---------------------------------------------------------------------------
# Download helper
# ---------------------------------------------------------------------------

def _download_video(url: str) -> Path:
    """Download a video from a URL and save it to the output directory."""
    out_path = _output_path()
    logger.info("Downloading generated video from %s", url)
    with requests.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with open(out_path, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=8192):
                fh.write(chunk)
    logger.info("Video saved: %s", out_path)
    return out_path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_video(prompt: str, duration_seconds: int = 10) -> Path:
    """
    Generate a vertical (1080×1920) AI video clip.

    Parameters
    ----------
    prompt:
        Detailed cinematic prompt describing the scene.
    duration_seconds:
        Desired clip length in seconds (6–20).

    Returns
    -------
    Path to the generated MP4 file inside the output directory.
    """
    backend = config.video_backend
    logger.info(
        "Generating video with backend='%s', duration=%ds, prompt='%s'",
        backend,
        duration_seconds,
        prompt[:80],
    )

    if backend == "runway":
        return _generate_runway(prompt, duration_seconds)
    elif backend == "pika":
        return _generate_pika(prompt, duration_seconds)
    elif backend == "stable_video":
        return _generate_stable_video(prompt, duration_seconds)
    else:
        raise ValueError(f"Unknown video backend: '{backend}'")
