from typing import Optional

from app.domain.models import Reason, ScoringConfig, Transaction


class StaticRuleEngine:
    def __init__(self) -> None:
        self._amount_history: dict[str, list[float]] = {}

    def evaluate(self, txn: Transaction, config: ScoringConfig) -> list[Reason]:
        reasons: list[Reason] = []

        r = self._amount_anomaly(txn, config)
        if r:
            reasons.append(r)
        r = self._country_mismatch(txn, config)
        if r:
            reasons.append(r)
        r = self._unusual_hour(txn, config)
        if r:
            reasons.append(r)

        self._amount_history.setdefault(txn.card_id, []).append(txn.amount)
        return reasons

    def _amount_anomaly(
        self, txn: Transaction, config: ScoringConfig
    ) -> Optional[Reason]:
        if not config.amount_anomaly.enabled:
            return None
        history = self._amount_history.get(txn.card_id, [])
        if not history:
            return None
        avg = sum(history) / len(history)
        if txn.amount > 3 * avg:
            return Reason(
                rule="amount_anomaly",
                weight=config.amount_anomaly.weight,
                detail=f"amount={txn.amount} > 3x avg={avg:.2f} (history={len(history)} txns)",
            )
        return None

    def _country_mismatch(
        self, txn: Transaction, config: ScoringConfig
    ) -> Optional[Reason]:
        if not config.country_mismatch.enabled:
            return None
        if txn.country != txn.ip_country:
            return Reason(
                rule="country_mismatch",
                weight=config.country_mismatch.weight,
                detail=f"card_country={txn.country}, ip_country={txn.ip_country}",
            )
        return None

    def _unusual_hour(
        self, txn: Transaction, config: ScoringConfig
    ) -> Optional[Reason]:
        if not config.unusual_hour.enabled:
            return None
        hour = txn.timestamp.hour
        if 1 <= hour < 5:
            return Reason(
                rule="unusual_hour",
                weight=config.unusual_hour.weight,
                detail=f"{hour:02d}:{txn.timestamp.minute:02d} local time",
            )
        return None
