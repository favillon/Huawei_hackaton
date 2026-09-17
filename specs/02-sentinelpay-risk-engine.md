# SPEC 02 — SentinelPay Risk Engine

> **Estado:** Aprobado
> **Depende de:** Ninguno
> **Fecha:** 2026-09-17
> **Objetivo:** Construir un motor de scoring de riesgo en tiempo real que evalúa transacciones con reglas configurables y velocity checks, expone decisión + razones, y una GUI para evaluación manual y simulación de ráfagas — cubriendo las Fases 1-4 del RETO 4.

## Por qué existe esta spec

El RETO 4 define 4 fases acopladas + 4 bonos en 80 minutos. A diferencia del RETO 1, aquí GLM 5.2 es **copiloto de desarrollo**, no el motor de scoring — el scoring es determinístico (reglas + pesos). Esta spec captura el núcleo de 100 puntos con stack y arquitectura decididos de antemano.

## Scope

**In:**

- Fase 1 — Ingesta de transacciones + 3 reglas estáticas configurables (monto anómalo +25, país distinto +30, hora inusual +10) con pesos activables/desactivables.
- Fase 2 — Sliding window rate limiter por tarjeta y dispositivo, velocity rules (+40/+50), blocklist temporal con auto-expiración (120s).
- Fase 3 — Score ponderado con umbrales APPROVE/REVIEW/DECLINE, cap 100, circuit breaker sobre `mock_bank_auth()`, desglose de razones.
- Fase 4 — GUI: formulario de transacción, score color-coded, razones, simular ráfaga.
- Tests con pytest (incluye test de concurrencia).
- `README.md`, `requerimientos.txt`, `prompt_usado.txt`.

**Out of scope (for future specs):**

- Bono A — Detección de colusión por grafo.
- Bono B — Concurrencia segura con prueba de carga real.
- Bono C — Explicabilidad exportable (JSON + NL por IA).
- Bono D — Suite de pruebas adversariales.
- GLM 5.2 en runtime (solo es dev copilot).
- Base de datos externa.

## Data model

```python
# app/domain/models.py

class Transaction(BaseModel):
    id: str
    card_id: str
    merchant_id: str
    amount: float
    currency: str
    country: str            # país registrado de la tarjeta
    ip_country: str         # país inferido de la IP
    device_id: str
    ip: str
    timestamp: datetime

class Reason(BaseModel):
    rule: str               # "country_mismatch", "unusual_hour", ...
    weight: int
    detail: str

class EvaluationResult(BaseModel):
    transaction_id: str
    score: int              # 0-100
    decision: Literal["APPROVE", "REVIEW", "DECLINE"]
    reasons: list[Reason]
    bank_auth_status: str | None = None   # "ok" | "timeout" | "circuit_open_degraded"

class RuleConfig(BaseModel):
    enabled: bool = True
    weight: int

class ScoringConfig(BaseModel):
    amount_anomaly: RuleConfig         # weight=25
    country_mismatch: RuleConfig       # weight=30
    unusual_hour: RuleConfig           # weight=10
    velocity_card: RuleConfig          # weight=40
    velocity_device: RuleConfig        # weight=50
    card_velocity_window_s: int = 10
    card_velocity_max: int = 5
    device_velocity_window_s: int = 30
    device_velocity_max_cards: int = 3
    blocklist_ttl_s: int = 120
    approve_below: int = 40            # score < 40 → APPROVE
    decline_at: int = 75               # score >= 75 → DECLINE
    circuit_failure_threshold: int = 3
    circuit_open_s: int = 15
```

Convenciones:

- Score = `min(sum(weights of triggered rules), 100)`.
- `REVIEW` si el circuit breaker está abierto (degradación segura).
- Blocklist check **antes** de evaluar reglas → DECLINE inmediato.

## Implementation plan

1. **Scaffold.** Crear `fabian-villon-g4/codigo/sentinelpay/` con `app/__init__.py`, `run.py` (uvicorn), `requirements.txt`, `.env.example`. Verificar: `pip install -r requirements.txt && uvicorn run:app --reload` arranca en `:8000`.
2. **Modelos de dominio.** `app/domain/models.py` (Transaction, Reason, EvaluationResult, RuleConfig, ScoringConfig). `app/config.py` con defaults del reto.
3. **Reglas estáticas (Fase 1).** `app/rules/static.py`: `amount_anomaly` (amount > 3x promedio histórico de la tarjeta), `country_mismatch` (country ≠ ip_country), `unusual_hour` (1am-5am). Cada regla devuelve `Optional[Reason]`. Pesos desde `ScoringConfig`. Historial in-memory `dict[card_id, list[amount]]`.
4. **Sliding window + velocity (Fase 2).** `app/state/sliding_window.py`: deque por `card_id` y `device_id` con timestamps. `app/rules/velocity.py`: `velocity_card` (>5 txns en 10s), `velocity_device` (>3 cards distintas en 30s). `app/state/blocklist.py`: `dict[card_id|device_id, expiry]` con auto-expiración lazy. `asyncio.Lock` protege todo el estado.
5. **Scoring + circuit breaker (Fase 3).** `app/engine/scoring.py`: combina razones, `score = min(sum(weights), 100)`, decisión por umbrales. `app/engine/circuit_breaker.py`: 3 fallos consecutivos → open 15s → semi-open → retry. `app/engine/mock_bank_auth.py`: mock con 30% fail/timeout.
6. **Orquestador.** `app/engine/evaluate.py`: `evaluate(transaction)`: check blocklist → static rules → velocity rules → score → bank auth (circuit breaker) → `EvaluationResult`. Blocklist activo → DECLINE inmediato sin re-evaluar.
7. **Rutas API.** `app/api/routes.py`: `POST /api/evaluate` (single), `POST /api/evaluate/batch`, `POST /api/simulate/burst` (N txns misma tarjeta), `GET /api/config`, `GET /api/state` (blocklist + circuit status).
8. **GUI (Fase 4).** `app/templates/` (Jinja2 + HTMX): formulario con campos de transacción, botón "Evaluar", botón "Simular ráfaga (6x)", resultado con score color-coded (verde/amarillo/rojo) + lista de razones.
9. **Tests.** `tests/`: `test_reglas_estaticas.py` (3 reglas), `test_velocity_card.py` (6 txns → +40 + blocklist), `test_velocity_device.py` (3 cards → +50), `test_blocklist_expiry.py` (120s → unblock), `test_scoring_umbrales.py` (APPROVE/REVIEW/DECLINE), `test_score_cap.py` (max 100), `test_circuit_breaker.py` (3 fallos → open → degrade), `test_concurrencia.py` (`asyncio.gather` misma tarjeta → no race).
10. **Documentación.** `fabian-villon-g4/README.md` (arquitectura, decisiones, cómo correr, config). `requerimientos.txt`. `prompt_usado.txt` (bitácora de prompts con GLM 5.2).

## Acceptance criteria

- [ ] `pip install -r requirements.txt && uvicorn run:app` arranca sin errores en `localhost:8000`.
- [ ] `POST /api/evaluate` con la transacción del ejemplo (CO/RU, 4:58am) devuelve `score=40`, `decision=REVIEW`, `reasons=[country_mismatch(+30), unusual_hour(+10)]`.
- [ ] Cada regla es activable/desactivable y su peso configurable vía `ScoringConfig`.
- [ ] 6 transacciones de la misma tarjeta en 7s → la 6ª activa `velocity_card` (+40) y marca la tarjeta como bloqueada.
- [ ] Transacciones #7+ de una tarjeta bloqueada → `DECLINE` inmediato con razón `"card_temporarily_blocked"`, sin re-evaluar reglas.
- [ ] Tras 120s, la tarjeta se desbloquea automáticamente y se evalúa normal.
- [ ] 3 tarjetas distintas desde el mismo `device_id` en 30s → `velocity_device` (+50).
- [ ] Score nunca supera 100 aunque múltiples reglas se disparen.
- [ ] Umbrales: `score < 40 → APPROVE`, `40-74 → REVIEW`, `≥ 75 → DECLINE`.
- [ ] Circuit breaker: 3 fallos consecutivos de `mock_bank_auth` → circuit open 15s → degradación segura (REVIEW) → semi-open → retry.
- [ ] Cada `EvaluationResult` incluye el desglose de razones (`rule`, `weight`, `detail`).
- [ ] La GUI en `:8000` permite ingresar una transacción por formulario, ver score + decisión color-coded + razones, y simular una ráfaga de 6x.
- [ ] `pytest` pasa incluyendo test de concurrencia (`asyncio.gather` sin race conditions).
- [ ] El estado interno (sliding window, blocklist) es seguro ante ráfagas concurrentes (`asyncio.Lock`).

## Decisions

- **Sí:** Mismo stack que SPEC 01 (Python + FastAPI + Pydantic). Consistencia, patrones compartidos, async nativo.
- **No:** Stack diferente. Pierde consistencia y tooling compartido.
- **Sí:** GLM 5.2 solo como dev copilot. El scoring es determinístico; razones estructuradas. Sin dependencia de API en runtime.
- **No:** GLM 5.2 en runtime para explicabilidad NL. Eso es Bono C, fuera de alcance.
- **Sí:** asyncio cooperativo + asyncio.Lock. Single-thread, sin GIL issues, consistente con FastAPI. Suficiente para ráfagas HTTP I/O-bound.
- **No:** Threading/multiprocessing. Overkill para trabajo I/O-bound.
- **Sí:** Subfolder `codigo/sentinelpay/`. Coexiste con SPEC 01 (`codigo/atlas/`) sin acoplamiento.
- **Sí:** Persistencia en memoria (dict + deque). El reto lo permite; sin DB.
- **No:** SQLite/Redis. Overengineering para 80 min.
- **Sí:** Bonos fuera de alcance. Mismo patrón que SPEC 01; mejor núcleo sólido.
- **Sí:** Circuit breaker con degradación a REVIEW. Exigido por Fase 3; seguro (no bloquea todo).

## Risks

| Riesgo | Mitigación |
|---|---|
| Race condition en sliding window/blocklist bajo ráfaga concurrente | `asyncio.Lock` protege todo acceso al estado. Test con `asyncio.gather`. |
| `mock_bank_auth` timeout bloquea el event loop | `asyncio.wait_for` con timeout; circuit breaker abre tras 3 fallos. |
| Blocklist crece sin límite (memory leak) | Expiry timestamp per entry; cleanup lazy on access. |
| Score > 100 con muchas reglas | `min(sum(weights), 100)` explícito. |
| Config cambiada en runtime rompe estado | Config cargada al arranque; cambios requieren restart (documentado). |

## What is **not** in this spec

- Bono A (grafo de colusión) — otra spec.
- Bono B (prueba de carga real) — otra spec. (La concurrencia básica sí está en el núcleo.)
- Bono C (explicabilidad exportable + NL) — otra spec.
- Bono D (suite adversarial) — otra spec.
- GLM 5.2 en runtime.
- Base de datos externa.
- Autenticación / multiusuario.

Cada uno, si se implementa, va en su propia spec.
