import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from app.main import app
from core.firebase import get_firestore_db

client = TestClient(app)

TEST_USER_ID = "test_user_rhythm_qa"
TEST_SONG_ID = "UPJYO3v0"  # Real song ID on JioSaavn: "Ishq de Fanniyar - Female"


def setup():
    print(f"Setting up test user: {TEST_USER_ID} in Firestore...")
    db = get_firestore_db()
    user_ref = db.collection("users").document(TEST_USER_ID)
    user_ref.set({"name": "Test QA User", "email": "test_qa@rhythm.local"})
    print("Test user created.")


def teardown():
    print("Cleaning up test data in Firestore...")
    db = get_firestore_db()
    user_ref = db.collection("users").document(TEST_USER_ID)
    recent_docs = user_ref.collection("recent_plays").stream()
    for doc in recent_docs:
        doc.reference.delete()
    pl_docs = user_ref.collection("playlists").stream()
    for doc in pl_docs:
        for s in doc.reference.collection("songs").stream():
            s.reference.delete()
        doc.reference.delete()
    user_ref.delete()
    print("Cleanup complete.")


def run_all():
    setup()
    passed = 0
    failed = 0

    tests = [
        ("test_health_check", test_health_check),
        ("test_user_verification_failure_for_home", test_user_verification_failure_for_home),
        ("test_user_verification_failure_for_recent_plays_post", test_user_verification_failure_for_recent_plays_post),
        ("test_user_verification_failure_for_recent_plays_get", test_user_verification_failure_for_recent_plays_get),
        ("test_post_recent_play_success", test_post_recent_play_success),
        ("test_get_recent_plays_success", test_get_recent_plays_success),
        ("test_get_home_api_success", test_get_home_api_success),
        ("test_home_sections_caching", test_home_sections_caching),
        ("test_multi_language_home_filter", test_multi_language_home_filter),
        ("test_get_available_languages", test_get_available_languages),
        ("test_set_user_languages_success", test_set_user_languages_success),
        ("test_get_user_languages_success", test_get_user_languages_success),
        ("test_edit_user_languages_put", test_edit_user_languages_put),
        ("test_set_user_languages_invalid", test_set_user_languages_invalid),
        ("test_home_api_uses_saved_user_languages", test_home_api_uses_saved_user_languages),
        ("test_post_invalid_song_id", test_post_invalid_song_id),
        ("test_home_song_image_not_playlist_cover", test_home_song_image_not_playlist_cover),
        ("test_unified_details_song_with_suggestions", test_unified_details_song_with_suggestions),
        ("test_unified_details_song_by_path", test_unified_details_song_by_path),
        ("test_dedicated_song_details", test_dedicated_song_details),
        ("test_unified_details_playlist", test_unified_details_playlist),
        ("test_unified_details_artist", test_unified_details_artist),
        ("test_unified_details_album", test_unified_details_album),
        ("test_unified_details_invalid_type", test_unified_details_invalid_type),
        ("test_unified_details_song_not_found", test_unified_details_song_not_found),
        ("test_add_favorite_song", test_add_favorite_song),
        ("test_get_favorites", test_get_favorites),
        ("test_check_favorite", test_check_favorite),
        ("test_remove_favorite_song", test_remove_favorite_song),
        ("test_remove_favorite_by_path", test_remove_favorite_by_path),
        ("test_create_user_playlist", test_create_user_playlist),
        ("test_get_user_playlists_includes_favorites", test_get_user_playlists_includes_favorites),
        ("test_add_and_remove_song_from_custom_playlist", test_add_and_remove_song_from_custom_playlist),
        ("test_delete_custom_playlist", test_delete_custom_playlist),
        ("test_unified_details_for_user_favorites", test_unified_details_for_user_favorites),
    ]

    try:
        for name, fn in tests:
            try:
                fn()
                print(f"  PASSED: {name}")
                passed += 1
            except Exception:
                print(f"  FAILED: {name}")
                traceback.print_exc()
                failed += 1
    finally:
        teardown()

    print(f"\nSummary: {passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Rhythm Backend"


def test_user_verification_failure_for_home():
    response = client.get("/api/v1/home?user_id=unknown_fake_user_99999")
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    data = response.json()
    assert "not found in Firebase" in data["detail"]


def test_user_verification_failure_for_recent_plays_post():
    response = client.post(
        "/api/v1/recent-plays",
        json={"user_id": "unknown_fake_user_99999", "song_id": TEST_SONG_ID}
    )
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    data = response.json()
    assert "not found in Firebase" in data["detail"]


def test_user_verification_failure_for_recent_plays_get():
    response = client.get("/api/v1/recent-plays?user_id=unknown_fake_user_99999")
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    data = response.json()
    assert "not found in Firebase" in data["detail"]


def test_post_recent_play_success():
    response = client.post(
        "/api/v1/recent-plays",
        json={"user_id": TEST_USER_ID, "song_id": TEST_SONG_ID}
    )
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert data["data"]["id"] == TEST_SONG_ID
    assert "name" in data["data"]
    assert "played_at" in data["data"]


def test_get_recent_plays_success():
    response = client.get(f"/api/v1/recent-plays?user_id={TEST_USER_ID}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data["success"] is True
    assert isinstance(data["data"], list)
    assert len(data["data"]) >= 1
    assert data["data"][0]["id"] == TEST_SONG_ID


def test_get_home_api_success():
    response = client.get(f"/api/v1/home?user_id={TEST_USER_ID}&limit=5")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["success"] is True
    home_data = data["data"]

    # Verify recent_plays contains our saved test song
    assert "recent_plays" in home_data, "recent_plays missing"
    assert len(home_data["recent_plays"]) >= 1, "recent_plays is empty"
    assert home_data["recent_plays"][0]["id"] == TEST_SONG_ID

    # Verify Saavn sections are populated
    assert "trending_songs" in home_data, "trending_songs missing"
    assert len(home_data["trending_songs"]) > 0, "trending_songs is empty"

    assert "featured_playlists" in home_data, "featured_playlists missing"
    assert len(home_data["featured_playlists"]) > 0, "featured_playlists is empty"

    assert "trending_albums" in home_data, "trending_albums missing"
    assert len(home_data["trending_albums"]) > 0, "trending_albums is empty"

    assert "top_artists" in home_data, "top_artists missing"
    assert len(home_data["top_artists"]) > 0, "top_artists is empty"

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
    import time

    from core.cache import ttl_cache
    from core.config import settings

    # Verify TTL is 1 day (86400s)
    assert settings.HOME_CACHE_TTL_SECONDS == 86400, "Expected 86400s (1 day) TTL"

    # Reset cache stats
    ttl_cache.clear()
    stats_initial = ttl_cache.get_stats()
    assert stats_initial["hits"] == 0
    assert stats_initial["active_items"] == 0

    # 1st call: Cache miss, fetches from JioSaavn API
    t0 = time.time()
    resp1 = client.get(f"/api/v1/home?user_id={TEST_USER_ID}&limit=5")
    duration1 = time.time() - t0
    assert resp1.status_code == 200

    stats_after_first = ttl_cache.get_stats()
    assert stats_after_first["active_items"] > 0, "Expected items to be stored in cache"
    initial_hits = stats_after_first["hits"]

    # 2nd call: Must hit cache and NOT call JioSaavn API again
    t1 = time.time()
    resp2 = client.get(f"/api/v1/home?user_id={TEST_USER_ID}&limit=5")
    duration2 = time.time() - t1
    assert resp2.status_code == 200

    stats_after_second = ttl_cache.get_stats()
    assert stats_after_second["hits"] > initial_hits, "Expected cache hit on 2nd request"

    # Content verification
    data1 = resp1.json()["data"]
    data2 = resp2.json()["data"]
    assert data1["trending_songs"] == data2["trending_songs"]
    assert data1["featured_playlists"] == data2["featured_playlists"]
    assert data1["trending_albums"] == data2["trending_albums"]
    assert data1["top_artists"] == data2["top_artists"]


def test_multi_language_home_filter():
    response = client.get(f"/api/v1/home?user_id={TEST_USER_ID}&language=english, malayalam, tamil&limit=10")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()["data"]

    # Verify all 3 languages are present in trending_songs
    song_langs = set(s.get("language") for s in data["trending_songs"])
    assert "english" in song_langs, f"english missing in trending_songs: {song_langs}"
    assert "malayalam" in song_langs, f"malayalam missing in trending_songs: {song_langs}"
    assert "tamil" in song_langs, f"tamil missing in trending_songs: {song_langs}"

    # Verify all 3 languages are present in featured_playlists
    playlist_langs = set(p.get("language") for p in data["featured_playlists"])
    assert "english" in playlist_langs, f"english missing in featured_playlists: {playlist_langs}"
    assert "malayalam" in playlist_langs, f"malayalam missing in featured_playlists: {playlist_langs}"
    assert "tamil" in playlist_langs, f"tamil missing in featured_playlists: {playlist_langs}"

    # Verify all 3 languages are present in trending_albums
    album_langs = set(a.get("language") for a in data["trending_albums"])
    assert "english" in album_langs, f"english missing in trending_albums: {album_langs}"
    assert "malayalam" in album_langs, f"malayalam missing in trending_albums: {album_langs}"
    assert "tamil" in album_langs, f"tamil missing in trending_albums: {album_langs}"

    # Verify all 3 languages are present in top_artists
    artist_langs = set(ar.get("language") for ar in data["top_artists"])
    assert "english" in artist_langs, f"english missing in top_artists: {artist_langs}"
    assert "malayalam" in artist_langs, f"malayalam missing in top_artists: {artist_langs}"
    assert "tamil" in artist_langs, f"tamil missing in top_artists: {artist_langs}"


def test_get_available_languages():
    response = client.get("/api/v1/languages")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert data["success"] is True
    expected = ["malayalam", "tamil", "hindi", "kannada", "telugu", "english"]
    assert data["data"] == expected, f"Expected {expected}, got {data['data']}"


def test_set_user_languages_success():
    response = client.post(
        "/api/v1/languages/user",
        json={"user_id": TEST_USER_ID, "languages": ["malayalam", "tamil"]}
    )
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["success"] is True
    assert data["data"]["languages"] == ["malayalam", "tamil"]


def test_get_user_languages_success():
    response = client.get(f"/api/v1/languages/user?user_id={TEST_USER_ID}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["success"] is True
    assert data["data"]["languages"] == ["malayalam", "tamil"]


def test_edit_user_languages_put():
    response = client.put(
        "/api/v1/languages/user",
        json={"user_id": TEST_USER_ID, "languages": ["kannada", "telugu", "english"]}
    )
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["success"] is True
    assert data["data"]["languages"] == ["kannada", "telugu", "english"]

    # Verify read back
    get_res = client.get(f"/api/v1/languages/user?user_id={TEST_USER_ID}")
    assert get_res.json()["data"]["languages"] == ["kannada", "telugu", "english"]


def test_set_user_languages_invalid():
    # Attempting to post unsupported languages like 'spanish'
    response = client.post(
        "/api/v1/languages/user",
        json={"user_id": TEST_USER_ID, "languages": ["spanish", "french"]}
    )
    assert response.status_code in (400, 422), f"Expected 400 or 422, got {response.status_code}"


def test_home_api_uses_saved_user_languages():
    # Set user languages to malayalam and tamil
    client.put(
        "/api/v1/languages/user",
        json={"user_id": TEST_USER_ID, "languages": ["malayalam", "tamil"]}
    )
    # Call Home API WITHOUT language query parameter
    response = client.get(f"/api/v1/home?user_id={TEST_USER_ID}&limit=6")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()["data"]

    # Verify user_languages and languages sections in Home response
    assert "user_languages" in data, "user_languages missing from home data"
    assert data["user_languages"] == ["malayalam", "tamil"], f"Expected ['malayalam', 'tamil'], got {data['user_languages']}"

    assert "languages" in data, "languages missing from home data"
    assert len(data["languages"]) == 2, f"Expected 2 language items, got {len(data['languages'])}"
    assert data["languages"][0]["id"] == "malayalam"
    assert data["languages"][0]["name"] == "Malayalam"
    assert data["languages"][0]["image_url"].startswith("http")
    assert data["languages"][0]["type"] == "language"
    assert data["languages"][1]["id"] == "tamil"
    assert data["languages"][1]["name"] == "Tamil"
    assert data["languages"][1]["image_url"].startswith("http")
    assert data["languages"][1]["type"] == "language"

    # Check that songs contain both saved languages
    song_langs = set(s.get("language") for s in data["trending_songs"])
    assert "malayalam" in song_langs or "tamil" in song_langs, f"Saved languages not reflected: {song_langs}"


def test_post_invalid_song_id():
    response = client.post(
        "/api/v1/recent-plays",
        json={"user_id": TEST_USER_ID, "song_id": "non_existent_song_id_000"}
    )
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    data = response.json()
    assert "not found on JioSaavn" in data["detail"]


def test_home_song_image_not_playlist_cover():
    response = client.get(f"/api/v1/home?user_id={TEST_USER_ID}&language=malayalam&limit=5")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    songs = response.json()["data"]["trending_songs"]
    assert len(songs) > 0, "Expected trending_songs to be populated"
    for s in songs:
        img = s.get("image", "").lower()
        # Verify it does NOT use compilation playlist artwork like Top-Trending-Love-Songs-Malayalam
        assert "top-trending-love-songs" not in img, f"Found compilation playlist image instead of song cover: {img}"
        assert img.startswith("http"), f"Invalid image URL: {img}"


def test_unified_details_song_with_suggestions():
    response = client.get(f"/api/v1/details?type=song&id={TEST_SONG_ID}&limit=5")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    body = response.json()
    assert body["success"] is True
    assert body["type"] == "song"
    data = body["data"]
    assert data["id"] == TEST_SONG_ID
    assert data["name"]
    assert data["image_url"].startswith("http")
    # Verify suggested_songs list is returned
    assert "suggested_songs" in data
    assert isinstance(data["suggested_songs"], list)
    assert len(data["suggested_songs"]) > 0, "Expected suggested songs list to be populated"
    first_sug = data["suggested_songs"][0]
    assert "id" in first_sug
    assert "name" in first_sug
    assert "image_url" in first_sug
    assert first_sug["id"] != TEST_SONG_ID, "Suggested song should not be the current song"


def test_unified_details_song_by_path():
    response = client.get(f"/api/v1/details/song/{TEST_SONG_ID}?limit=3")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    body = response.json()
    assert body["success"] is True
    assert body["type"] == "song"
    assert body["data"]["id"] == TEST_SONG_ID
    assert len(body["data"]["suggested_songs"]) > 0


def test_dedicated_song_details():
    response = client.get(f"/api/v1/songs/{TEST_SONG_ID}?limit=3")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    body = response.json()
    assert body["success"] is True
    assert body["type"] == "song"
    assert body["data"]["id"] == TEST_SONG_ID
    assert len(body["data"]["suggested_songs"]) > 0


def test_unified_details_playlist():
    # Real JioSaavn playlist: "Malayalam 2000s"
    response = client.get("/api/v1/details?type=playlist&id=1181705742")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    body = response.json()
    assert body["success"] is True
    assert body["type"] == "playlist"
    data = body["data"]
    assert data["name"]
    assert "songs" in data
    assert isinstance(data["songs"], list)
    assert len(data["songs"]) > 0
    assert data["songs"][0]["image_url"].startswith("http")


def test_unified_details_artist():
    # Real JioSaavn artist: "Arijit Singh"
    response = client.get("/api/v1/details?type=artist&id=459320&song_count=5")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    body = response.json()
    assert body["success"] is True
    assert body["type"] == "artist"
    data = body["data"]
    assert data["name"]
    assert "topSongs" in data or "top_songs" in data
    top_songs = data.get("topSongs") or data.get("top_songs")
    assert len(top_songs) > 0


def test_unified_details_album():
    # Real JioSaavn album: "Paramathma"
    response = client.get("/api/v1/details?type=album&id=17787537")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    body = response.json()
    assert body["success"] is True
    assert body["type"] == "album"
    data = body["data"]
    assert data["name"] == "Paramathma"
    assert "songs" in data
    assert len(data["songs"]) > 0


def test_unified_details_invalid_type():
    response = client.get("/api/v1/details?type=podcast&id=123")
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"
    data = response.json()
    assert "Invalid details type" in data["detail"]


def test_unified_details_song_not_found():
    response = client.get("/api/v1/details?type=song&id=invalid_song_999999")
    assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    data = response.json()
    assert "not found on JioSaavn" in data["detail"]


CREATED_PLAYLIST_ID = None


def test_add_favorite_song():
    response = client.post(
        "/api/v1/favorites",
        json={"user_id": TEST_USER_ID, "song_id": TEST_SONG_ID}
    )
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["name"] == "Favorites"
    assert data["is_favorite"] is True
    assert data["song_count"] >= 1
    assert any(s["id"] == TEST_SONG_ID for s in data.get("songs", []))


def test_get_favorites():
    response = client.get(f"/api/v1/favorites?user_id={TEST_USER_ID}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["name"] == "Favorites"
    assert data["is_favorite"] is True
    assert len(data.get("songs", [])) >= 1
    song = data["songs"][0]
    assert song["id"] == TEST_SONG_ID
    assert song["image_url"].startswith("http")


def test_check_favorite():
    response = client.get(f"/api/v1/favorites/check?user_id={TEST_USER_ID}&song_id={TEST_SONG_ID}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    body = response.json()
    assert body["success"] is True
    assert body["is_favorite"] is True


def test_remove_favorite_song():
    response = client.delete(f"/api/v1/favorites?user_id={TEST_USER_ID}&song_id={TEST_SONG_ID}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    check_resp = client.get(f"/api/v1/favorites/check?user_id={TEST_USER_ID}&song_id={TEST_SONG_ID}")
    assert check_resp.json()["is_favorite"] is False


def test_remove_favorite_by_path():
    add_resp = client.post("/api/v1/favorites", json={"user_id": TEST_USER_ID, "song_id": TEST_SONG_ID})
    assert add_resp.status_code == 201
    del_resp = client.delete(f"/api/v1/favorites/{TEST_SONG_ID}?user_id={TEST_USER_ID}")
    assert del_resp.status_code == 200
    check_resp = client.get(f"/api/v1/favorites/check?user_id={TEST_USER_ID}&song_id={TEST_SONG_ID}")
    assert check_resp.json()["is_favorite"] is False


def test_create_user_playlist():
    global CREATED_PLAYLIST_ID
    response = client.post(
        "/api/v1/user-playlists",
        json={
            "user_id": TEST_USER_ID,
            "name": "Weekend Chill Vibes",
            "description": "My curated chill tracks"
        }
    )
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["name"] == "Weekend Chill Vibes"
    assert data["is_favorite"] is False
    assert data["id"].startswith("pl_")
    CREATED_PLAYLIST_ID = data["id"]


def test_get_user_playlists_includes_favorites():
    response = client.get(f"/api/v1/user-playlists?user_id={TEST_USER_ID}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    body = response.json()
    assert body["success"] is True
    playlists = body["data"]
    assert len(playlists) >= 2, f"Expected at least 2 playlists, got {len(playlists)}"
    first = playlists[0]
    assert first["id"] == "favorites"
    assert first["is_favorite"] is True
    assert first["name"] == "Favorites"
    custom = [p for p in playlists if p["id"] == CREATED_PLAYLIST_ID]
    assert len(custom) == 1
    assert custom[0]["name"] == "Weekend Chill Vibes"


def test_add_and_remove_song_from_custom_playlist():
    assert CREATED_PLAYLIST_ID is not None
    add_resp = client.post(
        f"/api/v1/user-playlists/{CREATED_PLAYLIST_ID}/songs",
        json={"user_id": TEST_USER_ID, "song_id": TEST_SONG_ID}
    )
    assert add_resp.status_code == 201, f"Expected 201, got {add_resp.status_code}: {add_resp.text}"
    data = add_resp.json()["data"]
    assert data["song_count"] == 1
    assert data["songs"][0]["id"] == TEST_SONG_ID

    del_resp = client.delete(f"/api/v1/user-playlists/{CREATED_PLAYLIST_ID}/songs/{TEST_SONG_ID}?user_id={TEST_USER_ID}")
    assert del_resp.status_code == 200
    get_resp = client.get(f"/api/v1/user-playlists/{CREATED_PLAYLIST_ID}?user_id={TEST_USER_ID}")
    assert get_resp.json()["data"]["song_count"] == 0


def test_delete_custom_playlist():
    assert CREATED_PLAYLIST_ID is not None
    fav_del = client.delete(f"/api/v1/user-playlists/favorites?user_id={TEST_USER_ID}")
    assert fav_del.status_code == 400

    del_resp = client.delete(f"/api/v1/user-playlists/{CREATED_PLAYLIST_ID}?user_id={TEST_USER_ID}")
    assert del_resp.status_code == 200

    get_resp = client.get(f"/api/v1/user-playlists/{CREATED_PLAYLIST_ID}?user_id={TEST_USER_ID}")
    assert get_resp.status_code == 404


def test_unified_details_for_user_favorites():
    client.post("/api/v1/favorites", json={"user_id": TEST_USER_ID, "song_id": TEST_SONG_ID})
    response = client.get(f"/api/v1/details?type=playlist&id=favorites&user_id={TEST_USER_ID}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    body = response.json()
    assert body["success"] is True
    assert body["type"] == "playlist"
    assert body["data"]["id"] == "favorites"
    assert body["data"]["is_favorite"] is True
    assert len(body["data"]["songs"]) >= 1


if __name__ == "__main__":
    run_all()
