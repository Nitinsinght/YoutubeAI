"""AI video generation for YouTube Shorts.

Supports multiple video generation providers:
  - Runway Gen (API)
  - Pika (API)
  - Stable Video Diffusion (local/API)

Generates vertical format (1080x1920) video clips from text prompts.
"""

import os
import time
import uuid

import requests

import config


def generate_video(prompt, duration=6, output_path=None):
    """Generate a video clip from a text prompt.

    Args:
        prompt: Text description of the desired video scene.
        duration: Desired video duration in seconds.
        output_path: Path to save the generated video. If None,
            a path is auto-generated in the video output directory.

    Returns:
        str: Path to the generated video file.
    """
    config.ensure_directories()

    if output_path is None:
        video_id = uuid.uuid4().hex[:8]
        output_path = os.path.join(config.VIDEO_DIR, f"scene_{video_id}.mp4")

    provider = config.VIDEO_PROVIDER

    if provider == "runway":
        return _generate_with_runway(prompt, duration, output_path)
    elif provider == "pika":
        return _generate_with_pika(prompt, duration, output_path)
    elif provider == "stable_video_diffusion":
        return _generate_with_svd(prompt, duration, output_path)
    else:
        raise ValueError(f"Unsupported video provider: {provider}")


def generate_video_scenes(script_data, output_dir=None):
    """Generate all video scenes for a script.

    Args:
        script_data: Script dictionary from generate_script().
        output_dir: Directory to save scene videos. If None,
            uses the default video output directory.

    Returns:
        list[str]: Paths to the generated scene video files.
    """
    config.ensure_directories()

    if output_dir is None:
        output_dir = config.VIDEO_DIR

    content_type = script_data.get("content_type", "curiosity_fact")
    scene_paths = []

    if content_type == "curiosity_fact":
        prompt = script_data.get("visual_prompt", "")
        duration = script_data.get("duration", 8)
        scene_id = uuid.uuid4().hex[:8]
        path = os.path.join(output_dir, f"scene_{scene_id}.mp4")
        result = generate_video(prompt, duration=duration, output_path=path)
        scene_paths.append(result)
    else:
        prompts = script_data.get("visual_prompts", [])
        total_duration = script_data.get("duration", 15)
        scene_duration = max(3, total_duration // max(len(prompts), 1))

        for i, prompt in enumerate(prompts):
            scene_id = uuid.uuid4().hex[:8]
            path = os.path.join(output_dir, f"scene_{scene_id}_{i}.mp4")
            result = generate_video(
                prompt, duration=scene_duration, output_path=path
            )
            scene_paths.append(result)

    return scene_paths


def _generate_with_runway(prompt, duration, output_path):
    """Generate video using Runway Gen API.

    Args:
        prompt: Text description of the scene.
        duration: Desired duration in seconds.
        output_path: Path to save the video file.

    Returns:
        str: Path to the saved video file.
    """
    api_key = config.RUNWAY_API_KEY
    if not api_key:
        raise ValueError("RUNWAY_API_KEY is required for Runway provider")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "prompt": prompt,
        "duration": min(duration, 16),
        "width": config.VIDEO_WIDTH,
        "height": config.VIDEO_HEIGHT,
    }

    response = requests.post(
        "https://api.runwayml.com/v1/generate/video",
        headers=headers,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()

    task_id = response.json().get("id")

    return _poll_and_download(
        poll_url=f"https://api.runwayml.com/v1/tasks/{task_id}",
        headers=headers,
        output_path=output_path,
    )


def _generate_with_pika(prompt, duration, output_path):
    """Generate video using Pika API.

    Args:
        prompt: Text description of the scene.
        duration: Desired duration in seconds.
        output_path: Path to save the video file.

    Returns:
        str: Path to the saved video file.
    """
    api_key = config.PIKA_API_KEY
    if not api_key:
        raise ValueError("PIKA_API_KEY is required for Pika provider")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": "9:16",
    }

    response = requests.post(
        "https://api.pika.art/v1/generate",
        headers=headers,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()

    task_id = response.json().get("id")

    return _poll_and_download(
        poll_url=f"https://api.pika.art/v1/tasks/{task_id}",
        headers=headers,
        output_path=output_path,
    )


def _generate_with_svd(prompt, duration, output_path):
    """Generate video using Stable Video Diffusion (local API).

    Expects a local or remote SVD-compatible API endpoint.
    Set SVD_API_URL environment variable to configure.

    Args:
        prompt: Text description of the scene.
        duration: Desired duration in seconds.
        output_path: Path to save the video file.

    Returns:
        str: Path to the saved video file.
    """
    api_url = os.getenv(
        "SVD_API_URL", "http://localhost:7860/api/generate-video"
    )

    payload = {
        "prompt": prompt,
        "num_frames": duration * config.VIDEO_FPS,
        "width": config.VIDEO_WIDTH,
        "height": config.VIDEO_HEIGHT,
        "fps": config.VIDEO_FPS,
    }

    response = requests.post(api_url, json=payload, timeout=300)
    response.raise_for_status()

    result = response.json()

    video_url = result.get("video_url")
    if video_url:
        return _download_file(video_url, output_path)

    video_data = result.get("video_data")
    if video_data:
        import base64

        with open(output_path, "wb") as f:
            f.write(base64.b64decode(video_data))
        return output_path

    raise RuntimeError("SVD API did not return video data")


def _poll_and_download(poll_url, headers, output_path,
                       max_wait=600, interval=10):
    """Poll a task endpoint until complete, then download the result.

    Args:
        poll_url: URL to poll for task status.
        headers: HTTP headers for the request.
        output_path: Path to save the downloaded video.
        max_wait: Maximum seconds to wait for completion.
        interval: Seconds between poll requests.

    Returns:
        str: Path to the downloaded video file.

    Raises:
        TimeoutError: If the task does not complete within max_wait.
        RuntimeError: If the task fails.
    """
    elapsed = 0

    while elapsed < max_wait:
        response = requests.get(poll_url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        status = data.get("status", "").lower()

        if status in ("completed", "succeeded", "done"):
            video_url = (
                data.get("output", {}).get("video_url")
                or data.get("video_url")
                or data.get("result", {}).get("url")
            )
            if video_url:
                return _download_file(video_url, output_path)
            raise RuntimeError("Task completed but no video URL found")

        if status in ("failed", "error"):
            error_msg = data.get("error", "Unknown error")
            raise RuntimeError(f"Video generation failed: {error_msg}")

        time.sleep(interval)
        elapsed += interval

    raise TimeoutError(
        f"Video generation timed out after {max_wait} seconds"
    )


def _download_file(url, output_path):
    """Download a file from a URL.

    Args:
        url: The URL to download from.
        output_path: Path to save the downloaded file.

    Returns:
        str: Path to the saved file.
    """
    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()

    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    return output_path
