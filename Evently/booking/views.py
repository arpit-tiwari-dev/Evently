from django.shortcuts import render
from django.db import transaction
from django.db.models import F
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.core.exceptions import ObjectDoesNotExist
from .models import Booking
from .serializers import (
    BookingSerializer, 
    CreateBookingSerializer, 
    BookingHistorySerializer,
    AvailabilitySerializer
)
from .tasks import process_booking_task
from admin_app.models import Event
from django.contrib.auth import get_user_model
from utils.cache_utils import cache_response

User = get_user_model()
import logging

# Set up logging
logger = logging.getLogger(__name__)


class BookingPagination(PageNumberPagination):
    """
    Custom pagination for booking history
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


@api_view(['GET'])
@permission_classes([])  # No authentication required
def health_check(request):
    """
    Health check endpoint to verify Celery is working
    """
    try:
        from celery import current_app
        import subprocess
        import os
        
        # Check if Celery app is configured
        app = current_app
        broker_url = app.conf.broker_url
        
        # Check running processes
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            celery_processes = [line for line in result.stdout.split('\n') if 'celery' in line.lower()]
        except:
            celery_processes = []
        
        # Try to inspect active workers
        try:
            inspect = app.control.inspect()
            active_workers = inspect.active()
            
            if active_workers:
                worker_count = len(active_workers)
                return Response({
                    'status': 'healthy',
                    'celery': 'running',
                    'workers': worker_count,
                    'broker': broker_url,
                    'processes': celery_processes,
                    'message': f'Celery is running with {worker_count} worker(s)'
                })
            else:
                return Response({
                    'status': 'unhealthy',
                    'celery': 'no_workers',
                    'broker': broker_url,
                    'processes': celery_processes,
                    'message': 'Celery is configured but no workers are running'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
                
        except Exception as e:
            return Response({
                'status': 'unhealthy',
                'celery': 'connection_error',
                'broker': broker_url,
                'processes': celery_processes,
                'error': str(e),
                'message': 'Cannot connect to Celery workers'
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            
    except Exception as e:
        return Response({
            'status': 'unhealthy',
            'celery': 'not_configured',
            'error': str(e),
            'message': 'Celery is not properly configured'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_booking(request):
    """
    Book Ticket API - Asynchronous Processing with Concurrency Control
    Endpoint: POST /bookings
    """
    serializer = CreateBookingSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'Invalid data', 'details': serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    validated_data = serializer.validated_data
    user_id = validated_data['user_id']
    event_id = validated_data['event_id']
    number_of_tickets = validated_data['number_of_tickets']
    
    # Import concurrency utilities
    from .concurrency_utils import BookingConcurrencyManager
    
    try:
        # Rate limiting check
        if not BookingConcurrencyManager.check_user_booking_rate_limit(user_id):
            return Response(
                {'error': 'Too many booking requests. Please wait a moment and try again.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        # Acquire booking lock to prevent duplicate requests
        if not BookingConcurrencyManager.acquire_booking_lock(event_id, user_id):
            return Response(
                {'error': 'You already have a booking request in progress for this event. Please wait for it to complete.'},
                status=status.HTTP_409_CONFLICT
            )
        
        try:
            # Reserve tickets atomically
            success, message = BookingConcurrencyManager.reserve_tickets_atomic(
                event_id, user_id, number_of_tickets
            )
            
            if not success:
                return Response(
                    {'error': message},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Get the created booking
            booking = Booking.objects.filter(
                event_id=event_id, 
                user_id=user_id, 
                status='processing'
            ).order_by('-booking_date').first()
            
            if not booking:
                return Response(
                    {'error': 'Failed to create booking'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Queue the booking processing task
            logger.info(f"🚀 QUEUING TASK: About to queue booking {booking.id} for async processing")
            task = process_booking_task.delay(booking.id)
            
            # Store the task ID in the booking
            booking.task_id = task.id
            booking.save(update_fields=['task_id'])
            
            logger.info(f"✅ TASK QUEUED SUCCESSFULLY: Booking {booking.id} queued with task ID {task.id}")
            logger.info(f"📊 Task details - Task ID: {task.id}, Booking ID: {booking.id}, Event: {event_id}, Tickets: {number_of_tickets}")
            
            # Return immediate response with processing status
            booking_serializer = BookingSerializer(booking)
            return Response(booking_serializer.data, status=status.HTTP_201_CREATED)
            
        finally:
            # Always release the booking lock
            BookingConcurrencyManager.release_booking_lock(event_id, user_id)
            
    except Exception as e:
        logger.error(f"Unexpected error during booking: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def cancel_booking(request, booking_id):
    """
    Cancel Booking API
    Endpoint: DELETE /bookings/{booking_id}
    """
    try:
        with transaction.atomic():
            # Use select_for_update to prevent race conditions
            booking = Booking.objects.select_for_update().get(id=booking_id)
            
            # Check if booking is already cancelled
            if booking.status == 'cancelled':
                return Response(
                    {'error': 'Booking is already cancelled'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update booking status; availability is computed from bookings
            booking.status = 'cancelled'
            booking.save(update_fields=['status'])
            
            logger.info(f"Booking cancelled successfully: {booking_id}")
            
            return Response(
                {
                    'booking_id': str(booking.id),
                    'status': 'cancelled'
                },
                status=status.HTTP_200_OK
            )
            
    except Booking.DoesNotExist:
        logger.warning(f"Booking not found: {booking_id}")
        return Response(
            {'error': 'Booking not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Unexpected error during cancellation: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@cache_response(key_prefix='evently:bookings:user')
def get_user_bookings(request, user_id):
    """
    Booking History API
    Endpoint: GET /users/{user_id}/bookings
    """
    try:
        # Verify user exists
        User.objects.get(id=user_id)
        
        # Get bookings for the user
        bookings = Booking.objects.filter(user_id=user_id).order_by('-booking_date')
        
        # Apply pagination
        paginator = BookingPagination()
        paginated_bookings = paginator.paginate_queryset(bookings, request)
        
        # Serialize the data
        serializer = BookingHistorySerializer(paginated_bookings, many=True)
        
        return paginator.get_paginated_response(serializer.data)
        
    except User.DoesNotExist:
        logger.warning(f"User not found: {user_id}")
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Unexpected error fetching user bookings: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([])  # No authentication required
def check_availability(request, event_id):
    """
    Check Availability API with Real-time Data
    Endpoint: GET /events/{event_id}/availability
    """
    try:
        from .concurrency_utils import EventAvailabilityManager
        
        # Get real-time availability with caching
        availability_data = EventAvailabilityManager.get_real_time_availability(event_id)
        
        serializer = AvailabilitySerializer({
            'event_id': str(event_id),
            'available_tickets': availability_data['available_tickets'],
            'total_capacity': availability_data['total_capacity'],
            'confirmed_bookings': availability_data['confirmed_bookings'],
            'cached': availability_data['cached']
        })
        
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        if 'Event not found' in str(e):
            logger.warning(f"Event not found: {event_id}")
            return Response(
                {'error': 'Event not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        else:
            logger.error(f"Unexpected error checking availability: {str(e)}")
            return Response(
                {'error': 'Internal server error'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )