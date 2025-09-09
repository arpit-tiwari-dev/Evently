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
from admin_app.models import Event
from django.contrib.auth import get_user_model

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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_booking(request):
    """
    Book Ticket API
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
    
    try:
        with transaction.atomic():
            # Use select_for_update to prevent race conditions
            event = Event.objects.select_for_update().get(id=event_id)
            user = User.objects.get(id=user_id)
            
            # Double-check capacity with pessimistic locking
            if event.available_tickets < number_of_tickets:
                logger.warning(f"Booking failed: insufficient tickets for event {event_id}")
                return Response(
                    {
                        'error': 'Insufficient tickets',
                        'available_tickets': event.available_tickets,
                        'requested_tickets': number_of_tickets
                    },
                    status=status.HTTP_409_CONFLICT
                )
            
            # Calculate total amount
            total_amount = event.price_per_ticket * number_of_tickets
            
            # Create booking
            booking = Booking.objects.create(
                event=event,
                user=user,
                ticket_count=number_of_tickets,
                total_amount=total_amount,
                status='confirmed'
            )
            
            # Update event capacity atomically
            event.available_tickets = F('available_tickets') - number_of_tickets
            event.save(update_fields=['available_tickets'])
            
            logger.info(f"Booking created successfully: {booking.id} for event {event_id}")
            
            # Return booking details
            booking_serializer = BookingSerializer(booking)
            return Response(booking_serializer.data, status=status.HTTP_201_CREATED)
            
    except ObjectDoesNotExist as e:
        logger.error(f"Object not found during booking: {str(e)}")
        return Response(
            {'error': 'Event or user not found'},
            status=status.HTTP_404_NOT_FOUND
        )
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
            
            # Update booking status
            booking.status = 'cancelled'
            booking.save(update_fields=['status'])
            
            # Update event capacity atomically
            event = Event.objects.select_for_update().get(id=booking.event.id)
            event.available_tickets = F('available_tickets') + booking.ticket_count
            event.save(update_fields=['available_tickets'])
            
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
    Check Availability API
    Endpoint: GET /events/{event_id}/availability
    """
    try:
        event = Event.objects.get(id=event_id)
        
        serializer = AvailabilitySerializer({
            'event_id': str(event.id),
            'available_tickets': event.available_tickets
        })
        
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Event.DoesNotExist:
        logger.warning(f"Event not found: {event_id}")
        return Response(
            {'error': 'Event not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Unexpected error checking availability: {str(e)}")
        return Response(
            {'error': 'Internal server error'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
