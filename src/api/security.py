"""Access control and abuse limits for the HTTP API.

Everything here is plain Python with injectable clocks, so it can be tested without a server.
"""

from __future__ import annotations

import hmac
import time
from collections import deque
from collections.abc import Callable
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any

from fastapi import HTTPException

from src import config

PUBLIC_PATHS = frozenset({"/api/v1/health"})

# After this many wrong keys from one address inside the window, that address is locked out
# (even for the right key) until the window passes.
FAILED_AUTH_LIMIT = 10
FAILED_AUTH_WINDOW_S = 60.0


class Access(str, Enum):
    ALLOWED = "allowed"
    UNAUTHORIZED = "unauthorized"
    MISCONFIGURED = "misconfigured"


def check_access(*, secret: str, app_env: str, method: str, path: str, auth_header: str) -> Access:
    """Decide whether a request may proceed. Fails closed in production without a secret."""
    if method == "OPTIONS" or path in PUBLIC_PATHS:
        return Access.ALLOWED
    if not secret:
        return Access.MISCONFIGURED if app_env == "production" else Access.ALLOWED
    expected = f"Bearer {secret}".encode()
    if hmac.compare_digest(auth_header.encode(), expected):
        return Access.ALLOWED
    return Access.UNAUTHORIZED


def client_ip(request: Any) -> str:
    """The caller's address. Only the header Fly's edge sets is trusted; X-Forwarded-For can be
    forged by the caller, so it is ignored."""
    forwarded = request.headers.get("Fly-Client-IP")
    if forwarded:
        return str(forwarded)
    return request.client.host if request.client else "unknown"


class SlidingWindowLimiter:
    """Counts events per key over a trailing window."""

    def __init__(
        self, limit: int, window_s: float, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._limit = limit
        self._window = window_s
        self._clock = clock
        self._events: dict[str, deque[float]] = {}
        self._last_sweep = clock()

    def _prune(self, key: str, now: float) -> deque[float]:
        events = self._events.get(key)
        if events is None:
            return deque()
        while events and now - events[0] >= self._window:
            events.popleft()
        if not events:
            del self._events[key]
            return deque()
        return events

    def _sweep(self, now: float) -> None:
        if now - self._last_sweep < self._window:
            return
        self._last_sweep = now
        for key in list(self._events):
            self._prune(key, now)

    def record(self, key: str) -> None:
        now = self._clock()
        self._sweep(now)
        self._prune(key, now)
        self._events.setdefault(key, deque()).append(now)

    def blocked(self, key: str) -> bool:
        now = self._clock()
        self._sweep(now)
        return len(self._prune(key, now)) >= self._limit

    def tracked_keys(self) -> int:
        return len(self._events)


class DailyBudget:
    """A per-day allowance (UTC). A limit of zero means the feature is off."""

    def __init__(
        self,
        limit: int,
        today: Callable[[], date] = lambda: datetime.now(timezone.utc).date(),
    ) -> None:
        self._limit = limit
        self._today = today
        self._day = today()
        self._used = 0

    def try_take(self) -> bool:
        today = self._today()
        if today != self._day:
            self._day, self._used = today, 0
        if self._used >= self._limit:
            return False
        self._used += 1
        return True

    @property
    def remaining(self) -> int:
        if self._today() != self._day:
            return self._limit
        return max(0, self._limit - self._used)

    @property
    def limit(self) -> int:
        return self._limit


failed_auth = SlidingWindowLimiter(FAILED_AUTH_LIMIT, FAILED_AUTH_WINDOW_S)
_ai_budget: DailyBudget | None = None


def consume_ai_budget() -> None:
    """Count one call to a Claude-backed endpoint, or refuse it for today."""
    global _ai_budget
    if _ai_budget is None or _ai_budget.limit != config.AI_DAILY_LIMIT:
        _ai_budget = DailyBudget(config.AI_DAILY_LIMIT)
    if not _ai_budget.try_take():
        raise HTTPException(429, "Daily AI call limit reached. Try again tomorrow.")


def reset_state() -> None:
    """Forget all counters. For tests."""
    global _ai_budget, failed_auth
    _ai_budget = None
    failed_auth = SlidingWindowLimiter(FAILED_AUTH_LIMIT, FAILED_AUTH_WINDOW_S)
