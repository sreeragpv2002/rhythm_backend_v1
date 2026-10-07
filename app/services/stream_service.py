import asyncio
import logging

import yt_dlp

from core.cache import ttl_cache

logger = logging.getLogger(__name__)

# Default in-memory cache TTL for direct audio stream URLs (1 hour).
# YouTube signed URLs are valid for ~6 hours; 1 hour prevents expiration while avoiding repeat extraction.
STREAM_CACHE_TTL_SECONDS = 3600


class StreamService:
    """
    Resolves YouTube / YouTube Music audio URLs into temporary direct audio stream URLs
    compatible with Flutter's `just_audio` package.
    """

    def __init__(self):
        self._ydl_opts = {
            "format": "bestaudio[ext=m4a]/bestaudio/best",
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,
            "extract_flat": False,
        }

    def _extract_stream_url_sync(self, url: str) -> str | None:
        try:
            with yt_dlp.YoutubeDL(self._ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return None
                if "entries" in info and info["entries"]:
                    info = info["entries"][0]

                # Direct URL selected by format filter
                direct_url = info.get("url")
                if direct_url:
                    return direct_url

                # Fallback: inspect formats list for audio stream with direct url
                formats = info.get("formats", [])
                for fmt in reversed(formats):
                    if fmt.get("acodec") != "none" and fmt.get("url"):
                        return fmt["url"]

                return None
        except Exception as e:
            logger.error(f"Error resolving stream URL with yt-dlp for {url}: {e}")
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

        direct_url = await asyncio.to_thread(self._extract_stream_url_sync, target_url)
        if direct_url:
            ttl_cache.set(cache_key, direct_url, ttl=STREAM_CACHE_TTL_SECONDS)
        return direct_url


stream_service = StreamService()
