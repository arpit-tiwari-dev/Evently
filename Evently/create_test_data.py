#!/usr/bin/env python
"""
Script to create test data for the Evently Booking API
Run this after starting the Django server
"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Evently.settings')
django.setup()

from django.contrib.auth import get_user_model
from admin_app.models import Event
from rest_framework.authtoken.models import Token

User = get_user_model()

def create_test_data():
    """Create test users and events"""
    print("🚀 Creating test data for Evently Booking API...")
    
    # Create test user
    try:
        user = User.objects.get(username="testuser")
        print("✅ Test user already exists")
    except User.DoesNotExist:
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User"
        )
        print(f"✅ Created test user: {user.username} (ID: {user.id})")
    
    # Create auth token for the user
    try:
        token = Token.objects.get(user=user)
        print(f"✅ Using existing auth token: {token.key}")
    except Token.DoesNotExist:
        token = Token.objects.create(user=user)
        print(f"✅ Created auth token: {token.key}")
    
    # Create test event
    try:
        event = Event.objects.get(name="Test Concert")
        print("✅ Test event already exists")
    except Event.DoesNotExist:
        event = Event.objects.create(
            name="Test Concert",
            capacity=50,
            organizer=user,  # Use the user as organizer
            description="A test concert for API testing",
            time=timezone.now() + timedelta(days=30),  # 30 days from now
            venue="Test Venue",
            price_per_ticket=25.00,
            is_active=True
        )
        print(f"✅ Created test event: {event.name} (ID: {event.id})")
    
    # Create another test event
    try:
        event2 = Event.objects.get(name="Test Festival")
        print("✅ Test festival already exists")
    except Event.DoesNotExist:
        event2 = Event.objects.create(
            name="Test Festival",
            capacity=100,
            organizer=user,  # Use the user as organizer
            description="A test festival for API testing",
            time=timezone.now() + timedelta(days=60),  # 60 days from now
            venue="Festival Grounds",
            price_per_ticket=50.00,
            is_active=True
        )
        print(f"✅ Created test festival: {event2.name} (ID: {event2.id})")
    
    print("\n📋 Test Data Summary:")
    print(f"   User ID: {user.id}")
    print(f"   Auth Token: {token.key}")
    print(f"   Event 1 ID: {event.id} ({event.name})")
    print(f"   Event 2 ID: {event2.id} ({event2.name})")
    
    print("\n🔧 Update your test_api.py with these values:")
    print(f"   AUTH_TOKEN = '{token.key}'")
    print(f"   test_user_id = '{user.id}'")
    print(f"   test_event_id = '{event.id}'")
    
    print("\n✅ Test data creation completed!")
    print("   You can now run: python test_api.py")

if __name__ == "__main__":
    create_test_data()
