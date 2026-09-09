import asyncio
import logging
from typing import Any

import requests

from core.cache import ttl_cache
from core.config import settings

logger = logging.getLogger(__name__)


def parse_languages(lang_str: str | None) -> list[str]:
    """
    Parses comma-separated language strings like 'english, malayalam, tamil'
    into a clean list of language strings ['english', 'malayalam', 'tamil'].
    """
    if not lang_str:
        return []
    return [lang.strip().lower() for lang in lang_str.split(",") if lang.strip()]


def is_compilation_song(song: dict[str, Any]) -> bool:
    """
    Checks if a song item is from a compilation album or playlist rather than
    an original single / studio soundtrack release.
    """
    album_name = ""
    album = song.get("album")
    if isinstance(album, dict):
        album_name = (album.get("name") or "").lower()
    elif isinstance(album, str):
        album_name = album.lower()

    img_url = ""
    imgs = song.get("image", [])
    if isinstance(imgs, list) and len(imgs) > 0:
        last = imgs[-1]
        img_url = (last.get("url") if isinstance(last, dict) else str(last)).lower()
    elif isinstance(imgs, str):
        img_url = imgs.lower()

    compilation_keywords = [
        "top trending", "trending songs", "playlist", "compilation",
        "various artists", "top 50", "top 20", "top 100", "best of 20"
    ]
    for kw in compilation_keywords:
        if kw in album_name or kw in img_url:
            return True
    return False


def interleave_results(results_list: list[list[dict[str, Any]]], total_limit: int | None = None) -> list[dict[str, Any]]:
    """
    Round-robin interleaves items from multiple language result groups.
    Ensures every requested language is fairly represented without only showing the first one.
    Deduplicates items by their 'id'.
    """
    if not results_list:
        return []
    if len(results_list) == 1:
        items = results_list[0]
        return items[:total_limit] if total_limit else items

    interleaved = []
    seen_ids = set()
    max_len = max((len(r) for r in results_list), default=0)

    for idx in range(max_len):
        for group in results_list:
            if idx < len(group):
                item = group[idx]
                item_id = item.get("id")
                if item_id and item_id not in seen_ids:
                    seen_ids.add(item_id)
                    interleaved.append(item)
                elif not item_id:
                    interleaved.append(item)

                if total_limit and len(interleaved) >= total_limit:
                    return interleaved

    return interleaved


class SaavnService:
    def __init__(self, base_url: str | None = None, timeout: float = 10.0):
        self.base_url = (base_url or settings.SAAVN_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "RhythmBackend/1.0",
            "Accept": "application/json"
        })

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        url = f"{self.base_url}{endpoint}"
        try:
            response = self._session.get(url, params=params, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Saavn API returned {response.status_code} for {url}: {response.text[:200]}")
                return None
        except Exception as e:
            logger.error(f"Error calling Saavn API at {url}: {e}")
            return None

    async def get_song_by_id(self, song_id: str) -> dict[str, Any] | None:
        """
        Retrieves song details by ID, cached for 1 day.
        Endpoint: /api/songs/{id}
        """
        cache_key = f"saavn_song:{song_id}"
        cached_song = ttl_cache.get(cache_key)
        if cached_song is not None:
            logger.info(f"Serving song {song_id} from cache")
            return cached_song

        def _fetch():
            data = self._get(f"/api/songs/{song_id}")
            if data and data.get("success") and data.get("data"):
                songs = data.get("data")
                if isinstance(songs, list) and len(songs) > 0:
                    return songs[0]
            return None

        song = await asyncio.to_thread(_fetch)
        if song:
            ttl_cache.set(cache_key, song, ttl=settings.HOME_CACHE_TTL_SECONDS)
        return song

    async def get_song_details_with_suggestions(self, song_id: str, limit: int = 10) -> dict[str, Any] | None:
        """
        Retrieves song details along with a list of suggested songs.
        Attempts JioSaavn /api/songs/{id}/suggestions with fallback to related artist/language search.
        Cached for 1 day.
        """
        cache_key = f"saavn_song_with_suggestions:{song_id}:{limit}"
        cached = ttl_cache.get(cache_key)
        if cached is not None:
            return cached

        song = await self.get_song_by_id(song_id)
        if not song:
            return None

        # Fetch suggestions
        suggestions = []
        def _fetch_sug():
            data = self._get(f"/api/songs/{song_id}/suggestions", params={"limit": limit})
            if data and data.get("success") and "data" in data:
                return data["data"]
            return []

        raw_suggestions = await asyncio.to_thread(_fetch_sug)
        if isinstance(raw_suggestions, list) and len(raw_suggestions) > 0:
            clean_sug = [s for s in raw_suggestions if str(s.get("id")) != str(song_id) and not is_compilation_song(s)]
            suggestions = clean_sug[:limit]

        # If suggestions endpoint fails or is empty, fallback to related search by artist / language
        if not suggestions:
            artist_name = ""
            artists = song.get("artists")
            if isinstance(artists, dict):
                primary = artists.get("primary", [])
                if isinstance(primary, list) and len(primary) > 0:
                    artist_name = primary[0].get("name", "")

            song_lang = song.get("language") or ""
            query_term = f"{artist_name} {song_lang} songs".strip() or f"{song_lang} songs".strip() or "songs"
            fallback_items = await self.search_songs(query=query_term, limit=limit + 3, language=song_lang or None)
            suggestions = [s for s in fallback_items if str(s.get("id")) != str(song_id)][:limit]

        result = {
            **song,
            "suggested_songs": suggestions
        }
        ttl_cache.set(cache_key, result, ttl=settings.HOME_CACHE_TTL_SECONDS)
        return result

    async def get_playlist_by_id(self, playlist_id: str) -> dict[str, Any] | None:
        """
        Retrieves playlist details by ID, cached for 1 day.
        Endpoint: /api/playlists?id={id}
        """
        cache_key = f"saavn_playlist:{playlist_id}"
        cached = ttl_cache.get(cache_key)
        if cached is not None:
            return cached

        def _fetch():
            data = self._get("/api/playlists", params={"id": playlist_id})
            if data and data.get("success") and "data" in data:
                return data["data"]
            return None

        playlist = await asyncio.to_thread(_fetch)
        if playlist:
            ttl_cache.set(cache_key, playlist, ttl=settings.HOME_CACHE_TTL_SECONDS)
        return playlist

    async def get_artist_by_id(self, artist_id: str, song_count: int = 10, album_count: int = 10) -> dict[str, Any] | None:
        """
        Retrieves artist details by ID, cached for 1 day.
        Endpoint: /api/artists/{id}?songCount={song_count}&albumCount={album_count}
        """
        cache_key = f"saavn_artist:{artist_id}:{song_count}:{album_count}"
        cached = ttl_cache.get(cache_key)
        if cached is not None:
            return cached

        def _fetch():
            data = self._get(f"/api/artists/{artist_id}", params={"songCount": song_count, "albumCount": album_count})
            if data and data.get("success") and "data" in data:
                return data["data"]
            return None

        artist = await asyncio.to_thread(_fetch)
        if artist:
            ttl_cache.set(cache_key, artist, ttl=settings.HOME_CACHE_TTL_SECONDS)
        return artist

    async def get_album_by_id(self, album_id: str) -> dict[str, Any] | None:
        """
        Retrieves album details by ID, cached for 1 day.
        Endpoint: /api/albums?id={id}
        """
        cache_key = f"saavn_album:{album_id}"
        cached = ttl_cache.get(cache_key)
        if cached is not None:
            return cached

        def _fetch():
            data = self._get("/api/albums", params={"id": album_id})
            if data and data.get("success") and "data" in data:
                return data["data"]
            return None

        album = await asyncio.to_thread(_fetch)
        if album:
            ttl_cache.set(cache_key, album, ttl=settings.HOME_CACHE_TTL_SECONDS)
        return album

    async def search_songs(self, query: str = "latest songs", limit: int = 10, language: str | None = None) -> list[dict[str, Any]]:
        """
        Search for songs, filtering out compilation playlist covers to ensure authentic song artwork.
        Cached for 1 day.
        Endpoint: /api/search/songs
        """
        cache_key = f"saavn_search_songs:{query}:{limit}"
        cached = ttl_cache.get(cache_key)
        if cached is not None:
            return cached

        def _fetch():
            # Fetch a wider batch to allow filtering out compilation covers
            fetch_limit = max(limit * 2, 20)
            data = self._get("/api/search/songs", params={"query": query, "limit": fetch_limit})
            if data and data.get("success") and "data" in data:
                res = data["data"].get("results", [])
                for item in res:
                    if language and not item.get("language"):
                        item["language"] = language

                # Filter out compilation playlist covers
                clean_songs = [s for s in res if not is_compilation_song(s)]
                # If filtering stripped everything, fall back to res so list isn't empty
                return clean_songs[:limit] if clean_songs else res[:limit]
            return []

        results = await asyncio.to_thread(_fetch)
        if results:
            ttl_cache.set(cache_key, results, ttl=settings.HOME_CACHE_TTL_SECONDS)
        return results

    async def search_playlists(self, query: str = "Top Playlists", limit: int = 10, language: str | None = None) -> list[dict[str, Any]]:
        """
        Search for playlists, cached for 1 day.
        Endpoint: /api/search/playlists
        """
        cache_key = f"saavn_search_playlists:{query}:{limit}"
        cached = ttl_cache.get(cache_key)
        if cached is not None:
            return cached

        def _fetch():
            data = self._get("/api/search/playlists", params={"query": query, "limit": limit})
            if data and data.get("success") and "data" in data:
                res = data["data"].get("results", [])
                for item in res:
                    if language and not item.get("language"):
                        item["language"] = language
                return res
            return []

        results = await asyncio.to_thread(_fetch)
        if results:
            ttl_cache.set(cache_key, results, ttl=settings.HOME_CACHE_TTL_SECONDS)
        return results

    async def search_albums(self, query: str = "Top Albums", limit: int = 10, language: str | None = None) -> list[dict[str, Any]]:
        """
        Search for albums, cached for 1 day.
        Endpoint: /api/search/albums
        """
        cache_key = f"saavn_search_albums:{query}:{limit}"
        cached = ttl_cache.get(cache_key)
        if cached is not None:
            return cached

        def _fetch():
            data = self._get("/api/search/albums", params={"query": query, "limit": limit})
            if data and data.get("success") and "data" in data:
                res = data["data"].get("results", [])
                for item in res:
                    if language and not item.get("language"):
                        item["language"] = language
                return res
            return []

        results = await asyncio.to_thread(_fetch)
        if results:
            ttl_cache.set(cache_key, results, ttl=settings.HOME_CACHE_TTL_SECONDS)
        return results

    async def search_artists(self, query: str = "Top Artists", limit: int = 10, language: str | None = None) -> list[dict[str, Any]]:
        """
        Search for artists, cached for 1 day.
        Endpoint: /api/search/artists
        """
        cache_key = f"saavn_search_artists:{query}:{limit}"
        cached = ttl_cache.get(cache_key)
        if cached is not None:
            return cached

        def _fetch():
            data = self._get("/api/search/artists", params={"query": query, "limit": limit})
            if data and data.get("success") and "data" in data:
                res = data["data"].get("results", [])
                for item in res:
                    if language and not item.get("language"):
                        item["language"] = language
                return res
            return []

        results = await asyncio.to_thread(_fetch)
        if results:
            ttl_cache.set(cache_key, results, ttl=settings.HOME_CACHE_TTL_SECONDS)
        return results

    async def fetch_home_sections(self, language: str | None = None, limit: int = 10) -> dict[str, list[dict[str, Any]]]:
        """
        Fetches trending songs, featured playlists, trending albums, and top artists.
        Supports single or multiple comma-separated languages (e.g. 'english, malayalam, tamil').
        When multiple languages are provided, fetches items for all languages and round-robin interleaves them.
        Uses authentic song search queries to avoid compilation/playlist covers.
        Caches the combined sections for 1 day (settings.HOME_CACHE_TTL_SECONDS = 86400s).
        """
        langs = parse_languages(language)
        normalized_langs = ",".join(sorted(langs)) if langs else "all"
        cache_key = f"saavn_home_sections:{normalized_langs}:{limit}"

        cached_sections = ttl_cache.get(cache_key)
        if cached_sections is not None:
            logger.info(f"Serving JioSaavn home sections from cache (key: {cache_key})")
            return cached_sections

        # Single language or default
        if len(langs) <= 1:
            lang = langs[0] if langs else None
            song_query = f"{lang} latest songs" if lang else "latest songs"
            playlist_query = f"{lang} Top Playlists" if lang else "Top Playlists"
            album_query = f"{lang} Top Albums" if lang else "Top Albums"
            artist_query = f"{lang} Top Artists" if lang else "Top Artists"

            songs, playlists, albums, artists = await asyncio.gather(
                self.search_songs(query=song_query, limit=limit, language=lang),
                self.search_playlists(query=playlist_query, limit=limit, language=lang),
                self.search_albums(query=album_query, limit=limit, language=lang),
                self.search_artists(query=artist_query, limit=limit, language=lang),
                return_exceptions=True
            )

            sections = {
                "trending_songs": songs if isinstance(songs, list) else [],
                "featured_playlists": playlists if isinstance(playlists, list) else [],
                "trending_albums": albums if isinstance(albums, list) else [],
                "top_artists": artists if isinstance(artists, list) else [],
            }
        else:
            # Multiple languages: fetch per language and interleave to show all languages
            fetch_limit = limit

            song_tasks = [self.search_songs(query=f"{lang} latest songs", limit=fetch_limit, language=lang) for lang in langs]
            playlist_tasks = [self.search_playlists(query=f"{lang} Top Playlists", limit=fetch_limit, language=lang) for lang in langs]
            album_tasks = [self.search_albums(query=f"{lang} Top Albums", limit=fetch_limit, language=lang) for lang in langs]
            artist_tasks = [self.search_artists(query=f"{lang} Top Artists", limit=fetch_limit, language=lang) for lang in langs]

            all_results = await asyncio.gather(
                asyncio.gather(*song_tasks, return_exceptions=True),
                asyncio.gather(*playlist_tasks, return_exceptions=True),
                asyncio.gather(*album_tasks, return_exceptions=True),
                asyncio.gather(*artist_tasks, return_exceptions=True),
            )

            songs_by_lang = [r for r in all_results[0] if isinstance(r, list)]
            playlists_by_lang = [r for r in all_results[1] if isinstance(r, list)]
            albums_by_lang = [r for r in all_results[2] if isinstance(r, list)]
            artists_by_lang = [r for r in all_results[3] if isinstance(r, list)]

            effective_limit = max(limit, len(langs))

            sections = {
                "trending_songs": interleave_results(songs_by_lang, total_limit=effective_limit),
                "featured_playlists": interleave_results(playlists_by_lang, total_limit=effective_limit),
                "trending_albums": interleave_results(albums_by_lang, total_limit=effective_limit),
                "top_artists": interleave_results(artists_by_lang, total_limit=effective_limit),
            }

        # Cache for 1 day if we received data
        if any(len(v) > 0 for v in sections.values()):
            ttl_cache.set(cache_key, sections, ttl=settings.HOME_CACHE_TTL_SECONDS)
            logger.info(f"Cached JioSaavn home sections for 1 day ({settings.HOME_CACHE_TTL_SECONDS}s)")

        return sections


saavn_service = SaavnService()
