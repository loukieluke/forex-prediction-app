import json
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Candle, NewsHeadline, PredictionLog, TradeLog
from app.schemas import SignalResponse
from app.services.features import build_training_dataframe, latest_feature_vector
from app.services.forex import fetch_forex_candles
from app.services.modeling import predict_signal
from app.services.news import fetch_news
from app.services.oanda import is_auto_trading_enabled, place_market_order, validate_trade_limits
from app.services.strategies import evaluate_multi_timeframe_strategy
from app.services.sentiment import keyword_sentiment_score


def ingest_candles(db: Session, instrument: str = "EUR_USD", granularity: str = "H1") -> int:
    candles = fetch_forex_candles(instrument=instrument, granularity=granularity)
    if not candles:
        return 0
    for row in candles:
        stmt = insert(Candle).values(**row)
        stmt = stmt.on_conflict_do_update(
            index_elements=["instrument", "granularity", "time"],
            set_={
                "open": row["open"],
                "high": row["high"],
                "low": row["low"],
                "close": row["close"],
                "volume": row["volume"],
            },
        )
        db.execute(stmt)
    db.commit()
    return len(candles)


def ingest_news(db: Session) -> int:
    headlines = fetch_news()
    if not headlines:
        return 0
    for item in headlines:
        score = keyword_sentiment_score(item["title"])
        entity = NewsHeadline(
            source=item["source"],
            published_at=item["published_at"],
            title=item["title"],
            url=item.get("url", ""),
            sentiment_score=score,
        )
        db.add(entity)
    db.commit()
    return len(headlines)


def build_signal(db: Session, instrument: str = "EUR_USD", granularity: str = "H1") -> SignalResponse:
    features = latest_feature_vector(db=db, instrument=instrument, granularity=granularity)
    strategy = evaluate_multi_timeframe_strategy(db=db, instrument=instrument)
    if not features:
        return SignalResponse(signal="HOLD", confidence=0.0, features={}, strategy=strategy)
    try:
        prediction = predict_signal(features)
    except Exception:
        prediction = {
            "signal": "HOLD",
            "confidence": 0.0,
        }
    ml_score = 0.0
    if prediction["signal"] == "BUY":
        ml_score = prediction["confidence"]
    elif prediction["signal"] == "SELL":
        ml_score = -prediction["confidence"]
    strategy_score = strategy.get("normalized_score", 0.0)
    combined = (settings.strategy_blend_weight * strategy_score) + (settings.ml_blend_weight * ml_score)
    if not strategy.get("top_down_aligned", False):
        final_signal = "HOLD"
        final_confidence = round(min(0.59, abs(combined)), 4)
    elif abs(combined) < settings.blend_hold_band:
        final_signal = "HOLD"
        final_confidence = round(abs(combined), 4)
    else:
        final_signal = "BUY" if combined > 0 else "SELL"
        final_confidence = round(min(0.99, abs(combined)), 4)
    record = PredictionLog(
        instrument=instrument,
        granularity=granularity,
        signal=final_signal,
        confidence=final_confidence,
        payload_json=json.dumps(
            {
                "features": {k: str(v) for k, v in features.items()},
                "ml_prediction": prediction,
                "strategy": strategy,
                "combined_score": round(combined, 4),
            }
        ),
    )
    db.add(record)
    db.commit()
    return SignalResponse(signal=final_signal, confidence=final_confidence, features=features, strategy=strategy)


def _trades_today_count(db: Session) -> int:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return db.scalar(select(func.count(TradeLog.id)).where(TradeLog.created_at >= start)) or 0


def maybe_execute_trade(
    db: Session,
    signal: SignalResponse,
    instrument: str = "EUR_USD",
    units: int = 1000,
    auto_trade: bool = True,
) -> dict | None:
    if signal.signal == "HOLD":
        return None
    if auto_trade and signal.confidence < settings.signal_confidence_threshold:
        return None
    if auto_trade and not is_auto_trading_enabled():
        return {"status": "skipped", "reason": "AUTO_TRADE_ENABLED is false or non-practice env"}
    trades_today = _trades_today_count(db)
    validate_trade_limits(units=units, trades_today=trades_today)
    payload = place_market_order(instrument=instrument, units=units, direction=signal.signal)
    trade = TradeLog(
        instrument=instrument,
        direction=signal.signal,
        units=units,
        confidence=signal.confidence,
        auto_trade=auto_trade,
        status="submitted",
        broker_response_json=json.dumps(payload),
    )
    db.add(trade)
    db.commit()
    return payload


def training_frame_from_db(db: Session, instrument: str = "EUR_USD", granularity: str = "H1") -> pd.DataFrame:
    return build_training_dataframe(db=db, instrument=instrument, granularity=granularity)
