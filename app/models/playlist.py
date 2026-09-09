from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.home import HomeItem


class FavoriteSongRequest(BaseModel):
    user_id: str = Field(..., description="Firebase User ID", example="user_12345")
    song_id: str = Field(..., description="JioSaavn Song ID to favorite", example="UPJYO3v0")


class FavoriteSongRemoveRequest(BaseModel):
    user_id: str = Field(..., description="Firebase User ID", example="user_12345")
    song_id: str = Field(..., description="JioSaavn Song ID to remove from favorites", example="UPJYO3v0")


class FavoriteStatusResponse(BaseModel):
    success: bool = True
    user_id: str
    song_id: str
    is_favorite: bool


class CreatePlaylistRequest(BaseModel):
    user_id: str = Field(..., description="Firebase User ID", example="user_12345")
    name: str = Field(..., min_length=1, max_length=100, description="Playlist title/name", example="My Chill Mix")
    description: str | None = Field(default=None, description="Optional playlist description", example="Relaxing evening songs")
    song_ids: list[str] | None = Field(default=None, description="Optional list of song IDs to initially add")


class AddSongToPlaylistRequest(BaseModel):
    user_id: str = Field(..., description="Firebase User ID", example="user_12345")
    song_id: str = Field(..., description="JioSaavn Song ID to add to playlist", example="UPJYO3v0")


class UserPlaylistData(BaseModel):
    id: str = Field(..., description="Unique playlist ID (e.g. 'favorites' or 'pl_...')")
    name: str = Field(..., description="Playlist name")
    description: str | None = Field(default="", description="Playlist description")
    is_favorite: bool = Field(default=False, description="True if this is the default Favorites playlist")
    user_id: str = Field(..., description="Owner Firebase User ID")
    song_count: int = Field(default=0, description="Total number of tracks in playlist")
    image: str | None = Field(default="", description="Cover image URL")
    image_url: str | None = Field(default="", description="Cover image URL (same as image)")
    created_at: str | None = Field(default=None, description="ISO creation timestamp")
    updated_at: str | None = Field(default=None, description="ISO last updated timestamp")
    songs: list[HomeItem] | None = Field(default=None, description="List of track items inside playlist")

    @field_validator("image", "image_url", mode="before")
    @classmethod
    def normalize_image_field(cls, v: Any) -> str:
        if isinstance(v, list) and len(v) > 0:
            last = v[-1]
            if isinstance(last, dict) and "url" in last:
                return last["url"]
            return str(last)
        elif isinstance(v, str):
            return v
        return ""


class UserPlaylistResponse(BaseModel):
    success: bool = True
    message: str = "Success"
    data: UserPlaylistData


class UserPlaylistsListResponse(BaseModel):
    success: bool = True
    data: list[UserPlaylistData]
