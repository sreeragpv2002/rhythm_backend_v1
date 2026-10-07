import asyncio
import logging
import os
import tempfile
from typing import Any

import httpx
import yt_dlp

from core.cache import ttl_cache

logger = logging.getLogger(__name__)

# In-memory cache TTL for direct audio stream URLs (1 hour).
# YouTube stream URLs are valid for ~6 hours; 1 hour prevents expiration while avoiding repeat fetches.
STREAM_CACHE_TTL_SECONDS = 3600

# Decentralized fallback instances used if Render's datacenter IP is blocked by YouTube
PIPED_INSTANCES = [
    "https://api.piped.private.coffee",
    "https://pipedapi.kavin.rocks",
    "https://piped-api.lunar.icu",
    "https://pipedapi.tokhmi.xyz",
]

INVIDIOUS_INSTANCES = [
    "https://inv.tux.pizza",
    "https://invidious.nerdvpn.de",
    "https://vid.puffyan.us",
]


class StreamService:
    """
    Resolves YouTube / YouTube Music audio URLs into temporary direct audio stream URLs
    compatible with Flutter's `just_audio` package.

    Designed to handle datacenter cloud environments (e.g. Render, AWS, GCP):
    1. Primary: yt-dlp using Android/iOS InnerTube mobile clients (bypasses web bot checks).
    2. Optional: YOUTUBE_COOKIES_PATH, YOUTUBE_COOKIES, or PROXY_URL env vars if configured on Render.
    3. Resilient Fallback: Decentralized stream APIs (Piped & Invidious) if the server IP is restricted.
    """

    def __init__(self):
        self._cookie_file_path: str | None = None
        self._init_cookie_file()

    def _init_cookie_file(self) -> None:
        """Configures cookies from secret file path or inline environment variable string."""
        path = os.getenv("YOUTUBE_COOKIES_PATH")
        if path and os.path.exists(path):
            self._cookie_file_path = path
            logger.info(f"Loaded YouTube cookies from path: {path}")
            return

        cookies_raw = os.getenv("YOUTUBE_COOKIES")
        if cookies_raw and cookies_raw.strip():
            try:
                temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt")
                temp_file.write(cookies_raw.strip())
                temp_file.close()
                self._cookie_file_path = temp_file.name
                logger.info("Loaded YouTube cookies from YOUTUBE_COOKIES environment variable")
            except Exception as e:
                logger.error(f"Failed to create temporary cookies file: {e}")

    def _get_ydl_opts(self) -> dict[str, Any]:
        """Constructs yt-dlp options optimized for datacenter cloud environments."""
        opts: dict[str, Any] = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "extract_flat": False,
            # Use android and ios player clients to bypass desktop web bot checkpoints on cloud IPs
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "ios", "mweb"],
                    "player_skip": ["webpage", "configs"],
                }
            },
        }

        # Apply cookies if available
        if self._cookie_file_path and os.path.exists(self._cookie_file_path):
            opts["cookiefile"] = self._cookie_file_path

        # Apply proxy if configured
        proxy = os.getenv("PROXY_URL") or os.getenv("YOUTUBE_PROXY") or os.getenv("HTTPS_PROXY")
        if proxy:
            opts["proxy"] = proxy

        return opts

    def _extract_stream_url_sync(self, url: str) -> str | None:
        """Extracts stream URL using yt-dlp."""
        opts = self._get_ydl_opts()
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return None
                if "entries" in info and info["entries"]:
                    info = info["entries"][0]

                direct_url = info.get("url")
                if direct_url:
                    return direct_url

                formats = info.get("formats", [])
                for fmt in reversed(formats):
                    if fmt.get("acodec") != "none" and fmt.get("url"):
                        return fmt["url"]

                return None
        except Exception as e:
            logger.warning(f"yt-dlp extraction failed for {url} (expected on datacenter IPs without cookies): {e}")
            return None

    async def _fetch_from_piped_fallback(self, song_id: str) -> str | None:
        """Fallback to decentralized Piped API instances if yt-dlp is blocked on the server's IP."""
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        async with httpx.AsyncClient(timeout=5.0) as client:
            for base_url in PIPED_INSTANCES:
                try:
                    resp = await client.get(f"{base_url}/streams/{song_id}", headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        audio_streams = data.get("audioStreams", [])
                        if audio_streams:
                            # Prefer M4A for native Flutter just_audio playback on iOS & Android
                            for stream in audio_streams:
                                if stream.get("format") == "M4A" and stream.get("url"):
                                    return stream["url"]
                            return audio_streams[0].get("url")
                except Exception as e:
                    logger.debug(f"Piped instance {base_url} failed for {song_id}: {e}")
        return None

    async def _fetch_from_invidious_fallback(self, song_id: str) -> str | None:
        """Fallback to Invidious instances if Piped is unavailable."""
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        async with httpx.AsyncClient(timeout=5.0) as client:
            for base_url in INVIDIOUS_INSTANCES:
                try:
                    resp = await client.get(f"{base_url}/api/v1/videos/{song_id}", headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        adaptive_formats = data.get("adaptiveFormats", [])
                        for fmt in adaptive_formats:
                            if fmt.get("type", "").startswith("audio/mp4") and fmt.get("url"):
                                return fmt["url"]
                        for fmt in adaptive_formats:
                            if fmt.get("type", "").startswith("audio/") and fmt.get("url"):
                                return fmt["url"]
                except Exception as e:
                    logger.debug(f"Invidious instance {base_url} failed for {song_id}: {e}")
        return None

    async def get_audio_stream_url(self, song_id: str, song_url: str | None = None) -> str | None:
        """
        Resolves a temporary direct audio stream URL for a given song ID or URL.
        Caches in-memory for 1 hour to speed up playback and avoid repeated yt-dlp queries.
        Never written to database.
        """
        if not song_id and not song_url:
            return None

        clean_id = str(song_id or "").strip()
        cache_key = f"stream_mp3:{clean_id}" if clean_id else f"stream_mp3:{song_url}"
        cached_url = ttl_cache.get(cache_key)
        if cached_url:
            return cached_url

        target_url = (
            song_url
            if (song_url and (song_url.startswith("http://") or song_url.startswith("https://")))
            else f"https://www.youtube.com/watch?v={clean_id}"
        )

        # 1. Primary: yt-dlp (with Android/iOS client and optional cookies/proxy)
        direct_url = await asyncio.to_thread(self._extract_stream_url_sync, target_url)

        # 2. Secondary fallback: Piped instances (ideal for datacenter IPs like Render)
        if not direct_url and clean_id:
            logger.info(f"Attempting Piped fallback stream resolution for song {clean_id}...")
            direct_url = await self._fetch_from_piped_fallback(clean_id)

        # 3. Tertiary fallback: Invidious instances
        if not direct_url and clean_id:
            logger.info(f"Attempting Invidious fallback stream resolution for song {clean_id}...")
            direct_url = await self._fetch_from_invidious_fallback(clean_id)

        if direct_url:
            ttl_cache.set(cache_key, direct_url, ttl=STREAM_CACHE_TTL_SECONDS)
        else:
            logger.error(f"Could not resolve audio stream URL for song {clean_id or target_url}")

        return direct_url


stream_service = StreamService()
