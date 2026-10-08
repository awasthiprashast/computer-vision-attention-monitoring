"""Fill the backend with synthetic attention data so the dashboard has something to show.

Usage:
    python scripts/seed_demo_data.py [--api-url URL] [--api-key KEY] [--students 4] [--minutes 30]

Uses only the standard library. Records are posted through the real API, so this also
exercises the backend's validation.
"""
import argparse
import json
import math
import os
import random
import time
import urllib.error
import urllib.request
import uuid


def post(url, payload, api_key):
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    req = urllib.request.Request(url, json.dumps(payload).encode(), headers, method="POST")
    with urllib.request.urlopen(req, timeout=5):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--api-url", default=os.environ.get("API_URL", "http://localhost:8000/attention"))
    parser.add_argument("--api-key", default=os.environ.get("API_KEY", ""))
    parser.add_argument("--students", type=int, default=4)
    parser.add_argument("--minutes", type=int, default=30)
    parser.add_argument("--interval", type=int, default=10, help="seconds between readings")
    args = parser.parse_args()

    rng = random.Random(42)
    end = time.time()
    start = end - args.minutes * 60
    sent = 0
    for n in range(args.students):
        student_id = f"demo_student_{n + 1:02d}"
        session_id = str(uuid.uuid4())
        base = rng.uniform(60, 85)          # how attentive this student is overall
        phase = rng.uniform(0, math.tau)
        t = start
        while t < end:
            drift = 12 * math.sin(t / 300 + phase)  # attention rises and falls over the lecture
            score = int(max(0, min(100, base + drift + rng.gauss(0, 6))))
            payload = {
                "session_id": session_id,
                "student_id": student_id,
                "timestamp": t,
                "attention_score": score,
                "ear": round(0.15 + score / 100 * 0.2, 4),
                "yaw": round(rng.gauss(0, 8), 2),
                "pitch": 0.0,
                "roll": 0.0,
            }
            try:
                post(args.api_url, payload, args.api_key)
            except (urllib.error.URLError, OSError) as e:
                raise SystemExit(f"Could not post to {args.api_url}: {e}") from e
            sent += 1
            t += args.interval
    print(f"Seeded {sent} records for {args.students} students.")


if __name__ == "__main__":
    main()
