from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView,
    CustomTokenObtainPairView,
    UserProfileViewSet,
    BroadcasterViewSet,
    GoogleLogin,
)

router = DefaultRouter()
router.register(r'profiles', UserProfileViewSet, basename='profile')
router.register(r'broadcasters', BroadcasterViewSet, basename='broadcaster')

urlpatterns = [
    # Authentication
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('google/', GoogleLogin.as_view(), name='google_login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Router URLs
    path('', include(router.urls)),
]
