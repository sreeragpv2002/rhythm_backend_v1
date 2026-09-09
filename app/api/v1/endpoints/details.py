from typing import Any

from fastapi import APIRouter, HTTPException, Path, Query, status

from app.api.v1.endpoints.home import extract_image_url, format_home_item
from app.models.details import UnifiedDetailsResponse
from app.services.saavn_service import saavn_service

router = APIRouter()

SUPPORTED_TYPES = {"song", "playlist", "artist", "album"}
TYPE_ALIASES = {
    "song": "song",
    "songs": "song",
    "playlist": "playlist",
    "playlists": "playlist",
    "artist": "artist",
    "artists": "artist",
    "album": "album",
    "albums": "album",
}


def normalize_type(raw_type: str) -> str:
    cleaned = raw_type.strip().lower()
    canonical = TYPE_ALIASES.get(cleaned)
    if not canonical:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid details type '{raw_type}'. Supported types are: {sorted(SUPPORTED_TYPES)}"
        )
    return canonical


def format_details_response(entity_type: str, data: dict[str, Any]) -> dict[str, Any]:
    """
    Enriches entity data with top-level high-res image_url and formats nested song lists.
    """
    result = dict(data)
    if "image" in result:
        result["image_url"] = extract_image_url(result["image"])

    # For songs: format suggested_songs into clean HomeItem cards
    if entity_type == "song" and "suggested_songs" in result:
        formatted_suggestions = [
            format_home_item(s, "song").model_dump()
            for s in result.get("suggested_songs", [])
        ]
        result["suggested_songs"] = formatted_suggestions

    # For playlists and albums: enrich embedded tracks with image_url
    if "songs" in result and isinstance(result["songs"], list):
        formatted_songs = []
        for s in result["songs"]:
            if isinstance(s, dict):
                item = dict(s)
                item["image_url"] = extract_image_url(item.get("image"))
                formatted_songs.append(item)
            else:
                formatted_songs.append(s)
        result["songs"] = formatted_songs

    # For artists: enrich topSongs with image_url
    if "topSongs" in result and isinstance(result["topSongs"], list):
        formatted_top_songs = []
        for s in result["topSongs"]:
            if isinstance(s, dict):
                item = dict(s)
                item["image_url"] = extract_image_url(item.get("image"))
                formatted_top_songs.append(item)
            else:
                formatted_top_songs.append(s)
        result["topSongs"] = formatted_top_songs
        result["top_songs"] = formatted_top_songs

    return result


async def fetch_details(
    entity_type: str,
    entity_id: str,
    user_id: str | None = None,
    limit: int = 10,
    song_count: int = 10,
    album_count: int = 10
) -> dict[str, Any]:
    canonical_type = normalize_type(entity_type)

    if canonical_type == "song":
        data = await saavn_service.get_song_details_with_suggestions(entity_id, limit=limit)
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Song with ID '{entity_id}' not found on JioSaavn"
            )
        return format_details_response(canonical_type, data)

    elif canonical_type == "playlist":
        if (entity_id == "favorites" or entity_id.startswith("pl_")) and user_id:
            from app.services.playlist_service import playlist_service
            data = await playlist_service.get_playlist_details(user_id=user_id, playlist_id=entity_id, limit=limit)
            return format_details_response(canonical_type, data)

        data = await saavn_service.get_playlist_by_id(entity_id)
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Playlist with ID '{entity_id}' not found on JioSaavn"
            )
        return format_details_response(canonical_type, data)

    elif canonical_type == "artist":
        data = await saavn_service.get_artist_by_id(entity_id, song_count=song_count, album_count=album_count)
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Artist with ID '{entity_id}' not found on JioSaavn"
            )
        return format_details_response(canonical_type, data)

    elif canonical_type == "album":
        data = await saavn_service.get_album_by_id(entity_id)
        if not data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Album with ID '{entity_id}' not found on JioSaavn"
            )
        return format_details_response(canonical_type, data)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported type: {entity_type}"
    )


@router.get(
    "",
    response_model=UnifiedDetailsResponse,
    summary="Get Details by Type (song, playlist, artist, album)"
)
async def get_details(
    type: str = Query(..., description="Entity type: 'song', 'playlist', 'artist', 'album'"),
    id: str = Query(..., description="Unique entity ID on JioSaavn or user playlist ID"),
    user_id: str | None = Query(None, description="Optional Firebase User ID (required for user-specific playlists like 'favorites')"),
    limit: int = Query(10, ge=1, le=50, description="Limit for suggestions or tracks (1-50)"),
    song_count: int = Query(10, ge=1, le=50, description="Artist top songs count (1-50)"),
    album_count: int = Query(10, ge=1, le=50, description="Artist top albums count (1-50)")
):
    """
    Single unified API endpoint to fetch detailed metadata by type:
    - **song**: Returns full song details + `suggested_songs` recommendation list.
    - **playlist**: Returns full playlist details with track list and artwork (supports both JioSaavn playlists and user Firestore playlists).
    - **artist**: Returns full artist details with `top_songs`, `topAlbums`, and bio.
    - **album**: Returns full album details with track list and metadata.
    """
    canonical_type = normalize_type(type)
    data = await fetch_details(
        entity_type=canonical_type,
        entity_id=id,
        user_id=user_id,
        limit=limit,
        song_count=song_count,
        album_count=album_count
    )
    return UnifiedDetailsResponse(success=True, type=canonical_type, data=data)


@router.get(
    "/{type}/{id}",
    response_model=UnifiedDetailsResponse,
    summary="Get Details by Path Type and ID"
)
async def get_details_by_path(
    type: str = Path(..., description="Entity type: 'song', 'playlist', 'artist', 'album'"),
    id: str = Path(..., description="Unique entity ID on JioSaavn or user playlist ID"),
    user_id: str | None = Query(None, description="Optional Firebase User ID (required for user-specific playlists like 'favorites')"),
    limit: int = Query(10, ge=1, le=50, description="Limit for suggestions or tracks (1-50)"),
    song_count: int = Query(10, ge=1, le=50, description="Artist top songs count (1-50)"),
    album_count: int = Query(10, ge=1, le=50, description="Artist top albums count (1-50)")
):
    """
    Path-based alias for the unified details API.
    """
    canonical_type = normalize_type(type)
    data = await fetch_details(
        entity_type=canonical_type,
        entity_id=id,
        user_id=user_id,
        limit=limit,
        song_count=song_count,
        album_count=album_count
    )
    return UnifiedDetailsResponse(success=True, type=canonical_type, data=data)


# Dedicated routers for convenient direct resource access
songs_router = APIRouter()
playlists_router = APIRouter()
artists_router = APIRouter()
albums_router = APIRouter()


@songs_router.get("/{id}", summary="Get Song Details with Suggested Songs")
async def get_song_by_id(
    id: str = Path(..., description="Unique Song ID on JioSaavn"),
    limit: int = Query(10, ge=1, le=50, description="Limit for suggested songs (1-50)")
):
    """
    Returns full song details along with a suggested songs list.
    """
    data = await fetch_details(entity_type="song", entity_id=id, limit=limit)
    return UnifiedDetailsResponse(success=True, type="song", data=data)


@playlists_router.get("/{id}", summary="Get Playlist Details")
async def get_playlist_by_id(
    id: str = Path(..., description="Unique Playlist ID on JioSaavn")
):
    """
    Returns full playlist details with track list and artwork.
    """
    data = await fetch_details(entity_type="playlist", entity_id=id)
    return UnifiedDetailsResponse(success=True, type="playlist", data=data)


@artists_router.get("/{id}", summary="Get Artist Details")
async def get_artist_by_id(
    id: str = Path(..., description="Unique Artist ID on JioSaavn"),
    song_count: int = Query(10, ge=1, le=50, description="Artist top songs count (1-50)"),
    album_count: int = Query(10, ge=1, le=50, description="Artist top albums count (1-50)")
):
    """
    Returns full artist details with topSongs, topAlbums, and bio.
    """
    data = await fetch_details(
        entity_type="artist",
        entity_id=id,
        song_count=song_count,
        album_count=album_count
    )
    return UnifiedDetailsResponse(success=True, type="artist", data=data)


@albums_router.get("/{id}", summary="Get Album Details")
async def get_album_by_id(
    id: str = Path(..., description="Unique Album ID on JioSaavn")
):
    """
    Returns full album details with tracks and artwork.
    """
    data = await fetch_details(entity_type="album", entity_id=id)
    return UnifiedDetailsResponse(success=True, type="album", data=data)
