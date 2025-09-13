"""
Caching utilities for Evently application
"""
import hashlib
import json
from functools import wraps
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from rest_framework.response import Response
import logging

logger = logging.getLogger(__name__)

# Cache TTL in seconds (15 minutes)
CACHE_TTL = 15 * 60

# Cache key prefixes
CACHE_PREFIXES = {
    'event_list': 'evently:events:list',
    'event_detail': 'evently:events:detail',
    'user_bookings': 'evently:bookings:user',
    'event_availability': 'evently:events:availability',
    'analytics': 'evently:analytics',
    'event_analytics': 'evently:analytics:event',
    'user_profile': 'evently:user:profile',
}


def generate_cache_key(prefix, *args, **kwargs):
    """
    Generate a unique cache key from prefix and arguments
    """
    # Convert all arguments to strings and create a hash
    key_parts = [str(prefix)]
    
    # Add positional arguments
    for arg in args:
        key_parts.append(str(arg))
    
    # Add keyword arguments (sorted for consistency)
    for key, value in sorted(kwargs.items()):
        key_parts.append(f"{key}:{value}")
    
    # Create a hash of the combined key parts
    key_string = ":".join(key_parts)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()
    
    return f"{prefix}:{key_hash}"


def cache_response(ttl=CACHE_TTL, key_prefix=None):
    """
    Decorator to cache API responses
    
    Args:
        ttl: Time to live in seconds (default: 15 minutes)
        key_prefix: Custom cache key prefix
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Generate cache key based on request parameters
            if key_prefix:
                prefix = key_prefix
            else:
                prefix = f"evently:{view_func.__name__}"
            
            # Include query parameters in cache key
            query_params = dict(request.GET)
            cache_key = generate_cache_key(prefix, *args, **kwargs, **query_params)
            
            # Try to get from cache
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                logger.info(f"Cache hit for key: {cache_key}")
                return Response(cached_response['data'], status=cached_response['status'])
            
            # Execute the view function
            response = view_func(request, *args, **kwargs)
            
            # Cache the response if it's successful
            if hasattr(response, 'status_code') and response.status_code == 200:
                cache_data = {
                    'data': response.data,
                    'status': response.status_code
                }
                cache.set(cache_key, cache_data, ttl)
                logger.info(f"Cached response for key: {cache_key} (TTL: {ttl}s)")
            
            return response
        
        return wrapper
    return decorator


def cache_class_method(ttl=CACHE_TTL, key_prefix=None):
    """
    Decorator for caching class-based view methods
    """
    def decorator(method):
        @wraps(method)
        def wrapper(self, request, *args, **kwargs):
            # Generate cache key
            if key_prefix:
                prefix = key_prefix
            else:
                prefix = f"evently:{self.__class__.__name__}:{method.__name__}"
            
            # Include query parameters in cache key
            query_params = dict(request.GET)
            cache_key = generate_cache_key(prefix, *args, **kwargs, **query_params)
            
            # Try to get from cache
            cached_response = cache.get(cache_key)
            if cached_response is not None:
                logger.info(f"Cache hit for key: {cache_key}")
                return Response(cached_response['data'], status=cached_response['status'])
            
            # Execute the method
            response = method(self, request, *args, **kwargs)
            
            # Cache the response if it's successful
            if hasattr(response, 'status_code') and response.status_code == 200:
                cache_data = {
                    'data': response.data,
                    'status': response.status_code
                }
                cache.set(cache_key, cache_data, ttl)
                logger.info(f"Cached response for key: {cache_key} (TTL: {ttl}s)")
            
            return response
        
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern):
    """
    Invalidate all cache keys matching a pattern
    """
    try:
        # Get all cache keys (this might not work with all cache backends)
        # For Redis, we can use pattern matching
        from django.core.cache import cache
        from django_redis import get_redis_connection
        
        redis_conn = get_redis_connection("default")
        keys = redis_conn.keys(f"*{pattern}*")
        
        if keys:
            redis_conn.delete(*keys)
            logger.info(f"Invalidated {len(keys)} cache keys matching pattern: {pattern}")
        
    except Exception as e:
        logger.error(f"Error invalidating cache pattern {pattern}: {e}")


def invalidate_event_cache(event_id=None):
    """
    Invalidate all event-related cache entries
    """
    patterns_to_invalidate = [
        'evently:events:list',
        'evently:user:events:list',  # User event list API
        'evently:admin:events:list',  # Admin event list API
        'evently:events:availability',
        'evently:user:events:detail',  # User event detail API
        'evently:admin:events:detail',  # Admin event detail API
        'evently:analytics',
        'evently:admin:analytics',  # Admin analytics API
    ]
    
    if event_id:
        patterns_to_invalidate.extend([
            f'evently:events:detail:*{event_id}*',
            f'evently:user:events:detail:*{event_id}*',  # User event detail with specific ID
            f'evently:admin:events:detail:*{event_id}*',  # Admin event detail with specific ID
            f'evently:analytics:event:*{event_id}*',
            f'evently:admin:analytics:event:*{event_id}*',  # Admin event analytics with specific ID
        ])
    
    for pattern in patterns_to_invalidate:
        invalidate_cache_pattern(pattern)


def invalidate_user_cache(user_id=None):
    """
    Invalidate all user-related cache entries
    """
    patterns_to_invalidate = [
        'evently:bookings:user',
        'evently:user:profile',
    ]
    
    if user_id:
        patterns_to_invalidate.extend([
            f'evently:bookings:user:*{user_id}*',
            f'evently:user:profile:*{user_id}*',
        ])
    
    for pattern in patterns_to_invalidate:
        invalidate_cache_pattern(pattern)


def invalidate_booking_cache():
    """
    Invalidate all booking-related cache entries
    """
    patterns_to_invalidate = [
        'evently:bookings:user',
        'evently:events:availability',
        'evently:analytics',
        'evently:admin:analytics',  # Admin analytics API
    ]
    
    for pattern in patterns_to_invalidate:
        invalidate_cache_pattern(pattern)
