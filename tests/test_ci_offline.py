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

    def test_song_details_endpoint(self):
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

        with patch("app.services.ytmusic_service.ytmusic_service.get_song_details_with_suggestions", return_value=mock_song_data):
            response = self.client.get("/api/v1/songs/HaU84TfH9nU?limit=50")
            self.assertEqual(response.status_code, 200)
            body = response.json()

            self.assertTrue(body.get("success"))
            self.assertEqual(body.get("type"), "song")
            self.assertNotIn("mp3", body, "mp3 must not be duplicated at root level")

            data = body.get("data", {})
            self.assertEqual(data.get("id"), "HaU84TfH9nU")
            self.assertEqual(data.get("url"), "https://music.youtube.com/watch?v=HaU84TfH9nU")
            self.assertNotIn("mp3", data, "mp3 stream URL field must not be present in song data")
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

    def test_direct_cdn_stream_endpoint(self):
        mock_cdn_info = {
            "id": "HaU84TfH9nU",
            "title": "Adyam Thammil",
            "artist": "Haricharan",
            "stream_url": "https://aac.saavncdn.com/123/adyam_thammil_320.mp4",
            "download_url": "https://aac.saavncdn.com/123/adyam_thammil_320.mp4",
            "download_urls": [{"quality": "320kbps", "url": "https://aac.saavncdn.com/123/adyam_thammil_320.mp4"}],
            "quality": "320kbps",
            "format": "m4a",
            "source": "saavn_cdn",
            "is_direct_cdn": True,
        }
        with patch("app.services.cdn_stream_service.cdn_stream_service.resolve_cdn_stream", return_value=mock_cdn_info):
            res = self.client.get("/api/v1/songs/HaU84TfH9nU/stream")
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertTrue(data.get("success"))
            self.assertEqual(data["data"]["stream_url"], "https://aac.saavncdn.com/123/adyam_thammil_320.mp4")
            self.assertEqual(data["data"]["source"], "saavn_cdn")
            self.assertTrue(data["data"]["is_direct_cdn"])

    def test_search_candidates_generation(self):
        from app.services.cdn_stream_service import (
            clean_artist_for_search,
            extract_movie_or_album,
            generate_search_candidates,
        )

        # Test video title with pipe: Vellarathaaram | Sarvam Maya | Nivin Pauly...
        title1 = "Vellarathaaram | Sarvam Maya | Nivin Pauly, Aju Varghese | Justin, Vineeth Sreenivasan"
        movie1 = extract_movie_or_album(title1)
        self.assertEqual(movie1, "Sarvam Maya")

        cands1 = generate_search_candidates(title1, artist="Saregama Malayalam")
        self.assertIn("Vellarathaaram Sarvam Maya", cands1)
        self.assertIn("Vellarathaaram", cands1)

        # Test title with (From "Sarvam Maya")
        title2 = 'Vellarathaaram (From "Sarvam Maya")'
        movie2 = extract_movie_or_album(title2)
        self.assertEqual(movie2, "Sarvam Maya")

        cands2 = generate_search_candidates(title2, artist="Justin Prabhakaran - Topic")
        self.assertIn("Vellarathaaram Sarvam Maya", cands2)
        self.assertIn("Vellarathaaram Justin Prabhakaran", cands2)
        self.assertIn("Vellarathaaram", cands2)

        # Test clean artist
        self.assertEqual(clean_artist_for_search("Justin Prabhakaran - Topic"), "Justin Prabhakaran")
        self.assertEqual(clean_artist_for_search("Saregama Malayalam VEVO"), "Saregama")


if __name__ == "__main__":
    unittest.main()


