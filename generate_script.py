"""
generate_script.py – AI-powered script generation for YouTube Shorts.

Produces two content types:
  • curiosity  – mind-blowing fact videos (6–10 s)
  • suspense   – micro-story suspense clips (10–20 s)

Each script is returned as a structured dict consumed by the rest of
the pipeline.
"""

from __future__ import annotations

import json
import logging
import random
from typing import Literal

from openai import OpenAI

from config import config

logger = logging.getLogger(__name__)

ContentType = Literal["curiosity", "suspense"]

# ---------------------------------------------------------------------------
# Topic banks (used as seeds; GPT expands on them)
# ---------------------------------------------------------------------------

_CURIOSITY_SEEDS = [
    "deep sea creatures", "ancient civilisations", "space exploration",
    "animal superpowers", "human body mysteries", "quantum physics facts",
    "prehistoric Earth", "extreme weather", "ocean mysteries",
    "strange natural phenomena", "mind-bending mathematics",
    "bizarre animal behaviours", "lost ancient technologies",
    "incredible survival stories", "weird science discoveries",
]

_SUSPENSE_SEEDS = [
    "wildlife encounter gone wrong", "haunted house exploration",
    "lost in the wilderness", "shark diving adventure",
    "midnight train mystery", "avalanche survival",
    "abandoned hospital at night", "swimming with crocodiles",
    "close call on a mountain", "deep cave exploration",
    "lightning storm at sea", "wolf pack encounter",
    "car breakdown in the desert", "night safari gone silent",
    "mysterious figure in the fog",
]

# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_CURIOSITY_SYSTEM = """
You are a viral YouTube Shorts scriptwriter specialising in mind-blowing curiosity facts.
Write concise, punchy scripts optimised for a 6–10 second vertical video that loops perfectly.
Always respond with valid JSON only – no markdown fences, no extra text.
"""

_CURIOSITY_USER = """
Topic seed: {topic}

Write a YouTube Shorts curiosity-fact script with the following JSON structure:
{{
  "type": "curiosity",
  "title": "<catchy title ≤60 chars>",
  "hashtags": ["<5-8 relevant hashtags>"],
  "hook": "<2-second spoken hook that grabs attention instantly>",
  "fact": "<one mind-blowing fact, 1-2 sentences>",
  "loop_cta": "<short loop call-to-action, e.g. 'Watch again – did you catch that?'>",
  "narration": "<full spoken script combining hook + fact + cta, ≤40 words>",
  "visual_prompt": "<detailed cinematic prompt for AI video generation, vertical 1080x1920>",
  "duration_seconds": <integer 6-10>
}}
"""

_SUSPENSE_SYSTEM = """
You are a viral YouTube Shorts scriptwriter specialising in suspenseful micro-stories.
Write gripping, cinematic scripts optimised for a 10–20 second vertical video.
Always respond with valid JSON only – no markdown fences, no extra text.
"""

_SUSPENSE_USER = """
Scenario seed: {topic}

Write a YouTube Shorts suspense micro-story script with the following JSON structure:
{{
  "type": "suspense",
  "title": "<catchy title ≤60 chars>",
  "hashtags": ["<5-8 relevant hashtags>"],
  "hook": "<spoken hook sentence that teases the danger/mystery>",
  "tension": "<one sentence escalating the danger>",
  "resolution": "<one sentence calm action taken>",
  "twist": "<surprising twist ending, 1 sentence>",
  "narration": "<full spoken script: hook + tension + resolution + twist, ≤80 words>",
  "visual_prompt": "<detailed cinematic prompt for AI video generation, vertical 1080x1920>",
  "duration_seconds": <integer 10-20>
}}
"""

# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------

def _call_openai(system: str, user: str) -> dict:
    """Call the OpenAI chat API and parse the JSON response."""
    client = OpenAI(api_key=config.openai_api_key)
    response = client.chat.completions.create(
        model=config.openai_model,
        messages=[
            {"role": "system", "content": system.strip()},
            {"role": "user", "content": user.strip()},
        ],
        response_format={"type": "json_object"},
        temperature=0.9,
    )
    raw = response.choices[0].message.content
    return json.loads(raw)


def generate_curiosity_script(topic: str | None = None) -> dict:
    """
    Generate a curiosity / mind-blowing facts script.

    Parameters
    ----------
    topic:
        Optional seed topic. If None, one is chosen at random.

    Returns
    -------
    dict with keys: type, title, hashtags, hook, fact, loop_cta,
                    narration, visual_prompt, duration_seconds
    """
    seed = topic or random.choice(_CURIOSITY_SEEDS)
    logger.info("Generating curiosity script for topic: %s", seed)
    script = _call_openai(
        _CURIOSITY_SYSTEM,
        _CURIOSITY_USER.format(topic=seed),
    )
    script.setdefault("type", "curiosity")
    return script


def generate_suspense_script(topic: str | None = None) -> dict:
    """
    Generate a suspense micro-story script.

    Parameters
    ----------
    topic:
        Optional seed scenario. If None, one is chosen at random.

    Returns
    -------
    dict with keys: type, title, hashtags, hook, tension, resolution,
                    twist, narration, visual_prompt, duration_seconds
    """
    seed = topic or random.choice(_SUSPENSE_SEEDS)
    logger.info("Generating suspense script for topic: %s", seed)
    script = _call_openai(
        _SUSPENSE_SYSTEM,
        _SUSPENSE_USER.format(topic=seed),
    )
    script.setdefault("type", "suspense")
    return script


def generate_script(content_type: ContentType | Literal["random"] = "random") -> dict:
    """
    High-level entry point that dispatches to the correct generator.

    Parameters
    ----------
    content_type:
        "curiosity", "suspense", or "random" (50/50 chance).
    """
    if content_type == "random":
        content_type = random.choice(["curiosity", "suspense"])

    if content_type == "curiosity":
        return generate_curiosity_script()
    elif content_type == "suspense":
        return generate_suspense_script()
    else:
        raise ValueError(f"Unknown content_type: '{content_type}'")
