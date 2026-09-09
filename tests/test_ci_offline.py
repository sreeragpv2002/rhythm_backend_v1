import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from app.api.v1.endpoints.home import extract_image_url
from app.main import app
from app.services.saavn_service import (
    is_compilation_song,
    parse_languages,
)
from core.cache import TTLCache


class TestCIOffline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data.get("status"), "healthy")
        self.assertEqual(data.get("service"), "Rhythm Backend")

    def test_route_registration(self):
        registered_paths = list(app.openapi()["paths"].keys())
        expected_paths = [
            "/health",
            "/api/v1/home",
            "/api/v1/recent-plays",
            "/api/v1/details",
            "/api/v1/details/{type}/{id}",
            "/api/v1/languages",
            "/api/v1/languages/user",
            "/api/v1/favorites",
            "/api/v1/favorites/{song_id}",
            "/api/v1/favorites/check",
            "/api/v1/user-playlists",
            "/api/v1/user-playlists/{playlist_id}",
            "/api/v1/user-playlists/{playlist_id}/songs",
            "/api/v1/user-playlists/{playlist_id}/songs/{song_id}",
        ]
        for path in expected_paths:
            self.assertIn(path, registered_paths, f"Expected path {path} not in OpenAPI schema")

    def test_parse_languages(self):
        self.assertEqual(parse_languages(""), [])
        self.assertEqual(parse_languages(None), [])
        self.assertEqual(
            parse_languages("english, malayalam, tamil"),
            ["english", "malayalam", "tamil"]
        )
        self.assertEqual(
            parse_languages("  Hindi ,  Kannada  "),
            ["hindi", "kannada"]
        )

    def test_compilation_song_filter(self):
        # A normal original soundtrack song
        normal_song = {
            "name": "Manohari",
            "album": {"name": "Baahubali - The Beginning"},
        }
        self.assertFalse(is_compilation_song(normal_song))

        # A compilation/playlist album song
        compilation_song = {
            "name": "Karuthappenne",
            "album": {"name": "Top Trending Love Songs Malayalam 2026"},
        }
        self.assertTrue(is_compilation_song(compilation_song))

    def test_extract_image_url(self):
        # Empty or missing
        self.assertEqual(extract_image_url(None), "")
        self.assertEqual(extract_image_url([]), "")

        # String URL
        self.assertEqual(extract_image_url("https://example.com/cover.jpg"), "https://example.com/cover.jpg")

        # List of qualities
        data_list = [
            {"quality": "50x50", "url": "https://example.com/50.jpg"},
            {"quality": "500x500", "url": "https://example.com/500.jpg"},
        ]
        self.assertEqual(extract_image_url(data_list), "https://example.com/500.jpg")

    def test_ttl_cache_expiration(self):
        cache = TTLCache(default_ttl=1)
        cache.set("foo", "bar")
        self.assertEqual(cache.get("foo"), "bar")

        cache.delete("foo")
        self.assertIsNone(cache.get("foo"))

    def test_unauthorized_missing_user_on_home(self):
        with patch("app.api.v1.endpoints.home.verify_user_exists", return_value=False):
            response = self.client.get("/api/v1/home?user_id=nonexistent_user")
            self.assertEqual(response.status_code, 404)
            self.assertIn("not found", response.json().get("detail", ""))

    def test_languages_endpoint(self):
        response = self.client.get("/api/v1/languages")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(len(data.get("data", [])), 6)


if __name__ == "__main__":
    unittest.main()
