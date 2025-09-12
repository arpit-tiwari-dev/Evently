"""
Django signals for cache invalidation
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from admin_app.models import Event
from booking.models import Booking
from .cache_utils import (
    invalidate_event_cache,
    invalidate_user_cache,
    invalidate_booking_cache
)
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(post_save, sender=Event)
def invalidate_cache_on_event_save(sender, instance, created, **kwargs):
    """
    Invalidate cache when an event is created or updated
    """
    try:
        if created:
            logger.info(f"Event created: {instance.id} - Invalidating event caches")
            invalidate_event_cache()
        else:
            logger.info(f"Event updated: {instance.id} - Invalidating event caches")
            invalidate_event_cache(instance.id)
    except Exception as e:
        logger.error(f"Error invalidating cache on event save: {e}")


@receiver(post_delete, sender=Event)
def invalidate_cache_on_event_delete(sender, instance, **kwargs):
    """
    Invalidate cache when an event is deleted
    """
    try:
        logger.info(f"Event deleted: {instance.id} - Invalidating event caches")
        invalidate_event_cache(instance.id)
    except Exception as e:
        logger.error(f"Error invalidating cache on event delete: {e}")


@receiver(post_save, sender=Booking)
def invalidate_cache_on_booking_save(sender, instance, created, **kwargs):
    """
    Invalidate cache when a booking is created or updated
    """
    try:
        if created:
            logger.info(f"Booking created: {instance.id} - Invalidating booking and event caches")
            invalidate_booking_cache()
            invalidate_event_cache(instance.event.id)
        else:
            logger.info(f"Booking updated: {instance.id} - Invalidating booking and event caches")
            invalidate_booking_cache()
            invalidate_event_cache(instance.event.id)
    except Exception as e:
        logger.error(f"Error invalidating cache on booking save: {e}")


@receiver(post_delete, sender=Booking)
def invalidate_cache_on_booking_delete(sender, instance, **kwargs):
    """
    Invalidate cache when a booking is deleted
    """
    try:
        logger.info(f"Booking deleted: {instance.id} - Invalidating booking and event caches")
        invalidate_booking_cache()
        invalidate_event_cache(instance.event.id)
    except Exception as e:
        logger.error(f"Error invalidating cache on booking delete: {e}")


@receiver(post_save, sender=User)
def invalidate_cache_on_user_save(sender, instance, created, **kwargs):
    """
    Invalidate cache when a user is created or updated
    """
    try:
        if created:
            logger.info(f"User created: {instance.id} - Invalidating user caches")
            invalidate_user_cache()
        else:
            logger.info(f"User updated: {instance.id} - Invalidating user caches")
            invalidate_user_cache(instance.id)
    except Exception as e:
        logger.error(f"Error invalidating cache on user save: {e}")


@receiver(post_delete, sender=User)
def invalidate_cache_on_user_delete(sender, instance, **kwargs):
    """
    Invalidate cache when a user is deleted
    """
    try:
        logger.info(f"User deleted: {instance.id} - Invalidating user caches")
        invalidate_user_cache(instance.id)
    except Exception as e:
        logger.error(f"Error invalidating cache on user delete: {e}")
