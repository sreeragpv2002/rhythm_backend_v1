from django.core.cache import cache
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
    RecentlyPlayedSerializer, FavoriteSerializer, MusicListSerializer,
    NormalizedMusicSerializer, HomeSectionSerializer, HomeFeedSerializer
)


class PlaylistViewSet(viewsets.ModelViewSet):
# ... (existing PlaylistViewSet remains the same, I'll use multi_replace if needed but for now I'll replace the whole file or use multi_replace for accuracy)

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
    """ViewSet for personalized home feed with normalization and pagination"""
    permission_classes = [IsAuthenticated]
    
    def get_home_sections(self, user, request):
        """Define and fetch data for home sections"""
        sections = []
        music_ids = set()
        
        # 1. Recently Played (Preserve order)
        recently_played_ids = list(RecentlyPlayed.objects.filter(user=user).order_by('-played_at').values_list('music_id', flat=True)[:10])
        if recently_played_ids:
            sections.append({
                'title': "Recently Played",
                'slug': "recently_played",
                'items': recently_played_ids
            })
            music_ids.update(recently_played_ids)
        
        # 2. Favorites (Preserve order)
        favorite_ids = list(Favorite.objects.filter(user=user).order_by('-created_at').values_list('music_id', flat=True)[:15])
        if favorite_ids:
            sections.append({
                'title': "Favorites",
                'slug': "favorites",
                'items': favorite_ids
            })
            music_ids.update(favorite_ids)
        
        # 3. Recommended by Artists
        favorite_artists = user.profile.favorite_artists.all()
        if favorite_artists.exists():
            recommended_by_artists = Music.objects.filter(
                artist__in=favorite_artists
            ).exclude(id__in=recently_played_ids).distinct().order_by('-play_count')[:15]
            
            rec_ids = list(recommended_by_artists.values_list('id', flat=True))
            if rec_ids:
                sections.append({
                    'title': "Recommended for You",
                    'slug': "recommended_for_you",
                    'items': rec_ids
                })
                music_ids.update(rec_ids)

        # 4. Recommended by Mood/Tags
        if recently_played_ids:
            recent_tags = Tag.objects.filter(music_tracks__id__in=recently_played_ids[:5]).distinct()
            if recent_tags.exists():
                recommended_by_tags = Music.objects.filter(tags__in=recent_tags).exclude(id__in=recently_played_ids).distinct().order_by('-play_count')[:15]
                tag_ids = list(recommended_by_tags.values_list('id', flat=True))
                if tag_ids:
                    sections.append({
                        'title': "Based on your mood",
                        'slug': "recommended_mood",
                        'items': tag_ids
                    })
                    music_ids.update(tag_ids)

        # 5. Trending
        trending = Music.objects.order_by('-play_count')[:15]
        trending_ids = list(trending.values_list('id', flat=True))
        if trending_ids:
            sections.append({
                'title': "Trending",
                'slug': "trending",
                'items': trending_ids
            })
            music_ids.update(trending_ids)

        # 6. New Releases
        new_releases = Music.objects.order_by('-created_at')[:15]
        new_ids = list(new_releases.values_list('id', flat=True))
        if new_ids:
            sections.append({
                'title': "New Releases",
                'slug': "new_releases",
                'items': new_ids
            })
            music_ids.update(new_ids)

        # 7. Popular in Language
        user_lang = user.profile.language
        lang_enum = Music.Language.ARABIC if user_lang == 'ar' else Music.Language.ENGLISH
        popular_lang = Music.objects.filter(language=lang_enum).order_by('-play_count')[:15]
        lang_ids = list(popular_lang.values_list('id', flat=True))
        if lang_ids:
            sections.append({
                'title': "Popular in your language",
                'slug': "popular_language",
                'items': lang_ids
            })
            music_ids.update(lang_ids)

        return sections, music_ids



    def list(self, request):
        """Get normalized home feed"""
        user = request.user
        
        # Use profile language or default
        try:
            lang = user.profile.language
        except:
            lang = 'en'
            
        cache_key = f"home_feed_{user.id}_{lang}"
        
        # Try to get from cache
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(success_response(data=cached_data))

        sections_data, music_ids = self.get_home_sections(user, request)
        
        # Fetch all music objects for the map
        music_objs = Music.objects.filter(id__in=music_ids).prefetch_related('artist', 'tags', 'album')
        music_map = {str(m.id): NormalizedMusicSerializer(m, context={'request': request}).data for m in music_objs}
        
        data = {
            'sections': sections_data,
            'music_map': music_map
        }
        
        # Cache for 5 minutes
        cache.set(cache_key, data, 300)
        
        return Response(success_response(
            message="Home feed loaded successfully",
            data=data
        ))


    @action(detail=False, methods=['get'], url_path='section/(?P<slug>[^/.]+)')
    def section(self, request, slug=None):
        """Get paginated music for a specific section"""
        user = request.user
        queryset = Music.objects.none()

        if slug == 'recently_played':
            recently_played_ids = RecentlyPlayed.objects.filter(user=user).order_by('-played_at').values_list('music_id', flat=True)
            queryset = Music.objects.filter(id__in=recently_played_ids)
        elif slug == 'favorites':
            favorite_ids = Favorite.objects.filter(user=user).values_list('music_id', flat=True)
            queryset = Music.objects.filter(id__in=favorite_ids)
        elif slug == 'trending':
            queryset = Music.objects.order_by('-play_count')
        elif slug == 'new_releases':
            queryset = Music.objects.order_by('-created_at')
        elif slug == 'recommended_for_you':
            favorite_artists = user.profile.favorite_artists.all()
            queryset = Music.objects.filter(artist__in=favorite_artists).order_by('-play_count')
        elif slug == 'recommended_mood':
            recently_played_ids = RecentlyPlayed.objects.filter(user=user).order_by('-played_at').values_list('music_id', flat=True)[:5]
            recent_tags = Tag.objects.filter(music_tracks__id__in=recently_played_ids).distinct()
            queryset = Music.objects.filter(tags__in=recent_tags).exclude(id__in=recently_played_ids).distinct().order_by('-play_count')
        elif slug == 'popular_language':
            user_lang = getattr(user.profile, 'language', 'en')
            lang_enum = Music.Language.ARABIC if user_lang == 'ar' else Music.Language.ENGLISH
            queryset = Music.objects.filter(language=lang_enum).order_by('-play_count')
        else:
            return Response(error_response(message="Invalid section slug"), status=status.HTTP_404_NOT_FOUND)


        # Use standard pagination
        from api.pagination import StandardResultsSetPagination
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request)
        
        if page is not None:
            serializer = NormalizedMusicSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        serializer = NormalizedMusicSerializer(queryset, many=True, context={'request': request})
        return Response(success_response(data=serializer.data))

