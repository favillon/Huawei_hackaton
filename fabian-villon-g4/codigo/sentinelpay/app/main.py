from fastapi import FastAPI

from app.api.routes import html_router, router as api_router

app = FastAPI(title="SentinelPay Risk Engine", version="0.1.0")
app.include_router(api_router)
app.include_router(html_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
