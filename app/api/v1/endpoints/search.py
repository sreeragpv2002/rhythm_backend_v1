from typing import Any

from fastapi import APIRouter, Query

from app.models.home import HomeItem
from app.models.search import PlaylistsListResponse, SearchResponse, SearchResults, SongsListResponse
from app.services.saavn_service import saavn_service

router = APIRouter()


def _extract_image_url(image_data: Any) -> str:
    """Extracts the highest-quality image URL from JioSaavn image data."""
    if isinstance(image_data, list) and image_data:
        last = image_data[-1]
        if isinstance(last, dict) and "url" in last:
            return last["url"]
        elif isinstance(last, str):
            return last
    elif isinstance(image_data, str):
        return image_data
    return ""


def _to_home_item(item: dict[str, Any], default_type: str = "song") -> HomeItem:
    """Converts a raw Saavn search result item to a HomeItem."""
    name = item.get("name") or item.get("title") or ""
    image_url = _extract_image_url(item.get("image"))
    item_type = item.get("type") or default_type

    subtitle = (
        item.get("description")
        or item.get("primaryArtists")
        or item.get("artist")
        or None
    )

    return HomeItem(
        id=str(item.get("id", "")),
        name=name,
        title=name,
        image=image_url,
        image_url=image_url,
        type=item_type,
        subtitle=subtitle,
        language=item.get("language"),
    )


def _section_to_items(section: Any, default_type: str) -> list[HomeItem]:
    """Extracts and formats results from a search section dict or list."""
    if isinstance(section, dict):
        results = section.get("results", [])
    elif isinstance(section, list):
        results = section
    else:
        return []
    return [_to_home_item(r, default_type) for r in results if isinstance(r, dict)]


@router.get("", response_model=SearchResponse, summary="Universal Search")
async def universal_search(
    query: str = Query(..., min_length=1, description="Search term"),
    limit: int = Query(10, ge=1, le=50, description="Max results per section (1-50)"),
):
    """
    Performs a universal search across **songs, albums, artists, and playlists**
    in a single request using the JioSaavn API (`saavn.sumit.co`).

    Returns structured results grouped by category:
    - **songs** – matching song tracks
    - **albums** – matching albums
    - **artists** – matching artists
    - **playlists** – matching playlists
    - **top_query** – top query result (if available)
    """
    raw = await saavn_service.universal_search(query=query, limit=limit)

    results = SearchResults(
        songs=_section_to_items(raw.get("songs"), "song"),
        albums=_section_to_items(raw.get("albums"), "album"),
        artists=_section_to_items(raw.get("artists"), "artist"),
        playlists=_section_to_items(raw.get("playlists"), "playlist"),
        top_query=_section_to_items(raw.get("topQuery"), "song"),
    )

    return SearchResponse(success=True, query=query, data=results)


@router.get("/songs", response_model=SongsListResponse, summary="Search Songs")
async def search_songs(
    query: str = Query(..., min_length=1, description="Search term"),
    limit: int = Query(10, ge=1, le=50, description="Max number of songs to return (1-50)"),
    language: str | None = Query(None, description="Optional language filter (e.g. 'hindi', 'english')"),
):
    """
    Returns a flat list of **songs** matching the search query.

    - Filters out compilation/playlist covers automatically.
    - Use `language` to narrow results to a specific language.
    - Results are cached for 1 day.
    """
    raw = await saavn_service.search_songs(query=query, limit=limit, language=language)
    songs = [_to_home_item(item, "song") for item in raw]
    return SongsListResponse(
        success=True,
        query=query,
        limit=limit,
        total=len(songs),
        songs=songs,
    )


@router.get("/playlists", response_model=PlaylistsListResponse, summary="Search Playlists")
async def search_playlists(
    query: str = Query(..., min_length=1, description="Search term"),
    limit: int = Query(10, ge=1, le=50, description="Max number of playlists to return (1-50)"),
    language: str | None = Query(None, description="Optional language filter (e.g. 'hindi', 'english')"),
):
    """
    Returns a flat list of **playlists** matching the search query.

    - Use `language` to narrow results to a specific language.
    - Results are cached for 1 day.
    """
    raw = await saavn_service.search_playlists(query=query, limit=limit, language=language)
    playlists = [_to_home_item(item, "playlist") for item in raw]
    return PlaylistsListResponse(
        success=True,
        query=query,
        limit=limit,
        total=len(playlists),
        playlists=playlists,
    )
