# SentinelPay Risk Engine — RETO 4

Motor de scoring de riesgo en tiempo real para una pasarela de pagos. Evalúa
transacciones con reglas configurables y velocity checks, expone decisión +
razones explicables, y una GUI para evaluación manual y simulación de ráfagas.

## Stack

- **Python 3.11** + **FastAPI** + **Pydantic** + **httpx** + **Jinja2/HTMX**
- GLM 5.2 se usa como **copiloto de desarrollo** (no en runtime)
- Scoring determinístico: reglas + pesos configurables

## Arquitectura

```
codigo/sentinelpay/
├── app/
│   ├── domain/          # modelos Pydantic (Transaction, EvaluationResult, ...)
│   ├── rules/           # reglas estáticas + velocity
│   ├── engine/          # scoring, circuit breaker, orquestador
│   ├── state/           # sliding window, blocklist (in-memory)
│   ├── api/             # rutas FastAPI
│   ├── templates/       # GUI (Jinja2 + HTMX)
│   ├── config.py        # settings + ScoringConfig con defaults
│   └── main.py          # app FastAPI
├── tests/               # pytest
├── run.py               # uvicorn entrypoint
├── requirements.txt
└── .env.example
```

## Instalación

```bash
cd fabian-villon-g4/codigo/sentinelpay
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Ejecución

```bash
uvicorn app.main:app --reload --port 8000
# o
python run.py
```

Abrir `http://localhost:8000` en el navegador.

## Estado de implementación

- [x] **Step 1 — Scaffold:** Proyecto FastAPI creado, servidor arranca en :8000.
- [x] **Step 2 — Modelos de dominio:** Transaction, Reason, EvaluationResult, RuleConfig, ScoringConfig con defaults del reto.
- [x] Step 3 — Reglas estáticas (Fase 1): amount_anomaly, country_mismatch, unusual_hour
- [x] Step 4 — Sliding window + velocity + blocklist (Fase 2): velocity_card +40, velocity_device +50, blocklist 120s con auto-expiración
- [x] Step 5 — Scoring + circuit breaker (Fase 3): score cap 100, umbrales APPROVE/REVIEW/DECLINE, circuit breaker 3 fallos → open 15s → semi-open
- [ ] Step 6 — Orquestador evaluate()
- [ ] Step 7 — Rutas API
- [ ] Step 8 — GUI (Fase 4)
- [ ] Step 9 — Tests
- [ ] Step 10 — Documentación final

## Configuración

Pesos por defecto (configurables vía ScoringConfig):

| Regla | Peso | Descripción |
|---|---|---|
| `amount_anomaly` | 25 | amount > 3x promedio histórico |
| `country_mismatch` | 30 | country ≠ ip_country |
| `unusual_hour` | 10 | 1am-5am hora local |
| `velocity_card` | 40 | >5 txns en 10s |
| `velocity_device` | 50 | >3 cards distintas en 30s |

Umbrales: `APPROVE < 40` · `REVIEW 40-74` · `DECLINE >= 75`
Blocklist TTL: 120s · Circuit breaker: 3 fallos → open 15s
