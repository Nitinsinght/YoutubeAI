"""AI voice narration generation for YouTube Shorts.

Uses edge-tts (Microsoft Edge Text-to-Speech) to generate
natural-sounding voice narration from script text.
"""

import asyncio
import os
import uuid

import edge_tts

import config


def generate_voice(text, output_path=None, voice=None, rate=None):
    """Generate voice narration audio from text.

    Args:
        text: The narration text to convert to speech.
        output_path: Path to save the audio file. If None,
            a path is auto-generated in the audio output directory.
        voice: The voice name to use. Defaults to config.VOICE_NAME.
        rate: Speech rate adjustment (e.g., '+10%', '-5%').
            Defaults to config.VOICE_RATE.

    Returns:
        str: Path to the generated audio file.
    """
    config.ensure_directories()

    if output_path is None:
        audio_id = uuid.uuid4().hex[:8]
        output_path = os.path.join(config.AUDIO_DIR, f"voice_{audio_id}.mp3")

    if voice is None:
        voice = config.VOICE_NAME

    if rate is None:
        rate = config.VOICE_RATE

    asyncio.run(_generate_voice_async(text, output_path, voice, rate))

    return output_path


async def _generate_voice_async(text, output_path, voice, rate):
    """Async implementation of voice generation.

    Args:
        text: The narration text.
        output_path: Path to save the audio file.
        voice: The TTS voice name.
        rate: Speech rate adjustment string.
    """
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)


def generate_voice_with_timestamps(text, output_path=None, voice=None,
                                   rate=None):
    """Generate voice narration with word-level timestamps.

    Useful for precisely syncing subtitles with narration.

    Args:
        text: The narration text to convert to speech.
        output_path: Path to save the audio file. If None,
            a path is auto-generated.
        voice: The voice name to use.
        rate: Speech rate adjustment.

    Returns:
        tuple: (audio_path, word_timestamps) where word_timestamps
            is a list of dicts with 'text', 'start', and 'end' keys
            (times in seconds).
    """
    config.ensure_directories()

    if output_path is None:
        audio_id = uuid.uuid4().hex[:8]
        output_path = os.path.join(config.AUDIO_DIR, f"voice_{audio_id}.mp3")

    if voice is None:
        voice = config.VOICE_NAME

    if rate is None:
        rate = config.VOICE_RATE

    timestamps = asyncio.run(
        _generate_voice_with_timestamps_async(
            text, output_path, voice, rate
        )
    )

    return output_path, timestamps


async def _generate_voice_with_timestamps_async(text, output_path,
                                                voice, rate):
    """Async implementation of voice generation with timestamps.

    Args:
        text: The narration text.
        output_path: Path to save the audio file.
        voice: The TTS voice name.
        rate: Speech rate adjustment string.

    Returns:
        list[dict]: Word-level timestamps with 'text', 'start',
            and 'end' keys.
    """
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    timestamps = []

    with open(output_path, "wb") as audio_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_file.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                timestamps.append({
                    "text": chunk["text"],
                    "start": chunk["offset"] / 10_000_000,
                    "end": (chunk["offset"] + chunk["duration"]) / 10_000_000,
                })

    return timestamps


def list_available_voices(language="en"):
    """List available TTS voices for a given language.

    Args:
        language: Language code prefix to filter voices (e.g., 'en').

    Returns:
        list[dict]: Available voices with 'name', 'gender',
            and 'locale' keys.
    """
    voices = asyncio.run(edge_tts.list_voices())
    return [
        {
            "name": v["ShortName"],
            "gender": v["Gender"],
            "locale": v["Locale"],
        }
        for v in voices
        if v["Locale"].startswith(language)
    ]
