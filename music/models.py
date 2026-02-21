from django.db import models
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _
from .validators import validate_audio_file_size, validate_image_file_size

# Import advertisement models
from .ads_models import Advertisement, AdImpression, AdClick


class Artist(models.Model):
    """Artist model for music creators"""
    name = models.CharField(_('name'), max_length=200)
    bio = models.TextField(_('bio'), blank=True)
    image = models.ImageField(
        _('image'),
        upload_to='artists/',
        null=True,
        blank=True,
        validators=[validate_image_file_size]
    )
    image_url = models.URLField(_('image URL'), max_length=500, null=True, blank=True)

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('artist')
        verbose_name_plural = _('artists')
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
        ]
    
    def __str__(self):
        return self.name


class Album(models.Model):
    """Album model for grouping music"""
    title = models.CharField(_('title'), max_length=200)
    artist = models.ManyToManyField(
        Artist,
        related_name='albums',
        verbose_name=_('artists'),
        blank=True
    )
    release_date = models.DateField(_('release date'), null=True, blank=True)
    cover_image = models.ImageField(
        _('cover image'),
        upload_to='albums/',
        null=True,
        blank=True,
        validators=[validate_image_file_size]
    )
    cover_image_url = models.URLField(_('cover image URL'), max_length=500, null=True, blank=True)

    description = models.TextField(_('description'), blank=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('album')
        verbose_name_plural = _('albums')
        ordering = ['-release_date']
        indexes = [
            models.Index(fields=['-release_date']),
        ]
    
    def __str__(self):
        artist_names = ', '.join(self.artist.values_list('name', flat=True))
        return f"{self.title} - {artist_names}" if artist_names else self.title


class Tag(models.Model):
    """Tag model for categorizing music"""
    
    class Category(models.TextChoices):
        MOOD = 'MOOD', _('Mood')
        GENRE = 'GENRE', _('Genre')
        THEME = 'THEME', _('Theme')
    
    name = models.CharField(_('name'), max_length=50, unique=True)
    category = models.CharField(
        _('category'),
        max_length=20,
        choices=Category.choices,
        default=Category.MOOD
    )
    description = models.TextField(_('description'), blank=True)
    color_code = models.CharField(
        _('color code'),
        max_length=7,
        default='#000000',
        help_text=_('Hex color code for UI display')
    )
    icon = models.CharField(
        _('icon'),
        max_length=50,
        blank=True,
        help_text=_('Icon name or emoji')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('tag')
        verbose_name_plural = _('tags')
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['category']),
        ]
    
    def __str__(self):
        return f"#{self.name} ({self.get_category_display()})"


class Music(models.Model):
    """Music model for audio tracks"""
    
    class Language(models.TextChoices):
        ENGLISH = 'ENGLISH', _('English')
        ARABIC = 'ARABIC', _('Arabic')
        MALAYALAM = 'MALAYALAM', _('Malayalam')
        HINDI = 'HINDI', _('Hindi')
        TELUGU = 'TELUGU', _('Telugu')
        KANNADA = 'KANNADA', _('Kannada')
        TAMIL = 'TAMIL', _('Tamil')
        INSTRUMENTAL = 'INSTRUMENTAL', _('Instrumental')
        BILINGUAL = 'BILINGUAL', _('Bilingual')
    
    title = models.CharField(_('title'), max_length=200)
    artist = models.ManyToManyField(
        Artist,
        related_name='music_tracks',
        verbose_name=_('artists'),
        blank=True
    )
    album = models.ForeignKey(
        Album,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tracks',
        verbose_name=_('album')
    )
    audio_file = models.FileField(
        _('audio file'),
        upload_to='music/',
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=settings.ALLOWED_AUDIO_EXTENSIONS),
            validate_audio_file_size
        ]
    )
    audio_url = models.URLField(_('audio URL'), max_length=500, null=True, blank=True)
    thumb_url = models.URLField(_('thumbnail URL'), max_length=500, null=True, blank=True)

    duration = models.PositiveIntegerField(
        _('duration'),
        help_text=_('Duration in seconds'),
        default=0
    )
    language = models.CharField(
        _('language'),
        max_length=20,
        choices=Language.choices,
        default=Language.ENGLISH
    )
    tags = models.ManyToManyField(
        Tag,
        related_name='music_tracks',
        blank=True,
        verbose_name=_('tags')
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_music',
        verbose_name=_('uploaded by')
    )
    play_count = models.PositiveIntegerField(_('play count'), default=0)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('music')
        verbose_name_plural = _('music')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['album']),
            models.Index(fields=['language']),
            models.Index(fields=['-play_count']),
        ]
    
    def __str__(self):
        artist_names = ', '.join(self.artist.values_list('name', flat=True))
        return f"{self.title} - {artist_names}" if artist_names else self.title
    
    def increment_play_count(self):
        """Increment play count"""
        self.play_count += 1
        self.save(update_fields=['play_count'])


class Playlist(models.Model):
    """Playlist model for user-created collections"""
    name = models.CharField(_('name'), max_length=200)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='playlists',
        verbose_name=_('user')
    )
    music_tracks = models.ManyToManyField(
        Music,
        related_name='playlists',
        blank=True,
        verbose_name=_('music tracks')
    )
    is_public = models.BooleanField(_('is public'), default=False)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('playlist')
        verbose_name_plural = _('playlists')
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', '-updated_at']),
        ]
    
    def __str__(self):
        return f"{self.name} by {self.user.email}"
    
    @property
    def track_count(self):
        return self.music_tracks.count()


class RecentlyPlayed(models.Model):
    """Track recently played music for each user"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='recently_played',
        verbose_name=_('user')
    )
    music = models.ForeignKey(
        Music,
        on_delete=models.CASCADE,
        related_name='recent_plays',
        verbose_name=_('music')
    )
    played_at = models.DateTimeField(_('played at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('recently played')
        verbose_name_plural = _('recently played')
        ordering = ['-played_at']
        indexes = [
            models.Index(fields=['user', '-played_at']),
        ]
        unique_together = [['user', 'music']]
    
    def __str__(self):
        return f"{self.user.email} played {self.music.title}"


class Favorite(models.Model):
    """Track user's favorite music"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name=_('user')
    )
    music = models.ForeignKey(
        Music,
        on_delete=models.CASCADE,
        related_name='favorited_by',
        verbose_name=_('music')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('favorite')
        verbose_name_plural = _('favorites')
        ordering = ['-created_at']
        unique_together = [['user', 'music']]
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} favorited {self.music.title}"
