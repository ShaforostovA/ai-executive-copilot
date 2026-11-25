import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

_MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


class OriginCSRFMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, allowed_origins: set[str]) -> None:
        super().__init__(app)
        self.allowed_origins = allowed_origins

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.method in _MUTATING_METHODS and request.url.path.startswith("/api/"):
            origin = request.headers.get("Origin")
            if origin not in self.allowed_origins:
                request_id = getattr(request.state, "request_id", str(uuid4()))
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "csrf_rejected",
                            "message": "Request origin is not allowed.",
                            "request_id": request_id,
                        }
                    },
                    headers={"X-Request-ID": request_id},
                )
        return await call_next(request)


class SlidingWindowRateLimiter:
    def __init__(self, attempts: int, window_seconds: float) -> None:
        self.attempts = attempts
        self.window_seconds = window_seconds
        self._requests: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        requests = self._requests[key]
        while requests and requests[0] <= now - self.window_seconds:
            requests.popleft()
        if len(requests) >= self.attempts:
            return False
        requests.append(now)
        return True
