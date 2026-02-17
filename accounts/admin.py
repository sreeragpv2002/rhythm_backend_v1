from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, UserProfile, Broadcaster


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for custom User model"""
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name')}),
        (_('Permissions'), {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'is_email_verified',
                       'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role'),
        }),
    )
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_email_verified', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_superuser', 'is_active', 'is_email_verified')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('-created_at',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin configuration for UserProfile model"""
    list_display = ('user', 'language', 'created_at')
    list_filter = ('language', 'created_at')
    search_fields = ('user__email', 'bio')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('favorite_artists',)


@admin.register(Broadcaster)
class BroadcasterAdmin(admin.ModelAdmin):
    """Admin configuration for Broadcaster model"""
    list_display = ('user', 'verification_status', 'total_uploads', 'total_plays', 'created_at')
    list_filter = ('verification_status', 'created_at')
    search_fields = ('user__email', 'bio')
    readonly_fields = ('total_uploads', 'total_plays', 'verified_at', 'created_at', 'updated_at')
    actions = ['verify_broadcasters', 'reject_broadcasters']
    
    def verify_broadcasters(self, request, queryset):
        """Bulk verify broadcasters"""
        from django.utils import timezone
        updated = queryset.update(
            verification_status=Broadcaster.VerificationStatus.VERIFIED,
            verified_at=timezone.now()
        )
        self.message_user(request, f'{updated} broadcaster(s) verified successfully.')
    verify_broadcasters.short_description = "Verify selected broadcasters"
    
    def reject_broadcasters(self, request, queryset):
        """Bulk reject broadcasters"""
        updated = queryset.update(
            verification_status=Broadcaster.VerificationStatus.REJECTED
        )
        self.message_user(request, f'{updated} broadcaster(s) rejected.')
    reject_broadcasters.short_description = "Reject selected broadcasters"
