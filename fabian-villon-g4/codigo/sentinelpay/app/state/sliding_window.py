import asyncio
from collections import deque
from datetime import datetime, timedelta


class SlidingWindow:
    """Rate limiter con ventana deslizante para contar eventos por key."""

    def __init__(self, window_s: int) -> None:
        self._window = timedelta(seconds=window_s)
        self._events: dict[str, deque[datetime]] = {}
        self._lock = asyncio.Lock()

    async def record_and_count(self, key: str, timestamp: datetime) -> int:
        async with self._lock:
            events = self._events.setdefault(key, deque())
            cutoff = timestamp - self._window
            while events and events[0] < cutoff:
                events.popleft()
            events.append(timestamp)
            return len(events)


class DeviceCardWindow:
    """Ventana deslizante que cuenta card_ids distintos por device_id."""

    def __init__(self, window_s: int) -> None:
        self._window = timedelta(seconds=window_s)
        self._events: dict[str, deque[tuple[datetime, str]]] = {}
        self._lock = asyncio.Lock()

    async def record_and_count_distinct_cards(
        self, device_id: str, card_id: str, timestamp: datetime
    ) -> int:
        async with self._lock:
            events = self._events.setdefault(device_id, deque())
            cutoff = timestamp - self._window
            while events and events[0][0] < cutoff:
                events.popleft()
            events.append((timestamp, card_id))
            return len({card for _, card in events})
