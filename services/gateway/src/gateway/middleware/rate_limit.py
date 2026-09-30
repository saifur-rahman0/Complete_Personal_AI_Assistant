import time
from typing import Dict, Tuple
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window token-bucket rate limiter per client IP or X-Device-Id.
    Protects downstream microservices against abusive loops or runaway clients.
    Excludes liveness/readiness health probes.
    """

    def __init__(self, app, requests_per_minute: int = 120, burst_limit: int = 30) -> None:
        super().__init__(app)
        self.rpm = requests_per_minute
        self.burst_limit = burst_limit
        # Storage: {client_identifier: (token_count, last_refill_timestamp)}
        self._buckets: Dict[str, Tuple[float, float]] = {}

    def _get_client_id(self, request: Request) -> str:
        device_id = request.headers.get("X-Device-Id")
        if device_id and device_id != "unknown":
            return f"dev:{device_id}"
        client_host = request.client.host if request.client else "127.0.0.1"
        return f"ip:{client_host}"

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # Exclude health, readiness, and websocket streams from strict rate limiting
        if path.startswith("/health") or path.startswith("/ready") or path.startswith("/ws/"):
            return await call_next(request)

        client_id = self._get_client_id(request)
        now = time.monotonic()
        refill_rate = self.rpm / 60.0  # tokens per second

        if client_id not in self._buckets:
            tokens = float(self.burst_limit)
            last_refill = now
        else:
            tokens, last_refill = self._buckets[client_id]
            elapsed = now - last_refill
            tokens = min(float(self.burst_limit), tokens + elapsed * refill_rate)
            last_refill = now

        if tokens < 1.0:
            retry_after = round((1.0 - tokens) / refill_rate, 2)
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many requests. Please slow down.",
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(max(1, int(retry_after)))},
            )

        # Consume 1 token
        self._buckets[client_id] = (tokens - 1.0, last_refill)
        return await call_next(request)
