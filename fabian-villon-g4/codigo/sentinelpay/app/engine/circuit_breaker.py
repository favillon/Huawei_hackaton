import asyncio
import time
from enum import Enum
from typing import Any, Awaitable, Callable


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    SEMI_OPEN = "semi_open"


class CircuitBreaker:
    """Circuit breaker: 3 fallos consecutivos → open 15s → semi-open → retry."""

    def __init__(
        self, failure_threshold: int = 3, open_duration_s: int = 15
    ) -> None:
        self._failure_threshold = failure_threshold
        self._open_duration = open_duration_s
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._lock = asyncio.Lock()

    async def call(
        self, func: Callable[..., Awaitable[Any]], *args: Any, timeout: float = 2.0
    ) -> dict:
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if time.monotonic() - self._last_failure_time >= self._open_duration:
                    self._state = CircuitState.SEMI_OPEN
                else:
                    return {"status": "circuit_open_degraded"}

        try:
            result = await asyncio.wait_for(func(*args), timeout=timeout)
            async with self._lock:
                self._failure_count = 0
                self._state = CircuitState.CLOSED
            return result
        except asyncio.TimeoutError:
            await self._on_failure()
            return {"status": "timeout"}
        except Exception:
            await self._on_failure()
            return {"status": "error"}

    async def _on_failure(self) -> None:
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._failure_count >= self._failure_threshold:
                self._state = CircuitState.OPEN

    async def get_state(self) -> dict:
        async with self._lock:
            return {
                "state": self._state.value,
                "failure_count": self._failure_count,
            }
