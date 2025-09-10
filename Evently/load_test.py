#!/usr/bin/env python
"""
High-volume async load tester for Evently (or any HTTP endpoint).

Sends thousands of requests with configurable concurrency and reports:
- Overall results: total, success, error rate
- Throughput: requests per second
- Latency stats: min/avg/max and p50/p90/p95/p99
- Status code distribution

Usage examples:
  # Stress-test public availability endpoint with 10k GET requests, 500 concurrency
  python load_test.py --base http://localhost:8000 \
      --path /api/events/1/availability/ --method GET --total 10000 --concurrency 500

  # Test authenticated POST to create bookings using a token (payload from file)
  python load_test.py --base http://localhost:8000 \
      --path /api/bookings/ --method POST --total 5000 --concurrency 300 \
      --token %EVENTLY_USER_TOKEN% --data '{"user_id":"1","event_id":"1","number_of_tickets":1}'

Notes:
- For write endpoints, run against a disposable database to avoid polluting data.
- For max performance on Windows, run with Python 3.11+.
"""

import argparse
import asyncio
import json
import statistics
import time
from collections import Counter
from typing import Optional

import aiohttp


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Async load tester for Evently")
    p.add_argument("--base", required=False, default="http://localhost:8000", help="Base URL, e.g., http://localhost:8000")
    p.add_argument("--path", required=True, help="Request path, e.g., /api/events/1/availability/")
    p.add_argument("--method", default="GET", choices=["GET", "POST", "PUT", "DELETE"], help="HTTP method")
    p.add_argument("--total", type=int, default=10000, help="Total number of requests to send")
    p.add_argument("--concurrency", type=int, default=500, help="Max concurrent requests")
    p.add_argument("--token", default=None, help="Auth token (DRF Token)")
    p.add_argument("--data", default=None, help="JSON string payload for POST/PUT")
    p.add_argument("--timeout", type=float, default=10.0, help="Per-request timeout seconds")
    p.add_argument("--verify-tls", action="store_true", help="Verify TLS certificates for https")
    return p.parse_args()


async def worker(session: aiohttp.ClientSession, sem: asyncio.Semaphore, method: str, url: str,
                 payload: Optional[dict], timeout: float, stats) -> None:
    async with sem:
        start = time.perf_counter()
        status = -1
        ok = False
        try:
            if method in ("POST", "PUT"):
                async with session.request(method, url, json=payload, timeout=timeout) as resp:
                    status = resp.status
                    # read and discard to reuse the connection
                    await resp.read()
            else:
                async with session.request(method, url, timeout=timeout) as resp:
                    status = resp.status
                    await resp.read()
            ok = 200 <= status < 300
        except Exception:
            status = 0  # network/timeout
            ok = False
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            stats.record(status, ok, elapsed_ms)


class Stats:
    def __init__(self):
        self.count = 0
        self.ok = 0
        self.errors = 0
        self.latencies = []  # ms
        self.status_counts = Counter()

    def record(self, status: int, ok: bool, latency_ms: float):
        self.count += 1
        self.ok += 1 if ok else 0
        self.errors += 0 if ok else 1
        self.latencies.append(latency_ms)
        self.status_counts[status] += 1

    def merge(self, other: "Stats"):
        self.count += other.count
        self.ok += other.ok
        self.errors += other.errors
        self.latencies.extend(other.latencies)
        self.status_counts.update(other.status_counts)

    def summary(self, duration_s: float) -> str:
        if not self.latencies:
            return "No results collected"
        lat_sorted = sorted(self.latencies)
        def pct(p):
            idx = int(len(lat_sorted) * p)
            idx = min(max(idx, 0), len(lat_sorted) - 1)
            return lat_sorted[idx]
        rps = self.count / duration_s if duration_s > 0 else float("nan")
        out = []
        out.append(f"Total: {self.count}")
        out.append(f"Success: {self.ok}  Errors: {self.errors}  Error%: {self.errors / self.count * 100:.2f}%")
        out.append(f"Throughput: {rps:.1f} req/s over {duration_s:.2f}s")
        out.append(
            "Latency ms -> min: %.1f  avg: %.1f  max: %.1f  p50: %.1f  p90: %.1f  p95: %.1f  p99: %.1f"
            % (lat_sorted[0], statistics.mean(lat_sorted), lat_sorted[-1], pct(0.50), pct(0.90), pct(0.95), pct(0.99))
        )
        out.append("Status codes:")
        for k in sorted(self.status_counts.keys()):
            out.append(f"  {k}: {self.status_counts[k]}")
        return "\n".join(out)


async def run_load(args: argparse.Namespace):
    url = args.base.rstrip("/") + args.path
    headers = {"Content-Type": "application/json"}
    if args.token:
        headers["Authorization"] = f"Token {args.token}"

    connector = aiohttp.TCPConnector(ssl=args.verify_tls)
    timeout = aiohttp.ClientTimeout(total=args.timeout)

    payload = None
    if args.data:
        payload = json.loads(args.data)

    stats = Stats()
    sem = asyncio.Semaphore(args.concurrency)
    started = time.perf_counter()

    async with aiohttp.ClientSession(headers=headers, connector=connector, timeout=timeout) as session:
        tasks = [
            asyncio.create_task(worker(session, sem, args.method.upper(), url, payload, args.timeout, stats))
            for _ in range(args.total)
        ]
        # Progress: gather in chunks to keep the loop responsive
        chunk = 1000
        for i in range(0, len(tasks), chunk):
            await asyncio.gather(*tasks[i:i+chunk])

    duration = time.perf_counter() - started
    print("=== Load Test Report ===")
    print(f"Target: {args.method.upper()} {url}")
    print(stats.summary(duration))


def main():
    args = parse_args()
    try:
        asyncio.run(run_load(args))
    except KeyboardInterrupt:
        print("Interrupted by user")


if __name__ == "__main__":
    main()
