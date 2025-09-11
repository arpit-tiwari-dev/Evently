#!/usr/bin/env python
"""
Concurrent booking stress test for Evently.

This creates an admin-owned event with a known capacity, registers multiple
users, then fires many simultaneous booking requests against the same event
and validates that total confirmed tickets never exceed capacity.

Run:
  python concurrency_test.py

Env vars:
  EVENTLY_BASE_URL           (default http://localhost:8000)
  EVENTLY_ADMIN_TOKEN        (preferred)
  EVENTLY_ADMIN_USERNAME     (optional, fallback login)
  EVENTLY_ADMIN_PASSWORD     (optional, fallback login)
  CT_USERS                   number of users to create (default 20)
  CT_TICKETS_PER_USER        requested tickets per booking (default 1)
  CT_CAPACITY                event capacity (default 10)
  CT_CONCURRENCY             max concurrent requests (default 20)
"""

import os
import sys
import time
import uuid
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

BASE_URL = os.environ.get("EVENTLY_BASE_URL", "http://localhost:8000")
API = f"{BASE_URL}/api"
USER_API = f"{API}/user"
ADMIN_API = f"{API}/admin"

ADMIN_TOKEN = os.environ.get("EVENTLY_ADMIN_TOKEN", "")
ADMIN_LOGIN_USERNAME = "admin"
ADMIN_LOGIN_PASSWORD = "admin123"

NUM_USERS = int(os.environ.get("CT_USERS", "20"))
TICKETS_PER_USER = int(os.environ.get("CT_TICKETS_PER_USER", "1"))
EVENT_CAPACITY = int(os.environ.get("CT_CAPACITY", "10"))
MAX_WORKERS = int(os.environ.get("CT_CONCURRENCY", str(NUM_USERS)))

TEST_EVENT_NAME = f"CT Event {uuid.uuid4().hex[:6]}"


def hdr(token: str | None = None) -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Token {token}"
    return h


def get_admin_token() -> str:
    if ADMIN_TOKEN:
        return ADMIN_TOKEN
    if ADMIN_LOGIN_USERNAME and ADMIN_LOGIN_PASSWORD:
        r = requests.post(
            f"{USER_API}/auth/login/",
            json={"username": ADMIN_LOGIN_USERNAME, "password": ADMIN_LOGIN_PASSWORD}
        )
        if r.status_code == 200:
            return r.json().get("token", "")
        raise RuntimeError(f"Admin login failed: {r.status_code} {r.text}")
    raise RuntimeError("Set EVENTLY_ADMIN_TOKEN or admin username/password env vars.")


def admin_create_event(admin_token: str) -> str:
    from datetime import datetime, timedelta
    start_time = (datetime.utcnow() + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "name": TEST_EVENT_NAME,
        "venue": "CT Venue",
        "time": start_time,
        "capacity": EVENT_CAPACITY,
        "description": "Concurrency test event",
        "price_per_ticket": "5.00"
    }
    r = requests.post(f"{ADMIN_API}/events/", json=payload, headers=hdr(admin_token))
    if r.status_code != 201:
        raise RuntimeError(f"Create event failed: {r.status_code} {r.text}")
    return r.json()["event_id"]


def register_user() -> str:
    username = f"ct_{uuid.uuid4().hex[:10]}"
    password = "CtP@ssw0rd!"
    email = f"{username}@example.com"
    # Register
    requests.post(f"{USER_API}/auth/register/", json={"username": username, "email": email, "password": password})
    # Login
    r = requests.post(f"{USER_API}/auth/login/", json={"username": username, "password": password})
    if r.status_code != 200:
        raise RuntimeError(f"Login failed: {r.status_code} {r.text}")
    return r.json()["token"]


def get_user_profile(token: str) -> Dict[str, Any]:
    r = requests.get(f"{USER_API}/auth/me/", headers=hdr(token))
    if r.status_code != 200:
        raise RuntimeError(f"me failed: {r.status_code} {r.text}")
    return r.json()


def availability(event_id: str) -> int:
    r = requests.get(f"{API}/events/{event_id}/availability/")
    if r.status_code != 200:
        raise RuntimeError(f"availability failed: {r.status_code} {r.text}")
    return int(r.json()["available_tickets"])


def attempt_booking(token: str, user_id: str, event_id: str, tickets: int) -> Dict[str, Any]:
    r = requests.post(
        f"{API}/bookings/",
        json={"user_id": user_id, "event_id": event_id, "number_of_tickets": tickets},
        headers=hdr(token)
    )
    ok = r.status_code == 201
    data = {}
    try:
        data = r.json()
    except Exception:
        data = {"raw": r.text}
    return {"ok": ok, "status": r.status_code, "data": data}


def main() -> None:
    print(f"BASE: {BASE_URL}")
    admin_token = get_admin_token()
    print("✅ Admin token ready")

    event_id = admin_create_event(admin_token)
    print(f"✅ Event created: {event_id} (capacity={EVENT_CAPACITY})")

    start_available = availability(event_id)
    print(f"🔎 Initial availability: {start_available}")

    print(f"👥 Creating {NUM_USERS} users and tokens...")
    tokens: List[str] = []
    with ThreadPoolExecutor(max_workers=min(NUM_USERS, MAX_WORKERS)) as pool:
        futures = [pool.submit(register_user) for _ in range(NUM_USERS)]
        for f in as_completed(futures):
            tokens.append(f.result())
    print("✅ Users ready")

    # Resolve user ids
    profiles = []
    with ThreadPoolExecutor(max_workers=min(NUM_USERS, MAX_WORKERS)) as pool:
        futures = [pool.submit(get_user_profile, t) for t in tokens]
        for f in as_completed(futures):
            profiles.append(f.result())

    # Fire concurrent bookings
    print("🚀 Firing concurrent bookings...")
    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [
            pool.submit(
                attempt_booking,
                tokens[i],
                str(profiles[i]["id"]),
                event_id,
                TICKETS_PER_USER,
            )
            for i in range(NUM_USERS)
        ]
        for f in as_completed(futures):
            results.append(f.result())

    successes = [r for r in results if r["ok"]]
    failures = [r for r in results if not r["ok"]]
    print(f"✅ Successes: {len(successes)} | ❌ Failures: {len(failures)}")

    end_available = availability(event_id)
    print(f"🔎 Availability after: {end_available}")

    successful_tickets = len(successes) * TICKETS_PER_USER
    oversold = successful_tickets > EVENT_CAPACITY

    print(f"📊 Requested tickets: {NUM_USERS * TICKETS_PER_USER}")
    print(f"📊 Confirmed tickets: {successful_tickets}")
    print(f"📊 Capacity: {EVENT_CAPACITY}")

    if oversold:
        print("❌ OVERSOLD! Confirmed tickets exceeded capacity.")
        sys.exit(1)
    else:
        print("🎉 No oversell detected. Concurrency controls working.")
        sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
