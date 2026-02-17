from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ArtistViewSet, AlbumViewSet, TagViewSet, MusicViewSet
from .customer_views import (
    PlaylistViewSet, FavoriteViewSet, RecentlyPlayedViewSet, HomeViewSet
)
from .ads_views import AdvertisementViewSet

router = DefaultRouter()

# Music browsing
router.register(r'artists', ArtistViewSet, basename='artist')
router.register(r'albums', AlbumViewSet, basename='album')
router.register(r'tags', TagViewSet, basename='tag')
router.register(r'music', MusicViewSet, basename='music')

# Customer features
router.register(r'playlists', PlaylistViewSet, basename='playlist')
router.register(r'favorites', FavoriteViewSet, basename='favorite')
router.register(r'recently-played', RecentlyPlayedViewSet, basename='recently-played')
router.register(r'home', HomeViewSet, basename='home')

# Advertisements
router.register(r'ads', AdvertisementViewSet, basename='advertisement')

urlpatterns = [
    path('', include(router.urls)),
]
