import asyncio
from datetime import datetime, timedelta


class Blocklist:
    """Blocklist temporal con auto-expiración lazy."""

    def __init__(self, ttl_s: int) -> None:
        self._ttl = timedelta(seconds=ttl_s)
        self._blocked: dict[str, datetime] = {}
        self._lock = asyncio.Lock()

    async def is_blocked(self, key: str, now: datetime) -> bool:
        async with self._lock:
            expiry = self._blocked.get(key)
            if expiry is None:
                return False
            if now >= expiry:
                del self._blocked[key]
                return False
            return True

    async def block(self, key: str, now: datetime) -> datetime:
        async with self._lock:
            expiry = now + self._ttl
            self._blocked[key] = expiry
            return expiry

    async def get_blocked_items(self, now: datetime) -> dict[str, str]:
        async with self._lock:
            expired = [k for k, v in self._blocked.items() if now >= v]
            for k in expired:
                del self._blocked[k]
            return {k: v.isoformat() for k, v in self._blocked.items()}
