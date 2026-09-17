from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class Transaction(BaseModel):
    id: str
    card_id: str
    merchant_id: str
    amount: float
    currency: str
    country: str
    ip_country: str
    device_id: str
    ip: str
    timestamp: datetime


class Reason(BaseModel):
    rule: str
    weight: int
    detail: str


class EvaluationResult(BaseModel):
    transaction_id: str
    score: int
    decision: Literal["APPROVE", "REVIEW", "DECLINE"]
    reasons: list[Reason]
    bank_auth_status: str | None = None


class RuleConfig(BaseModel):
    enabled: bool = True
    weight: int


class ScoringConfig(BaseModel):
    amount_anomaly: RuleConfig
    country_mismatch: RuleConfig
    unusual_hour: RuleConfig
    velocity_card: RuleConfig
    velocity_device: RuleConfig
    card_velocity_window_s: int = 10
    card_velocity_max: int = 5
    device_velocity_window_s: int = 30
    device_velocity_max_cards: int = 3
    blocklist_ttl_s: int = 120
    approve_below: int = 40
    decline_at: int = 75
    circuit_failure_threshold: int = 3
    circuit_open_s: int = 15
