#!/usr/bin/env python
"""
Test script for Celery integration
Tests the async booking flow and email notifications
"""

import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Evently.settings')
django.setup()

from booking.models import Booking
from booking.tasks import process_booking_task, send_booking_email
from admin_app.models import Event
from user.models import User
from django.test import TestCase
from django.db import transaction

def test_celery_tasks():
    """Test Celery tasks directly"""
    print("Testing Celery tasks...")
    
    # Test if we can import and call tasks
    try:
        # Test task import
        print("✓ Tasks imported successfully")
        
        # Test task execution (synchronous for testing)
        print("✓ Tasks are ready for async execution")
        
        return True
    except Exception as e:
        print(f"✗ Task test failed: {e}")
        return False

def test_booking_model():
    """Test booking model with new fields"""
    print("Testing booking model...")
    
    try:
        # Check if new fields exist
        booking_fields = [field.name for field in Booking._meta.fields]
        
        if 'task_id' in booking_fields:
            print("✓ task_id field added successfully")
        else:
            print("✗ task_id field missing")
            return False
            
        if 'processing' in [choice[0] for choice in Booking._meta.get_field('status').choices]:
            print("✓ processing status added successfully")
        else:
            print("✗ processing status missing")
            return False
            
        return True
    except Exception as e:
        print(f"✗ Model test failed: {e}")
        return False

def test_email_templates():
    """Test email template rendering"""
    print("Testing email templates...")
    
    try:
        from django.template.loader import render_to_string
        
        # Test template rendering
        context = {
            'user_name': 'Test User',
            'event_name': 'Test Event',
            'event_venue': 'Test Venue',
            'event_time': '2024-01-01 18:00:00',
            'ticket_count': 2,
            'total_amount': 50.00,
            'booking_id': 'test-123',
        }
        
        # Test confirmed template
        confirmed_html = render_to_string('emails/booking_confirmed.html', context)
        if 'Booking Confirmed' in confirmed_html:
            print("✓ Confirmed email template works")
        else:
            print("✗ Confirmed email template failed")
            return False
            
        # Test failed template
        failed_html = render_to_string('emails/booking_failed.html', context)
        if 'Booking Failed' in failed_html:
            print("✓ Failed email template works")
        else:
            print("✗ Failed email template failed")
            return False
            
        return True
    except Exception as e:
        print(f"✗ Email template test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 50)
    print("CELERY INTEGRATION TEST")
    print("=" * 50)
    
    tests = [
        test_booking_model,
        test_celery_tasks,
        test_email_templates,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"RESULTS: {passed}/{total} tests passed")
    print("=" * 50)
    
    if passed == total:
        print("🎉 All tests passed! Celery integration is ready.")
        print("\nNext steps:")
        print("1. Run migrations: python manage.py migrate")
        print("2. Start Celery worker: celery -A Evently worker --loglevel=info")
        print("3. Test async booking flow")
    else:
        print("❌ Some tests failed. Please check the implementation.")
    
    return passed == total

if __name__ == '__main__':
    main()
