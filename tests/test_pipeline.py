"""Tests for the AI YouTube Shorts production system."""

import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from generate_script import (
    build_narration_text,
    generate_title_and_hashtags,
)


class TestConfig(unittest.TestCase):
    """Tests for configuration module."""

    def test_ensure_directories_creates_dirs(self):
        """ensure_directories creates required output directories."""
        with patch("os.makedirs") as mock_makedirs:
            config.ensure_directories()
            self.assertEqual(mock_makedirs.call_count, 4)

    def test_content_types_defined(self):
        """CONTENT_TYPES contains the expected content types."""
        self.assertIn("curiosity_fact", config.CONTENT_TYPES)
        self.assertIn("suspense_story", config.CONTENT_TYPES)

    def test_video_dimensions(self):
        """Video dimensions are vertical format for Shorts."""
        self.assertEqual(config.VIDEO_WIDTH, 1080)
        self.assertEqual(config.VIDEO_HEIGHT, 1920)

    def test_duration_ranges(self):
        """Duration ranges are within specification."""
        self.assertGreaterEqual(config.CURIOSITY_DURATION_MIN, 6)
        self.assertLessEqual(config.CURIOSITY_DURATION_MAX, 10)
        self.assertGreaterEqual(config.SUSPENSE_DURATION_MIN, 10)
        self.assertLessEqual(config.SUSPENSE_DURATION_MAX, 20)


class TestGenerateScript(unittest.TestCase):
    """Tests for script generation module."""

    def test_generate_title_and_hashtags(self):
        """generate_title_and_hashtags extracts title and formats hashtags."""
        script = {
            "title": "Test Title",
            "hashtags": ["shorts", "viral", "facts"],
        }
        title, hashtags = generate_title_and_hashtags(script)
        self.assertEqual(title, "Test Title")
        self.assertIn("#shorts", hashtags)
        self.assertIn("#viral", hashtags)
        self.assertIn("#facts", hashtags)

    def test_generate_title_and_hashtags_defaults(self):
        """generate_title_and_hashtags uses defaults when data is missing."""
        script = {}
        title, hashtags = generate_title_and_hashtags(script)
        self.assertIsInstance(title, str)
        self.assertIsInstance(hashtags, str)

    def test_generate_title_and_hashtags_strips_hash(self):
        """generate_title_and_hashtags doesn't double the # prefix."""
        script = {
            "title": "Test",
            "hashtags": ["#already_hashed", "no_hash"],
        }
        _, hashtags = generate_title_and_hashtags(script)
        self.assertNotIn("##", hashtags)
        self.assertIn("#already_hashed", hashtags)
        self.assertIn("#no_hash", hashtags)

    def test_build_narration_text_curiosity(self):
        """build_narration_text assembles curiosity fact narration."""
        script = {
            "content_type": "curiosity_fact",
            "hook": "Did you know?",
            "fact": "Sharks are older than trees.",
        }
        text = build_narration_text(script)
        self.assertIn("Did you know?", text)
        self.assertIn("Sharks are older than trees.", text)

    def test_build_narration_text_suspense(self):
        """build_narration_text assembles suspense story narration."""
        script = {
            "content_type": "suspense_story",
            "hook": "Two hikers were lost.",
            "tension": "They heard a growl.",
            "resolution": "They stayed still.",
            "twist": "It was just the wind.",
        }
        text = build_narration_text(script)
        self.assertIn("Two hikers were lost.", text)
        self.assertIn("They heard a growl.", text)
        self.assertIn("They stayed still.", text)
        self.assertIn("It was just the wind.", text)

    def test_build_narration_text_skips_empty(self):
        """build_narration_text skips empty segments."""
        script = {
            "content_type": "curiosity_fact",
            "hook": "Did you know?",
            "fact": "",
        }
        text = build_narration_text(script)
        self.assertEqual(text, "Did you know?")

    @patch("generate_script.OpenAI")
    def test_generate_script_curiosity(self, mock_openai_class):
        """generate_script returns valid curiosity fact script."""
        from generate_script import generate_script

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "title": "Sharks vs Trees",
            "hashtags": ["nature", "facts"],
            "hook": "Did you know?",
            "fact": "Sharks existed before trees.",
            "visual_prompt": "Prehistoric shark swimming",
            "duration": 8,
        })

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        result = generate_script(content_type="curiosity_fact")

        self.assertEqual(result["title"], "Sharks vs Trees")
        self.assertEqual(result["content_type"], "curiosity_fact")
        self.assertIn("hook", result)
        self.assertIn("fact", result)

    @patch("generate_script.OpenAI")
    def test_generate_script_suspense(self, mock_openai_class):
        """generate_script returns valid suspense story script."""
        from generate_script import generate_script

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "title": "The Lion Encounter",
            "hashtags": ["suspense", "safari"],
            "hook": "Two girls on safari.",
            "tension": "A lion approached.",
            "resolution": "They locked the doors.",
            "twist": "The lion walked away.",
            "visual_prompts": ["lion scene 1", "lion scene 2"],
            "duration": 15,
        })

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        result = generate_script(content_type="suspense_story")

        self.assertEqual(result["content_type"], "suspense_story")
        self.assertIn("hook", result)
        self.assertIn("tension", result)
        self.assertIn("twist", result)


class TestGenerateVideo(unittest.TestCase):
    """Tests for video generation module."""

    def test_generate_video_invalid_provider(self):
        """generate_video raises ValueError for unsupported provider."""
        from generate_video import generate_video

        original = config.VIDEO_PROVIDER
        try:
            config.VIDEO_PROVIDER = "nonexistent_provider"
            with self.assertRaises(ValueError):
                generate_video("test prompt", output_path="/tmp/test.mp4")
        finally:
            config.VIDEO_PROVIDER = original

    def test_generate_video_runway_no_key(self):
        """generate_video raises ValueError when Runway key is missing."""
        from generate_video import generate_video

        original_provider = config.VIDEO_PROVIDER
        original_key = config.RUNWAY_API_KEY
        try:
            config.VIDEO_PROVIDER = "runway"
            config.RUNWAY_API_KEY = ""
            with self.assertRaises(ValueError):
                generate_video("test prompt", output_path="/tmp/test.mp4")
        finally:
            config.VIDEO_PROVIDER = original_provider
            config.RUNWAY_API_KEY = original_key

    def test_generate_video_pika_no_key(self):
        """generate_video raises ValueError when Pika key is missing."""
        from generate_video import generate_video

        original_provider = config.VIDEO_PROVIDER
        original_key = config.PIKA_API_KEY
        try:
            config.VIDEO_PROVIDER = "pika"
            config.PIKA_API_KEY = ""
            with self.assertRaises(ValueError):
                generate_video("test prompt", output_path="/tmp/test.mp4")
        finally:
            config.VIDEO_PROVIDER = original_provider
            config.PIKA_API_KEY = original_key

    def test_generate_video_scenes_curiosity(self):
        """generate_video_scenes handles curiosity fact scripts."""
        from generate_video import generate_video_scenes

        script = {
            "content_type": "curiosity_fact",
            "visual_prompt": "A shark in the ocean",
            "duration": 8,
        }

        with patch("generate_video.generate_video") as mock_gen:
            mock_gen.return_value = "/tmp/scene.mp4"
            paths = generate_video_scenes(script, output_dir="/tmp")
            self.assertEqual(len(paths), 1)
            mock_gen.assert_called_once()

    def test_generate_video_scenes_suspense(self):
        """generate_video_scenes handles suspense story scripts."""
        from generate_video import generate_video_scenes

        script = {
            "content_type": "suspense_story",
            "visual_prompts": ["scene 1", "scene 2", "scene 3"],
            "duration": 15,
        }

        with patch("generate_video.generate_video") as mock_gen:
            mock_gen.return_value = "/tmp/scene.mp4"
            paths = generate_video_scenes(script, output_dir="/tmp")
            self.assertEqual(len(paths), 3)
            self.assertEqual(mock_gen.call_count, 3)


class TestUploadVideo(unittest.TestCase):
    """Tests for upload module."""

    def test_upload_video_missing_file(self):
        """upload_video raises FileNotFoundError for missing files."""
        from upload_video import upload_video

        with self.assertRaises(FileNotFoundError):
            upload_video("/nonexistent/video.mp4", "Title", "Desc")

    def test_build_description_curiosity(self):
        """build_description formats curiosity fact descriptions."""
        from upload_video import build_description

        script = {
            "content_type": "curiosity_fact",
            "hook": "Did you know?",
            "topic": "nature",
        }
        desc = build_description(script, "#shorts #nature")
        self.assertIn("Did you know?", desc)
        self.assertIn("#shorts", desc)

    def test_build_description_suspense(self):
        """build_description formats suspense story descriptions."""
        from upload_video import build_description

        script = {
            "content_type": "suspense_story",
            "hook": "A dark night.",
            "topic": "horror",
        }
        desc = build_description(script, "#shorts #horror")
        self.assertIn("A dark night.", desc)
        self.assertIn("Watch till the end", desc)


class TestComposeVideo(unittest.TestCase):
    """Tests for video composition module."""

    def test_group_words_into_phrases(self):
        """_group_words_into_phrases groups words correctly."""
        from compose_video import _group_words_into_phrases

        timestamps = [
            {"text": f"word{i}", "start": i * 0.5, "end": (i + 1) * 0.5}
            for i in range(12)
        ]

        groups = _group_words_into_phrases(timestamps, max_words=5)
        self.assertEqual(len(groups), 3)
        self.assertEqual(len(groups[0]), 5)
        self.assertEqual(len(groups[1]), 5)
        self.assertEqual(len(groups[2]), 2)

    def test_group_words_empty(self):
        """_group_words_into_phrases handles empty input."""
        from compose_video import _group_words_into_phrases

        groups = _group_words_into_phrases([])
        self.assertEqual(groups, [])

    def test_create_subtitle_clips_curiosity(self):
        """_create_subtitle_clips creates clips for curiosity facts."""
        from compose_video import _create_subtitle_clips

        script = {
            "content_type": "curiosity_fact",
            "hook": "Did you know?",
            "fact": "Sharks are old.",
        }
        with patch("compose_video.TextClip") as mock_tc:
            mock_clip = MagicMock()
            mock_clip.with_position.return_value = mock_clip
            mock_clip.with_start.return_value = mock_clip
            mock_clip.with_duration.return_value = mock_clip
            mock_tc.return_value = mock_clip

            clips = _create_subtitle_clips(script, total_duration=8.0)
            self.assertEqual(len(clips), 2)

    def test_create_subtitle_clips_empty(self):
        """_create_subtitle_clips handles missing script data."""
        from compose_video import _create_subtitle_clips

        clips = _create_subtitle_clips({}, total_duration=8.0)
        self.assertEqual(clips, [])


class TestRunBot(unittest.TestCase):
    """Tests for the main bot module."""

    @patch("run_bot.upload_video")
    @patch("run_bot.compose_video")
    @patch("run_bot.generate_voice")
    @patch("run_bot.generate_video_scenes")
    @patch("run_bot.generate_script")
    def test_produce_and_upload_short(
        self, mock_script, mock_scenes, mock_voice,
        mock_compose, mock_upload
    ):
        """produce_and_upload_short runs the full pipeline."""
        from run_bot import produce_and_upload_short

        mock_script.return_value = {
            "content_type": "curiosity_fact",
            "title": "Test Video",
            "hashtags": ["test"],
            "hook": "Hook text",
            "fact": "Fact text",
            "visual_prompt": "visual prompt",
            "duration": 8,
            "topic": "nature",
        }
        mock_scenes.return_value = ["/tmp/scene.mp4"]
        mock_voice.return_value = "/tmp/voice.mp3"
        mock_compose.return_value = "/tmp/final.mp4"
        mock_upload.return_value = {"id": "test123"}

        result = produce_and_upload_short()

        self.assertEqual(result["id"], "test123")
        mock_script.assert_called_once()
        mock_scenes.assert_called_once()
        mock_voice.assert_called_once()
        mock_compose.assert_called_once()
        mock_upload.assert_called_once()


if __name__ == "__main__":
    unittest.main()
