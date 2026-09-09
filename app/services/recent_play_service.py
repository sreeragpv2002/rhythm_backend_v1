import asyncio
from typing import Any

from fastapi import HTTPException, status

from app.services.saavn_service import saavn_service
from core.firebase import get_recent_plays, save_recent_play, verify_user_exists


class RecentPlayService:
    async def record_recent_play(self, user_id: str, song_id: str) -> dict[str, Any]:
        """
        Records a song as recently played:
        1. Verifies user exists in Firebase.
        2. Retrieves full song metadata from JioSaavn API by song_id.
        3. Saves/updates song in Firestore under users/{user_id}/recent_plays/{song_id}.
        """
        # 1. Verify user in Firebase
        user_exists = await asyncio.to_thread(verify_user_exists, user_id)
        if not user_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{user_id}' not found in Firebase"
            )

        # 2. Fetch song from JioSaavn API
        song_data = await saavn_service.get_song_by_id(song_id)
        if not song_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Song with ID '{song_id}' not found on JioSaavn"
            )

        # 3. Save to Firestore
        saved_record = await asyncio.to_thread(save_recent_play, user_id, song_data)
        return saved_record

    async def get_user_recent_plays(self, user_id: str, limit: int = 10) -> list[dict[str, Any]]:
        """
        Fetches recently played songs for a verified user from Firestore.
        """
        user_exists = await asyncio.to_thread(verify_user_exists, user_id)
        if not user_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{user_id}' not found in Firebase"
            )

        return await asyncio.to_thread(get_recent_plays, user_id, limit)


recent_play_service = RecentPlayService()
