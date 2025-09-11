#!/usr/bin/env python
"""
Simple test script to demonstrate the Evently Booking API functionality.
Run this after setting up the Django project and creating some test data.
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:8000/api"
AUTH_TOKEN = "94873eab2992152df8dfe9c2d686606561463fbc"  # From create_test_data.py

# Test data IDs - from create_test_data.py
TEST_USER_ID = "1"
TEST_EVENT_ID = "1"

headers = {
    'Content-Type': 'application/json',
    'Authorization': f'Token {AUTH_TOKEN}'
}

def test_check_availability(event_id):
    """Test the availability check endpoint"""
    print(f"\n=== Testing Availability Check for Event {event_id} ===")
    try:
        response = requests.get(f"{BASE_URL}/events/{event_id}/availability/")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Available tickets: {data['available_tickets']}")
            return data['available_tickets']
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return 0
    except Exception as e:
        print(f"❌ Exception: {e}")
        return 0

def test_create_booking(user_id, event_id, number_of_tickets):
    """Test the booking creation endpoint"""
    print(f"\n=== Testing Booking Creation ===")
    booking_data = {
        "user_id": user_id,
        "event_id": event_id,
        "number_of_tickets": number_of_tickets
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/bookings/",
            json=booking_data,
            headers=headers
        )
        
        if response.status_code == 201:
            data = response.json()
            print(f"✅ Booking created successfully!")
            print(f"   Booking ID: {data['booking_id']}")
            print(f"   Status: {data['status']}")
            print(f"   Total Amount: ${data['total_amount']}")
            return data['booking_id']
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ Exception: {e}")
        return None

def test_get_user_bookings(user_id):
    """Test the user booking history endpoint"""
    print(f"\n=== Testing User Booking History ===")
    try:
        response = requests.get(
            f"{BASE_URL}/users/{user_id}/bookings/",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['count']} bookings")
            for booking in data['results'][:3]:  # Show first 3 bookings
                print(f"   - Booking {booking['booking_id']}: {booking['number_of_tickets']} tickets, Status: {booking['status']}")
            return data['results']
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        print(f"❌ Exception: {e}")
        return []

def test_cancel_booking(booking_id):
    """Test the booking cancellation endpoint"""
    print(f"\n=== Testing Booking Cancellation ===")
    try:
        response = requests.delete(
            f"{BASE_URL}/bookings/{booking_id}/",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Booking cancelled successfully!")
            print(f"   Booking ID: {data['booking_id']}")
            print(f"   Status: {data['status']}")
            return True
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_concurrent_booking_scenario():
    """Test concurrent booking scenario"""
    print(f"\n=== Testing Concurrent Booking Scenario ===")
    
    # Test data - replace with actual IDs from your database
    test_user_id = TEST_USER_ID
    test_event_id = TEST_EVENT_ID
    
    # Check initial availability
    initial_availability = test_check_availability(test_event_id)
    
    if initial_availability == 0:
        print("❌ No tickets available for testing")
        return
    
    # Try to book more tickets than available
    print(f"\n--- Testing Overselling Prevention ---")
    oversell_tickets = initial_availability + 5
    booking_id = test_create_booking(test_user_id, test_event_id, oversell_tickets)
    
    if booking_id is None:
        print("✅ Overselling prevention working correctly")
    else:
        print("❌ Overselling prevention failed!")
    
    # Book available tickets
    print(f"\n--- Testing Normal Booking ---")
    normal_tickets = min(2, initial_availability)
    booking_id = test_create_booking(test_user_id, test_event_id, normal_tickets)
    
    if booking_id:
        # Check availability after booking
        new_availability = test_check_availability(test_event_id)
        print(f"✅ Availability updated: {initial_availability} -> {new_availability}")
        
        # Get user bookings
        bookings = test_get_user_bookings(test_user_id)
        
        # Cancel the booking
        if test_cancel_booking(booking_id):
            # Check availability after cancellation
            final_availability = test_check_availability(test_event_id)
            print(f"✅ Availability restored: {new_availability} -> {final_availability}")

def main():
    """Main test function"""
    print("🚀 Evently Booking API Test Suite")
    print("=" * 50)
    
    print("\n⚠️  Before running this test:")
    print("1. Make sure Django server is running (python manage.py runserver)")
    print("2. Create test data: python create_test_data.py")
    print("3. Update AUTH_TOKEN in this script with the token from step 2")
    print("4. Update TEST_USER_ID and TEST_EVENT_ID with actual IDs from step 2")
    
    # Uncomment the line below to run the actual tests
    test_concurrent_booking_scenario()
    
    print("\n📝 Quick Setup:")
    print("1. Run: python create_test_data.py")
    print("2. Copy the token and IDs from the output")
    print("3. Update this script with those values")
    print("4. Uncomment the test_concurrent_booking_scenario() call")
    print("5. Run: python test_api.py")

if __name__ == "__main__":
    main()
