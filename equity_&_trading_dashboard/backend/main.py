# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import market, backtest


app = FastAPI(title="TradeSmart Pro API", version="1.0.0")
app.include_router(market.router,   prefix="/api/market",   tags=["market"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])
# Allow the Next.js dev server to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market.router, prefix="/api/market", tags=["market"])


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "TradeSmart Pro API"}