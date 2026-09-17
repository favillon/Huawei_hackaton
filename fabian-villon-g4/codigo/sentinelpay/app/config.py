from pydantic_settings import BaseSettings

from app.domain.models import RuleConfig, ScoringConfig


class Settings(BaseSettings):
    app_host: str = "0.0.0.0"
    app_port: int = 8000


def default_scoring_config() -> ScoringConfig:
    return ScoringConfig(
        amount_anomaly=RuleConfig(enabled=True, weight=25),
        country_mismatch=RuleConfig(enabled=True, weight=30),
        unusual_hour=RuleConfig(enabled=True, weight=10),
        velocity_card=RuleConfig(enabled=True, weight=40),
        velocity_device=RuleConfig(enabled=True, weight=50),
    )


settings = Settings()
