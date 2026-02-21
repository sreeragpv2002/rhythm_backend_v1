from django.conf import settings
from rest_framework import serializers
from .models import Artist, Album, Tag, Music, Playlist, RecentlyPlayed, Favorite



class ArtistSerializer(serializers.ModelSerializer):
    """Serializer for Artist model"""
    
    class Meta:
        model = Artist
        fields = ['id', 'name', 'bio', 'image', 'image_url', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def validate(self, data):
        """Ensure either image or image_url is provided"""
        if not data.get('image') and not data.get('image_url'):
            raise serializers.ValidationError(
                "Either 'image' or 'image_url' must be provided."
            )
        return data




class ArtistListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing artists"""
    
    class Meta:
        model = Artist
        fields = ['id', 'name', 'image','image_url']


class AlbumSerializer(serializers.ModelSerializer):
    """Serializer for Album model"""
    artist = ArtistListSerializer(many=True, read_only=True)
    artist_ids = serializers.PrimaryKeyRelatedField(
        queryset=Artist.objects.all(),
        source='artist',
        many=True,
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Album
        fields = ['id', 'title', 'artist', 'artist_ids', 'release_date',
                  'cover_image', 'cover_image_url', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def validate(self, data):
        """Ensure either cover_image or cover_image_url is provided"""
        if not data.get('cover_image') and not data.get('cover_image_url'):
            raise serializers.ValidationError(
                "Either 'cover_image' or 'cover_image_url' must be provided."
            )
        return data
    
    def create(self, validated_data):
        artists = validated_data.pop('artist', [])
        album = Album.objects.create(**validated_data)
        if artists:
            album.artist.set(artists)
        return album
    
    def update(self, instance, validated_data):
        artists = validated_data.pop('artist', None)
        instance = super().update(instance, validated_data)
        if artists is not None:
            instance.artist.set(artists)
        return instance




class AlbumListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing albums"""
    artist_names = serializers.SerializerMethodField()
    
    class Meta:
        model = Album
        fields = ['id', 'title', 'artist_names', 'cover_image', 'cover_image_url', 'release_date']
    
    def get_artist_names(self, obj):
        return list(obj.artist.values_list('name', flat=True))


class TagSerializer(serializers.ModelSerializer):
    """Serializer for Tag model"""
    
    class Meta:
        model = Tag
        fields = ['id', 'name', 'category', 'description', 'color_code', 'icon', 'created_at']
        read_only_fields = ['id', 'created_at']


class MusicSerializer(serializers.ModelSerializer):
    """Detailed serializer for Music model"""
    artist = ArtistListSerializer(many=True, read_only=True)
    album = AlbumListSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    is_favorited = serializers.SerializerMethodField()
    related_by_album = serializers.SerializerMethodField()
    related_by_artist = serializers.SerializerMethodField()
    related_by_tags = serializers.SerializerMethodField()

    language_display = serializers.CharField(source='get_language_display', read_only=True)
    
    class Meta:
        model = Music
        fields = ['id', 'title', 'artist', 'album', 'audio_file', 'audio_url', 'thumb_url', 'duration',
                  'language', 'language_display', 'tags', 'play_count', 'is_favorited', 'created_at',
                  'related_by_album', 'related_by_artist', 'related_by_tags']
        read_only_fields = ['id', 'play_count', 'created_at']


    
    def get_is_favorited(self, obj):
        """Check if current user has favorited this music"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(user=request.user, music=obj).exists()
        return False
    
    def get_related_by_album(self, obj):
        """Get other songs from the same album"""
        if not obj.album:
            return []
        related = Music.objects.filter(album=obj.album).exclude(id=obj.id)
        return MusicListSerializer(related[:10], many=True, context=self.context).data
        
    def get_related_by_artist(self, obj):
        """Get other songs by the same artists"""
        artists = obj.artist.all()
        related = Music.objects.filter(artist__in=artists).exclude(id=obj.id).distinct()
        # Exclude songs already in the album list if applicable
        if obj.album:
            related = related.exclude(album=obj.album)
        return MusicListSerializer(related[:10], many=True, context=self.context).data
        
    def get_related_by_tags(self, obj):
        """Get other songs sharing at least one tag"""
        tags = obj.tags.all()
        if not tags:
            return []
        artists = obj.artist.all()
        related = Music.objects.filter(tags__in=tags).exclude(id=obj.id).distinct()
        # Exclude songs already in artist or album list
        related = related.exclude(artist__in=artists)
        if obj.album:
            related = related.exclude(album=obj.album)
        return MusicListSerializer(related[:10], many=True, context=self.context).data



class MusicListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing music"""
    artist_names = serializers.SerializerMethodField()
    album_title = serializers.CharField(source='album.title', read_only=True, allow_null=True)
    tags = TagSerializer(many=True, read_only=True)
    language_display = serializers.CharField(source='get_language_display', read_only=True)
    
    is_favorited = serializers.SerializerMethodField()
    
    class Meta:
        model = Music
        fields = ['id', 'title', 'artist_names', 'album_title', 'thumb_url', 'audio_url', 'duration',
                  'language', 'language_display', 'tags', 'play_count', 'is_favorited']
    
    def get_artist_names(self, obj):
        return list(obj.artist.values_list('name', flat=True))
    
    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(user=request.user, music=obj).exists()
        return False


class MusicUploadSerializer(serializers.ModelSerializer):
    """Serializer for uploading music (broadcaster/admin)"""
    artist_ids = serializers.PrimaryKeyRelatedField(
        queryset=Artist.objects.all(),
        source='artist',
        many=True,
        write_only=True,
        required=False
    )
    album_id = serializers.PrimaryKeyRelatedField(
        queryset=Album.objects.all(),
        source='album',
        write_only=True,
        required=False,
        allow_null=True
    )
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Music
        fields = ['id', 'title', 'artist_ids', 'album_id', 'audio_file', 'audio_url', 'thumb_url',
                  'duration', 'language', 'tag_ids']
    
    def validate(self, data):
        """Ensure either audio_file or audio_url is provided"""
        if not data.get('audio_file') and not data.get('audio_url'):
            raise serializers.ValidationError(
                "Either 'audio_file' or 'audio_url' must be provided."
            )
        return data

    
    def create(self, validated_data):
        artist_ids = validated_data.pop('artist', [])
        tag_ids = validated_data.pop('tag_ids', [])
        music = Music.objects.create(**validated_data)
        if artist_ids:
            music.artist.set(artist_ids)
        if tag_ids:
            music.tags.set(tag_ids)
        return music


class PlaylistSerializer(serializers.ModelSerializer):
    """Serializer for Playlist model"""
    user_email = serializers.CharField(source='user.email', read_only=True)
    music_tracks = MusicListSerializer(many=True, read_only=True)
    track_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Playlist
        fields = ['id', 'name', 'user_email', 'music_tracks', 'track_count',
                  'is_public', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user_email', 'track_count', 'created_at', 'updated_at']


class PlaylistCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating playlists"""
    
    class Meta:
        model = Playlist
        fields = ['name', 'is_public']


class PlaylistAddTrackSerializer(serializers.Serializer):
    """Serializer for adding tracks to playlist"""
    music_id = serializers.PrimaryKeyRelatedField(
        queryset=Music.objects.all(),
        required=True
    )


class RecentlyPlayedSerializer(serializers.ModelSerializer):
    """Serializer for RecentlyPlayed model"""
    music = MusicListSerializer(read_only=True)
    
    class Meta:
        model = RecentlyPlayed
        fields = ['id', 'music', 'played_at']
        read_only_fields = ['id', 'played_at']


class FavoriteSerializer(serializers.ModelSerializer):
    """Serializer for Favorite model"""
    music = MusicListSerializer(read_only=True)
    
    class Meta:
        model = Favorite
        fields = ['id', 'music', 'created_at']
        read_only_fields = ['id', 'created_at']


class MusicSearchSerializer(serializers.Serializer):
    """Serializer for music search parameters"""
    q = serializers.CharField(required=False, help_text="Search query")
    artist = serializers.CharField(required=False, help_text="Artist name")
    album = serializers.CharField(required=False, help_text="Album title")
    language = serializers.ChoiceField(
        choices=Music.Language.choices,
        required=False,
        help_text="Music language"
    )
    tags = serializers.CharField(required=False, help_text="Comma-separated tag names")
    min_duration = serializers.IntegerField(required=False, help_text="Minimum duration in seconds")
    max_duration = serializers.IntegerField(required=False, help_text="Maximum duration in seconds")

class NormalizedMusicSerializer(serializers.ModelSerializer):
    """Compact serializer for normalization, including multi-language titles"""
    titles = serializers.SerializerMethodField()
    artist_names = serializers.SerializerMethodField()
    album_title = serializers.CharField(source='album.title', read_only=True, allow_null=True)
    language_display = serializers.CharField(source='get_language_display', read_only=True)
    is_favorited = serializers.SerializerMethodField()

    class Meta:
        model = Music
        fields = [
            'id', 'titles', 'artist_names', 'album_title', 'thumb_url', 
            'audio_url', 'duration', 'language', 'language_display', 
            'play_count', 'is_favorited'
        ]

    def get_titles(self, obj):
        """Return a map of titles in different languages"""
        titles = {}
        for lang_code, lang_name in settings.LANGUAGES:
            field_name = f'title_{lang_code}'
            # Check if translated field exists (modeltranslation adds these)
            if hasattr(obj, field_name):
                titles[lang_code] = getattr(obj, field_name) or obj.title
            else:
                titles[lang_code] = obj.title
        return titles

    def get_artist_names(self, obj):
        return list(obj.artist.values_list('name', flat=True))

    def get_is_favorited(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Favorite.objects.filter(user=request.user, music=obj).exists()
        return False


class HomeSectionSerializer(serializers.Serializer):
    """Serializer for a section in the home feed"""
    title = serializers.CharField()
    slug = serializers.CharField()
    items = serializers.ListField(child=serializers.IntegerField())
    has_more = serializers.BooleanField(default=False)


class HomeFeedSerializer(serializers.Serializer):
    """Serializer for the entire normalized home feed"""
    sections = HomeSectionSerializer(many=True)
    music_map = serializers.DictField(child=NormalizedMusicSerializer())
