import asyncio
import logging
import re
from typing import Any

import requests

from core.cache import ttl_cache
from core.config import settings

logger = logging.getLogger(__name__)


def clean_song_title(title: str) -> str:
    """
    Cleans song titles by stripping extraneous video metadata, brackets, and labels.
    Example: 'Premalu | Kuthanthram Video Song | Fahadh Faasil' -> 'Kuthanthram'
    """
    if not title:
        return ""
    # Remove contents inside brackets/parentheses like (Official Video), [4K], (Lyrical), (From "Movie")
    cleaned = re.sub(r"\[.*?\]|\(.*?\)", "", title)
    # Remove common video keywords
    cleaned = re.sub(
        r"\b(official video|video song|lyrical video|full song|audio song|4k video|remix|hd|visualizer)\b",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    # Split by pipe or hyphen if common in YouTube titles
    parts = [p.strip() for p in re.split(r"[|•\-:]", cleaned) if p.strip()]
    if parts:
        # Prefer the first or second meaningful segment
        return parts[0]
    return cleaned.strip()


def extract_best_cdn_audio(download_data: Any) -> tuple[str, list[dict[str, str]], str]:
    """
    Extracts the highest bitrate direct audio CDN URL, list of all quality streams,
    and the quality label from JioSaavn downloadUrl payload.
    """
    if not download_data:
        return "", [], ""

    if isinstance(download_data, str):
        return download_data, [{"quality": "standard", "url": download_data}], "standard"

    if isinstance(download_data, list) and len(download_data) > 0:
        clean_list = []
        for item in download_data:
            if isinstance(item, dict) and item.get("url"):
                clean_list.append({"quality": str(item.get("quality", "unknown")), "url": str(item["url"])})

        if not clean_list:
            return "", [], ""

        # Find 320kbps first, fallback to 160kbps, or the last available item
        best = next((x for x in clean_list if "320" in x["quality"]), None)
        if not best:
            best = next((x for x in clean_list if "160" in x["quality"]), None)
        if not best:
            best = clean_list[-1]

        return best["url"], clean_list, best["quality"]

    return "", [], ""


class CDNStreamService:
    def __init__(self, base_url: str | None = None, timeout: float = 8.0):
        self.base_url = (base_url or settings.SAAVN_BASE_URL).rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "RhythmBackend/1.0",
            "Accept": "application/json",
        })

    def _get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        url = f"{self.base_url}{endpoint}"
        try:
            response = self._session.get(url, params=params, timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
            logger.warning(f"JioSaavn API status {response.status_code} for {url}")
            return None
        except Exception as e:
            logger.error(f"Error calling JioSaavn API at {url}: {e}")
            return None

    async def get_song_by_saavn_id(self, song_id: str) -> dict[str, Any] | None:
        """
        Direct lookup for JioSaavn Song ID.
        """
        def _fetch():
            data = self._get(f"/api/songs/{song_id}")
            if data and data.get("success") and data.get("data"):
                items = data.get("data")
                if isinstance(items, list) and len(items) > 0:
                    return items[0]
            return None

        return await asyncio.to_thread(_fetch)

    async def search_saavn_song(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """
        Searches JioSaavn for songs matching query.
        """
        def _fetch():
            data = self._get("/api/search/songs", params={"query": query, "limit": limit})
            if data and data.get("success") and "data" in data:
                return data["data"].get("results", [])
            return []

        return await asyncio.to_thread(_fetch)

    async def resolve_cdn_stream(
        self,
        song_id: str,
        title: str | None = None,
        artist: str | None = None
    ) -> dict[str, Any] | None:
        """
        Retrieves direct CDN audio stream links for any song without scraping YouTube.
        1. Checks TTL cache.
        2. Tries direct JioSaavn ID lookup.
        3. If not found or if ID is a YouTube ID, resolves via metadata matching on JioSaavn CDN.
        4. Returns direct CDN stream metadata (320kbps MP3 / M4A stream).
        """
        cache_key = f"cdn_stream_v1:{song_id}:{title or ''}:{artist or ''}"
        cached = ttl_cache.get(cache_key)
        if cached is not None:
            return cached

        saavn_song = None

        # 1. Try direct ID lookup if ID does not look like a 11-char YouTube ID
        if len(song_id) != 11:
            saavn_song = await self.get_song_by_saavn_id(song_id)

        # 2. If title is not passed and direct lookup was empty, resolve title/artist from YTMusic metadata
        if not saavn_song and (not title or len(title.strip()) == 0):
            from app.services.ytmusic_service import ytmusic_service
            yt_song = await ytmusic_service.get_song_by_id(song_id)
            if yt_song:
                title = yt_song.get("name") or yt_song.get("title")
                artist = yt_song.get("artist") or yt_song.get("subtitle")

        # 3. Match against JioSaavn search using title and artist
        if not saavn_song and title:
            clean_title = clean_song_title(title)
            clean_artist = (artist or "").split(",")[0].strip()

            queries = [
                f"{clean_title} {clean_artist}".strip(),
                clean_title,
                title,
            ]

            for q in queries:
                if not q:
                    continue
                results = await self.search_saavn_song(query=q, limit=5)
                if results:
                    # Select the closest match
                    saavn_song = results[0]
                    break

        if not saavn_song:
            return None

        # Extract direct CDN audio link
        best_url, quality_list, quality = extract_best_cdn_audio(saavn_song.get("downloadUrl"))
        if not best_url:
            return None

        audio_format = "m4a"
        if ".mp3" in best_url.lower():
            audio_format = "mp3"
        elif ".mp4" in best_url.lower():
            audio_format = "m4a"

        result = {
            "id": song_id,
            "saavn_id": str(saavn_song.get("id", "")),
            "title": saavn_song.get("name") or title or "",
            "name": saavn_song.get("name") or title or "",
            "artist": saavn_song.get("artist") or artist or "",
            "stream_url": best_url,
            "download_url": best_url,
            "download_urls": quality_list,
            "quality": quality or "320kbps",
            "format": audio_format,
            "duration": int(saavn_song.get("duration", 0)) if saavn_song.get("duration") else None,
            "source": "saavn_cdn",
            "is_direct_cdn": True,
        }

        ttl_cache.set(cache_key, result, ttl=settings.HOME_CACHE_TTL_SECONDS)
        return result


cdn_stream_service = CDNStreamService()
