from fastapi import APIRouter, Query, status

from app.models.language import (
    AvailableLanguagesResponse,
    UserLanguagesRequest,
    UserLanguagesResponse,
)
from app.services.language_service import language_service

router = APIRouter()


@router.get(
    "",
    response_model=AvailableLanguagesResponse,
    summary="Get list of available supported languages"
)
async def get_available_languages():
    """
    Returns the fixed list of supported languages:
    - malayalam
    - tamil
    - hindi
    - kannada
    - telugu
    - english
    """
    langs = language_service.get_available_languages()
    return AvailableLanguagesResponse(success=True, data=langs)


@router.get(
    "/user",
    response_model=UserLanguagesResponse,
    summary="Get user's selected languages from Firestore"
)
async def get_user_languages(
    user_id: str = Query(..., description="Firebase User ID (required)")
):
    """
    Retrieves the languages selected and saved for the verified user from Firebase Firestore.
    """
    data = await language_service.get_user_languages(user_id=user_id)
    return UserLanguagesResponse(
        success=True,
        message="User languages retrieved successfully",
        data=data
    )


@router.post(
    "/user",
    response_model=UserLanguagesResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Save user's selected languages to Firestore"
)
async def set_user_languages(payload: UserLanguagesRequest):
    """
    Saves the user's selected languages in Firebase Firestore.
    Only allows: malayalam, tamil, hindi, kannada, telugu, english.
    """
    saved_data = await language_service.update_user_languages(
        user_id=payload.user_id,
        languages=payload.languages
    )
    return UserLanguagesResponse(
        success=True,
        message="User languages saved successfully",
        data=saved_data
    )


@router.put(
    "/user",
    response_model=UserLanguagesResponse,
    summary="Edit / update user's selected languages in Firestore"
)
async def edit_user_languages(payload: UserLanguagesRequest):
    """
    Edits and updates the user's selected languages in Firebase Firestore.
    Only allows: malayalam, tamil, hindi, kannada, telugu, english.
    """
    updated_data = await language_service.update_user_languages(
        user_id=payload.user_id,
        languages=payload.languages
    )
    return UserLanguagesResponse(
        success=True,
        message="User languages updated successfully",
        data=updated_data
    )
