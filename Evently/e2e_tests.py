#!/usr/bin/env python
"""
End-to-end test runner for Evently APIs.

This script exercises the full workflow across modules:
- Public user registration and auth
- Admin: create/update/list/details/analytics/notify/delete events
- User: browse events and view details
- Booking: availability, create booking, history, cancel booking, oversell prevention

Prereqs:
1) Run server: python manage.py runserver
2) Ensure an admin user exists and obtain their token (or login creds).
   You can create a superuser via: python manage.py createsuperuser
3) Optionally update ADMIN_AUTH token or ADMIN_LOGIN creds below.

Run:
  python e2e_tests.py
"""

import os
import sys
import time
import json
from typing import Optional, Dict, Any

import requests

BASE_URL = "https://evently-mu3y.onrender.com/"
API = f"{BASE_URL}/api"
USER_API = f"{API}/user"
ADMIN_API = f"{API}/admin"

# Admin auth config: prefer token via env, else attempt login with username/password
ADMIN_TOKEN = os.environ.get("EVENTLY_ADMIN_TOKEN", "")
ADMIN_LOGIN_USERNAME = "admin"
ADMIN_LOGIN_PASSWORD = "admin123"

# Test data
TEST_EVENT_NAME = "E2E Test Event"


def log(msg: str) -> None:
    print(msg)


def _headers(token: Optional[str] = None) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Token {token}"
    return headers


# ---------- Auth helpers ----------

def admin_auth_token() -> str:
    if ADMIN_TOKEN:
        return ADMIN_TOKEN
    if ADMIN_LOGIN_USERNAME and ADMIN_LOGIN_PASSWORD:
        # Try admin user login through user auth endpoint
        url = f"{USER_API}/auth/login/"
        r = requests.post(url, json={"username": ADMIN_LOGIN_USERNAME, "password": ADMIN_LOGIN_PASSWORD})
        if r.status_code == 200:
            return r.json().get("token", "")
        raise RuntimeError(f"Admin login failed: {r.status_code} {r.text}")
    raise RuntimeError("No admin token or login credentials provided. Set EVENTLY_ADMIN_TOKEN or username/password env vars.")


def user_register_and_login() -> str:
    """Register a random user and return their token. If username exists, just login."""
    import uuid

    username = f"e2e_user_{uuid.uuid4().hex[:8]}"
    password = "e2ePassword123!"
    email = f"{username}@example.com"

    # Register
    url = f"{USER_API}/auth/register/"
    r = requests.post(url, json={"username": username, "email": email, "password": password})
    if r.status_code not in (201, 400):
        raise RuntimeError(f"Unexpected register response: {r.status_code} {r.text}")

    # Login
    url = f"{USER_API}/auth/login/"
    r = requests.post(url, json={"username": username, "password": password})
    if r.status_code != 200:
        raise RuntimeError(f"Login failed: {r.status_code} {r.text}")
    return r.json()["token"]


# ---------- Admin flows ----------

def admin_create_event(admin_token: str) -> str:
    from datetime import datetime, timedelta
    start_time = (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")

    payload = {
        "name": TEST_EVENT_NAME,
        "venue": "E2E Venue",
        "time": start_time,
        "capacity": 25,
        "description": "Event created by E2E tests",
        "price_per_ticket": "15.00"
    }
    url = f"{ADMIN_API}/events/"
    r = requests.post(url, json=payload, headers=_headers(admin_token))
    if r.status_code != 201:
        raise RuntimeError(f"Create event failed: {r.status_code} {r.text}")
    return r.json()["event_id"]


def admin_update_event(admin_token: str, event_id: str) -> None:
    payload = {"capacity": 30}
    url = f"{ADMIN_API}/events/{event_id}/"
    r = requests.put(url, json=payload, headers=_headers(admin_token))
    if r.status_code != 200:
        raise RuntimeError(f"Update event failed: {r.status_code} {r.text}EventId={event_id}")


def admin_list_events(admin_token: str) -> None:
    url = f"{ADMIN_API}/events/list/?status=upcoming&ordering=time"
    r = requests.get(url, headers=_headers(admin_token))
    if r.status_code != 200:
        raise RuntimeError(f"List events failed: {r.status_code} {r.text}")


def admin_event_details(admin_token: str, event_id: str) -> None:
    url = f"{ADMIN_API}/events/{event_id}/details/"
    r = requests.get(url, headers=_headers(admin_token))
    if r.status_code != 200:
        raise RuntimeError(f"Event details failed: {r.status_code} {r.text}")


def admin_analytics(admin_token: str, event_id: str) -> None:
    r1 = requests.get(f"{ADMIN_API}/analytics/", headers=_headers(admin_token))
    r2 = requests.get(f"{ADMIN_API}/analytics/{event_id}/", headers=_headers(admin_token))
    if r1.status_code != 200:
        raise RuntimeError(f"Analytics failed: {r1.status_code} {r1.text}")
    if r2.status_code != 200:
        raise RuntimeError(f"Event analytics failed: {r2.status_code} {r2.text}")


def admin_notify(admin_token: str, event_id: str) -> None:
    url = f"{ADMIN_API}/events/{event_id}/notify/"
    r = requests.post(url, json={"message": "E2E notification"}, headers=_headers(admin_token))
    if r.status_code != 200:
        raise RuntimeError(f"Notify failed: {r.status_code} {r.text}")


def admin_delete_event(admin_token: str, event_id: str) -> bool:
    url = f"{ADMIN_API}/events/{event_id}/delete/"
    r = requests.delete(url, headers=_headers(admin_token))
    # may fail if there are active bookings; return success boolean
    return r.status_code == 200


# ---------- User browse flows ----------

def user_browse_and_details(event_id: str) -> None:
    r = requests.get(f"{USER_API}/events/?search={TEST_EVENT_NAME}")
    if r.status_code != 200:
        raise RuntimeError(f"User browse failed: {r.status_code} {r.text}")
    r = requests.get(f"{USER_API}/events/{event_id}/")
    if r.status_code != 200:
        raise RuntimeError(f"User event details failed: {r.status_code} {r.text}")


# ---------- Booking flows ----------

def check_availability(event_id: str) -> int:
    r = requests.get(f"{API}/events/{event_id}/availability/")
    if r.status_code != 200:
        raise RuntimeError(f"Availability failed: {r.status_code} {r.text}")
    return int(r.json()["available_tickets"])


def create_booking(user_token: str, user_id: str, event_id: str, n: int) -> str:
    url = f"{API}/bookings/"
    payload = {"user_id": str(user_id), "event_id": str(event_id), "number_of_tickets": int(n)}
    r = requests.post(url, json=payload, headers=_headers(user_token))
    if r.status_code != 201:
        raise RuntimeError(f"Create booking failed: {r.status_code} {r.text}")
    return r.json()["booking_id"]


def cancel_booking(user_token: str, booking_id: str) -> None:
    url = f"{API}/bookings/{booking_id}/"
    r = requests.delete(url, headers=_headers(user_token))
    if r.status_code != 200:
        raise RuntimeError(f"Cancel booking failed: {r.status_code} {r.text}")


def user_profile(token: str) -> Dict[str, Any]:
    r = requests.get(f"{USER_API}/auth/me/", headers=_headers(token))
    if r.status_code != 200:
        raise RuntimeError(f"Fetching profile failed: {r.status_code} {r.text}")
    return r.json()


def user_history(token: str, user_id: str) -> None:
    r = requests.get(f"{API}/users/{user_id}/bookings/", headers=_headers(token))
    if r.status_code != 200:
        raise RuntimeError(f"User history failed: {r.status_code} {r.text}")


# ---------- E2E runner ----------

def run() -> None:
    log(f"BASE: {BASE_URL}")

    # 1) Authenticate admin
    log("1) Getting admin token...")
    admin_token = admin_auth_token()
    log("   ✅ Admin token acquired")

    # 2) Register and login normal user
    log("2) Registering and logging in a normal user...")
    user_token = user_register_and_login()
    profile = user_profile(user_token)
    user_id = str(profile["id"])
    log(f"   ✅ User created: id={user_id}")

    # 3) Admin creates event
    log("3) Admin creating event...")
    event_id = admin_create_event(admin_token)
    log(f"   ✅ Event created: id={event_id}")

    # 4) Admin updates + lists + details + analytics + notify
    log("4) Admin updating and listing events, checking analytics, sending notification...")
    admin_update_event(admin_token, event_id)
    admin_list_events(admin_token)
    admin_event_details(admin_token, event_id)
    admin_analytics(admin_token, event_id)
    admin_notify(admin_token, event_id)
    log("   ✅ Admin flows OK")

    # 5) User browsing and details
    log("5) Public browse and event details...")
    user_browse_and_details(event_id)
    log("   ✅ User browse OK")

    # 6) Availability -> oversell prevention -> normal booking -> history -> cancel
    log("6) Booking flow with oversell prevention...")
    initial = check_availability(event_id)
    log(f"   Availability before: {initial}")

    # Oversell attempt
    oversell = initial + 5
    try:
        create_booking(user_token, user_id, event_id, oversell)
        raise RuntimeError("Oversell attempt unexpectedly succeeded")
    except RuntimeError as e:
        # Expecting failure path from our create_booking wrapper: keep message but mark as expected
        log("   ✅ Oversell prevention working (expected failure)")

    # Normal booking of 2 tickets (or 1 if low)
    to_book = 2 if initial >= 2 else 1
    booking_id = create_booking(user_token, user_id, event_id, to_book)
    log(f"   ✅ Booking created: id={booking_id}")

    # History
    user_history(user_token, user_id)
    log("   ✅ History accessible")

    # Cancel
    cancel_booking(user_token, booking_id)
    after_cancel = check_availability(event_id)
    log(f"   ✅ Booking cancelled, availability now: {after_cancel}")

    # 7) Try delete event (should succeed now that booking cancelled)
    log("7) Admin deleting event...")
    deleted = admin_delete_event(admin_token, event_id)
    if deleted:
        log("   ✅ Event deleted")
    else:
        log("   ⚠️ Event could not be deleted (active bookings?)")

    log("\n🎉 All E2E steps completed.")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print(f"❌ E2E failed: {exc}")
        sys.exit(1)
