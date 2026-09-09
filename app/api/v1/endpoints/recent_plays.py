from fastapi import APIRouter, Query, status

from app.models.recent_play import (
    RecentPlayRequest,
    RecentPlayResponse,
    RecentPlaysListResponse,
)
from app.services.recent_play_service import recent_play_service

router = APIRouter()


@router.post(
    "",
    response_model=RecentPlayResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a recently played song"
)
async def create_recent_play(payload: RecentPlayRequest):
    """
    Records a song play to Firebase Firestore:
    - **user_id**: Verified in Firebase Firestore/Auth.
    - **song_id**: JioSaavn Song ID (metadata fetched automatically).
    """
    saved_song = await recent_play_service.record_recent_play(
        user_id=payload.user_id,
        song_id=payload.song_id
    )
    return RecentPlayResponse(
        success=True,
        message="Recent play recorded successfully",
        data=saved_song
    )


@router.get(
    "",
    response_model=RecentPlaysListResponse,
    summary="Get user's recent plays"
)
async def list_recent_plays(
    user_id: str = Query(..., description="Firebase User ID (required)"),
    limit: int = Query(20, ge=1, le=50, description="Number of recent songs to retrieve")
):
    """
    Retrieves the list of recently played songs for the verified user from Firebase Firestore.
    """
    plays = await recent_play_service.get_user_recent_plays(user_id=user_id, limit=limit)
    return RecentPlaysListResponse(success=True, data=plays)
