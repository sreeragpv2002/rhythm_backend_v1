from fastapi import APIRouter, Path, Query, status

from app.models.playlist import (
    AddSongToPlaylistRequest,
    CreatePlaylistRequest,
    UserPlaylistResponse,
    UserPlaylistsListResponse,
)
from app.services.playlist_service import playlist_service

router = APIRouter()


@router.post(
    "",
    response_model=UserPlaylistResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new custom user playlist"
)
async def create_playlist(payload: CreatePlaylistRequest):
    """
    Creates a new custom playlist in Firestore for the verified user.
    Optionally accepts an initial array of song_ids.
    """
    data = await playlist_service.create_playlist(
        user_id=payload.user_id,
        name=payload.name,
        description=payload.description,
        song_ids=payload.song_ids
    )
    return UserPlaylistResponse(
        success=True,
        message="Playlist created successfully",
        data=data
    )


@router.get(
    "",
    response_model=UserPlaylistsListResponse,
    summary="Get all playlists for user (including Favorites playlist)"
)
async def get_user_playlists(
    user_id: str = Query(..., description="Firebase User ID")
):
    """
    Retrieves all playlists belonging to the user.
    The system 'Favorites' playlist (is_favorite=True) is automatically included at the top.
    """
    playlists = await playlist_service.get_user_playlists(user_id=user_id)
    return UserPlaylistsListResponse(
        success=True,
        data=playlists
    )


@router.get(
    "/{playlist_id}",
    response_model=UserPlaylistResponse,
    summary="Get specific playlist details and tracklist"
)
async def get_playlist_details(
    playlist_id: str = Path(..., description="Playlist ID (e.g. 'favorites' or 'pl_...')"),
    user_id: str = Query(..., description="Firebase User ID"),
    limit: int = Query(50, ge=1, le=100, description="Max songs to return")
):
    """
    Retrieves detailed metadata and songs list for any user playlist (including 'favorites').
    """
    data = await playlist_service.get_playlist_details(
        user_id=user_id,
        playlist_id=playlist_id,
        limit=limit
    )
    return UserPlaylistResponse(
        success=True,
        message="Playlist details retrieved successfully",
        data=data
    )


@router.delete(
    "/{playlist_id}",
    summary="Delete a custom user playlist"
)
async def delete_playlist(
    playlist_id: str = Path(..., description="Custom Playlist ID"),
    user_id: str = Query(..., description="Firebase User ID")
):
    """
    Deletes a custom user playlist and all its tracks from Firestore.
    Protected: The default 'Favorites' playlist cannot be deleted.
    """
    await playlist_service.delete_playlist(user_id=user_id, playlist_id=playlist_id)
    return {
        "success": True,
        "message": f"Playlist '{playlist_id}' deleted successfully"
    }


@router.post(
    "/{playlist_id}/songs",
    response_model=UserPlaylistResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a song to a user playlist"
)
async def add_song_to_playlist(
    playlist_id: str = Path(..., description="Playlist ID (e.g. 'favorites' or 'pl_...')"),
    payload: AddSongToPlaylistRequest = ...
):
    """
    Adds a song to any user playlist (or Favorites playlist).
    Validates the user, fetches track metadata from JioSaavn, and saves to Firestore.
    """
    data = await playlist_service.add_song_to_playlist(
        user_id=payload.user_id,
        playlist_id=playlist_id,
        song_id=payload.song_id
    )
    return UserPlaylistResponse(
        success=True,
        message="Song added to playlist successfully",
        data=data
    )


@router.delete(
    "/{playlist_id}/songs/{song_id}",
    summary="Remove a song from a user playlist"
)
async def remove_song_from_playlist(
    playlist_id: str = Path(..., description="Playlist ID"),
    song_id: str = Path(..., description="JioSaavn Song ID"),
    user_id: str = Query(..., description="Firebase User ID")
):
    """
    Removes a song from the specified user playlist.
    """
    await playlist_service.remove_song_from_playlist(
        user_id=user_id,
        playlist_id=playlist_id,
        song_id=song_id
    )
    return {
        "success": True,
        "message": f"Song '{song_id}' removed from playlist '{playlist_id}'"
    }
