from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.domain.models import EvaluationResult, Transaction
from app.engine.evaluate import RiskEngine

router = APIRouter(prefix="/api", tags=["sentinelpay"])
html_router = APIRouter(tags=["gui"])
engine = RiskEngine()

templates = Jinja2Templates(directory=Path(__file__).resolve().parent.parent / "templates")


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


def _parse_timestamp(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _form_to_transaction(
    id: str,
    card_id: str,
    merchant_id: str,
    amount: float,
    currency: str,
    country: str,
    ip_country: str,
    device_id: str,
    ip: str,
    timestamp: str,
) -> Transaction:
    return Transaction(
        id=id,
        card_id=card_id,
        merchant_id=merchant_id,
        amount=amount,
        currency=currency,
        country=country,
        ip_country=ip_country,
        device_id=device_id,
        ip=ip,
        timestamp=_parse_timestamp(timestamp),
    )


@html_router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")


@html_router.post("/evaluate-form", response_class=HTMLResponse)
async def evaluate_form(
    request: Request,
    id: str = Form(...),
    card_id: str = Form(...),
    merchant_id: str = Form(...),
    amount: float = Form(...),
    currency: str = Form(...),
    country: str = Form(...),
    ip_country: str = Form(...),
    device_id: str = Form(...),
    ip: str = Form(...),
    timestamp: str = Form(...),
) -> HTMLResponse:
    txn = _form_to_transaction(
        id, card_id, merchant_id, amount, currency, country,
        ip_country, device_id, ip, timestamp,
    )
    result = await engine.evaluate(txn)
    return templates.TemplateResponse(
        request, "_result.html", {"result": result}
    )


@html_router.post("/burst-form", response_class=HTMLResponse)
async def burst_form(
    request: Request,
    id: str = Form(...),
    card_id: str = Form(...),
    merchant_id: str = Form(...),
    amount: float = Form(...),
    currency: str = Form(...),
    country: str = Form(...),
    ip_country: str = Form(...),
    device_id: str = Form(...),
    ip: str = Form(...),
    timestamp: str = Form(...),
) -> HTMLResponse:
    txn = _form_to_transaction(
        id, card_id, merchant_id, amount, currency, country,
        ip_country, device_id, ip, timestamp,
    )
    results = []
    base_ts = txn.timestamp
    for i in range(6):
        burst_txn = txn.model_copy(
            update={
                "id": f"{txn.id}_burst_{i}",
                "timestamp": base_ts + timedelta(seconds=i),
            }
        )
        results.append(await engine.evaluate(burst_txn))
    return templates.TemplateResponse(
        request, "_burst.html", {"results": results}
    )
