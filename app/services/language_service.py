import asyncio
from typing import Any

from fastapi import HTTPException, status

from app.models.language import ALLOWED_LANGUAGES
from core.firebase import get_user_languages, save_user_languages, verify_user_exists


class LanguageService:
    def get_available_languages(self) -> list[str]:
        """Returns the fixed list of allowed languages."""
        return list(ALLOWED_LANGUAGES)

    async def update_user_languages(self, user_id: str, languages: list[str]) -> dict[str, Any]:
        """
        Validates user existence and languages, then saves to Firestore.
        """
        # 1. Verify user in Firebase
        user_exists = await asyncio.to_thread(verify_user_exists, user_id)
        if not user_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{user_id}' not found in Firebase"
            )

        # 2. Validate languages
        normalized = []
        invalid = []
        for lang in languages:
            clean = lang.strip().lower()
            if clean in ALLOWED_LANGUAGES:
                if clean not in normalized:
                    normalized.append(clean)
            else:
                invalid.append(lang)

        if invalid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid language(s): {invalid}. Allowed languages: {ALLOWED_LANGUAGES}"
            )

        if not normalized:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one valid language must be selected."
            )

        # 3. Save to Firestore
        saved_data = await asyncio.to_thread(save_user_languages, user_id, normalized)
        return saved_data

    async def get_user_languages(self, user_id: str) -> dict[str, Any]:
        """
        Retrieves user's saved languages from Firestore.
        """
        user_exists = await asyncio.to_thread(verify_user_exists, user_id)
        if not user_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{user_id}' not found in Firebase"
            )

        languages = await asyncio.to_thread(get_user_languages, user_id)
        return {
            "user_id": user_id,
            "languages": languages
        }


language_service = LanguageService()
