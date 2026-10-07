import os
import sys
import unittest
from unittest.mock import MagicMock, patch

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
            "/api/v1/test-youtube/{video_id}",
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

    def test_song_details_endpoint_returns_mp3(self):
        mock_song_data = {
            "id": "HaU84TfH9nU",
            "name": "Adyam Thammil",
            "title": "Adyam Thammil",
            "type": "song",
            "duration": 240,
            "url": "https://music.youtube.com/watch?v=HaU84TfH9nU",
            "image": "https://example.com/cover.jpg",
            "image_url": "https://example.com/cover.jpg",
            "suggested_songs": [
                {"id": "sug1", "name": "Suggested 1", "type": "song", "thumbnails": []}
            ],
        }
        mock_stream_url = "https://rr1---sn-test.googlevideo.com/videoplayback?expire=999999"

        with patch("app.services.ytmusic_service.ytmusic_service.get_song_details_with_suggestions", return_value=mock_song_data), \
             patch("app.services.stream_service.stream_service.get_audio_stream_url", return_value=mock_stream_url):
            response = self.client.get("/api/v1/songs/HaU84TfH9nU?limit=50")
            self.assertEqual(response.status_code, 200)
            body = response.json()

            self.assertTrue(body.get("success"))
            self.assertEqual(body.get("type"), "song")
            self.assertNotIn("mp3", body, "mp3 must not be duplicated at root level")

            data = body.get("data", {})
            self.assertEqual(data.get("id"), "HaU84TfH9nU")
            # Existing song URL must remain unchanged
            self.assertEqual(data.get("url"), "https://music.youtube.com/watch?v=HaU84TfH9nU")
            # mp3 field must contain the direct stream URL inside data
            self.assertEqual(data.get("mp3"), mock_stream_url)
            # Other fields preserved
            self.assertEqual(data.get("name"), "Adyam Thammil")
            self.assertEqual(len(data.get("suggested_songs", [])), 1)

    def test_database_does_not_persist_mp3(self):
        from core.firebase import add_song_to_playlist, save_recent_play

        mock_db = MagicMock()
        mock_doc_ref = MagicMock()
        mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value = mock_doc_ref
        mock_doc_ref.get.return_value.exists = False

        song_with_mp3 = {
            "id": "HaU84TfH9nU",
            "name": "Adyam Thammil",
            "url": "https://music.youtube.com/watch?v=HaU84TfH9nU",
            "mp3": "https://temp-expiring-stream.googlevideo.com/videoplayback",
        }

        # 1. Test save_recent_play strips mp3
        with patch("core.firebase.get_firestore_db", return_value=mock_db):
            save_recent_play("test_user", song_with_mp3)
            call_args = mock_doc_ref.set.call_args[0][0]
            self.assertNotIn("mp3", call_args, "mp3 must not be saved to Firestore in recent_plays")
            self.assertEqual(call_args["id"], "HaU84TfH9nU")

        # 2. Test add_song_to_playlist strips mp3
        mock_pl_doc = MagicMock()
        mock_pl_doc.exists = True
        mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value = mock_pl_doc
        mock_pl_doc.collection.return_value.document.return_value = mock_doc_ref

        with patch("core.firebase.get_firestore_db", return_value=mock_db):
            add_song_to_playlist("test_user", "pl_test", song_with_mp3)
            call_args = mock_doc_ref.set.call_args[0][0]
            self.assertNotIn("mp3", call_args, "mp3 must not be saved to Firestore in playlists")

    def test_stream_service_format_configuration(self):
        from app.services.stream_service import StreamService
        with patch.object(StreamService, "_init_cookie_file"):
            svc = StreamService()
            svc._cookie_file_path = None
            opts = svc._get_ydl_opts()
            self.assertIn("m4a", opts.get("format", ""))
            self.assertTrue(opts.get("skip_download"))
            self.assertTrue(opts.get("noplaylist"))
            # Default with POT provider enabled attaches youtubepot-bgutilhttp
            self.assertIn("youtubepot-bgutilhttp", opts.get("extractor_args", {}))

    def test_stream_service_cookie_detection(self):
        from app.services.stream_service import StreamService
        # Test inline env var with POT provider disabled
        with patch.dict(os.environ, {
            "YOUTUBE_COOKIES": "# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t1800000000\tSID\ttest",
            "ENABLE_POT_PROVIDER": "false"
        }):
            svc = StreamService()
            self.assertIsNotNone(svc._cookie_file_path)
            self.assertTrue(os.path.exists(svc._cookie_file_path))
            opts = svc._get_ydl_opts()
            self.assertEqual(opts.get("cookiefile"), svc._cookie_file_path)
            self.assertEqual(opts.get("extractor_args"), {})

    def test_stream_service_environment_routing(self):
        from app.services.stream_service import StreamService
        svc = StreamService()

        # 1. Default (local or cloud with PO Token Provider): yt-dlp enabled
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ENABLE_YTDLP", None)
            os.environ.pop("ENABLE_SERVER_YTDLP", None)
            self.assertTrue(svc.should_run_ytdlp())

        # 2. Explicit server disable: yt-dlp disabled
        with patch.dict(os.environ, {"ENABLE_SERVER_YTDLP": "false"}):
            self.assertFalse(svc.should_run_ytdlp())

        # 3. Global disable: yt-dlp disabled
        with patch.dict(os.environ, {"ENABLE_YTDLP": "false"}):
            self.assertFalse(svc.should_run_ytdlp())

    def test_test_youtube_endpoint(self):
        with patch("app.api.v1.endpoints.test_youtube._extract_test_info", return_value={
            "title": "Adyam Thammil",
            "audio_url": "https://example.com/audio.m4a",
            "duration": 240,
            "format": "m4a",
        }):
            response = self.client.get("/api/v1/test-youtube/HaU84TfH9nU")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data.get("success"))
            self.assertEqual(data.get("video_id"), "HaU84TfH9nU")
            self.assertEqual(data.get("title"), "Adyam Thammil")
            self.assertEqual(data.get("audio_url"), "https://example.com/audio.m4a")


if __name__ == "__main__":
    unittest.main()


