"""
tests/test_upload_video.py – Unit tests for upload_video.py.

All Google API and YouTube API calls are mocked.
"""

from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path


# ---------------------------------------------------------------------------
# Minimal config mock
# ---------------------------------------------------------------------------

_CONFIG_ATTRS = {
    "youtube_client_secrets_file": "client_secrets.json",
    "youtube_token_file": "/tmp/youtube_token_test.json",
    "youtube_category_id": "22",
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


def _make_google_mocks():
    """Return mocked google API modules."""
    # google.oauth2.credentials
    creds_mock = MagicMock()
    creds_mock.valid = True
    creds_mock.expired = False
    credentials_mod = types.ModuleType("google.oauth2.credentials")
    credentials_mod.Credentials = MagicMock(return_value=creds_mock)

    # google.auth.transport.requests
    transport_mod = types.ModuleType("google.auth.transport.requests")
    transport_mod.Request = MagicMock()

    # google_auth_oauthlib.flow
    flow_mock = MagicMock()
    flow_mock.run_local_server.return_value = creds_mock
    oauthlib_mod = types.ModuleType("google_auth_oauthlib.flow")
    oauthlib_mod.InstalledAppFlow = MagicMock()
    oauthlib_mod.InstalledAppFlow.from_client_secrets_file = MagicMock(
        return_value=flow_mock
    )

    # googleapiclient.discovery
    youtube_service = MagicMock()
    insert_request = MagicMock()
    insert_request.next_chunk.return_value = (None, {"id": "test_video_id"})
    youtube_service.videos.return_value.insert.return_value = insert_request
    discovery_mod = types.ModuleType("googleapiclient.discovery")
    discovery_mod.build = MagicMock(return_value=youtube_service)

    # googleapiclient.http
    http_mod = types.ModuleType("googleapiclient.http")
    http_mod.MediaFileUpload = MagicMock()

    # googleapiclient.errors
    errors_mod = types.ModuleType("googleapiclient.errors")
    errors_mod.HttpError = Exception

    return {
        "google.oauth2.credentials": credentials_mod,
        "google.auth.transport.requests": transport_mod,
        "google_auth_oauthlib.flow": oauthlib_mod,
        "googleapiclient.discovery": discovery_mod,
        "googleapiclient.http": http_mod,
        "googleapiclient.errors": errors_mod,
        # parent packages
        "google": types.ModuleType("google"),
        "google.oauth2": types.ModuleType("google.oauth2"),
        "google.auth": types.ModuleType("google.auth"),
        "google.auth.transport": types.ModuleType("google.auth.transport"),
        "google_auth_oauthlib": types.ModuleType("google_auth_oauthlib"),
        "googleapiclient": types.ModuleType("googleapiclient"),
    }, youtube_service, creds_mock


class TestBuildDescription(unittest.TestCase):

    def tearDown(self):
        for mod in ["config", "upload_video"]:
            sys.modules.pop(mod, None)

    def _import(self):
        config_mod = types.ModuleType("config")
        config_mod.config = config_mock
        google_mocks, _, _ = _make_google_mocks()
        with patch.dict(sys.modules, {"config": config_mod, **google_mocks}):
            import importlib
            return importlib.import_module("upload_video")

    def test_curiosity_description_includes_fact(self):
        uv = self._import()
        script = {
            "type": "curiosity",
            "fact": "Sharks predate trees.",
            "hashtags": ["sharks", "nature"],
        }
        desc = uv.build_description(script)
        self.assertIn("Sharks predate trees.", desc)
        self.assertIn("#sharks", desc)
        self.assertIn("#Shorts", desc)

    def test_suspense_description_includes_hook_and_twist(self):
        uv = self._import()
        script = {
            "type": "suspense",
            "hook": "Two girls drove into the wild.",
            "twist": "The lion just walked away.",
            "hashtags": ["wildlife", "safari"],
        }
        desc = uv.build_description(script)
        self.assertIn("Two girls drove into the wild.", desc)
        self.assertIn("The lion just walked away.", desc)
        self.assertIn("#Shorts", desc)

    def test_hashtags_get_hash_prefix(self):
        uv = self._import()
        script = {
            "type": "curiosity",
            "fact": "A fact.",
            "hashtags": ["nohash", "#alreadyhash"],
        }
        desc = uv.build_description(script)
        self.assertIn("#nohash", desc)
        self.assertIn("#alreadyhash", desc)


class TestUploadToYouTube(unittest.TestCase):

    def tearDown(self):
        for mod in list(sys.modules.keys()):
            if mod in ("config", "upload_video") or mod.startswith("google") or mod.startswith("googleapiclient"):
                sys.modules.pop(mod, None)

    def test_upload_returns_video_id(self):
        config_mod = types.ModuleType("config")
        config_mod.config = config_mock
        google_mocks, youtube_service, creds = _make_google_mocks()

        # Pre-populate token file so no OAuth flow is triggered
        import json, os
        token_data = {"token": "fake", "refresh_token": "fake", "token_uri": "https://oauth2.googleapis.com/token", "client_id": "cid", "client_secret": "cs", "scopes": ["https://www.googleapis.com/auth/youtube.upload"]}
        token_path = _CONFIG_ATTRS["youtube_token_file"]
        with open(token_path, "w") as f:
            json.dump(token_data, f)

        with patch.dict(sys.modules, {"config": config_mod, **google_mocks}):
            import importlib
            uv = importlib.import_module("upload_video")

            video_id = uv.upload_to_youtube(
                video_path=Path("/tmp/test_short.mp4"),
                title="Test Short",
                description="A test video #Shorts",
                tags=["test", "shorts"],
            )

        self.assertEqual(video_id, "test_video_id")

        # Cleanup
        if os.path.exists(token_path):
            os.remove(token_path)


if __name__ == "__main__":
    unittest.main()
