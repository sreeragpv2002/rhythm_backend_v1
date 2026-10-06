"""
Backwards-compatibility module redirecting JioSaavn service to YouTube Music (ytmusicapi).
"""

from app.services.ytmusic_service import (
    YTMusicService,
    extract_image_url,
    interleave_results,
    is_compilation_song,
    normalize_yt_album,
    normalize_yt_artist,
    normalize_yt_playlist,
    normalize_yt_song,
    parse_languages,
    ytmusic_service,
)

# Backwards compatibility aliases
SaavnService = YTMusicService
saavn_service = ytmusic_service

__all__ = [
    "SaavnService",
    "YTMusicService",
    "extract_image_url",
    "interleave_results",
    "is_compilation_song",
    "normalize_yt_album",
    "normalize_yt_artist",
    "normalize_yt_playlist",
    "normalize_yt_song",
    "parse_languages",
    "saavn_service",
    "ytmusic_service",
]
