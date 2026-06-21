import time
from fastapi import HTTPException

# Simple in-memory rate limiter: IP -> list of timestamps
IP_REQUESTS = {}

LIMIT_REQUESTS = 30
TIME_WINDOW = 60  # seconds


def check_rate_limit(ip: str):
    now = time.time()
    if ip not in IP_REQUESTS:
        IP_REQUESTS[ip] = []

    # Filter out timestamps older than the window
    IP_REQUESTS[ip] = [t for t in IP_REQUESTS[ip] if now - t < TIME_WINDOW]

    if len(IP_REQUESTS[ip]) >= LIMIT_REQUESTS:
        raise HTTPException(
            status_code=429, detail="Too many requests. Please wait a moment."
        )

    IP_REQUESTS[ip].append(now)
