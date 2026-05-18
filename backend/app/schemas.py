from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CandleOut(BaseModel):
    instrument: str
    granularity: str
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class SignalRequest(BaseModel):
    instrument: str = "EUR_USD"
    granularity: str = "H1"
    threshold: float | None = None


class SignalResponse(BaseModel):
    signal: str
    confidence: float
    features: dict[str, Any]
    strategy: dict[str, Any] | None = None


class ManualTradeRequest(BaseModel):
    instrument: str = "EUR_USD"
    direction: str = Field(pattern="^(BUY|SELL)$")
    units: int = 1000
    confidence: float = 1.0


class TradeResponse(BaseModel):
    status: str
    payload: dict[str, Any]


class RunPipelineResponse(BaseModel):
    status: str
    signal: SignalResponse
    trade: dict[str, Any] | None
