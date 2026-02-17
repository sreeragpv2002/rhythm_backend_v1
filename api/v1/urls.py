from django.urls import path, include

urlpatterns = [
    # Authentication endpoints
    path('auth/', include('accounts.urls')),
    
    # Music endpoints
    path('', include('music.urls')),
]
