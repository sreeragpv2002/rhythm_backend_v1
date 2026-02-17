from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class Advertisement(models.Model):
    """Advertisement model for displaying ads in the app"""
    
    class AdType(models.TextChoices):
        BANNER = 'BANNER', _('Banner')
        VIDEO = 'VIDEO', _('Video')
        AUDIO = 'AUDIO', _('Audio')
        INTERSTITIAL = 'INTERSTITIAL', _('Interstitial')
    
    class AdPlacement(models.TextChoices):
        HOME_TOP = 'HOME_TOP', _('Home Top')
        HOME_MIDDLE = 'HOME_MIDDLE', _('Home Middle')
        PLAYER = 'PLAYER', _('Player')
        SEARCH = 'SEARCH', _('Search')
        PLAYLIST = 'PLAYLIST', _('Playlist')
    
    title = models.CharField(_('title'), max_length=200)
    description = models.TextField(_('description'), blank=True)
    ad_type = models.CharField(
        _('ad type'),
        max_length=20,
        choices=AdType.choices,
        default=AdType.BANNER
    )
    placement = models.CharField(
        _('placement'),
        max_length=20,
        choices=AdPlacement.choices,
        default=AdPlacement.HOME_TOP
    )
    image = models.ImageField(
        _('image'),
        upload_to='ads/images/',
        null=True,
        blank=True,
        help_text=_('For banner and interstitial ads')
    )
    video_file = models.FileField(
        _('video file'),
        upload_to='ads/videos/',
        null=True,
        blank=True,
        help_text=_('For video ads')
    )
    audio_file = models.FileField(
        _('audio file'),
        upload_to='ads/audio/',
        null=True,
        blank=True,
        help_text=_('For audio ads')
    )
    click_url = models.URLField(
        _('click URL'),
        max_length=500,
        help_text=_('URL to redirect when ad is clicked')
    )
    duration = models.PositiveIntegerField(
        _('duration'),
        default=0,
        help_text=_('Duration in seconds (for video/audio ads)')
    )
    is_active = models.BooleanField(_('is active'), default=True)
    priority = models.PositiveIntegerField(
        _('priority'),
        default=0,
        help_text=_('Higher priority ads are shown first')
    )
    impression_count = models.PositiveIntegerField(_('impression count'), default=0)
    click_count = models.PositiveIntegerField(_('click count'), default=0)
    start_date = models.DateTimeField(_('start date'), null=True, blank=True)
    end_date = models.DateTimeField(_('end date'), null=True, blank=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('advertisement')
        verbose_name_plural = _('advertisements')
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['placement', 'is_active', '-priority']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.get_ad_type_display()})"
    
    def increment_impression(self):
        """Increment impression count"""
        self.impression_count += 1
        self.save(update_fields=['impression_count'])
    
    def increment_click(self):
        """Increment click count"""
        self.click_count += 1
        self.save(update_fields=['click_count'])
    
    @property
    def click_through_rate(self):
        """Calculate click-through rate"""
        if self.impression_count == 0:
            return 0
        return (self.click_count / self.impression_count) * 100


class AdImpression(models.Model):
    """Track ad impressions per user"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ad_impressions',
        verbose_name=_('user'),
        null=True,
        blank=True
    )
    advertisement = models.ForeignKey(
        Advertisement,
        on_delete=models.CASCADE,
        related_name='impressions',
        verbose_name=_('advertisement')
    )
    session_id = models.CharField(
        _('session ID'),
        max_length=100,
        help_text=_('For tracking anonymous users')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('ad impression')
        verbose_name_plural = _('ad impressions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['advertisement', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.advertisement.title} - {self.created_at}"


class AdClick(models.Model):
    """Track ad clicks per user"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ad_clicks',
        verbose_name=_('user'),
        null=True,
        blank=True
    )
    advertisement = models.ForeignKey(
        Advertisement,
        on_delete=models.CASCADE,
        related_name='clicks',
        verbose_name=_('advertisement')
    )
    session_id = models.CharField(
        _('session ID'),
        max_length=100,
        help_text=_('For tracking anonymous users')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('ad click')
        verbose_name_plural = _('ad clicks')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['advertisement', '-created_at']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.advertisement.title} - {self.created_at}"
