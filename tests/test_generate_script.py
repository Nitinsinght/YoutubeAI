"""
tests/test_generate_script.py – Unit tests for generate_script.py.

All OpenAI API calls are mocked so the tests run without credentials.
"""

from __future__ import annotations

import json
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Mock the openai package before importing the module under test
# ---------------------------------------------------------------------------

def _make_openai_mock(response_json: dict):
    """Return a mock openai module that yields a fixed JSON response."""
    choice = MagicMock()
    choice.message.content = json.dumps(response_json)
    completion = MagicMock()
    completion.choices = [choice]

    client_instance = MagicMock()
    client_instance.chat.completions.create.return_value = completion

    openai_mod = types.ModuleType("openai")
    openai_mod.OpenAI = MagicMock(return_value=client_instance)
    return openai_mod, client_instance


# ---------------------------------------------------------------------------
# Minimal config mock so we don't need a real .env
# ---------------------------------------------------------------------------

_CONFIG_ATTRS = {
    "openai_api_key": "sk-test",
    "openai_model": "gpt-4o",
    "video_backend": "runway",
    "tts_backend": "openai",
    "output_dir": "/tmp/youtubeai_test",
    "video_width": 1080,
    "video_height": 1920,
    "uploads_per_day": 12,
    "content_type": "random",
    "seconds_between_uploads": 7200.0,
}

config_mock = MagicMock(**_CONFIG_ATTRS)


class TestGenerateCuriosityScript(unittest.TestCase):

    _SAMPLE_CURIOSITY = {
        "type": "curiosity",
        "title": "Sharks Existed Before Trees!",
        "hashtags": ["#sharks", "#nature", "#facts"],
        "hook": "Did you know sharks existed before trees?",
        "fact": "Sharks have existed for over 400 million years.",
        "loop_cta": "Watch again!",
        "narration": "Did you know sharks existed before trees? Sharks have existed for over 400 million years. Watch again!",
        "visual_prompt": "Cinematic underwater shot of a shark in a prehistoric ocean.",
        "duration_seconds": 8,
    }

    def setUp(self):
        self.openai_mod, self.client = _make_openai_mock(self._SAMPLE_CURIOSITY)

    def tearDown(self):
        for mod in ["openai", "config", "generate_script"]:
            sys.modules.pop(mod, None)

    def test_returns_dict_with_required_keys(self):
        config_mod = types.ModuleType("config")
        config_mod.config = config_mock
        with patch.dict(sys.modules, {"openai": self.openai_mod, "config": config_mod}):
            import importlib
            gs = importlib.import_module("generate_script")
            script = gs.generate_curiosity_script("sharks")

        required_keys = {"type", "title", "hashtags", "hook", "fact",
                         "loop_cta", "narration", "visual_prompt", "duration_seconds"}
        self.assertTrue(required_keys.issubset(script.keys()))

    def test_type_is_curiosity(self):
        config_mod = types.ModuleType("config")
        config_mod.config = config_mock
        with patch.dict(sys.modules, {"openai": self.openai_mod, "config": config_mod}):
            import importlib
            gs = importlib.import_module("generate_script")
            script = gs.generate_curiosity_script("sharks")

        self.assertEqual(script["type"], "curiosity")

    def test_duration_in_valid_range(self):
        config_mod = types.ModuleType("config")
        config_mod.config = config_mock
        with patch.dict(sys.modules, {"openai": self.openai_mod, "config": config_mod}):
            import importlib
            gs = importlib.import_module("generate_script")
            script = gs.generate_curiosity_script("sharks")

        self.assertGreaterEqual(script["duration_seconds"], 6)
        self.assertLessEqual(script["duration_seconds"], 10)


class TestGenerateSuspenseScript(unittest.TestCase):

    _SAMPLE_SUSPENSE = {
        "type": "suspense",
        "title": "Lion vs Safari Car",
        "hashtags": ["#lion", "#safari", "#wildlife"],
        "hook": "Two girls were driving through a safari road.",
        "tension": "A lion suddenly started walking toward their car.",
        "resolution": "They stayed calm and locked the doors.",
        "twist": "The lion circled the car… then walked away.",
        "narration": (
            "Two girls were driving through a safari road. "
            "A lion suddenly started walking toward their car. "
            "They stayed calm and locked the doors. "
            "The lion circled the car… then walked away."
        ),
        "visual_prompt": "Cinematic shot of a lion slowly approaching a safari car.",
        "duration_seconds": 15,
    }

    def setUp(self):
        self.openai_mod, self.client = _make_openai_mock(self._SAMPLE_SUSPENSE)

    def tearDown(self):
        for mod in ["openai", "config", "generate_script"]:
            sys.modules.pop(mod, None)

    def test_returns_dict_with_required_keys(self):
        config_mod = types.ModuleType("config")
        config_mod.config = config_mock
        with patch.dict(sys.modules, {"openai": self.openai_mod, "config": config_mod}):
            import importlib
            gs = importlib.import_module("generate_script")
            script = gs.generate_suspense_script("lion encounter")

        required_keys = {"type", "title", "hashtags", "hook", "tension",
                         "resolution", "twist", "narration", "visual_prompt",
                         "duration_seconds"}
        self.assertTrue(required_keys.issubset(script.keys()))

    def test_type_is_suspense(self):
        config_mod = types.ModuleType("config")
        config_mod.config = config_mock
        with patch.dict(sys.modules, {"openai": self.openai_mod, "config": config_mod}):
            import importlib
            gs = importlib.import_module("generate_script")
            script = gs.generate_suspense_script("lion encounter")

        self.assertEqual(script["type"], "suspense")

    def test_duration_in_valid_range(self):
        config_mod = types.ModuleType("config")
        config_mod.config = config_mock
        with patch.dict(sys.modules, {"openai": self.openai_mod, "config": config_mod}):
            import importlib
            gs = importlib.import_module("generate_script")
            script = gs.generate_suspense_script("lion encounter")

        self.assertGreaterEqual(script["duration_seconds"], 10)
        self.assertLessEqual(script["duration_seconds"], 20)


class TestGenerateScriptDispatch(unittest.TestCase):

    _CURIOSITY = {
        "type": "curiosity",
        "title": "Amazing Fact",
        "hashtags": [],
        "hook": "Wow!",
        "fact": "Interesting.",
        "loop_cta": "Watch again!",
        "narration": "Wow! Interesting. Watch again!",
        "visual_prompt": "Nice visual.",
        "duration_seconds": 7,
    }

    def setUp(self):
        self.openai_mod, self.client = _make_openai_mock(self._CURIOSITY)

    def tearDown(self):
        for mod in ["openai", "config", "generate_script"]:
            sys.modules.pop(mod, None)

    def test_generate_script_curiosity(self):
        config_mod = types.ModuleType("config")
        config_mod.config = config_mock
        with patch.dict(sys.modules, {"openai": self.openai_mod, "config": config_mod}):
            import importlib
            gs = importlib.import_module("generate_script")
            script = gs.generate_script("curiosity")
        self.assertEqual(script["type"], "curiosity")

    def test_generate_script_random_returns_dict(self):
        config_mod = types.ModuleType("config")
        config_mod.config = config_mock
        with patch.dict(sys.modules, {"openai": self.openai_mod, "config": config_mod}):
            import importlib
            gs = importlib.import_module("generate_script")
            script = gs.generate_script("random")
        self.assertIsInstance(script, dict)

    def test_generate_script_invalid_type_raises(self):
        config_mod = types.ModuleType("config")
        config_mod.config = config_mock
        with patch.dict(sys.modules, {"openai": self.openai_mod, "config": config_mod}):
            import importlib
            gs = importlib.import_module("generate_script")
            with self.assertRaises(ValueError):
                gs.generate_script("invalid_type")


if __name__ == "__main__":
    unittest.main()
