from rest_framework import serializers
from .ads_models import Advertisement, AdImpression, AdClick


class AdvertisementSerializer(serializers.ModelSerializer):
    """Serializer for Advertisement model"""
    click_through_rate = serializers.FloatField(read_only=True)
    
    class Meta:
        model = Advertisement
        fields = ['id', 'title', 'description', 'ad_type', 'placement', 'image',
                  'video_file', 'audio_file', 'click_url', 'duration', 'priority',
                  'impression_count', 'click_count', 'click_through_rate', 'created_at']
        read_only_fields = ['id', 'impression_count', 'click_count', 'created_at']


class AdImpressionSerializer(serializers.Serializer):
    """Serializer for tracking ad impressions"""
    ad_id = serializers.IntegerField(required=True)
    session_id = serializers.CharField(required=True, max_length=100)


class AdClickSerializer(serializers.Serializer):
    """Serializer for tracking ad clicks"""
    ad_id = serializers.IntegerField(required=True)
    session_id = serializers.CharField(required=True, max_length=100)
