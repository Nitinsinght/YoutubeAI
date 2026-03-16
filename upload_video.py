"""YouTube video upload automation.

Uses the YouTube Data API v3 to upload videos to YouTube Shorts
with auto-generated titles, descriptions, and tags.
"""

import os
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

import config

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_youtube_service():
    """Build and return an authenticated YouTube API service.

    Handles OAuth2 authentication flow, loading cached credentials
    from a token file or initiating a new auth flow if needed.

    Returns:
        googleapiclient.discovery.Resource: Authenticated YouTube
            API service object.
    """
    creds = None

    if os.path.exists(config.YOUTUBE_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(
            config.YOUTUBE_TOKEN_FILE, SCOPES
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                config.YOUTUBE_CLIENT_SECRETS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(config.YOUTUBE_TOKEN_FILE, "w") as token_file:
            token_file.write(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_video(video_path, title, description, tags=None,
                 category_id="22", privacy="public"):
    """Upload a video to YouTube.

    Args:
        video_path: Path to the video file to upload.
        title: Video title (max 100 characters).
        description: Video description.
        tags: List of tags for the video.
        category_id: YouTube category ID (default "22" for
            People & Blogs).
        privacy: Privacy status ("public", "private", "unlisted").

    Returns:
        dict: YouTube API response with video ID and details.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    youtube = get_youtube_service()

    if tags is None:
        tags = ["shorts", "viral", "ai"]

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": tags,
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=10 * 1024 * 1024,
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = _resumable_upload(request)

    return response


def _resumable_upload(request, max_retries=5):
    """Execute a resumable upload with retry logic.

    Args:
        request: The YouTube API upload request.
        max_retries: Maximum number of retry attempts.

    Returns:
        dict: YouTube API response on success.

    Raises:
        RuntimeError: If upload fails after all retries.
    """
    response = None
    retries = 0

    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                print(f"Upload progress: {progress}%")
        except Exception as e:
            retries += 1
            if retries > max_retries:
                raise RuntimeError(
                    f"Upload failed after {max_retries} retries: {e}"
                ) from e
            wait_time = 2 ** retries
            print(f"Upload error, retrying in {wait_time}s: {e}")
            time.sleep(wait_time)

    video_id = response.get("id", "unknown")
    print(f"Upload complete: https://youtube.com/shorts/{video_id}")

    return response


def build_description(script_data, hashtag_str):
    """Build a YouTube video description from script data.

    Args:
        script_data: Script dictionary from generate_script().
        hashtag_str: Formatted hashtag string.

    Returns:
        str: Formatted video description for YouTube.
    """
    content_type = script_data.get("content_type", "curiosity_fact")
    topic = script_data.get("topic", "")

    lines = []

    if content_type == "curiosity_fact":
        hook = script_data.get("hook", "")
        lines.append(hook)
        lines.append("")
        lines.append(f"Topic: {topic}")
    else:
        hook = script_data.get("hook", "")
        lines.append(hook)
        lines.append("")
        lines.append("Watch till the end! 😱")

    lines.append("")
    lines.append(hashtag_str)
    lines.append("#shorts #viral #ai")

    return "\n".join(lines)
