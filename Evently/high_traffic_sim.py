#!/usr/bin/env python
"""
High-traffic simulation for Evently

Creates many events and users, then sends parallel booking requests to
simulate heavy traffic and measure performance.

Run:
  python high_traffic_sim.py

Config (env vars):
  EVENTLY_BASE_URL         Base URL (default http://localhost:8000)
  EVENTLY_ADMIN_TOKEN      Admin token (preferred)
  EVENTLY_ADMIN_USERNAME   Admin username (fallback)
  EVENTLY_ADMIN_PASSWORD   Admin password (fallback)
  HT_EVENTS                Number of events to create (default 10)
  HT_USERS                 Number of users to create (default 200)
  HT_TICKETS_PER_USER      Tickets per booking (default 1)
  HT_CONCURRENCY           Max concurrent requests (default 200)
  HT_PRICE_CENTS           Price per ticket in cents (default 500)
"""

import os
import sys
import time
import uuid
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


BASE_URL = os.environ.get("EVENTLY_BASE_URL", "http://localhost:8000")
API = f"{BASE_URL}/api"
USER_API = f"{API}/user"
ADMIN_API = f"{API}/admin"

ADMIN_TOKEN = os.environ.get("EVENTLY_ADMIN_TOKEN", "")
ADMIN_LOGIN_USERNAME = os.environ.get("EVENTLY_ADMIN_USERNAME", "admin")
ADMIN_LOGIN_PASSWORD = os.environ.get("EVENTLY_ADMIN_PASSWORD", "admin123")

NUM_EVENTS = int(os.environ.get("HT_EVENTS", "10"))
NUM_USERS = int(os.environ.get("HT_USERS", "200"))
TICKETS_PER_USER = int(os.environ.get("HT_TICKETS_PER_USER", "1"))
MAX_WORKERS = int(os.environ.get("HT_CONCURRENCY", str(min(20, NUM_USERS))))
PRICE_CENTS = int(os.environ.get("HT_PRICE_CENTS", "500"))


def headers(token: str | None = None) -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    if token:
        h["Authorization"] = f"Token {token}"
    return h


def admin_token() -> str:
    if ADMIN_TOKEN:
        return ADMIN_TOKEN
    r = requests.post(
        f"{USER_API}/auth/login/",
        json={"username": ADMIN_LOGIN_USERNAME, "password": ADMIN_LOGIN_PASSWORD}
    )
    if r.status_code == 200:
        return r.json().get("token", "")
    raise RuntimeError(f"Admin login failed: {r.status_code} {r.text}")


def admin_create_event(admin_tok: str, idx: int) -> str:
    start_time = (datetime.utcnow() + timedelta(days=1 + idx)).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "name": f"HT Event {idx} {uuid.uuid4().hex[:6]}",
        "venue": "HT Venue",
        "time": start_time,
        "capacity": random.randint(50, 200),
        "description": "High-traffic test event",
        "price_per_ticket": f"{PRICE_CENTS / 100:.2f}"
    }
    r = requests.post(f"{ADMIN_API}/events/", json=payload, headers=headers(admin_tok))
    if r.status_code != 201:
        raise RuntimeError(f"Create event failed: {r.status_code} {r.text}")
    return r.json()["event_id"]


def register_and_login_user() -> str:
    username = f"ht_{uuid.uuid4().hex[:10]}"
    password = "HtP@ssw0rd!"
    email = f"{username}@example.com"
    requests.post(f"{USER_API}/auth/register/", json={"username": username, "email": email, "password": password})
    r = requests.post(f"{USER_API}/auth/login/", json={"username": username, "password": password})
    if r.status_code != 200:
        raise RuntimeError(f"Login failed: {r.status_code} {r.text}")
    return r.json()["token"]


def user_profile(token: str) -> Dict[str, Any]:
    r = requests.get(f"{USER_API}/auth/me/", headers=headers(token))
    if r.status_code != 200:
        raise RuntimeError(f"me failed: {r.status_code} {r.text}")
    return r.json()


def attempt_booking(token: str, user_id: str, event_id: str, tickets: int) -> Tuple[bool, int]:
    r = requests.post(
        f"{API}/bookings/",
        json={"user_id": user_id, "event_id": event_id, "number_of_tickets": tickets},
        headers=headers(token)
    )
    return (r.status_code == 201, r.status_code)


def list_user_booking_ids(token: str, user_id: str, page_size: int = 100) -> List[str]:
    ids: List[str] = []
    url = f"{API}/users/{user_id}/bookings/?page_size={page_size}"
    while url:
        r = requests.get(url, headers=headers(token))
        if r.status_code != 200:
            break
        data = r.json()
        for item in data.get("results", []):
            bid = item.get("booking_id") or item.get("id") or item.get("booking")
            if bid:
                ids.append(str(bid))
        url = data.get("next")
    return ids


def cancel_booking_by_id(token: str, booking_id: str) -> bool:
    r = requests.delete(f"{API}/bookings/{booking_id}/", headers=headers(token))
    return r.status_code == 200


def admin_delete_event(admin_tok: str, event_id: str) -> bool:
    r = requests.delete(f"{ADMIN_API}/events/{event_id}/delete/", headers=headers(admin_tok))
    return r.status_code in (200, 204)


def admin_bulk_delete_users(admin_tok: str, prefix: str = "ht_") -> int:
    r = requests.post(f"{ADMIN_API}/users/bulk_delete/", json={"prefix": prefix}, headers=headers(admin_tok))
    if r.status_code == 200:
        try:
            return int(r.json().get("deleted_users", 0))
        except Exception:
            return 0
    return 0


def main() -> None:
    print(f"BASE: {BASE_URL}")
    admin_tok = admin_token()
    print("✅ Admin token ready")

    print(f"🗓️ Creating {NUM_EVENTS} events...")
    event_ids: List[str] = []
    with ThreadPoolExecutor(max_workers=min(NUM_EVENTS, MAX_WORKERS)) as pool:
        futures = [pool.submit(admin_create_event, admin_tok, i) for i in range(NUM_EVENTS)]
        for f in as_completed(futures):
            event_ids.append(f.result())
    print(f"✅ Events ready: {len(event_ids)}")

    print(f"👥 Creating {NUM_USERS} users and tokens...")
    tokens: List[str] = []
    usernames: List[str] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        def _reg():
            # return (token, username)
            username = f"ht_{uuid.uuid4().hex[:10]}"
            password = "HtP@ssw0rd!"
            email = f"{username}@example.com"
            requests.post(f"{USER_API}/auth/register/", json={"username": username, "email": email, "password": password})
            r = requests.post(f"{USER_API}/auth/login/", json={"username": username, "password": password})
            if r.status_code != 200:
                raise RuntimeError(f"Login failed: {r.status_code} {r.text}")
            return r.json()["token"], username
        futures = [pool.submit(_reg) for _ in range(NUM_USERS)]
        for f in as_completed(futures):
            tok, uname = f.result()
            tokens.append(tok)
            usernames.append(uname)
    print("✅ Users ready")

    profiles: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [pool.submit(user_profile, t) for t in tokens]
        for f in as_completed(futures):
            profiles.append(f.result())

    jobs = []
    for i in range(len(tokens)):
        user_id = str(profiles[i]["id"])
        event_id = random.choice(event_ids)
        jobs.append((tokens[i], user_id, event_id, TICKETS_PER_USER))

    print("🚀 Firing parallel bookings...")
    started = time.perf_counter()
    successes = 0
    status_counts: Dict[int, int] = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = [
            pool.submit(attempt_booking, tok, uid, eid, tix)
            for (tok, uid, eid, tix) in jobs
        ]
        for f in as_completed(futures):
            ok, status = f.result()
            successes += 1 if ok else 0
            status_counts[status] = status_counts.get(status, 0) + 1
    duration = time.perf_counter() - started

    total = len(jobs)
    errors = total - successes
    rps = total / duration if duration > 0 else float("nan")

    print("\n=== High Traffic Report ===")
    print(f"Requests: {total}  Success: {successes}  Errors: {errors}  Error%: {(errors/total*100 if total else 0):.2f}%")
    print(f"Throughput: {rps:.1f} req/s over {duration:.2f}s")
    print("Status codes:")
    for code in sorted(status_counts.keys()):
        print(f"  {code}: {status_counts[code]}")

    # Cleanup phase: cancel user bookings and delete created events
    print("\n🧹 Cleaning up test data (bookings and events)...")
    # 1) Cancel bookings for each created user
    cancelled = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = []
        for i in range(len(tokens)):
            token = tokens[i]
            uid = str(profiles[i]["id"]) if i < len(profiles) else None
            if not uid:
                continue
            # Fetch booking ids for this user
            bids = list_user_booking_ids(token, uid)
            for bid in bids:
                futures.append(pool.submit(cancel_booking_by_id, token, bid))
        for f in as_completed(futures):
            cancelled += 1 if f.result() else 0
    print(f"   🗑️ Cancelled bookings: {cancelled}")

    # 2) Delete events with admin token
    deleted_events = 0
    with ThreadPoolExecutor(max_workers=min(NUM_EVENTS, MAX_WORKERS)) as pool:
        futures = [pool.submit(admin_delete_event, admin_tok, eid) for eid in event_ids]
        for f in as_completed(futures):
            deleted_events += 1 if f.result() else 0
    print(f"   🗑️ Deleted events: {deleted_events}/{len(event_ids)}")

    # 3) Delete created users via admin bulk-delete by prefix
    deleted_users = admin_bulk_delete_users(admin_tok, prefix="ht_")
    print(f"   🗑️ Deleted users: {deleted_users}")

    if errors > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Simulation failed: {e}")
        sys.exit(1)


