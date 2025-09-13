"""
Concurrency utilities for booking management
"""
import time
import logging
from django.core.cache import cache
from django.db import transaction
from django.db.models import F, Sum
from django.core.exceptions import ValidationError
from admin_app.models import Event
from booking.models import Booking

logger = logging.getLogger(__name__)

# Cache TTL for booking locks (5 minutes)
BOOKING_LOCK_TTL = 300
# Cache TTL for availability cache (30 seconds)
AVAILABILITY_CACHE_TTL = 30


class BookingConcurrencyManager:
    """
    Manages concurrent booking requests to prevent race conditions
    """
    
    @staticmethod
    def get_booking_lock_key(event_id: str, user_id: str) -> str:
        """Generate cache key for booking lock"""
        return f"booking_lock:{event_id}:{user_id}"
    
    @staticmethod
    def get_availability_cache_key(event_id: str) -> str:
        """Generate cache key for availability cache"""
        return f"event_availability:{event_id}"
    
    @staticmethod
    def acquire_booking_lock(event_id: str, user_id: str, timeout: int = 30) -> bool:
        """
        Acquire a booking lock to prevent duplicate bookings
        
        Args:
            event_id: Event ID
            user_id: User ID
            timeout: Lock timeout in seconds
            
        Returns:
            bool: True if lock acquired, False if already locked
        """
        lock_key = BookingConcurrencyManager.get_booking_lock_key(event_id, user_id)
        
        # Try to acquire lock
        acquired = cache.add(lock_key, time.time(), BOOKING_LOCK_TTL)
        
        if acquired:
            logger.info(f"🔒 Booking lock acquired: {lock_key}")
            return True
        else:
            logger.warning(f"⚠️ Booking lock already exists: {lock_key}")
            return False
    
    @staticmethod
    def release_booking_lock(event_id: str, user_id: str) -> None:
        """Release booking lock"""
        lock_key = BookingConcurrencyManager.get_booking_lock_key(event_id, user_id)
        cache.delete(lock_key)
        logger.info(f"🔓 Booking lock released: {lock_key}")
    
    @staticmethod
    def get_cached_availability(event_id: str) -> int:
        """Get cached availability or calculate and cache it"""
        cache_key = BookingConcurrencyManager.get_availability_cache_key(event_id)
        
        # Try to get from cache first
        cached_availability = cache.get(cache_key)
        if cached_availability is not None:
            return cached_availability
        
        # Calculate and cache availability
        try:
            event = Event.objects.get(id=event_id)
            confirmed_bookings = Booking.objects.filter(
                event=event, 
                status='confirmed'
            ).aggregate(total=Sum('ticket_count'))['total'] or 0
            
            available_tickets = max(0, event.capacity - confirmed_bookings)
            
            # Cache the result
            cache.set(cache_key, available_tickets, AVAILABILITY_CACHE_TTL)
            
            logger.debug(f"📊 Calculated availability for event {event_id}: {available_tickets}")
            return available_tickets
            
        except Event.DoesNotExist:
            raise ValidationError("Event not found")
    
    @staticmethod
    def invalidate_availability_cache(event_id: str) -> None:
        """Invalidate availability cache when booking status changes"""
        cache_key = BookingConcurrencyManager.get_availability_cache_key(event_id)
        cache.delete(cache_key)
        logger.info(f"🗑️ Invalidated availability cache: {cache_key}")
    
    @staticmethod
    def reserve_tickets_atomic(event_id: str, user_id: str, ticket_count: int) -> tuple[bool, str]:
        """
        Atomically reserve tickets for a booking
        
        Args:
            event_id: Event ID
            user_id: User ID  
            ticket_count: Number of tickets to reserve
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            with transaction.atomic():
                # Get event with row lock
                event = Event.objects.select_for_update().get(id=event_id)
                
                # Calculate current availability
                confirmed_bookings = Booking.objects.filter(
                    event=event, 
                    status='confirmed'
                ).aggregate(total=Sum('ticket_count'))['total'] or 0
                
                current_availability = event.capacity - confirmed_bookings
                
                # Check if enough tickets available
                if current_availability < ticket_count:
                    return False, f"Insufficient tickets. Available: {current_availability}, Requested: {ticket_count}"
                
                # Create booking with processing status
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(id=user_id)
                
                booking = Booking.objects.create(
                    event=event,
                    user=user,
                    ticket_count=ticket_count,
                    total_amount=event.price_per_ticket * ticket_count,
                    status='processing'
                )
                
                logger.info(f"🎫 Reserved {ticket_count} tickets for booking {booking.id}")
                
                # Invalidate availability cache
                BookingConcurrencyManager.invalidate_availability_cache(event_id)
                
                return True, f"Successfully reserved {ticket_count} tickets"
                
        except Event.DoesNotExist:
            return False, "Event not found"
        except Exception as e:
            logger.error(f"❌ Error reserving tickets: {e}")
            return False, f"Error reserving tickets: {str(e)}"
    
    @staticmethod
    def check_user_booking_rate_limit(user_id: str, max_bookings_per_minute: int = 10) -> bool:
        """
        Check if user is within booking rate limits
        
        Args:
            user_id: User ID
            max_bookings_per_minute: Maximum bookings per minute
            
        Returns:
            bool: True if within limits, False if rate limited
        """
        rate_limit_key = f"booking_rate_limit:{user_id}"
        
        # Get current count
        current_count = cache.get(rate_limit_key, 0)
        
        if current_count >= max_bookings_per_minute:
            logger.warning(f"🚫 Rate limit exceeded for user {user_id}: {current_count}/{max_bookings_per_minute}")
            return False
        
        # Increment counter
        cache.set(rate_limit_key, current_count + 1, 60)  # 1 minute TTL
        
        return True


class EventAvailabilityManager:
    """
    Manages event availability calculations with caching
    """
    
    @staticmethod
    def get_real_time_availability(event_id: str) -> dict:
        """
        Get real-time availability with caching
        
        Returns:
            dict: {
                'available_tickets': int,
                'total_capacity': int,
                'confirmed_bookings': int,
                'cached': bool
            }
        """
        cache_key = f"event_availability_detail:{event_id}"
        
        # Try cache first
        cached_data = cache.get(cache_key)
        if cached_data is not None:
            cached_data['cached'] = True
            return cached_data
        
        # Calculate real-time availability
        try:
            event = Event.objects.get(id=event_id)
            confirmed_bookings = Booking.objects.filter(
                event=event, 
                status='confirmed'
            ).aggregate(total=Sum('ticket_count'))['total'] or 0
            
            available_tickets = max(0, event.capacity - confirmed_bookings)
            
            availability_data = {
                'available_tickets': available_tickets,
                'total_capacity': event.capacity,
                'confirmed_bookings': confirmed_bookings,
                'cached': False
            }
            
            # Cache for 30 seconds
            cache.set(cache_key, availability_data, AVAILABILITY_CACHE_TTL)
            
            return availability_data
            
        except Event.DoesNotExist:
            raise ValidationError("Event not found")
    
    @staticmethod
    def invalidate_event_cache(event_id: str) -> None:
        """Invalidate all event-related caches"""
        cache_keys = [
            f"event_availability:{event_id}",
            f"event_availability_detail:{event_id}",
        ]
        
        for key in cache_keys:
            cache.delete(key)
        
        logger.info(f"🗑️ Invalidated event caches for {event_id}")
