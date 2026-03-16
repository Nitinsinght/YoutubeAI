"""
upload_video.py – Upload a composed Short to YouTube via the Data API v3.

Authentication uses OAuth 2.0 with offline access.  On the first run the
script opens a browser for consent; subsequent runs use the saved token file
(YOUTUBE_TOKEN_FILE in .env).

References:
  https://developers.google.com/youtube/v3/guides/uploading_a_video
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from config import config

logger = logging.getLogger(__name__)

# OAuth 2.0 scopes required for upload
_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Maximum number of retry attempts for resumable uploads
_MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def _get_authenticated_service():
    """
    Return an authenticated YouTube API service object.

    Loads credentials from the token file if it exists, otherwise runs the
    OAuth flow and saves the credentials for future use.
    """
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError as exc:
        raise ImportError(
            "Google API client libraries are required for YouTube upload. "
            "Install with:\n"
            "  pip install google-api-python-client google-auth-oauthlib"
        ) from exc

    token_file = config.youtube_token_file
    secrets_file = config.youtube_client_secrets_file

    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, _SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(secrets_file):
                raise FileNotFoundError(
                    f"YouTube client secrets file not found: '{secrets_file}'. "
                    "Download it from https://console.cloud.google.com/ and "
                    "set YOUTUBE_CLIENT_SECRETS_FILE in your .env file."
                )
            flow = InstalledAppFlow.from_client_secrets_file(secrets_file, _SCOPES)
            creds = flow.run_local_server(port=0)

        with open(token_file, "w") as fh:
            fh.write(creds.to_json())
        logger.info("YouTube credentials saved to %s", token_file)

    return build("youtube", "v3", credentials=creds)


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def upload_to_youtube(
    video_path: Path,
    title: str,
    description: str,
    tags: list[str],
) -> str:
    """
    Upload a video file to YouTube and return the video ID.

    Parameters
    ----------
    video_path:
        Absolute path to the MP4 file to upload.
    title:
        Video title (≤ 100 chars).
    description:
        Video description with hashtags.
    tags:
        List of tag strings (without the # prefix).

    Returns
    -------
    YouTube video ID string (e.g. "dQw4w9WgXcQ").
    """
    try:
        from googleapiclient.http import MediaFileUpload
        from googleapiclient.errors import HttpError
    except ImportError as exc:
        raise ImportError(
            "google-api-python-client is required for YouTube upload."
        ) from exc

    youtube = _get_authenticated_service()

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags,
            "categoryId": config.youtube_category_id,
        },
        "status": {
            "privacyStatus": "public",
            # YouTube automatically classifies videos as Shorts based on
            # their duration (≤60 s) and vertical aspect ratio (9:16).
            # No extra metadata field is needed to request Short status.
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        str(video_path),
        mimetype="video/mp4",
        resumable=True,
        chunksize=4 * 1024 * 1024,  # 4 MB chunks
    )

    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )

    response = None
    attempt = 0
    while response is None:
        try:
            logger.info(
                "Uploading '%s' to YouTube (attempt %d)…",
                video_path.name,
                attempt + 1,
            )
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                logger.info("Upload progress: %d%%", pct)
        except Exception as exc:
            attempt += 1
            if attempt >= _MAX_RETRIES:
                raise RuntimeError(
                    f"YouTube upload failed after {_MAX_RETRIES} attempts: {exc}"
                ) from exc
            logger.warning("Upload error (attempt %d): %s – retrying…", attempt, exc)

    video_id = response["id"]
    logger.info(
        "Upload complete! Video ID: %s  URL: https://youtu.be/%s",
        video_id,
        video_id,
    )
    return video_id


# ---------------------------------------------------------------------------
# Convenience: build description from script
# ---------------------------------------------------------------------------

def build_description(script: dict) -> str:
    """
    Build a YouTube video description from a script dict.

    Includes the hashtags inline so they are indexed by YouTube.
    """
    hashtags = script.get("hashtags", [])
    tag_line = " ".join(
        h if h.startswith("#") else f"#{h}" for h in hashtags
    )
    parts = []

    if script.get("type") == "curiosity":
        parts.append(script.get("fact", ""))
    elif script.get("type") == "suspense":
        parts.append(script.get("hook", ""))
        parts.append(script.get("twist", ""))

    parts.append("")  # blank line before hashtags
    parts.append(tag_line)
    parts.append("#Shorts #YouTubeShorts")

    return "\n".join(p for p in parts if p is not None)
