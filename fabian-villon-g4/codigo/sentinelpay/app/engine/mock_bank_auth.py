import asyncio
import random


class MockBankAuth:
    """Servicio de autorización bancaria mock — 30% falla o timeout."""

    def __init__(
        self, failure_rate: float = 0.30, timeout_s: float = 2.0
    ) -> None:
        self._failure_rate = failure_rate
        self._timeout_s = timeout_s
        self._random = random.Random(42)

    async def authorize(self, transaction_id: str) -> dict:
        r = self._random.random()
        if r < self._failure_rate / 2:
            await asyncio.sleep(self._timeout_s + 0.5)
            raise TimeoutError(f"Bank auth timeout for {transaction_id}")
        if r < self._failure_rate:
            raise RuntimeError(f"Bank auth error for {transaction_id}")
        await asyncio.sleep(0.01)
        return {"status": "ok", "transaction_id": transaction_id}
