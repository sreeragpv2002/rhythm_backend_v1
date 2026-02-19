from django.contrib import admin
from modeltranslation.admin import TranslationAdmin
from .models import Artist, Album, Tag, Music, Playlist, RecentlyPlayed, Favorite


@admin.register(Artist)
class ArtistAdmin(TranslationAdmin):
    """Admin configuration for Artist model"""
    list_display = ('name', 'image', 'image_url', 'created_at')
    search_fields = ('name', 'bio')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Album)
class AlbumAdmin(TranslationAdmin):
    """Admin configuration for Album model"""
    list_display = ('title', 'release_date', 'cover_image', 'cover_image_url', 'created_at')
    list_filter = ('release_date',)
    search_fields = ('title', 'artist__name')
    filter_horizontal = ('artist',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Tag)
class TagAdmin(TranslationAdmin):
    """Admin configuration for Tag model"""
    list_display = ('name', 'category', 'color_code', 'created_at')
    list_filter = ('category',)
    search_fields = ('name',)
    readonly_fields = ('created_at',)


@admin.register(Music)
class MusicAdmin(TranslationAdmin):
    """Admin configuration for Music model"""
    list_display = ('title', 'album', 'audio_file', 'audio_url', 'language', 'play_count', 'uploaded_by', 'created_at')
    list_filter = ('language', 'album', 'created_at')
    search_fields = ('title', 'artist__name', 'album__title')
    filter_horizontal = ('artist', 'tags',)
    readonly_fields = ('play_count', 'created_at', 'updated_at')
    
    def save_model(self, request, obj, form, change):
        if not change:  # If creating new object
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Playlist)
class PlaylistAdmin(TranslationAdmin):
    """Admin configuration for Playlist model"""
    list_display = ('name', 'user', 'is_public', 'track_count', 'created_at')
    list_filter = ('is_public', 'created_at')
    search_fields = ('name', 'user__email')
    filter_horizontal = ('music_tracks',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(RecentlyPlayed)
class RecentlyPlayedAdmin(admin.ModelAdmin):
    """Admin configuration for RecentlyPlayed model"""
    list_display = ('user', 'music', 'played_at')
    list_filter = ('played_at',)
    search_fields = ('user__email', 'music__title')
    readonly_fields = ('played_at',)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    """Admin configuration for Favorite model"""
    list_display = ('user', 'music', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__email', 'music__title')
    readonly_fields = ('created_at',)


# Import and register advertisement models
from .ads_models import Advertisement, AdImpression, AdClick


@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    """Admin configuration for Advertisement model"""
    list_display = ('title', 'ad_type', 'placement', 'is_active', 'priority', 
                    'impression_count', 'click_count', 'click_through_rate', 'created_at')
    list_filter = ('ad_type', 'placement', 'is_active', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('impression_count', 'click_count', 'click_through_rate', 'created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'ad_type', 'placement')
        }),
        ('Media Files', {
            'fields': ('image', 'video_file', 'audio_file', 'duration')
        }),
        ('Settings', {
            'fields': ('click_url', 'is_active', 'priority', 'start_date', 'end_date')
        }),
        ('Statistics', {
            'fields': ('impression_count', 'click_count', 'click_through_rate', 'created_at', 'updated_at')
        }),
    )
    actions = ['activate_ads', 'deactivate_ads']
    
    def activate_ads(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} ad(s) activated successfully.')
    activate_ads.short_description = "Activate selected ads"
    
    def deactivate_ads(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} ad(s) deactivated.')
    deactivate_ads.short_description = "Deactivate selected ads"


@admin.register(AdImpression)
class AdImpressionAdmin(admin.ModelAdmin):
    """Admin configuration for AdImpression model"""
    list_display = ('advertisement', 'user', 'session_id', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('advertisement__title', 'user__email', 'session_id')
    readonly_fields = ('created_at',)


@admin.register(AdClick)
class AdClickAdmin(admin.ModelAdmin):
    """Admin configuration for AdClick model"""
    list_display = ('advertisement', 'user', 'session_id', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('advertisement__title', 'user__email', 'session_id')
    readonly_fields = ('created_at',)
