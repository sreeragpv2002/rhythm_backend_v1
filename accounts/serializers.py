from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import UserProfile, Broadcaster

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model"""
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role', 
                  'is_email_verified', 'created_at']
        read_only_fields = ['id', 'is_email_verified', 'created_at']


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile model"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = UserProfile
        fields = ['id', 'user', 'language', 'profile_image', 'bio',
                  'favorite_artists', 'listening_preferences', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    
    class Meta:
        model = User
        fields = ['email', 'password', 'password2', 'first_name', 'last_name', 'role']
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                "password": "Password fields didn't match."
            })
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with additional user info"""
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['email'] = user.email
        token['role'] = user.role
        token['is_email_verified'] = user.is_email_verified
        
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add extra responses
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'role': self.user.role,
            'is_email_verified': self.user.is_email_verified,
        }
        
        return data


class BroadcasterSerializer(serializers.ModelSerializer):
    """Serializer for Broadcaster model"""
    user = UserSerializer(read_only=True)
    
    class Meta:
        model = Broadcaster
        fields = ['id', 'user', 'verification_status', 'bio', 'profile_image',
                  'total_uploads', 'total_plays', 'verified_at', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'verification_status', 'total_uploads',
                            'total_plays', 'verified_at', 'created_at', 'updated_at']


class BroadcasterCreateSerializer(serializers.Serializer):
    """Serializer for creating broadcaster profile"""
    bio = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    profile_image = serializers.ImageField(required=False, allow_null=True)
    
    def create(self, validated_data):
        user = self.context['request'].user
        
        # Update user role to broadcaster
        user.role = User.Role.BROADCASTER
        user.save()
        
        # Create broadcaster profile
        broadcaster = Broadcaster.objects.create(
            user=user,
            **validated_data
        )
        return broadcaster
