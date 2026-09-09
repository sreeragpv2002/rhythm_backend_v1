import asyncio
from typing import Any

from fastapi import HTTPException, status

from app.api.v1.endpoints.home import extract_image_url, format_home_item
from app.services.saavn_service import saavn_service
from core.firebase import (
    add_song_to_playlist,
    create_user_playlist,
    delete_user_playlist,
    get_user_playlist_details,
    get_user_playlists,
    is_song_favorited,
    remove_song_from_playlist,
    verify_user_exists,
)


class PlaylistService:
    async def _verify_user(self, user_id: str):
        exists = await asyncio.to_thread(verify_user_exists, user_id)
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User '{user_id}' not found in Firebase"
            )

    async def _fetch_and_prepare_song(self, song_id: str) -> dict[str, Any]:
        song = await saavn_service.get_song_by_id(song_id)
        if not song:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Song with ID '{song_id}' not found on JioSaavn"
            )
        return song

    async def add_favorite(self, user_id: str, song_id: str) -> dict[str, Any]:
        """
        Adds a song to the user's default 'favorites' playlist in Firestore.
        """
        await self._verify_user(user_id)
        song_data = await self._fetch_and_prepare_song(song_id)

        await asyncio.to_thread(add_song_to_playlist, user_id, "favorites", song_data)
        details = await asyncio.to_thread(get_user_playlist_details, user_id, "favorites", 50)
        return self._format_playlist(details)

    async def remove_favorite(self, user_id: str, song_id: str) -> bool:
        """
        Removes a song from the user's default 'favorites' playlist in Firestore.
        """
        await self._verify_user(user_id)
        removed = await asyncio.to_thread(remove_song_from_playlist, user_id, "favorites", song_id)
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Song '{song_id}' was not in favorites"
            )
        return True

    async def get_favorites(self, user_id: str, limit: int = 50) -> dict[str, Any]:
        """
        Retrieves the user's 'favorites' playlist and its favorited tracks.
        """
        await self._verify_user(user_id)
        details = await asyncio.to_thread(get_user_playlist_details, user_id, "favorites", limit)
        return self._format_playlist(details)

    async def check_favorite(self, user_id: str, song_id: str) -> bool:
        """
        Checks whether a song is favorited by the user.
        """
        await self._verify_user(user_id)
        return await asyncio.to_thread(is_song_favorited, user_id, song_id)

    async def create_playlist(
        self,
        user_id: str,
        name: str,
        description: str | None = None,
        song_ids: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Creates a new custom user playlist in Firestore, optionally adding initial songs.
        """
        await self._verify_user(user_id)
        created = await asyncio.to_thread(create_user_playlist, user_id, name, description)
        playlist_id = created["id"]

        if song_ids:
            for s_id in song_ids:
                try:
                    s_data = await self._fetch_and_prepare_song(s_id)
                    await asyncio.to_thread(add_song_to_playlist, user_id, playlist_id, s_data)
                except HTTPException:
                    pass

        details = await asyncio.to_thread(get_user_playlist_details, user_id, playlist_id, 50)
        return self._format_playlist(details or created)

    async def get_user_playlists(self, user_id: str) -> list[dict[str, Any]]:
        """
        Lists all playlists for the user (always including 'Favorites' at the top).
        """
        await self._verify_user(user_id)
        raw_playlists = await asyncio.to_thread(get_user_playlists, user_id)
        return [self._format_playlist(p) for p in raw_playlists]

    async def get_playlist_details(self, user_id: str, playlist_id: str, limit: int = 50) -> dict[str, Any]:
        """
        Retrieves a specific playlist's metadata and track list.
        """
        await self._verify_user(user_id)
        details = await asyncio.to_thread(get_user_playlist_details, user_id, playlist_id, limit)
        if not details:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Playlist '{playlist_id}' not found for user '{user_id}'"
            )
        return self._format_playlist(details)

    async def add_song_to_playlist(self, user_id: str, playlist_id: str, song_id: str) -> dict[str, Any]:
        """
        Adds a song to any user playlist by ID.
        """
        await self._verify_user(user_id)
        song_data = await self._fetch_and_prepare_song(song_id)

        try:
            await asyncio.to_thread(add_song_to_playlist, user_id, playlist_id, song_data)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            ) from e

        details = await asyncio.to_thread(get_user_playlist_details, user_id, playlist_id, 50)
        return self._format_playlist(details)

    async def remove_song_from_playlist(self, user_id: str, playlist_id: str, song_id: str) -> bool:
        """
        Removes a song from any user playlist by ID.
        """
        await self._verify_user(user_id)
        removed = await asyncio.to_thread(remove_song_from_playlist, user_id, playlist_id, song_id)
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Song '{song_id}' not found in playlist '{playlist_id}'"
            )
        return True

    async def delete_playlist(self, user_id: str, playlist_id: str) -> bool:
        """
        Deletes a custom user playlist. Blocks deletion of the system 'favorites' playlist.
        """
        await self._verify_user(user_id)
        if playlist_id == "favorites":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The default 'Favorites' playlist cannot be deleted."
            )
        try:
            deleted = await asyncio.to_thread(delete_user_playlist, user_id, playlist_id)
            if not deleted:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Playlist '{playlist_id}' not found"
                )
            return True
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            ) from e

    def _format_playlist(self, pl_dict: dict[str, Any] | None) -> dict[str, Any]:
        if not pl_dict:
            return {}
        result = dict(pl_dict)
        if "image" in result:
            result["image"] = extract_image_url(result["image"])
        if "image_url" in result:
            result["image_url"] = extract_image_url(result["image_url"])
        elif "image" in result:
            result["image_url"] = result["image"]

        if "songs" in result and isinstance(result["songs"], list):
            result["songs"] = [format_home_item(s, "song").model_dump() for s in result["songs"]]
        return result


playlist_service = PlaylistService()
