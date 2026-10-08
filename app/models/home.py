from pydantic import BaseModel, Field

from app.models.categories import CategoryItem, MoodAndGenresData


class HomeItem(BaseModel):
    id: str = Field(..., description="Unique ID of the item")
    name: str = Field(..., description="Name of the item")
    title: str = Field(..., description="Title of the item (same as name)")
    image: str = Field(..., description="Image URL")
    image_url: str = Field(..., description="Image URL (same as image)")
    type: str | None = Field(default="song", description="Item type: song, playlist, album, artist, language, mood, genre, activity")
    subtitle: str | None = Field(default=None, description="Optional artist / subtitle information")
    artist: str | None = Field(default=None, description="Artist name")
    language: str | None = Field(default=None, description="Language of the item (e.g. malayalam, english, tamil)")
    rank: int | None = Field(default=None, description="Position rank for chart items (1, 2, 3...)")
    duration: int | None = Field(default=None, description="Duration in seconds")
    duration_formatted: str | None = Field(default=None, description="Duration formatted (e.g. '3:45')")
    url: str | None = Field(default=None, description="Direct watch / playback URL")
    stream_url: str | None = Field(default=None, description="Direct CDN audio stream URL (MP3/M4A)")
    download_url: str | None = Field(default=None, description="Direct CDN audio download URL")


class HomeData(BaseModel):
    # Language preferences
    user_languages: list[str] = Field(default_factory=list, description="User's selected language codes from Firestore database")
    languages: list[HomeItem] = Field(default_factory=list, description="User's selected languages formatted as cards")

    # 3. Recently Played (empty if no plays, client hides this section)
    recent_plays: list[HomeItem] = Field(default_factory=list, description="User's recently played songs from Firestore")

    # 4. Quick Picks For You
    quick_picks: list[HomeItem] = Field(default_factory=list, description="Personalized recommendations based on listening history")

    # 5. Trending Songs
    trending_songs: list[HomeItem] = Field(default_factory=list, description="Currently trending songs")

    # 6. New Malayalam Releases
    new_malayalam_releases: list[HomeItem] = Field(default_factory=list, description="Newly released Malayalam songs")

    # 7. Top Charts
    top_charts: list[HomeItem] = Field(default_factory=list, description="Most popular songs with rank numbers (#1, #2, #3...)")

    # 8. Featured Playlists
    featured_playlists: list[HomeItem] = Field(default_factory=list, description="Curated and popular playlists")

    # 9. Mood & Genres
    mood_and_genres: MoodAndGenresData = Field(default_factory=MoodAndGenresData, description="Categories for moods, activities, and genres")

    # 10. Trending Albums
    trending_albums: list[HomeItem] = Field(default_factory=list, description="Currently popular albums")

    # 11. Popular Artists
    popular_artists: list[HomeItem] = Field(default_factory=list, description="Popular/trending artists with circular profile artwork")
    top_artists: list[HomeItem] = Field(default_factory=list, description="Alias for popular_artists for backward compatibility")

    # 12. Old Is Gold
    old_is_gold: list[HomeItem] = Field(default_factory=list, description="Evergreen classic Malayalam songs and golden hits")

    # Structured order metadata for dynamic rendering on client
    sections_order: list[str] = Field(
        default_factory=lambda: [
            "recent_plays",
            "quick_picks",
            "trending_songs",
            "new_malayalam_releases",
            "top_charts",
            "featured_playlists",
            "mood_and_genres",
            "trending_albums",
            "popular_artists",
            "old_is_gold",
        ],
        description="The canonical visual section order for the Rhythm home screen",
    )


class HomeResponse(BaseModel):
    success: bool = True
    data: HomeData


class CategoryExploreResponse(BaseModel):
    success: bool = True
    category: CategoryItem
    songs: list[HomeItem] = Field(default_factory=list, description="Songs matching the category")
    playlists: list[HomeItem] = Field(default_factory=list, description="Playlists matching the category")
