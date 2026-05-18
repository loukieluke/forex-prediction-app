from sqlalchemy.orm import Session

from app.schemas import SignalResponse
from app.services.pipeline import build_signal, ingest_candles, ingest_news, maybe_execute_trade


def run_pipeline_cycle(db: Session, instrument: str = "EUR_USD", granularity: str = "H1", units: int = 1000) -> dict:
    candles_count = ingest_candles(db, instrument=instrument, granularity=granularity)
    news_count = ingest_news(db)
    signal: SignalResponse = build_signal(db, instrument=instrument, granularity=granularity)
    trade_payload = maybe_execute_trade(db, signal=signal, instrument=instrument, units=units, auto_trade=True)
    return {
        "candles_upserted": candles_count,
        "news_inserted": news_count,
        "signal": signal.model_dump(),
        "trade": trade_payload,
    }
