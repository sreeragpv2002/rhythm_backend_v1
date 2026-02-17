from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q, Count
from django.utils import timezone
from datetime import timedelta
from accounts.permissions import IsOwnerOrAdmin
from api.response import success_response, error_response
from api.messages import *
from .models import Playlist, RecentlyPlayed, Favorite, Music, Tag
from .serializers import (
    PlaylistSerializer, PlaylistCreateSerializer, PlaylistAddTrackSerializer,
    RecentlyPlayedSerializer, FavoriteSerializer, MusicListSerializer
)


class PlaylistViewSet(viewsets.ModelViewSet):
    """ViewSet for Playlist management"""
    serializer_class = PlaylistSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return user's own playlists or public playlists"""
        if self.request.user.is_authenticated:
            return Playlist.objects.filter(
                Q(user=self.request.user) | Q(is_public=True)
            ).prefetch_related('music_tracks').annotate(
                track_count=Count('music_tracks')
            )
        return Playlist.objects.filter(is_public=True).annotate(
            track_count=Count('music_tracks')
        )
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PlaylistCreateSerializer
        return PlaylistSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a new playlist"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        playlist = serializer.save(user=request.user)
        
        return Response(
            success_response(
                message=SUCCESS_CREATED,
                data=PlaylistSerializer(playlist).data
            ),
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def add_track(self, request, pk=None):
        """Add a track to playlist"""
        playlist = self.get_object()
        
        # Check ownership
        if playlist.user != request.user:
            return Response(
                error_response(message=PERMISSION_DENIED),
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = PlaylistAddTrackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        music = serializer.validated_data['music_id']
        playlist.music_tracks.add(music)
        
        return Response(success_response(
            message=SUCCESS_ADDED,
            data=PlaylistSerializer(playlist).data
        ))
    
    @action(detail=True, methods=['post'])
    def remove_track(self, request, pk=None):
        """Remove a track from playlist"""
        playlist = self.get_object()
        
        # Check ownership
        if playlist.user != request.user:
            return Response(
                error_response(message=PERMISSION_DENIED),
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = PlaylistAddTrackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        music = serializer.validated_data['music_id']
        playlist.music_tracks.remove(music)
        
        return Response(success_response(
            message=SUCCESS_REMOVED,
            data=PlaylistSerializer(playlist).data
        ))
    
    @action(detail=False, methods=['get'])
    def my_playlists(self, request):
        """Get current user's playlists"""
        playlists = Playlist.objects.filter(user=request.user).annotate(
            track_count=Count('music_tracks')
        )
        serializer = PlaylistSerializer(playlists, many=True)
        return Response(success_response(data=serializer.data))


class FavoriteViewSet(viewsets.ViewSet):
    """ViewSet for managing favorites"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get user's favorite music"""
        favorites = Favorite.objects.filter(user=request.user).select_related('music')
        serializer = FavoriteSerializer(favorites, many=True, context={'request': request})
        return Response(success_response(data=serializer.data))
    
    def create(self, request):
        """Add music to favorites"""
        music_id = request.data.get('music_id')
        
        if not music_id:
            return Response(
                error_response(message="music_id is required"),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            music = Music.objects.get(id=music_id)
        except Music.DoesNotExist:
            return Response(
                error_response(message=NOT_FOUND_MUSIC),
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already favorited
        if Favorite.objects.filter(user=request.user, music=music).exists():
            return Response(
                error_response(message=BUSINESS_ALREADY_FAVORITED),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        favorite = Favorite.objects.create(user=request.user, music=music)
        serializer = FavoriteSerializer(favorite, context={'request': request})
        
        return Response(
            success_response(message=SUCCESS_ADDED, data=serializer.data),
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=False, methods=['delete'])
    def remove(self, request):
        """Remove music from favorites"""
        music_id = request.data.get('music_id')
        
        if not music_id:
            return Response(
                error_response(message="music_id is required"),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            favorite = Favorite.objects.get(user=request.user, music_id=music_id)
            favorite.delete()
            return Response(success_response(message=SUCCESS_REMOVED))
        except Favorite.DoesNotExist:
            return Response(
                error_response(message=BUSINESS_NOT_FAVORITED),
                status=status.HTTP_404_NOT_FOUND
            )


class RecentlyPlayedViewSet(viewsets.ViewSet):
    """ViewSet for recently played music"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get user's recently played music"""
        recently_played = RecentlyPlayed.objects.filter(
            user=request.user
        ).select_related('music').order_by('-played_at')[:50]
        
        serializer = RecentlyPlayedSerializer(recently_played, many=True, context={'request': request})
        return Response(success_response(data=serializer.data))


class HomeViewSet(viewsets.ViewSet):
    """ViewSet for personalized home feed"""
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Get personalized home feed based on user interests and recent activity"""
        user = request.user
        home_data = {}
        
        # 1. Recently Played
        recently_played = RecentlyPlayed.objects.filter(user=user).select_related('music')[:10]
        home_data['recently_played'] = RecentlyPlayedSerializer(
            recently_played, many=True, context={'request': request}
        ).data
        
        # 2. Favorites
        favorites = Favorite.objects.filter(user=user).select_related('music')[:10]
        home_data['favorites'] = FavoriteSerializer(
            favorites, many=True, context={'request': request}
        ).data
        
        # 3. Recommended based on favorite artists
        favorite_artists = user.profile.favorite_artists.all()
        if favorite_artists.exists():
            recommended_by_artists = Music.objects.filter(
                artist__in=favorite_artists
            ).exclude(
                id__in=recently_played.values_list('music_id', flat=True)
            ).order_by('-play_count')[:20]
            home_data['recommended_by_artists'] = MusicListSerializer(
                recommended_by_artists, many=True, context={'request': request}
            ).data
        else:
            home_data['recommended_by_artists'] = []
        
        # 4. Recommended based on recently played genres/tags
        recent_music_ids = recently_played.values_list('music_id', flat=True)[:5]
        if recent_music_ids:
            # Get tags from recently played music
            recent_tags = Tag.objects.filter(
                music_tracks__id__in=recent_music_ids
            ).distinct()
            
            # Find music with similar tags
            recommended_by_tags = Music.objects.filter(
                tags__in=recent_tags
            ).exclude(
                id__in=recent_music_ids
            ).distinct().order_by('-play_count')[:20]
            
            home_data['recommended_by_mood'] = MusicListSerializer(
                recommended_by_tags, many=True, context={'request': request}
            ).data
        else:
            home_data['recommended_by_mood'] = []
        
        # 5. Trending music (most played overall)
        trending = Music.objects.order_by('-play_count')[:20]
        home_data['trending'] = MusicListSerializer(
            trending, many=True, context={'request': request}
        ).data
        
        # 6. New releases (recent uploads)
        new_releases = Music.objects.order_by('-created_at')[:20]
        home_data['new_releases'] = MusicListSerializer(
            new_releases, many=True, context={'request': request}
        ).data
        
        # 7. Popular by language (based on user's preferred language)
        user_language = user.profile.language
        if user_language == 'ar':
            music_language = Music.Language.ARABIC
        else:
            music_language = Music.Language.ENGLISH
        
        popular_by_language = Music.objects.filter(
            language=music_language
        ).order_by('-play_count')[:20]
        home_data['popular_in_your_language'] = MusicListSerializer(
            popular_by_language, many=True, context={'request': request}
        ).data
        
        return Response(success_response(
            message="Home feed loaded successfully",
            data=home_data
        ))
