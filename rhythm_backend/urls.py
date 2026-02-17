"""
URL configuration for rhythm_backend project.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = i18n_patterns(
    # Admin
    path('admin/', admin.site.urls),
    
    # API v1
    path('api/v1/', include('api.v1.urls')),
    
    # API Schema and Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
)

# Non-localized patterns (must be outside i18n_patterns)
urlpatterns += [
    # Any other non-localized paths
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Customize admin site
admin.site.site_header = "Rhythm Admin"
admin.site.site_title = "Rhythm Admin Portal"
admin.site.index_title = "Welcome to Rhythm Music Streaming Platform"
