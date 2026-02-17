from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q
from accounts.permissions import IsAdmin
from api.response import success_response, error_response
from .ads_models import Advertisement, AdImpression, AdClick
from .ads_serializers import (
    AdvertisementSerializer,
    AdImpressionSerializer,
    AdClickSerializer
)


class AdvertisementViewSet(viewsets.ModelViewSet):
    """ViewSet for Advertisement management"""
    queryset = Advertisement.objects.all()
    serializer_class = AdvertisementSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'track_impression', 'track_click']:
            return [AllowAny()]
        return [IsAuthenticated(), IsAdmin()]
    
    def get_queryset(self):
        """Get active ads filtered by placement"""
        queryset = Advertisement.objects.filter(is_active=True)
        
        # Filter by placement
        placement = self.request.query_params.get('placement')
        if placement:
            queryset = queryset.filter(placement=placement)
        
        # Filter by date range
        now = timezone.now()
        queryset = queryset.filter(
            Q(start_date__isnull=True) | Q(start_date__lte=now)
        ).filter(
            Q(end_date__isnull=True) | Q(end_date__gte=now)
        )
        
        return queryset.order_by('-priority', '-created_at')
    
    @action(detail=False, methods=['get'])
    def by_placement(self, request):
        """Get ads for a specific placement"""
        placement = request.query_params.get('placement')
        
        if not placement:
            return Response(
                error_response(message="placement parameter is required"),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        ads = self.get_queryset().filter(placement=placement)[:5]
        serializer = self.get_serializer(ads, many=True)
        
        return Response(success_response(data=serializer.data))
    
    @action(detail=True, methods=['post'])
    def track_impression(self, request, pk=None):
        """Track ad impression"""
        ad = self.get_object()
        serializer = AdImpressionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create impression record
        AdImpression.objects.create(
            user=request.user if request.user.is_authenticated else None,
            advertisement=ad,
            session_id=serializer.validated_data['session_id']
        )
        
        # Increment ad impression count
        ad.increment_impression()
        
        return Response(success_response(message="Impression tracked"))
    
    @action(detail=True, methods=['post'])
    def track_click(self, request, pk=None):
        """Track ad click"""
        ad = self.get_object()
        serializer = AdClickSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Create click record
        AdClick.objects.create(
            user=request.user if request.user.is_authenticated else None,
            advertisement=ad,
            session_id=serializer.validated_data['session_id']
        )
        
        # Increment ad click count
        ad.increment_click()
        
        return Response(success_response(
            message="Click tracked",
            data={'redirect_url': ad.click_url}
        ))
    
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get ad analytics (admin only)"""
        ads = Advertisement.objects.all()
        
        analytics_data = []
        for ad in ads:
            analytics_data.append({
                'id': ad.id,
                'title': ad.title,
                'ad_type': ad.ad_type,
                'placement': ad.placement,
                'impressions': ad.impression_count,
                'clicks': ad.click_count,
                'ctr': ad.click_through_rate,
                'is_active': ad.is_active
            })
        
        return Response(success_response(data=analytics_data))
