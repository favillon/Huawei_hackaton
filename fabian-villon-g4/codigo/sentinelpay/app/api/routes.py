from datetime import timedelta

from fastapi import APIRouter
from pydantic import BaseModel

from app.domain.models import EvaluationResult, Transaction
from app.engine.evaluate import RiskEngine

router = APIRouter(prefix="/api", tags=["sentinelpay"])
engine = RiskEngine()


class BurstRequest(BaseModel):
    transaction: Transaction
    count: int = 6
    interval_s: float = 1.0


@router.post("/evaluate", response_model=EvaluationResult)
async def evaluate(txn: Transaction) -> EvaluationResult:
    return await engine.evaluate(txn)


@router.post("/evaluate/batch", response_model=list[EvaluationResult])
async def evaluate_batch(txns: list[Transaction]) -> list[EvaluationResult]:
    results = []
    for txn in txns:
        results.append(await engine.evaluate(txn))
    return results


@router.post("/simulate/burst", response_model=list[EvaluationResult])
async def simulate_burst(req: BurstRequest) -> list[EvaluationResult]:
    results = []
    base_ts = req.transaction.timestamp
    for i in range(req.count):
        txn = req.transaction.model_copy(
            update={
                "id": f"{req.transaction.id}_burst_{i}",
                "timestamp": base_ts + timedelta(seconds=i * req.interval_s),
            }
        )
        results.append(await engine.evaluate(txn))
    return results


@router.get("/config")
async def get_config() -> dict:
    return engine.config.model_dump()


@router.get("/state")
async def get_state() -> dict:
    return await engine.get_state()
