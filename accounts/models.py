from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Custom user manager where email is the unique identifier"""
    
    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password"""
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser with the given email and password"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('role', User.Role.ADMIN)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Custom user model using email as the unique identifier"""
    
    class Role(models.TextChoices):
        CUSTOMER = 'CUSTOMER', _('Customer')
        BROADCASTER = 'BROADCASTER', _('Broadcaster')
        ADMIN = 'ADMIN', _('Admin')
    
    username = None  # Remove username field
    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(
        _('role'),
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER
    )
    is_email_verified = models.BooleanField(_('email verified'), default=False)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-created_at']
    
    def __str__(self):
        return self.email
    
    @property
    def is_customer(self):
        return self.role == self.Role.CUSTOMER
    
    @property
    def is_broadcaster(self):
        return self.role == self.Role.BROADCASTER
    
    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN


class UserProfile(models.Model):
    """Extended user profile with additional information"""
    
    class Language(models.TextChoices):
        ENGLISH = 'en', _('English')
        ARABIC = 'ar', _('Arabic')
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_('user')
    )
    language = models.CharField(
        _('preferred language'),
        max_length=5,
        choices=Language.choices,
        default=Language.ENGLISH
    )
    profile_image = models.ImageField(
        _('profile image'),
        upload_to='profiles/',
        null=True,
        blank=True
    )
    bio = models.TextField(_('bio'), max_length=500, blank=True)
    favorite_artists = models.ManyToManyField(
        'music.Artist',
        related_name='favorited_by',
        blank=True,
        verbose_name=_('favorite artists')
    )
    listening_preferences = models.JSONField(
        _('listening preferences'),
        default=dict,
        blank=True,
        help_text=_('User preferences for recommendations')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('user profile')
        verbose_name_plural = _('user profiles')
    
    def __str__(self):
        return f"{self.user.email}'s profile"


class Broadcaster(models.Model):
    """Broadcaster profile for users who can upload music"""
    
    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        VERIFIED = 'VERIFIED', _('Verified')
        REJECTED = 'REJECTED', _('Rejected')
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='broadcaster_profile',
        verbose_name=_('user')
    )
    verification_status = models.CharField(
        _('verification status'),
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING
    )
    bio = models.TextField(_('bio'), max_length=1000, blank=True)
    profile_image = models.ImageField(
        _('profile image'),
        upload_to='broadcasters/',
        null=True,
        blank=True
    )
    total_uploads = models.PositiveIntegerField(_('total uploads'), default=0)
    total_plays = models.PositiveIntegerField(_('total plays'), default=0)
    verified_at = models.DateTimeField(_('verified at'), null=True, blank=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    
    class Meta:
        verbose_name = _('broadcaster')
        verbose_name_plural = _('broadcasters')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - Broadcaster"
    
    @property
    def is_verified(self):
        return self.verification_status == self.VerificationStatus.VERIFIED
