
from pydantic import BaseModel, Field


class HomeItem(BaseModel):
    id: str = Field(..., description="Unique ID of the item")
    name: str = Field(..., description="Name of the item")
    title: str = Field(..., description="Title of the item (same as name)")
    image: str = Field(..., description="Image URL")
    image_url: str = Field(..., description="Image URL (same as image)")
    type: str | None = Field(default="song", description="Item type: song, playlist, album, artist, language")
    subtitle: str | None = Field(default=None, description="Optional artist / subtitle information")
    language: str | None = Field(default=None, description="Language of the item (e.g. english, malayalam, tamil)")


class HomeData(BaseModel):
    user_languages: list[str] = Field(default_factory=list, description="User's selected language codes from Firestore database")
    languages: list[HomeItem] = Field(default_factory=list, description="User's selected languages from database formatted as cards with images")
    recent_plays: list[HomeItem] = Field(default_factory=list, description="Recently played songs for the user from Firestore")
    trending_songs: list[HomeItem] = Field(default_factory=list, description="Trending songs fetched from JioSaavn")
    featured_playlists: list[HomeItem] = Field(default_factory=list, description="Featured playlists fetched from JioSaavn")
    trending_albums: list[HomeItem] = Field(default_factory=list, description="Trending albums fetched from JioSaavn")
    top_artists: list[HomeItem] = Field(default_factory=list, description="Top artists fetched from JioSaavn")


class HomeResponse(BaseModel):
    success: bool = True
    data: HomeData
