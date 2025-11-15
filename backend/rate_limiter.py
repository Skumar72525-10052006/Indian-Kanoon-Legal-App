"""
Simple in-memory sliding window rate limiter for FastAPI endpoints.
"""
from collections import defaultdict, deque
from typing import Deque, DefaultDict
import asyncio
import time

from fastapi import Request, HTTPException


class SlidingWindowRateLimiter:
    """
    Lightweight rate limiter using an in-memory sliding window.
    Intended for single-process deployments.
    """

    def __init__(
        self,
        limit: int,
        window_seconds: int,
        identifier: str = "default",
        error_message: str | None = None,
    ):
        self.limit = limit
        self.window = window_seconds
        self.identifier = identifier
        self.error_message = (
            error_message
            or "Too many requests. Please slow down and try again."
        )
        self._requests: DefaultDict[str, Deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def __call__(self, request: Request) -> None:
        """
        FastAPI dependency entrypoint. Raises HTTPException if rate limit exceeded.
        """
        client_key = self._get_client_key(request)
        now = time.time()

        async with self._lock:
            timestamps = self._requests[client_key]

            # Drop timestamps outside the window
            while timestamps and now - timestamps[0] > self.window:
                timestamps.popleft()

            if len(timestamps) >= self.limit:
                raise HTTPException(status_code=429, detail=self.error_message)

            timestamps.append(now)

    def _get_client_key(self, request: Request) -> str:
        """
        Build a stable key per client (IP address). Falls back to identifier.
        """
        client_host = request.client.host if request.client else "anonymous"
        return f"{client_host}:{self.identifier}"

