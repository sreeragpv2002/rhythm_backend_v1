import asyncio
import logging
from typing import Any

import yt_dlp
from fastapi import APIRouter

from app.services.stream_service import stream_service

logger = logging.getLogger(__name__)

router = APIRouter()


def _extract_test_info(
    video_id: str,
    use_cookies: bool = True,
    client: str | None = None,
) -> dict[str, Any]:
    url = f"https://www.youtube.com/watch?v={video_id}"
    player_clients = [client] if client else None
    opts = stream_service._get_ydl_opts(use_cookies=use_cookies, player_client=player_clients)

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        if not info:
            raise ValueError(f"No info returned for video {video_id}")
        if "entries" in info and info["entries"]:
            info = info["entries"][0]

        direct_url = info.get("url")
        if not direct_url:
            formats = info.get("formats", [])
            for fmt in reversed(formats):
                if fmt.get("acodec") != "none" and fmt.get("url"):
                    direct_url = fmt["url"]
                    break

        return {
            "title": info.get("title"),
            "audio_url": direct_url,
            "duration": info.get("duration"),
            "format": info.get("format"),
            "used_cookies": bool(opts.get("cookiefile")),
            "client_used": client or "default_cascade",
        }


@router.get("/{video_id}", summary="Test YouTube stream extraction with yt-dlp & PO token provider")
async def test_youtube(
    video_id: str,
    use_cookies: bool = True,
    client: str | None = None,
):
    """
    Test endpoint to verify direct stream extraction for a given YouTube video ID.
    Supports ?use_cookies=false to test pure guest PO token extraction,
    and ?client=ios or ?client=android to test specific mobile player clients.
    """
    # Auto-ensure bgutil PO Token Provider is active
    stream_service.ensure_pot_provider_running()
    pot_status = stream_service.get_pot_provider_status()

    try:
        data = await asyncio.to_thread(_extract_test_info, video_id, use_cookies, client)
        return {
            "success": True,
            "video_id": video_id,
            "title": data.get("title"),
            "audio_url": data.get("audio_url"),
            "duration": data.get("duration"),
            "format": data.get("format"),
            "used_cookies": data.get("used_cookies"),
            "client_used": data.get("client_used"),
            "pot_provider": pot_status,
            "cookies_count": stream_service.get_cookies_count(),
        }
    except Exception as e:
        logger.error(f"test-youtube failed for {video_id}: {e}")
        return {
            "success": False,
            "video_id": video_id,
            "error": str(e),
            "used_cookies": use_cookies,
            "client_tested": client or "default",
            "pot_provider": pot_status,
            "cookies_count": stream_service.get_cookies_count(),
            "tip": "Try appending ?use_cookies=false to test clean guest mode with the PO Token Provider, or ?client=ios."
        }


