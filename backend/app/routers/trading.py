from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import PredictionLog, TradeLog
from app.schemas import ManualTradeRequest, RunPipelineResponse, SignalResponse, TradeResponse
from app.services.oanda import get_account_summary, get_open_positions, get_pricing
from app.services.pipeline import build_signal, maybe_execute_trade

router = APIRouter(prefix="/api/trade", tags=["trading"])


@router.get("/account")
def account_summary():
    return get_account_summary()


@router.get("/positions")
def open_positions():
    return get_open_positions()


@router.get("/pricing")
def pricing(instruments: str = "EUR_USD"):
    return get_pricing(instruments=instruments.split(","))


@router.post("/manual", response_model=TradeResponse)
def manual_trade(payload: ManualTradeRequest, db: Session = Depends(get_db)):
    try:
        result = maybe_execute_trade(
            db=db,
            signal=SignalResponse(signal=payload.direction, confidence=payload.confidence, features={}),
            instrument=payload.instrument,
            units=payload.units,
            auto_trade=False,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TradeResponse(status="ok", payload=result or {"status": "skipped"})


@router.post("/auto/run", response_model=RunPipelineResponse)
def run_auto_cycle(instrument: str = "EUR_USD", granularity: str = "H1", units: int = 1000, db: Session = Depends(get_db)):
    signal = build_signal(db=db, instrument=instrument, granularity=granularity)
    try:
        trade = maybe_execute_trade(db=db, signal=signal, instrument=instrument, units=units, auto_trade=True)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RunPipelineResponse(status="ok", signal=signal, trade=trade)


@router.get("/logs")
def trade_logs(limit: int = 100, db: Session = Depends(get_db)):
    trades = db.query(TradeLog).order_by(TradeLog.created_at.desc()).limit(limit).all()
    predictions = db.query(PredictionLog).order_by(PredictionLog.created_at.desc()).limit(limit).all()
    return {
        "trades": [
            {
                "id": row.id,
                "instrument": row.instrument,
                "direction": row.direction,
                "units": row.units,
                "confidence": row.confidence,
                "auto_trade": row.auto_trade,
                "status": row.status,
                "created_at": row.created_at,
            }
            for row in trades
        ],
        "predictions": [
            {
                "id": row.id,
                "instrument": row.instrument,
                "signal": row.signal,
                "confidence": row.confidence,
                "created_at": row.created_at,
            }
            for row in predictions
        ],
    }
