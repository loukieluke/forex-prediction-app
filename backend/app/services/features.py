from datetime import datetime, timedelta, timezone

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Candle, NewsHeadline
from app.services.indicators import compute_indicators


def candles_to_dataframe(candles: list[Candle]) -> pd.DataFrame:
    rows = [
        {
            "time": c.time,
            "open": c.open,
            "high": c.high,
            "low": c.low,
            "close": c.close,
            "volume": c.volume,
        }
        for c in candles
    ]
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    return df.sort_values("time").reset_index(drop=True)


def get_sentiment_window_score(db: Session, end_time: datetime, hours: int = 6) -> float:
    if end_time.tzinfo is None:
        end_time = end_time.replace(tzinfo=timezone.utc)
    start_time = end_time - timedelta(hours=hours)
    rows = db.scalars(
        select(NewsHeadline).where(NewsHeadline.published_at >= start_time, NewsHeadline.published_at <= end_time)
    ).all()
    if not rows:
        return 0.0
    return sum(row.sentiment_score for row in rows) / len(rows)


def latest_feature_vector(db: Session, instrument: str = "EUR_USD", granularity: str = "H1") -> dict:
    candles = db.scalars(
        select(Candle)
        .where(Candle.instrument == instrument, Candle.granularity == granularity)
        .order_by(Candle.time.desc())
        .limit(300)
    ).all()
    candles = list(reversed(candles))
    df = candles_to_dataframe(candles)
    if df.empty:
        return {}
    indicator_df = compute_indicators(df).dropna()
    if indicator_df.empty:
        return {}
    latest = indicator_df.iloc[-1].to_dict()
    latest["sentiment_score"] = get_sentiment_window_score(db, end_time=indicator_df.iloc[-1]["time"])
    return latest


def build_training_dataframe(db: Session, instrument: str = "EUR_USD", granularity: str = "H1") -> pd.DataFrame:
    """OHLCV rows with indicator columns and sentiment aligned to each bar time (for model training)."""
    candles = db.scalars(
        select(Candle)
        .where(Candle.instrument == instrument, Candle.granularity == granularity)
        .order_by(Candle.time.asc())
    ).all()
    if not candles:
        return pd.DataFrame()
    df = candles_to_dataframe(candles)
    indicator_df = compute_indicators(df).dropna()
    if indicator_df.empty:
        return pd.DataFrame()
    scores = [
        get_sentiment_window_score(db, end_time=row["time"])
        for _, row in indicator_df.iterrows()
    ]
    out = indicator_df.copy()
    out["sentiment_score"] = scores
    return out
