from datetime import datetime, timezone

from app.config import default_scoring_config
from app.domain.models import EvaluationResult, Reason, ScoringConfig, Transaction
from app.engine.circuit_breaker import CircuitBreaker
from app.engine.mock_bank_auth import MockBankAuth
from app.engine.scoring import build_result
from app.rules.static import StaticRuleEngine
from app.rules.velocity import VelocityRuleEngine


class RiskEngine:
    def __init__(self, config: ScoringConfig | None = None) -> None:
        self._config = config or default_scoring_config()
        self._static_rules = StaticRuleEngine()
        self._velocity_rules = VelocityRuleEngine(self._config)
        self._bank_auth = MockBankAuth()
        self._circuit = CircuitBreaker(
            failure_threshold=self._config.circuit_failure_threshold,
            open_duration_s=self._config.circuit_open_s,
        )

    async def evaluate(self, txn: Transaction) -> EvaluationResult:
        blocked, reason = await self._velocity_rules.check_blocklist(txn)
        if blocked:
            return EvaluationResult(
                transaction_id=txn.id,
                score=100,
                decision="DECLINE",
                reasons=[
                    Reason(rule=reason, weight=0, detail=f"{reason}: {txn.card_id}")
                ],
                bank_auth_status=None,
            )

        reasons = self._static_rules.evaluate(txn, self._config)
        reasons.extend(await self._velocity_rules.evaluate(txn))

        bank_result = await self._circuit.call(
            self._bank_auth.authorize, txn.id, timeout=2.0
        )

        return build_result(
            transaction_id=txn.id,
            reasons=reasons,
            config=self._config,
            bank_auth_status=bank_result.get("status"),
        )

    async def get_state(self) -> dict:
        now = datetime.now(timezone.utc)
        blocklist = await self._velocity_rules.get_blocklist_status(now)
        circuit = await self._circuit.get_state()
        return {"blocklist": blocklist, "circuit_breaker": circuit}

    @property
    def config(self) -> ScoringConfig:
        return self._config
