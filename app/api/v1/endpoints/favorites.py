
from fastapi import APIRouter, Body, Path, Query, status

from app.models.playlist import (
    FavoriteSongRemoveRequest,
    FavoriteSongRequest,
    FavoriteStatusResponse,
    UserPlaylistResponse,
)
from app.services.playlist_service import playlist_service

router = APIRouter()


@router.post(
    "",
    response_model=UserPlaylistResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add song to favorites (and Favorites playlist)"
)
async def add_favorite_song(payload: FavoriteSongRequest):
    """
    Marks a song as favorite for the user.
    Automatically saves the song into the user's default 'Favorites' playlist in Firestore.
    """
    data = await playlist_service.add_favorite(user_id=payload.user_id, song_id=payload.song_id)
    return UserPlaylistResponse(
        success=True,
        message="Song added to favorites successfully",
        data=data
    )


@router.delete(
    "",
    summary="Remove song from favorites (query params or JSON body)"
)
async def remove_favorite_song(
    payload: FavoriteSongRemoveRequest | None = Body(None),
    user_id: str | None = Query(None, description="Firebase User ID"),
    song_id: str | None = Query(None, description="JioSaavn Song ID")
):
    """
    Removes a song from the user's favorites playlist.
    Accepts user_id and song_id either in JSON body or as query parameters.
    """
    uid = (payload.user_id if payload else None) or user_id
    sid = (payload.song_id if payload else None) or song_id

    if not uid or not sid:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id and song_id are required"
        )

    await playlist_service.remove_favorite(user_id=uid, song_id=sid)
    return {
        "success": True,
        "message": f"Song '{sid}' removed from favorites"
    }


@router.delete(
    "/{song_id}",
    summary="Remove song from favorites by path parameter"
)
async def remove_favorite_song_by_path(
    song_id: str = Path(..., description="JioSaavn Song ID"),
    user_id: str = Query(..., description="Firebase User ID")
):
    """
    Removes a song from favorites using the song_id in the URL path.
    """
    await playlist_service.remove_favorite(user_id=user_id, song_id=song_id)
    return {
        "success": True,
        "message": f"Song '{song_id}' removed from favorites"
    }


@router.get(
    "",
    response_model=UserPlaylistResponse,
    summary="Get user's favorites playlist and songs"
)
async def get_favorites(
    user_id: str = Query(..., description="Firebase User ID"),
    limit: int = Query(50, ge=1, le=100, description="Max songs to return (1-100)")
):
    """
    Retrieves the user's 'Favorites' playlist along with its favorited songs list.
    """
    data = await playlist_service.get_favorites(user_id=user_id, limit=limit)
    return UserPlaylistResponse(
        success=True,
        message="Favorites retrieved successfully",
        data=data
    )


@router.get(
    "/check",
    response_model=FavoriteStatusResponse,
    summary="Check if a song is favorited"
)
async def check_is_favorite(
    user_id: str = Query(..., description="Firebase User ID"),
    song_id: str = Query(..., description="JioSaavn Song ID")
):
    """
    Returns true if the song is currently marked as favorite by the user.
    """
    is_fav = await playlist_service.check_favorite(user_id=user_id, song_id=song_id)
    return FavoriteStatusResponse(
        success=True,
        user_id=user_id,
        song_id=song_id,
        is_favorite=is_fav
    )
