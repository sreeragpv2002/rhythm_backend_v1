import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

from app.main import app
from core.firebase import get_firestore_db

client = TestClient(app)

TEST_USER_ID = "test_user_rhythm_qa"
TEST_SONG_ID = "UPJYO3v0"  # Real song ID on JioSaavn: "Ishq de Fanniyar - Female"


@pytest.fixture(scope="module", autouse=True)
def setup_teardown_test_user():
    """Create test user in Firestore before tests and clean up after."""
    db = get_firestore_db()
    user_ref = db.collection("users").document(TEST_USER_ID)
    user_ref.set({"name": "Test QA User", "email": "test_qa@rhythm.local"})

    yield

    # Cleanup recent_plays subcollection
    recent_docs = user_ref.collection("recent_plays").stream()
    for doc in recent_docs:
        doc.reference.delete()
    # Cleanup user document
    user_ref.delete()


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Rhythm Backend"


def test_user_verification_failure_for_home():
    response = client.get("/api/v1/home?user_id=unknown_fake_user_99999")
    assert response.status_code == 404
    data = response.json()
    assert "not found in Firebase" in data["detail"]


def test_user_verification_failure_for_recent_plays_post():
    response = client.post(
        "/api/v1/recent-plays",
        json={"user_id": "unknown_fake_user_99999", "song_id": TEST_SONG_ID}
    )
    assert response.status_code == 404
    data = response.json()
    assert "not found in Firebase" in data["detail"]


def test_user_verification_failure_for_recent_plays_get():
    response = client.get("/api/v1/recent-plays?user_id=unknown_fake_user_99999")
    assert response.status_code == 404
    data = response.json()
    assert "not found in Firebase" in data["detail"]


def test_post_recent_play_success():
    response = client.post(
        "/api/v1/recent-plays",
        json={"user_id": TEST_USER_ID, "song_id": TEST_SONG_ID}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert data["data"]["id"] == TEST_SONG_ID
    assert "name" in data["data"]
    assert "played_at" in data["data"]
    assert "downloadUrl" in data["data"] or "download_url" in data["data"]


def test_get_recent_plays_success():
    response = client.get(f"/api/v1/recent-plays?user_id={TEST_USER_ID}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 1
    assert data["data"][0]["id"] == TEST_SONG_ID


def test_get_home_api_success():
    response = client.get(f"/api/v1/home?user_id={TEST_USER_ID}&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    home_data = data["data"]

    # Verify recent_plays contains our saved test song
    assert "recent_plays" in home_data
    assert len(home_data["recent_plays"]) >= 1
    assert home_data["recent_plays"][0]["id"] == TEST_SONG_ID

    # Verify Saavn sections are populated
    assert "trending_songs" in home_data
    assert len(home_data["trending_songs"]) > 0

    assert "featured_playlists" in home_data
    assert len(home_data["featured_playlists"]) > 0

    assert "trending_albums" in home_data
    assert len(home_data["trending_albums"]) > 0

    assert "top_artists" in home_data
    assert len(home_data["top_artists"]) > 0

    # Verify concise card fields (id, name, title, image, image_url, type) and absence of bulky details
    for section_name in ["recent_plays", "trending_songs", "featured_playlists", "trending_albums", "top_artists"]:
        item = home_data[section_name][0]
        assert item.get("id")
        assert item.get("name")
        assert item.get("title")
        assert "image" in item and isinstance(item["image"], str)
        assert "image_url" in item and isinstance(item["image_url"], str)
        assert "type" in item
        # Ensure bulky fields are stripped out of home card view
        assert "downloadUrl" not in item
        assert "copyright" not in item
        assert "hasLyrics" not in item
        assert "lyricsId" not in item


def test_home_sections_caching():

    from core.cache import ttl_cache
    from core.config import settings

    # Verify TTL is 1 day (86400s)
    assert settings.HOME_CACHE_TTL_SECONDS == 86400

    # Reset cache stats
    ttl_cache.clear()

    # 1st call: Miss, caches from JioSaavn API
    resp1 = client.get(f"/api/v1/home?user_id={TEST_USER_ID}&limit=5")
    assert resp1.status_code == 200

    stats1 = ttl_cache.get_stats()
    assert stats1["active_items"] > 0
    initial_hits = stats1["hits"]

    # 2nd call: Hits cache, does not call JioSaavn
    resp2 = client.get(f"/api/v1/home?user_id={TEST_USER_ID}&limit=5")
    assert resp2.status_code == 200

    stats2 = ttl_cache.get_stats()
    assert stats2["hits"] > initial_hits

    # Verify identical data
    d1 = resp1.json()["data"]
    d2 = resp2.json()["data"]
    assert d1["trending_songs"] == d2["trending_songs"]
    assert d1["featured_playlists"] == d2["featured_playlists"]
    assert d1["trending_albums"] == d2["trending_albums"]
    assert d1["top_artists"] == d2["top_artists"]


def test_multi_language_home_filter():
    response = client.get(f"/api/v1/home?user_id={TEST_USER_ID}&language=english, malayalam, tamil&limit=10")
    assert response.status_code == 200
    data = response.json()["data"]

    # Verify all 3 languages are present in trending_songs
    song_langs = set(s.get("language") for s in data["trending_songs"])
    assert "english" in song_langs
    assert "malayalam" in song_langs
    assert "tamil" in song_langs

    # Verify all 3 languages are present in featured_playlists
    playlist_langs = set(p.get("language") for p in data["featured_playlists"])
    assert "english" in playlist_langs
    assert "malayalam" in playlist_langs
    assert "tamil" in playlist_langs

    # Verify all 3 languages are present in trending_albums
    album_langs = set(a.get("language") for a in data["trending_albums"])
    assert "english" in album_langs
    assert "malayalam" in album_langs
    assert "tamil" in album_langs

    # Verify all 3 languages are present in top_artists
    artist_langs = set(ar.get("language") for ar in data["top_artists"])
    assert "english" in artist_langs
    assert "malayalam" in artist_langs
    assert "tamil" in artist_langs


def test_get_available_languages():
    response = client.get("/api/v1/languages")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    expected = ["malayalam", "tamil", "hindi", "kannada", "telugu", "english"]
    assert data["data"] == expected


def test_set_user_languages_success():
    response = client.post(
        "/api/v1/languages/user",
        json={"user_id": TEST_USER_ID, "languages": ["malayalam", "tamil"]}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["languages"] == ["malayalam", "tamil"]


def test_get_user_languages_success():
    response = client.get(f"/api/v1/languages/user?user_id={TEST_USER_ID}")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["languages"] == ["malayalam", "tamil"]


def test_edit_user_languages_put():
    response = client.put(
        "/api/v1/languages/user",
        json={"user_id": TEST_USER_ID, "languages": ["kannada", "telugu", "english"]}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["languages"] == ["kannada", "telugu", "english"]

    get_res = client.get(f"/api/v1/languages/user?user_id={TEST_USER_ID}")
    assert get_res.json()["data"]["languages"] == ["kannada", "telugu", "english"]


def test_set_user_languages_invalid():
    response = client.post(
        "/api/v1/languages/user",
        json={"user_id": TEST_USER_ID, "languages": ["spanish", "french"]}
    )
    assert response.status_code in (400, 422)


def test_home_api_uses_saved_user_languages():
    client.put(
        "/api/v1/languages/user",
        json={"user_id": TEST_USER_ID, "languages": ["malayalam", "tamil"]}
    )
    response = client.get(f"/api/v1/home?user_id={TEST_USER_ID}&limit=6")
    assert response.status_code == 200
    data = response.json()["data"]

    # Verify user_languages and languages sections in Home response
    assert "user_languages" in data
    assert data["user_languages"] == ["malayalam", "tamil"]
    assert "languages" in data
    assert len(data["languages"]) == 2
    assert data["languages"][0]["id"] == "malayalam"
    assert data["languages"][0]["name"] == "Malayalam"
    assert data["languages"][0]["type"] == "language"
    assert data["languages"][1]["id"] == "tamil"
    assert data["languages"][1]["name"] == "Tamil"
    assert data["languages"][1]["type"] == "language"

    song_langs = set(s.get("language") for s in data["trending_songs"])
    assert "malayalam" in song_langs or "tamil" in song_langs


def test_post_invalid_song_id():
    response = client.post(
        "/api/v1/recent-plays",
        json={"user_id": TEST_USER_ID, "song_id": "non_existent_song_id_000"}
    )
    assert response.status_code == 404
    data = response.json()
    assert "not found on JioSaavn" in data["detail"]
