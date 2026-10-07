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

    def _create_writable_copy(self, source_path: str) -> str:
        """
        Creates a writable copy of the cookie file in the system temp directory.
        Render mounts secret files at /etc/secrets as read-only volumes.
        yt-dlp attempts to write updated session tokens back to the cookie file,
        causing [Errno 30] Read-only file system unless copied to a writable directory.
        """
        try:
            target_path = os.path.join(tempfile.gettempdir(), "yt_cookies_writable.txt")
            with open(source_path, encoding="utf-8", errors="ignore") as src:
                content = src.read()
            with open(target_path, "w", encoding="utf-8") as dst:
                dst.write(content)
            return target_path
        except Exception as e:
            logger.warning(f"Could not create writable copy of cookies from {source_path}: {e}")
            return source_path

    def _init_cookie_file(self) -> None:
        """Configures cookies from secret file path or inline environment variable string."""
        # 1. Custom path from env var
        path = os.getenv("YOUTUBE_COOKIES_PATH")
        if path and os.path.exists(path):
            self._cookie_file_path = self._create_writable_copy(path)
            logger.info(f"Loaded YouTube cookies from path: {path} (writable copy at {self._cookie_file_path})")
            return

        # 2. Render default secret file path (/etc/secrets/cookies.txt)
        render_path = "/etc/secrets/cookies.txt"
        if os.path.exists(render_path):
            self._cookie_file_path = self._create_writable_copy(render_path)
            logger.info(f"Loaded YouTube cookies from Render secret file: {render_path} (writable copy at {self._cookie_file_path})")
            return

        # 3. Local fallback paths (credentials/cookies.txt or cookies.txt)
        for local_path in ["credentials/cookies.txt", "cookies.txt"]:
            if os.path.exists(local_path):
                self._cookie_file_path = self._create_writable_copy(local_path)
                logger.info(f"Loaded YouTube cookies from local file: {local_path} (writable copy at {self._cookie_file_path})")
                return

        # 4. Inline env var string (YOUTUBE_COOKIES)
        cookies_raw = os.getenv("YOUTUBE_COOKIES")
        if cookies_raw and cookies_raw.strip():
            try:
                target_path = os.path.join(tempfile.gettempdir(), "yt_cookies_writable.txt")
                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(cookies_raw.strip())
                self._cookie_file_path = target_path
                logger.info("Loaded YouTube cookies from YOUTUBE_COOKIES environment variable")
            except Exception as e:
                logger.error(f"Failed to create temporary cookies file: {e}")

    def get_cookie_file_path(self) -> str | None:
        """Returns the active cookie file path or re-checks paths if not currently set."""
        if not self._cookie_file_path or not os.path.exists(self._cookie_file_path):
            self._init_cookie_file()
        return self._cookie_file_path

    def _get_ydl_opts(self) -> dict[str, Any]:
        """Constructs yt-dlp options optimized for datacenter cloud environments."""
        if not self._cookie_file_path or not os.path.exists(self._cookie_file_path):
            self._init_cookie_file()

        opts: dict[str, Any] = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "extract_flat": False,
            "cachedir": False,
            "socket_timeout": 12,
        }

        # Apply cookies if available
        if self._cookie_file_path and os.path.exists(self._cookie_file_path):
            opts["cookiefile"] = self._cookie_file_path
            # Allow yt-dlp to use its smart multi-client cascade (visionos, mweb, etc.)
            # Do not force web/android which triggers cloud datacenter bot challenges
        else:
            # Fallback when no cookies: use mobile android/ios clients
            opts["extractor_args"] = {
                "youtube": {
                    "player_client": ["android", "ios"],
                    "player_skip": ["webpage", "configs"],
                },
                "youtubemusic": {
                    "player_client": ["android", "ios"],
                },
            }

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

    async def _try_piped_instance(self, client: httpx.AsyncClient, base_url: str, song_id: str) -> str | None:
        try:
            resp = await client.get(
                f"{base_url}/streams/{song_id}",
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            if resp.status_code == 200:
                data = resp.json()
                audio_streams = data.get("audioStreams", [])
                for stream in audio_streams:
                    if stream.get("format") == "M4A" and stream.get("url"):
                        return stream["url"]
                if audio_streams and audio_streams[0].get("url"):
                    return audio_streams[0]["url"]
        except Exception:
            pass
        return None

    async def _fetch_from_piped_fallback(self, song_id: str) -> str | None:
        """Concurrent fallback to decentralized Piped API instances if yt-dlp is blocked on the server's IP."""
        async with httpx.AsyncClient(timeout=3.5) as client:
            tasks = [self._try_piped_instance(client, url, song_id) for url in PIPED_INSTANCES[:3]]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, str) and res.startswith("http"):
                    return res
        return None

    async def _try_invidious_instance(self, client: httpx.AsyncClient, base_url: str, song_id: str) -> str | None:
        try:
            resp = await client.get(
                f"{base_url}/api/v1/videos/{song_id}",
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            )
            if resp.status_code == 200:
                data = resp.json()
                adaptive_formats = data.get("adaptiveFormats", [])
                for fmt in adaptive_formats:
                    if fmt.get("type", "").startswith("audio/mp4") and fmt.get("url"):
                        return fmt["url"]
                for fmt in adaptive_formats:
                    if fmt.get("type", "").startswith("audio/") and fmt.get("url"):
                        return fmt["url"]
        except Exception:
            pass
        return None

    async def _fetch_from_invidious_fallback(self, song_id: str) -> str | None:
        """Concurrent fallback to Invidious instances if Piped is unavailable."""
        async with httpx.AsyncClient(timeout=3.5) as client:
            tasks = [self._try_invidious_instance(client, url, song_id) for url in INVIDIOUS_INSTANCES[:3]]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in results:
                if isinstance(res, str) and res.startswith("http"):
                    return res
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

        # Prefer standard youtube.com watch URL for yt-dlp extractor compatibility
        target_url = (
            f"https://www.youtube.com/watch?v={clean_id}"
            if clean_id
            else (song_url or "")
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
