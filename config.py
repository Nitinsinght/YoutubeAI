"""
config.py – Centralised configuration for the YoutubeAI pipeline.

All sensitive values are loaded from environment variables (never hard-coded).
Copy .env.example to .env and fill in your credentials before running.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Environment helper
# ---------------------------------------------------------------------------

def _require(name: str) -> str:
    """Return an environment variable value or raise a clear error."""
    value = os.environ.get(name)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{name}' is not set. "
            "See .env.example for the full list of required variables."
        )
    return value


def _optional(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


# ---------------------------------------------------------------------------
# Pipeline configuration dataclass
# ---------------------------------------------------------------------------

@dataclass
class PipelineConfig:
    # ── OpenAI ────────────────────────────────────────────────────────────
    openai_api_key: str = field(default_factory=lambda: _require("OPENAI_API_KEY"))
    openai_model: str = field(default_factory=lambda: _optional("OPENAI_MODEL", "gpt-4o"))

    # ── Video generation backend ──────────────────────────────────────────
    # Supported values: "runway", "pika", "stable_video"
    video_backend: str = field(
        default_factory=lambda: _optional("VIDEO_BACKEND", "runway")
    )

    # Runway ML
    runway_api_key: Optional[str] = field(
        default_factory=lambda: _optional("RUNWAY_API_KEY") or None
    )

    # Pika
    pika_api_key: Optional[str] = field(
        default_factory=lambda: _optional("PIKA_API_KEY") or None
    )

    # Stable Video Diffusion (local)
    svd_model_path: str = field(
        default_factory=lambda: _optional(
            "SVD_MODEL_PATH", "stabilityai/stable-video-diffusion-img2vid-xt"
        )
    )

    # ── Voice / TTS backend ───────────────────────────────────────────────
    # Supported values: "elevenlabs", "openai"
    tts_backend: str = field(
        default_factory=lambda: _optional("TTS_BACKEND", "openai")
    )

    # ElevenLabs
    elevenlabs_api_key: Optional[str] = field(
        default_factory=lambda: _optional("ELEVENLABS_API_KEY") or None
    )
    elevenlabs_voice_id: str = field(
        default_factory=lambda: _optional("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
    )

    # OpenAI TTS
    openai_tts_voice: str = field(
        default_factory=lambda: _optional("OPENAI_TTS_VOICE", "onyx")
    )

    # ── YouTube ───────────────────────────────────────────────────────────
    youtube_client_secrets_file: str = field(
        default_factory=lambda: _optional(
            "YOUTUBE_CLIENT_SECRETS_FILE", "client_secrets.json"
        )
    )
    youtube_token_file: str = field(
        default_factory=lambda: _optional("YOUTUBE_TOKEN_FILE", "youtube_token.json")
    )
    # Channel category ID (22 = People & Blogs; 24 = Entertainment)
    youtube_category_id: str = field(
        default_factory=lambda: _optional("YOUTUBE_CATEGORY_ID", "22")
    )

    # ── Scheduling ────────────────────────────────────────────────────────
    # How many Shorts to upload per day (10–20 recommended)
    uploads_per_day: int = field(
        default_factory=lambda: int(_optional("UPLOADS_PER_DAY", "12"))
    )

    # ── Output paths ──────────────────────────────────────────────────────
    output_dir: str = field(
        default_factory=lambda: _optional("OUTPUT_DIR", "output")
    )

    # ── Video dimensions ─────────────────────────────────────────────────
    video_width: int = 1080
    video_height: int = 1920

    # ── Content types ─────────────────────────────────────────────────────
    # Supported values: "curiosity", "suspense", "random"
    content_type: str = field(
        default_factory=lambda: _optional("CONTENT_TYPE", "random")
    )

    def __post_init__(self) -> None:
        os.makedirs(self.output_dir, exist_ok=True)
        self._validate_backends()

    def _validate_backends(self) -> None:
        valid_video = {"runway", "pika", "stable_video"}
        valid_tts = {"elevenlabs", "openai"}
        if self.video_backend not in valid_video:
            raise ValueError(
                f"VIDEO_BACKEND must be one of {valid_video}, got '{self.video_backend}'"
            )
        if self.tts_backend not in valid_tts:
            raise ValueError(
                f"TTS_BACKEND must be one of {valid_tts}, got '{self.tts_backend}'"
            )

    @property
    def seconds_between_uploads(self) -> float:
        """Interval in seconds between consecutive uploads."""
        return 86_400 / max(self.uploads_per_day, 1)


# Singleton – import this from all other modules
config = PipelineConfig()
