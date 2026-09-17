from datetime import datetime

from app.domain.models import Reason, ScoringConfig, Transaction
from app.state.blocklist import Blocklist
from app.state.sliding_window import DeviceCardWindow, SlidingWindow


class VelocityRuleEngine:
    def __init__(self, config: ScoringConfig) -> None:
        self._config = config
        self._card_window = SlidingWindow(config.card_velocity_window_s)
        self._device_window = DeviceCardWindow(config.device_velocity_window_s)
        self._blocklist = Blocklist(config.blocklist_ttl_s)

    async def check_blocklist(self, txn: Transaction) -> tuple[bool, str | None]:
        now = txn.timestamp
        if await self._blocklist.is_blocked(txn.card_id, now):
            return True, "card_temporarily_blocked"
        if await self._blocklist.is_blocked(txn.device_id, now):
            return True, "device_temporarily_blocked"
        return False, None

    async def evaluate(self, txn: Transaction) -> list[Reason]:
        reasons: list[Reason] = []

        count = await self._card_window.record_and_count(
            txn.card_id, txn.timestamp
        )
        if (
            self._config.velocity_card.enabled
            and count > self._config.card_velocity_max
        ):
            reasons.append(
                Reason(
                    rule="velocity_card",
                    weight=self._config.velocity_card.weight,
                    detail=f"{count} txns in {self._config.card_velocity_window_s}s "
                    f"(limit: {self._config.card_velocity_max})",
                )
            )
            await self._blocklist.block(txn.card_id, txn.timestamp)

        distinct = await self._device_window.record_and_count_distinct_cards(
            txn.device_id, txn.card_id, txn.timestamp
        )
        if (
            self._config.velocity_device.enabled
            and distinct > self._config.device_velocity_max_cards
        ):
            reasons.append(
                Reason(
                    rule="velocity_device",
                    weight=self._config.velocity_device.weight,
                    detail=f"{distinct} distinct cards in "
                    f"{self._config.device_velocity_window_s}s "
                    f"(limit: {self._config.device_velocity_max_cards})",
                )
            )
            await self._blocklist.block(txn.device_id, txn.timestamp)

        return reasons

    async def get_blocklist_status(self, now: datetime) -> dict[str, str]:
        return await self._blocklist.get_blocked_items(now)
