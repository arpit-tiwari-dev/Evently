#!/usr/bin/env python
"""
Evently Cache Management Script

This script provides utilities to test, monitor, and manage the Redis caching implementation.
Usage: python manage_cache.py [command] [options]

Commands:
  test        - Test cache functionality
  monitor     - Monitor cache performance
  clear       - Clear cache entries
  stats       - Show cache statistics
  warm        - Warm up cache with common requests
  health      - Check cache health
"""

import os
import sys
import django
import time
import json
import argparse
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.test import RequestFactory, Client
from django.contrib.auth import get_user_model
from django.db import connection
from django.core.management import call_command

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Evently.settings')
django.setup()

from admin_app.models import Event
from booking.models import Booking
from user.models import User
from utils.cache_utils import (
    generate_cache_key,
    invalidate_event_cache,
    invalidate_booking_cache,
    invalidate_user_cache,
    invalidate_cache_pattern
)
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CacheManager:
    """Cache management utilities"""
    
    def __init__(self):
        self.factory = RequestFactory()
        self.client = Client()
        self.User = get_user_model()
    
    def test_cache_functionality(self):
        """Test basic cache functionality"""
        print("🧪 Testing Cache Functionality")
        print("=" * 50)
        
        try:
            # Test 1: Basic cache operations
            print("1. Testing basic cache operations...")
            test_key = "test:cache:basic"
            test_data = {"message": "Hello Cache!", "timestamp": datetime.now().isoformat()}
            
            cache.set(test_key, test_data, 60)
            retrieved = cache.get(test_key)
            
            if retrieved == test_data:
                print("   ✅ Basic cache set/get works")
            else:
                print("   ❌ Basic cache set/get failed")
                return False
            
            # Test 2: Cache key generation
            print("2. Testing cache key generation...")
            key1 = generate_cache_key("test", "arg1", "arg2", param1="value1")
            key2 = generate_cache_key("test", "arg1", "arg2", param1="value1")
            key3 = generate_cache_key("test", "arg1", "arg2", param1="value2")
            
            if key1 == key2 and key1 != key3:
                print("   ✅ Cache key generation works")
            else:
                print("   ❌ Cache key generation failed")
                return False
            
            # Test 3: Cache TTL
            print("3. Testing cache TTL...")
            ttl_key = "test:cache:ttl"
            cache.set(ttl_key, "test_data", 1)  # 1 second TTL
            
            if cache.get(ttl_key) == "test_data":
                print("   ✅ Cache TTL set works")
                time.sleep(2)  # Wait for expiration
                if cache.get(ttl_key) is None:
                    print("   ✅ Cache TTL expiration works")
                else:
                    print("   ❌ Cache TTL expiration failed")
                    return False
            else:
                print("   ❌ Cache TTL set failed")
                return False
            
            # Cleanup
            cache.delete(test_key)
            cache.delete(ttl_key)
            
            print("\n✅ All cache functionality tests passed!")
            return True
            
        except Exception as e:
            print(f"❌ Cache functionality test failed: {e}")
            return False
    
    def test_api_caching(self):
        """Test API endpoint caching"""
        print("\n🌐 Testing API Endpoint Caching")
        print("=" * 50)
        
        try:
            # Create test data if needed
            self._create_test_data()
            
            # Test endpoints that should be cached
            endpoints_to_test = [
                {
                    'url': '/api/user/events/',
                    'method': 'GET',
                    'name': 'User Events List',
                    'expected_cache_prefix': 'evently:user:events:list'
                },
                {
                    'url': '/api/user/events/',
                    'method': 'GET',
                    'name': 'User Events List (with params)',
                    'params': {'upcoming_only': 'true'},
                    'expected_cache_prefix': 'evently:user:events:list'
                }
            ]
            
            for endpoint in endpoints_to_test:
                print(f"Testing {endpoint['name']}...")
                
                # First request (should miss cache)
                start_time = time.time()
                response1 = self.client.get(endpoint['url'], endpoint.get('params', {}))
                first_request_time = time.time() - start_time
                
                if response1.status_code == 200:
                    print(f"   ✅ First request successful ({first_request_time:.3f}s)")
                    
                    # Second request (should hit cache)
                    start_time = time.time()
                    response2 = self.client.get(endpoint['url'], endpoint.get('params', {}))
                    second_request_time = time.time() - start_time
                    
                    if response2.status_code == 200:
                        print(f"   ✅ Second request successful ({second_request_time:.3f}s)")
                        
                        # Check if second request was faster (indicating cache hit)
                        if second_request_time < first_request_time * 0.5:
                            print("   ✅ Cache hit detected (significant speed improvement)")
                        else:
                            print("   ⚠️  Cache hit not clearly detected")
                    else:
                        print(f"   ❌ Second request failed: {response2.status_code}")
                else:
                    print(f"   ❌ First request failed: {response1.status_code}")
            
            print("\n✅ API caching tests completed!")
            return True
            
        except Exception as e:
            print(f"❌ API caching test failed: {e}")
            return False
    
    def monitor_cache_performance(self, duration=60):
        """Monitor cache performance for specified duration"""
        print(f"📊 Monitoring Cache Performance for {duration} seconds")
        print("=" * 50)
        
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")
            
            start_time = time.time()
            end_time = start_time + duration
            
            # Get initial stats
            initial_info = redis_conn.info()
            initial_keys = len(redis_conn.keys("evently:*"))
            
            print(f"Initial cache keys: {initial_keys}")
            print(f"Initial memory usage: {initial_info.get('used_memory_human', 'N/A')}")
            print("\nMonitoring... (Press Ctrl+C to stop early)")
            
            while time.time() < end_time:
                try:
                    # Get current stats
                    current_info = redis_conn.info()
                    current_keys = len(redis_conn.keys("evently:*"))
                    
                    # Calculate hit rate
                    hits = current_info.get('keyspace_hits', 0)
                    misses = current_info.get('keyspace_misses', 0)
                    total_requests = hits + misses
                    hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0
                    
                    print(f"\rCache keys: {current_keys} | Hit rate: {hit_rate:.1f}% | Memory: {current_info.get('used_memory_human', 'N/A')}", end="")
                    
                    time.sleep(5)  # Update every 5 seconds
                    
                except KeyboardInterrupt:
                    print("\n\nMonitoring stopped by user")
                    break
            
            print(f"\n\n📈 Final Statistics:")
            final_info = redis_conn.info()
            final_keys = len(redis_conn.keys("evently:*"))
            
            print(f"Final cache keys: {final_keys}")
            print(f"Final memory usage: {final_info.get('used_memory_human', 'N/A')}")
            print(f"Total hits: {final_info.get('keyspace_hits', 0)}")
            print(f"Total misses: {final_info.get('keyspace_misses', 0)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Cache monitoring failed: {e}")
            return False
    
    def clear_cache(self, pattern=None):
        """Clear cache entries"""
        print("🧹 Clearing Cache")
        print("=" * 50)
        
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")
            
            if pattern:
                keys = redis_conn.keys(f"*{pattern}*")
                print(f"Clearing cache entries matching pattern: {pattern}")
            else:
                keys = redis_conn.keys("evently:*")
                print("Clearing all Evently cache entries")
            
            if keys:
                redis_conn.delete(*keys)
                print(f"✅ Cleared {len(keys)} cache entries")
            else:
                print("ℹ️  No cache entries found to clear")
            
            return True
            
        except Exception as e:
            print(f"❌ Cache clearing failed: {e}")
            return False
    
    def show_cache_stats(self):
        """Show cache statistics"""
        print("📊 Cache Statistics")
        print("=" * 50)
        
        try:
            from django_redis import get_redis_connection
            redis_conn = get_redis_connection("default")
            
            # Get Redis info
            info = redis_conn.info()
            
            # Count cache keys by pattern
            all_keys = redis_conn.keys("evently:*")
            key_patterns = {}
            
            for key in all_keys:
                key_str = key.decode('utf-8') if isinstance(key, bytes) else key
                pattern = key_str.split(':')[1] if ':' in key_str else 'unknown'
                key_patterns[pattern] = key_patterns.get(pattern, 0) + 1
            
            print(f"Total Evently cache keys: {len(all_keys)}")
            print(f"Redis memory usage: {info.get('used_memory_human', 'N/A')}")
            print(f"Redis uptime: {info.get('uptime_in_seconds', 0)} seconds")
            print(f"Total commands processed: {info.get('total_commands_processed', 0)}")
            
            # Calculate hit rate
            hits = info.get('keyspace_hits', 0)
            misses = info.get('keyspace_misses', 0)
            total_requests = hits + misses
            hit_rate = (hits / total_requests * 100) if total_requests > 0 else 0
            
            print(f"Cache hit rate: {hit_rate:.1f}% ({hits} hits, {misses} misses)")
            
            print(f"\nCache keys by pattern:")
            for pattern, count in sorted(key_patterns.items()):
                print(f"  {pattern}: {count} keys")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to get cache statistics: {e}")
            return False
    
    def warm_cache(self):
        """Warm up cache with common requests"""
        print("🔥 Warming Up Cache")
        print("=" * 50)
        
        try:
            # Create test data if needed
            self._create_test_data()
            
            # Common requests to warm up
            warm_up_requests = [
                {'url': '/api/user/events/', 'name': 'User Events List'},
                {'url': '/api/user/events/', 'params': {'upcoming_only': 'true'}, 'name': 'Upcoming Events'},
                {'url': '/api/user/events/', 'params': {'available_only': 'true'}, 'name': 'Available Events'},
            ]
            
            for request in warm_up_requests:
                print(f"Warming up: {request['name']}...")
                response = self.client.get(request['url'], request.get('params', {}))
                
                if response.status_code == 200:
                    print(f"   ✅ {request['name']} cached")
                else:
                    print(f"   ❌ {request['name']} failed: {response.status_code}")
            
            print("\n✅ Cache warming completed!")
            return True
            
        except Exception as e:
            print(f"❌ Cache warming failed: {e}")
            return False
    
    def check_cache_health(self):
        """Check cache health"""
        print("🏥 Checking Cache Health")
        print("=" * 50)
        
        try:
            # Test Redis connection
            print("1. Testing Redis connection...")
            test_key = "health:check"
            cache.set(test_key, "healthy", 10)
            result = cache.get(test_key)
            
            if result == "healthy":
                print("   ✅ Redis connection healthy")
                cache.delete(test_key)
            else:
                print("   ❌ Redis connection unhealthy")
                return False
            
            # Test cache invalidation
            print("2. Testing cache invalidation...")
            cache.set("evently:test:key", "test_data", 60)
            invalidate_cache_pattern("test")
            
            if cache.get("evently:test:key") is None:
                print("   ✅ Cache invalidation working")
            else:
                print("   ❌ Cache invalidation not working")
                return False
            
            # Test database connection
            print("3. Testing database connection...")
            event_count = Event.objects.count()
            print(f"   ✅ Database connection healthy ({event_count} events)")
            
            print("\n✅ All health checks passed!")
            return True
            
        except Exception as e:
            print(f"❌ Health check failed: {e}")
            return False
    
    def _create_test_data(self):
        """Create test data if needed"""
        try:
            # Check if we have any events
            if Event.objects.count() == 0:
                print("Creating test data...")
                
                # Create a test user
                user, created = self.User.objects.get_or_create(
                    username='test_user',
                    defaults={
                        'email': 'test@example.com',
                        'is_staff': True
                    }
                )
                
                # Create a test event
                event, created = Event.objects.get_or_create(
                    name='Test Event',
                    defaults={
                        'venue': 'Test Venue',
                        'time': timezone.now() + timedelta(days=1),
                        'capacity': 100,
                        'price_per_ticket': 25.00,
                        'organizer': user,
                        'is_active': True
                    }
                )
                
                print("✅ Test data created")
        except Exception as e:
            print(f"⚠️  Could not create test data: {e}")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Evently Cache Management Script')
    parser.add_argument('command', choices=[
        'test', 'monitor', 'clear', 'stats', 'warm', 'health'
    ], help='Command to execute')
    parser.add_argument('--pattern', help='Cache pattern for clear command')
    parser.add_argument('--duration', type=int, default=60, help='Monitoring duration in seconds')
    
    args = parser.parse_args()
    
    cache_manager = CacheManager()
    
    print("🚀 Evently Cache Management Script")
    print("=" * 50)
    
    success = False
    
    if args.command == 'test':
        success = cache_manager.test_cache_functionality()
        if success:
            success = cache_manager.test_api_caching()
    
    elif args.command == 'monitor':
        success = cache_manager.monitor_cache_performance(args.duration)
    
    elif args.command == 'clear':
        success = cache_manager.clear_cache(args.pattern)
    
    elif args.command == 'stats':
        success = cache_manager.show_cache_stats()
    
    elif args.command == 'warm':
        success = cache_manager.warm_cache()
    
    elif args.command == 'health':
        success = cache_manager.check_cache_health()
    
    if success:
        print(f"\n✅ Command '{args.command}' completed successfully!")
        sys.exit(0)
    else:
        print(f"\n❌ Command '{args.command}' failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
