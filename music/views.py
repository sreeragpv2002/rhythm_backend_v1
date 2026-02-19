from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from datetime import timedelta
from accounts.permissions import IsVerifiedBroadcaster, IsBroadcasterOrAdmin, IsOwnerOrAdmin
from api.response import success_response, error_response
from api.messages import *
from .models import (
    Artist, Album, Tag, Music, Playlist, 
    RecentlyPlayed, Favorite
)
from .serializers import (
    ArtistSerializer, ArtistListSerializer,
    AlbumSerializer, AlbumListSerializer,
    TagSerializer,
    MusicSerializer, MusicListSerializer, MusicUploadSerializer,
    PlaylistSerializer, PlaylistCreateSerializer, PlaylistAddTrackSerializer,
    RecentlyPlayedSerializer, FavoriteSerializer
)


class ArtistViewSet(viewsets.ModelViewSet):
    """ViewSet for Artist management"""
    queryset = Artist.objects.all()
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'bio']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ArtistListSerializer
        return ArtistSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsBroadcasterOrAdmin()]
        return [AllowAny()]
    
    @action(detail=True, methods=['get'])
    def music(self, request, pk=None):
        """Get all music by this artist"""
        artist = self.get_object()
        music_tracks = Music.objects.filter(artist=artist)
        serializer = MusicListSerializer(music_tracks, many=True, context={'request': request})
        return Response(success_response(data=serializer.data))
    
    @action(detail=True, methods=['get'])
    def albums(self, request, pk=None):
        """Get all albums by this artist"""
        artist = self.get_object()
        albums = Album.objects.filter(artist=artist)
        serializer = AlbumListSerializer(albums, many=True)
        return Response(success_response(data=serializer.data))


class AlbumViewSet(viewsets.ModelViewSet):
    """ViewSet for Album management"""
    queryset = Album.objects.prefetch_related('artist').all()
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'artist__name']
    ordering_fields = ['title', 'release_date', 'created_at']
    ordering = ['-release_date']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AlbumListSerializer
        return AlbumSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsBroadcasterOrAdmin()]
        return [AllowAny()]
    
    @action(detail=True, methods=['get'])
    def tracks(self, request, pk=None):
        """Get all tracks in this album"""
        album = self.get_object()
        tracks = Music.objects.filter(album=album)
        serializer = MusicListSerializer(tracks, many=True, context={'request': request})
        return Response(success_response(data=serializer.data))


class TagViewSet(viewsets.ModelViewSet):
    """ViewSet for Tag management"""
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'category']
    ordering = ['category', 'name']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsBroadcasterOrAdmin()]
        return [AllowAny()]
    
    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get tags grouped by category"""
        categories = {}
        for category_code, category_name in Tag.Category.choices:
            tags = Tag.objects.filter(category=category_code)
            categories[category_code] = TagSerializer(tags, many=True).data
        
        return Response(success_response(data=categories))
    
    @action(detail=True, methods=['get'])
    def music(self, request, pk=None):
        """Get all music with this tag"""
        tag = self.get_object()
        music_tracks = Music.objects.filter(tags=tag)
        serializer = MusicListSerializer(music_tracks, many=True, context={'request': request})
        return Response(success_response(data=serializer.data))


class MusicViewSet(viewsets.ModelViewSet):
    """ViewSet for Music management"""
    queryset = Music.objects.prefetch_related('artist', 'tags').select_related('album', 'uploaded_by').all()
    permission_classes = [IsAuthenticated()]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'artist__name', 'album__title']
    ordering_fields = ['title', 'play_count', 'created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return MusicUploadSerializer
        elif self.action == 'list':
            return MusicListSerializer
        return MusicSerializer
    
    def get_permissions(self):
        if self.action in ['create']:
            return [IsAuthenticated(), IsVerifiedBroadcaster()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsBroadcasterOrAdmin()]
        elif self.action in ['list', 'trending', 'discover', 'search']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by language
        language = self.request.query_params.get('language')
        if language:
            queryset = queryset.filter(language=language)
        
        # Filter by tags (comma-separated)
        tags = self.request.query_params.get('tags')
        if tags:
            tag_names = [t.strip() for t in tags.split(',')]
            queryset = queryset.filter(tags__name__in=tag_names).distinct()
        
        # Filter by artist
        artist_id = self.request.query_params.get('artist_id')
        if artist_id:
            queryset = queryset.filter(artist__id=artist_id)
        
        # Filter by album
        album_id = self.request.query_params.get('album_id')
        if album_id:
            queryset = queryset.filter(album_id=album_id)
        
        return queryset
    
    def create(self, request, *args, **kwargs):
        """Upload new music (broadcaster/admin only)"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        music = serializer.save(uploaded_by=request.user)
        
        # Update broadcaster stats
        if hasattr(request.user, 'broadcaster_profile'):
            broadcaster = request.user.broadcaster_profile
            broadcaster.total_uploads += 1
            broadcaster.save(update_fields=['total_uploads'])
        
        return Response(
            success_response(
                message=SUCCESS_CREATED,
                data=MusicSerializer(music, context={'request': request}).data
            ),
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def stream(self, request, pk=None):
        """Stream music and track play"""
        music = self.get_object()
        
        # Increment play count
        music.increment_play_count()
        
        # Track recently played for authenticated users
        if request.user.is_authenticated:
            RecentlyPlayed.objects.update_or_create(
                user=request.user,
                music=music,
                defaults={'played_at': timezone.now()}
            )
            
            # Update broadcaster stats
            if music.uploaded_by and hasattr(music.uploaded_by, 'broadcaster_profile'):
                broadcaster = music.uploaded_by.broadcaster_profile
                broadcaster.total_plays += 1
                broadcaster.save(update_fields=['total_plays'])
        
        serializer = MusicSerializer(music, context={'request': request})
        return Response(success_response(
            message="Music streaming started",
            data=serializer.data
        ))
    
    @action(detail=False, methods=['get'])
    def trending(self, request):
        """Get trending music (most played in last 7 days)"""
        # For simplicity, using play_count. In production, track plays with timestamps
        trending_music = Music.objects.order_by('-play_count')[:20]
        serializer = MusicListSerializer(trending_music, many=True, context={'request': request})
        return Response(success_response(data=serializer.data))
    
    @action(detail=False, methods=['get'])
    def discover(self, request):
        """Discover music by mood/genre"""
        tag_name = request.query_params.get('tag')
        if not tag_name:
            return Response(
                error_response(message="Tag parameter is required"),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            tag = Tag.objects.get(name__iexact=tag_name)
            music_tracks = Music.objects.filter(tags=tag).order_by('-play_count')[:50]
            serializer = MusicListSerializer(music_tracks, many=True, context={'request': request})
            return Response(success_response(data=serializer.data))
        except Tag.DoesNotExist:
            return Response(
                error_response(message="Tag not found"),
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def search(self, request):
        """Advanced search for music"""
        query = request.query_params.get('q', '')
        
        if not query:
            return Response(
                error_response(message="Search query is required"),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Search in title, artist name, album title
        music_tracks = Music.objects.filter(
            Q(title__icontains=query) |
            Q(artist__name__icontains=query) |
            Q(album__title__icontains=query)
        ).distinct()
        
        # Apply additional filters
        language = request.query_params.get('language')
        if language:
            music_tracks = music_tracks.filter(language=language)
        
        tags = request.query_params.get('tags')
        if tags:
            tag_names = [t.strip() for t in tags.split(',')]
            music_tracks = music_tracks.filter(tags__name__in=tag_names).distinct()
        
        serializer = MusicListSerializer(music_tracks, many=True, context={'request': request})
        return Response(success_response(data=serializer.data))
