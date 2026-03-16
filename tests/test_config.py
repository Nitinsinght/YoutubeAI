"""
tests/test_config.py – Unit tests for config.py.
"""

from __future__ import annotations

import os
import sys
import types
import unittest
from unittest.mock import patch


class TestPipelineConfig(unittest.TestCase):

    def tearDown(self):
        sys.modules.pop("config", None)

    def _import_config_with_env(self, env: dict):
        sys.modules.pop("config", None)
        with patch.dict(os.environ, env, clear=True):
            import importlib
            mod = importlib.import_module("config")
        return mod

    def test_valid_runway_config(self):
        mod = self._import_config_with_env({
            "OPENAI_API_KEY": "sk-test",
            "VIDEO_BACKEND": "runway",
            "TTS_BACKEND": "openai",
        })
        self.assertEqual(mod.config.video_backend, "runway")
        self.assertEqual(mod.config.tts_backend, "openai")

    def test_valid_pika_config(self):
        mod = self._import_config_with_env({
            "OPENAI_API_KEY": "sk-test",
            "VIDEO_BACKEND": "pika",
            "TTS_BACKEND": "openai",
        })
        self.assertEqual(mod.config.video_backend, "pika")

    def test_valid_stable_video_config(self):
        mod = self._import_config_with_env({
            "OPENAI_API_KEY": "sk-test",
            "VIDEO_BACKEND": "stable_video",
            "TTS_BACKEND": "openai",
        })
        self.assertEqual(mod.config.video_backend, "stable_video")

    def test_valid_elevenlabs_config(self):
        mod = self._import_config_with_env({
            "OPENAI_API_KEY": "sk-test",
            "VIDEO_BACKEND": "runway",
            "TTS_BACKEND": "elevenlabs",
        })
        self.assertEqual(mod.config.tts_backend, "elevenlabs")

    def test_missing_openai_key_raises(self):
        sys.modules.pop("config", None)
        with patch.dict(os.environ, {}, clear=True):
            import importlib
            with self.assertRaises(EnvironmentError):
                importlib.import_module("config")

    def test_invalid_video_backend_raises(self):
        sys.modules.pop("config", None)
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-test",
            "VIDEO_BACKEND": "not_a_backend",
            "TTS_BACKEND": "openai",
        }, clear=True):
            import importlib
            with self.assertRaises(ValueError):
                importlib.import_module("config")

    def test_invalid_tts_backend_raises(self):
        sys.modules.pop("config", None)
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-test",
            "VIDEO_BACKEND": "runway",
            "TTS_BACKEND": "not_a_backend",
        }, clear=True):
            import importlib
            with self.assertRaises(ValueError):
                importlib.import_module("config")

    def test_defaults(self):
        mod = self._import_config_with_env({"OPENAI_API_KEY": "sk-test"})
        self.assertEqual(mod.config.openai_model, "gpt-4o")
        self.assertEqual(mod.config.video_backend, "runway")
        self.assertEqual(mod.config.tts_backend, "openai")
        self.assertEqual(mod.config.uploads_per_day, 12)
        self.assertEqual(mod.config.video_width, 1080)
        self.assertEqual(mod.config.video_height, 1920)
        self.assertEqual(mod.config.content_type, "random")

    def test_seconds_between_uploads(self):
        mod = self._import_config_with_env({
            "OPENAI_API_KEY": "sk-test",
            "UPLOADS_PER_DAY": "24",
        })
        self.assertAlmostEqual(mod.config.seconds_between_uploads, 3600.0)

    def test_custom_uploads_per_day(self):
        mod = self._import_config_with_env({
            "OPENAI_API_KEY": "sk-test",
            "UPLOADS_PER_DAY": "20",
        })
        self.assertEqual(mod.config.uploads_per_day, 20)


if __name__ == "__main__":
    unittest.main()
