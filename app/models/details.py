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
    download_url: Any | None = None
    suggested_songs: list[HomeItem] = Field(default_factory=list, description="Recommended and similar songs list")


class UnifiedDetailsResponse(BaseModel):
    success: bool = True
    type: str = Field(..., description="Entity type: song, playlist, artist, album")
    data: dict[str, Any] = Field(..., description="Detailed entity data including suggestions or tracks")
