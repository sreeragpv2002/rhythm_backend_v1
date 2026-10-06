import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from app.main import app
from app.services.ytmusic_service import (
    extract_image_url,
    interleave_results,
    normalize_yt_album,
    normalize_yt_artist,
    normalize_yt_playlist,
    normalize_yt_song,
    parse_languages,
    ytmusic_service,
)


class TestHomeAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_parse_languages(self):
        self.assertEqual(parse_languages(""), [])
        self.assertEqual(parse_languages(None), [])
        self.assertEqual(parse_languages("english, malayalam, tamil"), ["english", "malayalam", "tamil"])
        self.assertEqual(parse_languages(" Hindi , Punjabi "), ["hindi", "punjabi"])

    def test_interleave_results(self):
        group1 = [{"id": "1"}, {"id": "2"}]
        group2 = [{"id": "3"}, {"id": "4"}]
        interleaved = interleave_results([group1, group2])
        self.assertEqual([item["id"] for item in interleaved], ["1", "3", "2", "4"])

    def test_extract_image_url(self):
        self.assertEqual(extract_image_url(None), "")
        self.assertEqual(extract_image_url([]), "")
        self.assertEqual(extract_image_url("https://example.com/cover.jpg"), "https://example.com/cover.jpg")
        thumbnails = [
            {"url": "https://example.com/small.jpg", "width": 60, "height": 60},
            {"url": "https://example.com/large.jpg", "width": 544, "height": 544},
        ]
        self.assertEqual(extract_image_url(thumbnails), "https://example.com/large.jpg")

    def test_normalizers(self):
        song = normalize_yt_song({
            "videoId": "abc123",
            "title": "Song Title",
            "artists": [{"name": "Artist A", "id": "art1"}],
            "album": {"name": "Album A", "id": "alb1"},
            "duration": "3:30",
            "duration_seconds": 210,
            "thumbnails": [{"url": "https://img/song.jpg", "width": 100}],
        })
        self.assertEqual(song["id"], "abc123")
        self.assertEqual(song["name"], "Song Title")
        self.assertEqual(song["type"], "song")
        self.assertEqual(song["image_url"], "https://img/song.jpg")
        self.assertEqual(song["artist"], "Artist A")

        playlist = normalize_yt_playlist({
            "browseId": "pl123",
            "title": "Playlist Title",
            "author": "Curator",
            "thumbnails": [{"url": "https://img/pl.jpg", "width": 100}],
        })
        self.assertEqual(playlist["id"], "pl123")
        self.assertEqual(playlist["name"], "Playlist Title")
        self.assertEqual(playlist["type"], "playlist")

        album = normalize_yt_album({
            "browseId": "alb123",
            "title": "Album Title",
            "artists": [{"name": "Artist B"}],
            "year": "2024",
            "thumbnails": [{"url": "https://img/alb.jpg", "width": 100}],
        })
        self.assertEqual(album["id"], "alb123")
        self.assertEqual(album["year"], "2024")

        artist = normalize_yt_artist({
            "browseId": "art123",
            "artist": "Artist C",
            "thumbnails": [{"url": "https://img/art.jpg", "width": 100}],
        })
        self.assertEqual(artist["id"], "art123")
        self.assertEqual(artist["name"], "Artist C")

    def test_home_endpoint_structure(self):
        mock_sections = {
            "trending_songs": [
                {"id": "s1", "name": "Song 1", "title": "Song 1", "image": "https://img/1.jpg", "image_url": "https://img/1.jpg", "type": "song"}
            ],
            "featured_playlists": [
                {"id": "p1", "name": "Playlist 1", "title": "Playlist 1", "image": "https://img/p1.jpg", "image_url": "https://img/p1.jpg", "type": "playlist"}
            ],
            "trending_albums": [
                {"id": "a1", "name": "Album 1", "title": "Album 1", "image": "https://img/a1.jpg", "image_url": "https://img/a1.jpg", "type": "album"}
            ],
            "top_artists": [
                {"id": "ar1", "name": "Artist 1", "title": "Artist 1", "image": "https://img/ar1.jpg", "image_url": "https://img/ar1.jpg", "type": "artist"}
            ],
        }

        with (
            patch("app.api.v1.endpoints.home.verify_user_exists", return_value=True),
            patch("app.api.v1.endpoints.home.get_user_languages", return_value=["hindi", "english"]),
            patch("app.api.v1.endpoints.home.get_recent_plays", return_value=[]),
            patch.object(ytmusic_service, "fetch_home_sections", return_value=mock_sections) as mock_fetch,
        ):
            response = self.client.get("/api/v1/home?user_id=test_user_123")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data.get("success"))
            home_data = data.get("data", {})

            # Check sections
            self.assertEqual(home_data.get("user_languages"), ["hindi", "english"])
            self.assertEqual(len(home_data.get("languages", [])), 2)
            self.assertEqual(len(home_data.get("trending_songs", [])), 1)
            self.assertEqual(home_data["trending_songs"][0]["name"], "Song 1")
            self.assertEqual(len(home_data.get("featured_playlists", [])), 1)
            self.assertEqual(len(home_data.get("trending_albums", [])), 1)
            self.assertEqual(len(home_data.get("top_artists", [])), 1)


if __name__ == "__main__":
    unittest.main()
