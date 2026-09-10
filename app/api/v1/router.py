from fastapi import APIRouter

from app.api.v1.endpoints.details import (
    albums_router,
    artists_router,
    playlists_router,
    songs_router,
)
from app.api.v1.endpoints.details import (
    router as details_router,
)
from app.api.v1.endpoints.favorites import router as favorites_router
from app.api.v1.endpoints.home import router as home_router
from app.api.v1.endpoints.languages import router as languages_router
from app.api.v1.endpoints.recent_plays import router as recent_plays_router
from app.api.v1.endpoints.search import router as search_router
from app.api.v1.endpoints.user_playlists import router as user_playlists_router

api_router = APIRouter()

api_router.include_router(home_router, prefix="/home", tags=["Home"])
api_router.include_router(recent_plays_router, prefix="/recent-plays", tags=["Recent Plays"])
api_router.include_router(languages_router, prefix="/languages", tags=["Languages"])
api_router.include_router(details_router, prefix="/details", tags=["Details"])
api_router.include_router(songs_router, prefix="/songs", tags=["Songs"])
api_router.include_router(playlists_router, prefix="/playlists", tags=["Playlists"])
api_router.include_router(artists_router, prefix="/artists", tags=["Artists"])
api_router.include_router(albums_router, prefix="/albums", tags=["Albums"])
api_router.include_router(favorites_router, prefix="/favorites", tags=["Favorites"])
api_router.include_router(search_router, prefix="/search", tags=["Search"])
api_router.include_router(user_playlists_router, prefix="/user-playlists", tags=["User Playlists"])
api_router.include_router(user_playlists_router, prefix="/playlists/user", tags=["User Playlists"])
