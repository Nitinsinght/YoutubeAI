"""
generate_voice.py – AI voice narration (TTS) for YouTube Shorts.

Supports two backends selected via the TTS_BACKEND environment variable:
  • "openai"      – OpenAI TTS (tts-1 / tts-1-hd)
  • "elevenlabs"  – ElevenLabs streaming TTS

The public interface is a single function:

    audio_path = generate_narration(text)

The result is an MP3 file saved to the output directory.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from config import config

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _audio_output_path() -> Path:
    name = f"narration_{uuid.uuid4().hex[:8]}.mp3"
    return Path(config.output_dir) / name


# ---------------------------------------------------------------------------
# OpenAI TTS backend
# ---------------------------------------------------------------------------

def _generate_openai_tts(text: str) -> Path:
    """
    Generate narration audio using the OpenAI TTS API.

    Uses the tts-1 model by default (low latency). Switch to tts-1-hd
    via OPENAI_TTS_MODEL for higher quality at slightly more cost.
    """
    import os
    from openai import OpenAI

    client = OpenAI(api_key=config.openai_api_key)
    model = os.environ.get("OPENAI_TTS_MODEL", "tts-1")
    voice = config.openai_tts_voice

    logger.info("Generating TTS with OpenAI (model=%s, voice=%s)", model, voice)

    response = client.audio.speech.create(
        model=model,
        voice=voice,
        input=text,
        response_format="mp3",
    )

    out_path = _audio_output_path()
    response.stream_to_file(str(out_path))
    logger.info("OpenAI TTS saved: %s", out_path)
    return out_path


# ---------------------------------------------------------------------------
# ElevenLabs backend
# ---------------------------------------------------------------------------

def _generate_elevenlabs_tts(text: str) -> Path:
    """
    Generate narration audio using the ElevenLabs streaming TTS API.

    Requires the `elevenlabs` Python package:
        pip install elevenlabs
    """
    try:
        from elevenlabs.client import ElevenLabs
        from elevenlabs import save
    except ImportError as exc:
        raise ImportError(
            "The 'elevenlabs' backend requires the elevenlabs package. "
            "Install with: pip install elevenlabs"
        ) from exc

    api_key = config.elevenlabs_api_key
    if not api_key:
        raise EnvironmentError(
            "ELEVENLABS_API_KEY is required when TTS_BACKEND='elevenlabs'."
        )

    voice_id = config.elevenlabs_voice_id
    logger.info("Generating TTS with ElevenLabs (voice_id=%s)", voice_id)

    client = ElevenLabs(api_key=api_key)
    audio = client.generate(
        text=text,
        voice=voice_id,
        model="eleven_turbo_v2",
    )

    out_path = _audio_output_path()
    save(audio, str(out_path))
    logger.info("ElevenLabs TTS saved: %s", out_path)
    return out_path


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_narration(text: str) -> Path:
    """
    Convert script narration text to an MP3 audio file.

    Parameters
    ----------
    text:
        The spoken narration text (≤ 80 words recommended for Shorts).

    Returns
    -------
    Path to the generated MP3 file inside the output directory.
    """
    backend = config.tts_backend
    logger.info(
        "Generating narration with backend='%s', text='%s…'",
        backend,
        text[:60],
    )

    if backend == "openai":
        return _generate_openai_tts(text)
    elif backend == "elevenlabs":
        return _generate_elevenlabs_tts(text)
    else:
        raise ValueError(f"Unknown TTS backend: '{backend}'")
