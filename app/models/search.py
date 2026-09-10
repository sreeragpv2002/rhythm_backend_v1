from pydantic import BaseModel, Field

from app.models.home import HomeItem


class SearchResults(BaseModel):
    songs: list[HomeItem] = []
    albums: list[HomeItem] = []
    artists: list[HomeItem] = []
    playlists: list[HomeItem] = []
    top_query: list[HomeItem] = []


class SearchResponse(BaseModel):
    success: bool
    query: str
    data: SearchResults


class SongsListResponse(BaseModel):
    success: bool
    query: str
    limit: int
    total: int = Field(..., description="Number of songs returned")
    songs: list[HomeItem]


class PlaylistsListResponse(BaseModel):
    success: bool
    query: str
    limit: int
    total: int = Field(..., description="Number of playlists returned")
    playlists: list[HomeItem]
