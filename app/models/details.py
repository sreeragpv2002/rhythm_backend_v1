from typing import Any

from pydantic import BaseModel, Field

from app.models.home import HomeItem


class SongDetailsData(BaseModel):
    id: str
    name: str
    title: str | None = None
    type: str = "song"
    year: str | None = None
    release_date: str | None = None
    duration: int | None = None
    label: str | None = None
    explicit_content: bool | None = False
    play_count: int | None = None
    language: str | None = None
    has_lyrics: bool | None = False
    lyrics_id: str | None = None
    url: str | None = None
    copyright: str | None = None
    album: dict[str, Any] | None = None
    artists: dict[str, Any] | None = None
    image: Any | None = None
    image_url: str | None = None
    stream_url: str | None = Field(default=None, description="Direct CDN audio stream URL (MP3/M4A)")
    download_url: str | None = Field(default=None, description="Direct CDN audio download URL")
    download_urls: list[dict[str, str]] = Field(default_factory=list, description="All available stream bitrates")
    is_direct_cdn: bool | None = Field(default=True, description="Indicates stream is served directly via CDN with no bot check")
    suggested_songs: list[HomeItem] = Field(default_factory=list, description="Recommended and similar songs list")


class UnifiedDetailsResponse(BaseModel):
    success: bool = True
    type: str = Field(..., description="Entity type: song, playlist, artist, album")
    data: dict[str, Any] = Field(..., description="Detailed entity data including suggestions or tracks")


class StreamData(BaseModel):
    id: str = Field(..., description="Song ID")
    title: str = Field(..., description="Song title")
    artist: str | None = Field(default=None, description="Artist name")
    stream_url: str = Field(..., description="Direct CDN audio stream URL (MP3 / M4A)")
    download_url: str = Field(..., description="Direct CDN audio download URL")
    download_urls: list[dict[str, str]] = Field(default_factory=list, description="Available qualities from 12kbps to 320kbps")
    quality: str = Field(default="320kbps", description="Audio stream bitrate quality")
    format: str = Field(default="m4a", description="Audio container format: m4a or mp3")
    source: str = Field(default="saavn_cdn", description="Streaming CDN provider")
    is_direct_cdn: bool = Field(default=True, description="Direct CDN playback flag")


class StreamResponse(BaseModel):
    success: bool = True
    data: StreamData
