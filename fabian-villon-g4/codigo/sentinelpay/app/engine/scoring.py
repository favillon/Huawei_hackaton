from app.domain.models import EvaluationResult, Reason, ScoringConfig


def compute_score(reasons: list[Reason]) -> int:
    return min(sum(r.weight for r in reasons), 100)


def make_decision(
    score: int, config: ScoringConfig, circuit_degraded: bool = False
) -> str:
    if score >= config.decline_at:
        return "DECLINE"
    if score < config.approve_below:
        if circuit_degraded:
            return "REVIEW"
        return "APPROVE"
    return "REVIEW"


def build_result(
    transaction_id: str,
    reasons: list[Reason],
    config: ScoringConfig,
    bank_auth_status: str | None = None,
) -> EvaluationResult:
    score = compute_score(reasons)
    circuit_degraded = bank_auth_status == "circuit_open_degraded"
    decision = make_decision(score, config, circuit_degraded)
    return EvaluationResult(
        transaction_id=transaction_id,
        score=score,
        decision=decision,
        reasons=reasons,
        bank_auth_status=bank_auth_status,
    )
