import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status

from app.models.home import HomeData, HomeItem, HomeResponse
from app.models.language import LANGUAGE_METADATA
from app.services.saavn_service import saavn_service
from core.firebase import get_recent_plays, get_user_languages, verify_user_exists

router = APIRouter()


def extract_image_url(image_data: Any) -> str:
    """
    Extracts the highest quality image URL string from JioSaavn/Firestore image data.
    """
    if isinstance(image_data, list) and len(image_data) > 0:
        # JioSaavn lists qualities in ascending order (50x50, 150x150, 500x500); pick best quality
        last = image_data[-1]
        if isinstance(last, dict) and "url" in last:
            return last["url"]
        elif isinstance(last, str):
            return last
    elif isinstance(image_data, str):
        return image_data
    return ""


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


def format_home_item(item: dict[str, Any], default_type: str = "song") -> HomeItem:
    """
    Simplifies raw song, playlist, album, or artist data to only:
    - id
    - name & title
    - image & image_url (best quality URL string)
    - type
    - optional subtitle
    """
    name = item.get("name") or item.get("title") or ""
    image_url = extract_image_url(item.get("image"))
    item_type = item.get("type") or default_type

    # Extract optional artist / subtitle string if present
    subtitle = None
    if "artists" in item and isinstance(item["artists"], dict):
        primary = item["artists"].get("primary", [])
        if isinstance(primary, list) and len(primary) > 0:
            subtitle = ", ".join(a.get("name", "") for a in primary if a.get("name"))
    elif "artist" in item and isinstance(item["artist"], str):
        subtitle = item["artist"]

    language = item.get("language")

    return HomeItem(
        id=str(item.get("id", "")),
        name=name,
        title=name,
        image=image_url,
        image_url=image_url,
        type=item_type,
        subtitle=subtitle,
        language=language,
    )


@router.get("", response_model=HomeResponse, summary="Get Home Page Data")
async def get_home_data(
    user_id: str = Query(..., description="Firebase User ID (required)"),
    language: str | None = Query(None, description="Optional language filter, supports single or comma-separated languages (e.g., 'hindi' or 'english, malayalam, tamil')"),
    limit: int = Query(10, ge=1, le=50, description="Number of items per section (1-50)")
):
    """
    Returns home screen sections formatted with concise card metadata (id, name, title, image, image_url, type):
    - **languages**: User's selected languages from database formatted as HomeItem cards.
    - **user_languages**: User's selected language codes from Firestore database.
    - **recent_plays**: User's recently played songs retrieved from Firebase Firestore.
    - **trending_songs**: Current trending songs from JioSaavn.
    - **featured_playlists**: Top playlists from JioSaavn.
    - **trending_albums**: Top albums from JioSaavn.
    - **top_artists**: Top artists from JioSaavn.

    Requires a valid `user_id` verified against Firebase.
    """
    # 1. Verify user exists in Firebase
    user_exists = await asyncio.to_thread(verify_user_exists, user_id)
    if not user_exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{user_id}' not found in Firebase"
        )

    # 2. Fetch user's saved languages from Firestore database
    saved_langs = await asyncio.to_thread(get_user_languages, user_id)

    # If language filter is not explicitly provided, fallback to user's saved languages in Firestore
    if not language and saved_langs:
        language = ", ".join(saved_langs)

    # 3. Concurrently fetch Recent Plays from Firestore and Home Sections from Saavn API (cached 1 day)
    recent_plays_task = asyncio.to_thread(get_recent_plays, user_id, limit)
    saavn_task = saavn_service.fetch_home_sections(language=language, limit=limit)

    recent_plays, saavn_sections = await asyncio.gather(recent_plays_task, saavn_task)

    # Format user's languages as HomeItem cards
    formatted_languages = [format_language_item(lang) for lang in (saved_langs or [])]

    # 4. Simplify each section to minimal card schema (id, name, title, image, image_url, type)
    home_data = HomeData(
        user_languages=saved_langs or [],
        languages=formatted_languages,
        recent_plays=[format_home_item(i, "song") for i in (recent_plays or [])],
        trending_songs=[format_home_item(i, "song") for i in saavn_sections.get("trending_songs", [])],
        featured_playlists=[format_home_item(i, "playlist") for i in saavn_sections.get("featured_playlists", [])],
        trending_albums=[format_home_item(i, "album") for i in saavn_sections.get("trending_albums", [])],
        top_artists=[format_home_item(i, "artist") for i in saavn_sections.get("top_artists", [])],
    )

    return HomeResponse(success=True, data=home_data)
