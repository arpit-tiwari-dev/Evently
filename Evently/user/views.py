from rest_framework import status, generics, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
import logging

from admin_app.models import Event
from .serializers import (
    EventListSerializer, EventDetailSerializer,
    RegisterSerializer
)
from django.contrib.auth import authenticate, get_user_model
from rest_framework.authtoken.models import Token

logger = logging.getLogger(__name__)
User = get_user_model()


class UserEventPagination(PageNumberPagination):
    """Custom pagination for user event lists"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class EventListView(generics.ListAPIView):
    """
    Browse Events API
    GET /api/user/events
    """
    serializer_class = EventListSerializer
    permission_classes = []  # No authentication required
    pagination_class = UserEventPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'venue', 'description']
    ordering_fields = ['time', 'created_at', 'price_per_ticket']
    ordering = ['time']  # Default to chronological order
    
    def get_queryset(self):
        queryset = Event.objects.filter(is_active=True)
        
        # Filter by date range
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)
        
        if date_from:
            queryset = queryset.filter(time__gte=date_from)
        if date_to:
            queryset = queryset.filter(time__lte=date_to)
        
        # Filter by venue
        venue = self.request.query_params.get('venue', None)
        if venue:
            queryset = queryset.filter(venue__icontains=venue)
        
        # Filter by price range
        min_price = self.request.query_params.get('min_price', None)
        max_price = self.request.query_params.get('max_price', None)
        
        if min_price:
            queryset = queryset.filter(price_per_ticket__gte=min_price)
        if max_price:
            queryset = queryset.filter(price_per_ticket__lte=max_price)
        
        # Filter by availability
        available_only = self.request.query_params.get('available_only', None)
        if available_only and available_only.lower() == 'true':
            # Only show events with available tickets
            queryset = queryset.filter(capacity__gt=0)  # This will be filtered by available_tickets property
        
        # Filter upcoming events by default
        upcoming_only = self.request.query_params.get('upcoming_only', 'true')
        if upcoming_only.lower() == 'true':
            queryset = queryset.filter(time__gt=timezone.now())
        
        return queryset


@api_view(['GET'])
@permission_classes([])  # No authentication required
def get_event_details(request, event_id):
    """
    View Event Details API
    GET /api/user/events/{event_id}
    """
    try:
        event = Event.objects.get(id=event_id, is_active=True)
        serializer = EventDetailSerializer(event)
        
        logger.info(f"Event details viewed by user: {event_id}")
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except Event.DoesNotExist:
        return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error getting event details {event_id}: {e}")
        return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([])
def register(request):
    """
    Public registration endpoint to create a normal user (non-staff).
    POST /api/user/auth/register
    """
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'token': token.key
        }, status=status.HTTP_201_CREATED)
    return Response({'error': 'Invalid data', 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([])
def login(request):
    """Username/password login; returns auth token.
    POST /api/user/auth/login
    """
    username = request.data.get('username')
    password = request.data.get('password')
    if not username or not password:
        return Response({'error': 'username and password are required'}, status=status.HTTP_400_BAD_REQUEST)
    user = authenticate(username=username, password=password)
    if not user:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """Logout by deleting the current token.
    POST /api/user/auth/logout
    """
    try:
        Token.objects.filter(user=request.user).delete()
    except Exception:
        pass
    return Response({'status': 'logged_out'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """Return current authenticated user's profile.
    GET /api/user/auth/me
    """
    user = request.user
    return Response({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'phone_number': getattr(user, 'phone_number', None),
        'address': getattr(user, 'address', None),
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser
    }, status=status.HTTP_200_OK)