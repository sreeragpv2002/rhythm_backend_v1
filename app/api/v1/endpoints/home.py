import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from app.models.categories import find_category_by_id, get_all_categories_data
from app.models.home import CategoryExploreResponse, HomeData, HomeItem, HomeResponse
from app.models.language import LANGUAGE_METADATA
from app.services.ytmusic_service import extract_image_url, ytmusic_service
from core.firebase import get_recent_plays, get_user_languages, verify_user_exists

router = APIRouter()


def format_language_item(lang: str) -> HomeItem:
    """
    Formats a language string into a HomeItem card using curated high-res artwork and metadata.
    """
    clean = lang.strip().lower()
    meta = LANGUAGE_METADATA.get(clean)
    if meta:
        return HomeItem(**meta)

    display = clean.capitalize()
    return HomeItem(
        id=clean,
        name=display,
        title=display,
        image="",
        image_url="",
        type="language",
        subtitle="Language",
        language=clean,
    )


def format_home_item(item: dict[str, Any], default_type: str = "song", rank: int | None = None) -> HomeItem:
    """
    Normalizes any raw item (song, playlist, album, artist) into a consistent HomeItem card.
    Directly playable for songs, and includes rank metadata for charts.
    """
    name = item.get("name") or item.get("title") or item.get("artist") or ""
    image_url = extract_image_url(
        item.get("image_url") or item.get("image") or item.get("thumbnails") or item.get("thumbnail")
    )
    item_type = item.get("type") or default_type

    # Extract artist name and subtitle
    artist_name = item.get("artist")
    subtitle = item.get("subtitle")

    if not subtitle:
        if "artists" in item and isinstance(item["artists"], dict):
            primary = item["artists"].get("primary", [])
            if isinstance(primary, list) and len(primary) > 0:
                subtitle = ", ".join(a.get("name", "") for a in primary if isinstance(a, dict) and a.get("name"))
        elif "artists" in item and isinstance(item["artists"], list) and len(item["artists"]) > 0:
            subtitle = ", ".join(a.get("name", "") if isinstance(a, dict) else str(a) for a in item["artists"])
        elif artist_name and isinstance(artist_name, str):
            subtitle = artist_name
        elif "author" in item and isinstance(item["author"], str):
            subtitle = item["author"]

    if not artist_name:
        artist_name = subtitle

    language = item.get("language")
    item_id = str(item.get("id") or item.get("videoId") or item.get("browseId") or "")

    # Playback URL
    url = item.get("url")
    if not url and item_id:
        if item_type == "song":
            url = f"https://music.youtube.com/watch?v={item_id}"
        elif item_type == "playlist":
            url = f"https://music.youtube.com/playlist?list={item_id}"
        elif item_type in ("album", "artist"):
            url = f"https://music.youtube.com/browse/{item_id}"

    return HomeItem(
        id=item_id,
        name=name,
        title=name,
        image=image_url,
        image_url=image_url,
        type=item_type,
        subtitle=subtitle,
        artist=artist_name,
        language=language,
        rank=rank,
        duration=item.get("duration"),
        duration_formatted=item.get("duration_formatted"),
        url=url,
    )


@router.get("", response_model=HomeResponse, summary="Get Complete Home Screen Data")
async def get_home_data(
    user_id: str = Query(..., description="Firebase User ID (required)"),
    limit: int = Query(10, ge=1, le=50, description="Number of items per section (1-50)")
):
    """
    Returns complete home screen sections arranged in canonical UI order:
    1. **recent_plays**: User's recently played songs from Firestore (empty if none, hide in UI).
    2. **quick_picks**: Personalized recommendations based on listening history & preferences.
    3. **trending_songs**: Currently trending songs with cover art and artist info.
    4. **new_malayalam_releases**: Newly released Malayalam songs.
    5. **top_charts**: Most popular songs with rank numbers (#1, #2, #3, ...).
    6. **featured_playlists**: Curated playlists with artwork and creator details.
    7. **mood_and_genres**: Curated Moods, Activities, and Genres with colors and emoji icons.
    8. **trending_albums**: Popular albums with square artwork.
    9. **popular_artists**: Trending artists with circular profile images.
    10. **old_is_gold**: Evergreen classic Malayalam songs & golden hits.

    User language preferences are automatically retrieved from Firestore.
    If no languages are configured for the user, it defaults to Malayalam and English.
    """
    # 1. Verify user exists in Firebase
    user_exists = await asyncio.to_thread(verify_user_exists, user_id)
    if not user_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found in Firebase"
        )

    # 2. Fetch user's saved languages from Firestore; fallback to ["malayalam", "english"] if none set
    saved_langs = await asyncio.to_thread(get_user_languages, user_id)
    if saved_langs:
        user_languages = [lang.strip().lower() for lang in saved_langs if lang.strip()]
    else:
        user_languages = []

    if not user_languages:
        user_languages = ["malayalam", "english"]

    language_context = ", ".join(user_languages)

    # 3. Fetch Recent Plays from Firestore and Home Sections from YouTube Music API concurrently
    recent_plays_task = asyncio.to_thread(get_recent_plays, user_id, limit)
    yt_task = ytmusic_service.fetch_home_sections(language=language_context, limit=limit)

    recent_plays, yt_sections = await asyncio.gather(recent_plays_task, yt_task)

    # 4. Generate personalized Quick Picks based on user's recent plays & language context
    quick_picks_raw = await ytmusic_service.get_personalized_quick_picks(
        recent_plays=recent_plays or [],
        language=language_context,
        limit=limit
    )

    # 5. Format user languages
    formatted_languages = [format_language_item(lang) for lang in user_languages]

    # 6. Format top charts with ranking numbers (#1, #2, #3, ...)
    raw_charts = yt_sections.get("top_charts", [])
    formatted_top_charts = [
        format_home_item(item, "song", rank=idx + 1)
        for idx, item in enumerate(raw_charts)
    ]

    # 7. Assemble canonical HomeData payload
    home_data = HomeData(
        user_languages=user_languages,
        languages=formatted_languages,
        # Section 3: Recently Played
        recent_plays=[format_home_item(i, "song") for i in (recent_plays or [])],
        # Section 4: Quick Picks For You
        quick_picks=[format_home_item(i, "song") for i in (quick_picks_raw or [])],
        # Section 5: Trending Songs
        trending_songs=[format_home_item(i, "song") for i in yt_sections.get("trending_songs", [])],
        # Section 6: New Malayalam Releases
        new_malayalam_releases=[format_home_item(i, "song") for i in yt_sections.get("new_malayalam_releases", [])],
        # Section 7: Top Charts
        top_charts=formatted_top_charts,
        # Section 8: Featured Playlists
        featured_playlists=[format_home_item(i, "playlist") for i in yt_sections.get("featured_playlists", [])],
        # Section 9: Mood & Genres
        mood_and_genres=get_all_categories_data(),
        # Section 10: Trending Albums
        trending_albums=[format_home_item(i, "album") for i in yt_sections.get("trending_albums", [])],
        # Section 11: Popular Artists
        popular_artists=[format_home_item(i, "artist") for i in yt_sections.get("popular_artists", [])],
        top_artists=[format_home_item(i, "artist") for i in yt_sections.get("top_artists", [])],
        # Section 12: Old Is Gold
        old_is_gold=[format_home_item(i, "song") for i in yt_sections.get("old_is_gold", [])],
    )

    return HomeResponse(success=True, data=home_data)


@router.get("/category/{category_id}", response_model=CategoryExploreResponse, summary="Get Category Songs and Playlists")
async def get_category_content(
    category_id: str,
    limit: int = Query(20, ge=1, le=50, description="Number of items to fetch (1-50)")
):
    """
    Retrieves songs and playlists dedicated to a specific mood, activity, or genre category.
    Allows clients to seamlessly open a full dedicated music view when any mood, activity, or genre card is tapped.
    """
    category = find_category_by_id(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Category '{category_id}' not found. Available categories can be found in /api/v1/home mood_and_genres"
        )

    content = await ytmusic_service.fetch_category_content(query=category.query, limit=limit)

    return CategoryExploreResponse(
        success=True,
        category=category,
        songs=[format_home_item(s, "song") for s in content.get("songs", [])],
        playlists=[format_home_item(p, "playlist") for p in content.get("playlists", [])],
    )
