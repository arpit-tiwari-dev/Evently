from rest_framework import status, generics, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db import models
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import datetime, timedelta
import logging
from utils.cache_utils import cache_response, cache_class_method

from .models import Event
from .serializers import (
    EventCreateSerializer, EventUpdateSerializer, EventListSerializer,
    EventDetailSerializer, EventDeleteSerializer, AnalyticsSerializer,
    EventAnalyticsSerializer, NotificationSerializer
)
from booking.models import Booking
from django.contrib.auth import get_user_model
from user.serializers import StaffUserCreateSerializer

logger = logging.getLogger(__name__)
User = get_user_model()


class AdminEventPagination(PageNumberPagination):
    """Custom pagination for admin event lists"""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class IsAdminOrOrganizer(IsAuthenticated):
    """Custom permission to allow admin or event organizer"""
    
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        
        # Admin users have full access
        if request.user.is_staff:
            return True
        
        # For specific event operations, check if user is the organizer
        if hasattr(view, 'get_object'):
            try:
                event = view.get_object()
                return event.organizer == request.user
            except:
                pass
        
        return False


@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_event(request):
    """
    Create Event API
    POST /admin/events
    """
    try:
        serializer = EventCreateSerializer(data=request.data)
        if serializer.is_valid():
            # Set the organizer to the current user
            event = serializer.save(organizer=request.user)
            
            response_data = {
                'event_id': str(event.id),
                'name': event.name,
                'venue': event.venue,
                'time': event.time,
                'capacity': event.capacity
            }
            
            logger.info(f"Event created: {event.id} by {request.user.username}")
            return Response(response_data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except ValidationError as e:
        logger.error(f"Validation error creating event: {e}")
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error creating event: {e}")
        return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['PUT'])
@permission_classes([IsAdminOrOrganizer])
def update_event(request, event_id):
    """
    Update Event API
    PUT /admin/events/{event_id}
    """
    try:
        event = Event.objects.get(id=event_id)
        
        # Check if user has permission to update this event
        if not request.user.is_staff and event.organizer != request.user:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = EventUpdateSerializer(event, data=request.data, partial=True)
        if serializer.is_valid():
            updated_event = serializer.save()
            
            response_data = {
                'event_id': str(updated_event.id),
                'name': updated_event.name,
                'venue': updated_event.venue,
                'time': updated_event.time,
                'capacity': updated_event.capacity
            }
            
            logger.info(f"Event updated: {event.id} by {request.user.username}")
            return Response(response_data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Event.DoesNotExist:
        return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)
    except ValidationError as e:
        logger.error(f"Validation error updating event {event_id}: {e}")
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error updating event {event_id}: {e}")
        return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([IsAdminOrOrganizer])
def delete_event(request, event_id):
    """
    Delete Event API
    DELETE /admin/events/{event_id}
    """
    try:
        event = Event.objects.get(id=event_id)
        
        # Check if user has permission to delete this event
        if not request.user.is_staff and event.organizer != request.user:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        # Check if event has active bookings
        active_bookings = Booking.objects.filter(event=event, status='confirmed').count()
        
        if active_bookings > 0:
            return Response({
                'error': f'Cannot delete event with {active_bookings} active bookings. Cancel bookings first.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        event_id_str = str(event.id)
        event.delete()
        
        response_data = {
            'event_id': event_id_str,
            'status': 'deleted'
        }
        
        logger.info(f"Event deleted: {event_id} by {request.user.username}")
        return Response(response_data, status=status.HTTP_200_OK)
    
    except Event.DoesNotExist:
        return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error deleting event {event_id}: {e}")
        return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EventListView(generics.ListAPIView):
    """
    List All Events API
    GET /admin/events
    """
    serializer_class = EventListSerializer
    permission_classes = [IsAdminUser]
    pagination_class = AdminEventPagination
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'venue']
    ordering_fields = ['time', 'created_at', 'capacity']
    ordering = ['-created_at']
    
    @cache_class_method(key_prefix='evently:admin:events:list')
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = Event.objects.all()
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter == 'upcoming':
            queryset = queryset.filter(time__gt=timezone.now())
        elif status_filter == 'past':
            queryset = queryset.filter(time__lte=timezone.now())
        
        # Filter by venue
        venue_filter = self.request.query_params.get('venue', None)
        if venue_filter:
            queryset = queryset.filter(venue__icontains=venue_filter)
        
        # Filter by active status
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset


@api_view(['GET'])
@permission_classes([IsAdminUser])
@cache_response(key_prefix='evently:admin:events:detail')
def get_event_details(request, event_id):
    """
    View Event Details API
    GET /admin/events/{event_id}
    """
    try:
        event = Event.objects.get(id=event_id)
        serializer = EventDetailSerializer(event)
        
        logger.info(f"Event details viewed: {event_id} by {request.user.username}")
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except Event.DoesNotExist:
        return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error getting event details {event_id}: {e}")
        return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
@cache_response(key_prefix='evently:admin:analytics')
def get_analytics(request):
    """
    View Booking Analytics API
    GET /admin/analytics
    """
    try:
        # Total bookings
        total_bookings = Booking.objects.filter(status='confirmed').count()
        
        # Most popular events
        popular_events = Event.objects.annotate(
            booking_count=Count('booking', filter=Q(booking__status='confirmed'))
        ).order_by('-booking_count')[:5]
        
        most_popular_events = [
            {
                'event_id': str(event.id),
                'name': event.name,
                'bookings': event.booking_count
            }
            for event in popular_events
        ]
        
        # Capacity utilization
        utilization_events = Event.objects.annotate(
            booking_count=Count('booking', filter=Q(booking__status='confirmed'))
        ).filter(booking_count__gt=0)
        
        capacity_utilization = [
            {
                'event_id': str(event.id),
                'name': event.name,
                'utilization_percentage': event.utilization_percentage
            }
            for event in utilization_events
        ]
        
        analytics_data = {
            'total_bookings': total_bookings,
            'most_popular_events': most_popular_events,
            'capacity_utilization': capacity_utilization
        }
        
        logger.info(f"Analytics viewed by {request.user.username}")
        return Response(analytics_data, status=status.HTTP_200_OK)
    
    except Exception as e:
        logger.error(f"Error getting analytics: {e}")
        return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
@cache_response(key_prefix='evently:admin:analytics:event')
def get_event_analytics(request, event_id):
    """
    Advanced Analytics for Specific Event API
    GET /admin/analytics/{event_id}
    """
    try:
        event = Event.objects.get(id=event_id)
        
        # Total bookings for this event
        total_bookings = Booking.objects.filter(event=event, status='confirmed').count()
        
        # Cancellation rate
        total_attempted_bookings = Booking.objects.filter(event=event).count()
        cancellation_rate = 0
        if total_attempted_bookings > 0:
            cancelled_bookings = Booking.objects.filter(event=event, status='cancelled').count()
            cancellation_rate = round((cancelled_bookings / total_attempted_bookings) * 100, 2)
        
        # Daily bookings (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        daily_bookings_data = []
        
        for i in range(30):
            date = thirty_days_ago + timedelta(days=i)
            next_date = date + timedelta(days=1)
            
            daily_count = Booking.objects.filter(
                event=event,
                status='confirmed',
                booking_date__gte=date,
                booking_date__lt=next_date
            ).count()
            
            daily_bookings_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'bookings': daily_count
            })
        
        analytics_data = {
            'event_id': str(event.id),
            'total_bookings': total_bookings,
            'cancellation_rate': cancellation_rate,
            'daily_bookings': daily_bookings_data
        }
        
        logger.info(f"Event analytics viewed: {event_id} by {request.user.username}")
        return Response(analytics_data, status=status.HTTP_200_OK)
    
    except Event.DoesNotExist:
        return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error getting event analytics {event_id}: {e}")
        return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def notify_users(request, event_id):
    """
    Notify Users API
    POST /admin/events/{event_id}/notify
    """
    try:
        event = Event.objects.get(id=event_id)
        serializer = NotificationSerializer(data=request.data)
        
        if serializer.is_valid():
            message = serializer.validated_data['message']
            
            # Get all users who have bookings for this event
            bookings = Booking.objects.filter(event=event, status='confirmed')
            users = set(booking.user for booking in bookings)
            
            # Here you would typically integrate with your notification system
            # For now, we'll just log the notification
            logger.info(f"Notification sent for event {event_id}: '{message}' to {len(users)} users")
            
            response_data = {
                'status': 'success',
                'message': f'Notification sent to {len(users)} users',
                'event_id': str(event.id),
                'users_notified': len(users)
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Event.DoesNotExist:
        return Response({'error': 'Event not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error sending notification for event {event_id}: {e}")
        return Response({'error': 'Internal server error'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def create_staff_user(request):
    """Superuser-only endpoint to create staff users for event management.
    POST /api/admin/users/staff/
    """
    # Only allow true superusers to create staff accounts
    if not request.user.is_superuser:
        return Response({'error': 'Only superusers can create staff users'}, status=status.HTTP_403_FORBIDDEN)

    serializer = StaffUserCreateSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_staff': user.is_staff
        }, status=status.HTTP_201_CREATED)
    return Response({'error': 'Invalid data', 'details': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def bulk_delete_test_users(request):
    """Admin-only endpoint to bulk delete test users by username prefix.
    POST /api/admin/users/bulk_delete/
    Body: { "prefix": "ht_" }
    Safeguards: excludes staff and superusers.
    """
    prefix = request.data.get('prefix', 'ht_')
    try:
        qs = User.objects.filter(username__startswith=prefix, is_staff=False, is_superuser=False)
        count = qs.count()
        qs.delete()
        logger.info(f"Bulk deleted {count} users with prefix '{prefix}' by {request.user.username}")
        return Response({"deleted_users": count, "prefix": prefix}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error bulk deleting users with prefix '{prefix}': {e}")
        return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)