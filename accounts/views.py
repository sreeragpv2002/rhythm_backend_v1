from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from .models import UserProfile, Broadcaster
from .serializers import (
    UserSerializer,
    UserProfileSerializer,
    RegisterSerializer,
    CustomTokenObtainPairSerializer,
    BroadcasterSerializer,
    BroadcasterCreateSerializer,
)
from .permissions import IsOwnerOrAdmin, IsBroadcaster, IsAdmin
from api.response import success_response, error_response
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from dj_rest_auth.registration.views import SocialLoginView

class GoogleLogin(SocialLoginView):
    """Google social login endpoint"""
    adapter_class = GoogleOAuth2Adapter


User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """User registration endpoint"""
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response(
            success_response(
                message="User registered successfully.",
                data=UserSerializer(user).data
            ),
            status=status.HTTP_201_CREATED
        )


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom JWT token obtain view"""
    serializer_class = CustomTokenObtainPairSerializer


class UserProfileViewSet(viewsets.ModelViewSet):
    """ViewSet for user profile management"""
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    
    def get_queryset(self):
        if self.request.user.is_admin:
            return UserProfile.objects.all()
        return UserProfile.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['get', 'put', 'patch'])
    def me(self, request):
        """Get or update current user's profile"""
        profile = request.user.profile
        
        if request.method == 'GET':
            serializer = self.get_serializer(profile)
            return Response(success_response(data=serializer.data))
        
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(
            success_response(
                message="Profile updated successfully",
                data=serializer.data
            )
        )


class BroadcasterViewSet(viewsets.ModelViewSet):
    """ViewSet for broadcaster profile management"""
    queryset = Broadcaster.objects.all()
    serializer_class = BroadcasterSerializer
    
    def get_permissions(self):
        if self.action in ['create']:
            return [IsAuthenticated()]
        elif self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsOwnerOrAdmin()]
        elif self.action in ['verify', 'reject']:
            return [IsAuthenticated(), IsAdmin()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        if self.request.user.is_admin:
            return Broadcaster.objects.all()
        elif self.request.user.is_broadcaster:
            return Broadcaster.objects.filter(user=self.request.user)
        return Broadcaster.objects.none()
    
    def create(self, request, *args, **kwargs):
        """Create broadcaster profile for current user"""
        if hasattr(request.user, 'broadcaster_profile'):
            return Response(
                error_response(message="Broadcaster profile already exists"),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = BroadcasterCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        broadcaster = serializer.save()
        
        return Response(
            success_response(
                message="Broadcaster profile created successfully",
                data=BroadcasterSerializer(broadcaster).data
            ),
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify a broadcaster (admin only)"""
        broadcaster = self.get_object()
        broadcaster.verification_status = Broadcaster.VerificationStatus.VERIFIED
        broadcaster.save()
        
        return Response(
            success_response(
                message="Broadcaster verified successfully",
                data=BroadcasterSerializer(broadcaster).data
            )
        )
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a broadcaster (admin only)"""
        broadcaster = self.get_object()
        broadcaster.verification_status = Broadcaster.VerificationStatus.REJECTED
        broadcaster.save()
        
        return Response(
            success_response(
                message="Broadcaster rejected",
                data=BroadcasterSerializer(broadcaster).data
            )
        )
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user's broadcaster profile"""
        if not hasattr(request.user, 'broadcaster_profile'):
            return Response(
                error_response(message="Broadcaster profile not found"),
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(request.user.broadcaster_profile)
        return Response(success_response(data=serializer.data))
