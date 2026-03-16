"""Script and idea generation for AI YouTube Shorts.

Uses OpenAI (or compatible) API to generate video ideas, scripts,
titles, and hashtags for two content types:
  1. Curiosity / Mind-Blowing Facts
  2. Suspense Micro-Stories
"""

import json
import random

from openai import OpenAI

import config

CURIOSITY_SYSTEM_PROMPT = """You are a viral YouTube Shorts script writer.
Generate a short curiosity/mind-blowing fact video script.

Return a JSON object with these exact keys:
{
  "title": "catchy YouTube Shorts title (max 70 chars)",
  "hashtags": ["relevant", "hashtags", "5-8 tags"],
  "hook": "attention-grabbing opening line (first 2 seconds)",
  "fact": "the surprising fact or statement",
  "visual_prompt": "detailed AI video generation prompt for the visual scene, cinematic, vertical format",
  "duration": <number between 6 and 10>
}

Rules:
- Hook must be extremely attention-grabbing
- Fact must be genuinely surprising and accurate
- Visual prompt should describe a cinematic, visually stunning scene
- Optimized for looping (ending connects back to beginning)
- Keep it concise and punchy"""

SUSPENSE_SYSTEM_PROMPT = """You are a viral YouTube Shorts script writer.
Generate a suspense micro-story video script.

Return a JSON object with these exact keys:
{
  "title": "catchy YouTube Shorts title (max 70 chars)",
  "hashtags": ["relevant", "hashtags", "5-8 tags"],
  "hook": "attention-grabbing opening line that sets the scene",
  "tension": "the rising tension or conflict",
  "resolution": "what the characters did",
  "twist": "unexpected ending or twist",
  "visual_prompts": [
    "detailed AI video generation prompt for hook scene",
    "detailed AI video generation prompt for tension scene",
    "detailed AI video generation prompt for resolution/twist scene"
  ],
  "duration": <number between 10 and 20>
}

Rules:
- Hook must immediately grab attention
- Build genuine suspense and curiosity
- Twist should be surprising but satisfying
- Visual prompts should describe cinematic scenes, dramatic lighting
- Each visual prompt is for a vertical format video scene
- Keep the story concise and engaging"""

TOPIC_CATEGORIES = [
    "nature and animals",
    "space and universe",
    "human body",
    "history",
    "ocean and deep sea",
    "technology",
    "psychology",
    "ancient civilizations",
    "weather and natural phenomena",
    "survival stories",
]


def generate_script(content_type=None):
    """Generate a video script for the specified content type.

    Args:
        content_type: Either 'curiosity_fact' or 'suspense_story'.
            If None, a random type is chosen.

    Returns:
        dict: The generated script data including title, hashtags,
            and scene descriptions.
    """
    if content_type is None:
        content_type = random.choice(config.CONTENT_TYPES)

    topic = random.choice(TOPIC_CATEGORIES)

    client = OpenAI(api_key=config.OPENAI_API_KEY)

    if content_type == "curiosity_fact":
        system_prompt = CURIOSITY_SYSTEM_PROMPT
        user_prompt = (
            f"Generate a curiosity/mind-blowing fact video about: {topic}. "
            "Make it viral-worthy and visually stunning."
        )
    else:
        system_prompt = SUSPENSE_SYSTEM_PROMPT
        user_prompt = (
            f"Generate a suspense micro-story video related to: {topic}. "
            "Make it thrilling and cinematic."
        )

    response = client.chat.completions.create(
        model=config.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.9,
        response_format={"type": "json_object"},
    )

    script_data = json.loads(response.choices[0].message.content)
    script_data["content_type"] = content_type
    script_data["topic"] = topic

    return script_data


def generate_title_and_hashtags(script_data):
    """Extract title and hashtags from script data.

    Args:
        script_data: The script dictionary from generate_script().

    Returns:
        tuple: (title, hashtags_string) ready for YouTube upload.
    """
    title = script_data.get("title", "Amazing Shorts #shorts")
    hashtags = script_data.get("hashtags", ["shorts", "viral", "facts"])

    hashtag_str = " ".join(
        f"#{tag.lstrip('#')}" for tag in hashtags
    )

    return title, hashtag_str


def build_narration_text(script_data):
    """Build the full narration text from script data.

    Args:
        script_data: The script dictionary from generate_script().

    Returns:
        str: The complete narration text for voice generation.
    """
    content_type = script_data.get("content_type", "curiosity_fact")

    if content_type == "curiosity_fact":
        parts = [
            script_data.get("hook", ""),
            script_data.get("fact", ""),
        ]
    else:
        parts = [
            script_data.get("hook", ""),
            script_data.get("tension", ""),
            script_data.get("resolution", ""),
            script_data.get("twist", ""),
        ]

    return " ".join(part for part in parts if part)
