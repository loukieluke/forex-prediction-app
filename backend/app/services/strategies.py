from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Candle


@dataclass
class Vote:
    name: str
    score: int
    weight: float


def _load_h1_dataframe(db: Session, instrument: str, max_rows: int = 1500) -> pd.DataFrame:
    rows = db.scalars(
        select(Candle).where(Candle.instrument == instrument, Candle.granularity == "H1").order_by(Candle.time.desc()).limit(max_rows)
    ).all()
    if not rows:
        return pd.DataFrame()
    rows = list(reversed(rows))
    data = pd.DataFrame(
        [
            {"time": r.time, "open": r.open, "high": r.high, "low": r.low, "close": r.close, "volume": r.volume}
            for r in rows
        ]
    )
    return data.sort_values("time").reset_index(drop=True)


def _resample(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    if df.empty:
        return df
    tmp = df.copy()
    tmp["time"] = pd.to_datetime(tmp["time"], utc=True)
    tmp = tmp.set_index("time")
    ohlc = tmp.resample(timeframe).agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    ohlc = ohlc.dropna().reset_index()
    return ohlc


def _trend_vote(df: pd.DataFrame, weight: float = 1.0) -> Vote:
    if len(df) < 220:
        return Vote("trend_following", 0, weight)
    fast = df["close"].ewm(span=50, adjust=False).mean().iloc[-1]
    slow = df["close"].ewm(span=200, adjust=False).mean().iloc[-1]
    score = 1 if fast > slow else -1
    return Vote("trend_following", score, weight)


def _rsi_vote(df: pd.DataFrame, weight: float = 0.8) -> Vote:
    if len(df) < 30:
        return Vote("rsi_reversion", 0, weight)
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    value = rsi.iloc[-1]
    if pd.isna(value):
        return Vote("rsi_reversion", 0, weight)
    if value < 30:
        return Vote("rsi_reversion", 1, weight)
    if value > 70:
        return Vote("rsi_reversion", -1, weight)
    return Vote("rsi_reversion", 0, weight)


def _breakout_vote(df: pd.DataFrame, weight: float = 0.9) -> Vote:
    if len(df) < 50:
        return Vote("breakout", 0, weight)
    lookback_high = df["high"].iloc[-21:-1].max()
    lookback_low = df["low"].iloc[-21:-1].min()
    last_close = df["close"].iloc[-1]
    if last_close > lookback_high:
        return Vote("breakout", 1, weight)
    if last_close < lookback_low:
        return Vote("breakout", -1, weight)
    return Vote("breakout", 0, weight)


def _pullback_vote(df: pd.DataFrame, weight: float = 0.7) -> Vote:
    if len(df) < 80:
        return Vote("pullback", 0, weight)
    latest = df["close"].iloc[-1]
    swing_high = df["high"].iloc[-61:-1].max()
    swing_low = df["low"].iloc[-61:-1].min()
    if swing_high <= swing_low:
        return Vote("pullback", 0, weight)
    span = swing_high - swing_low
    fib_50 = swing_high - (0.5 * span)
    fib_618 = swing_high - (0.618 * span)
    trend = _trend_vote(df).score
    if trend > 0 and fib_618 <= latest <= fib_50:
        return Vote("pullback", 1, weight)
    if trend < 0:
        inv_50 = swing_low + (0.5 * span)
        inv_618 = swing_low + (0.618 * span)
        if inv_50 <= latest <= inv_618:
            return Vote("pullback", -1, weight)
    return Vote("pullback", 0, weight)


def evaluate_timeframe_votes(df: pd.DataFrame) -> dict:
    votes = [_trend_vote(df), _rsi_vote(df), _breakout_vote(df), _pullback_vote(df)]
    weighted_total = sum(v.score * v.weight for v in votes)
    max_abs = sum(v.weight for v in votes)
    normalized = 0.0 if max_abs == 0 else weighted_total / max_abs
    direction = "BUY" if normalized > 0 else "SELL" if normalized < 0 else "HOLD"
    return {
        "votes": [{"name": v.name, "score": v.score, "weight": v.weight} for v in votes],
        "weighted_score": round(weighted_total, 4),
        "normalized_score": round(normalized, 4),
        "direction": direction,
    }


def evaluate_multi_timeframe_strategy(db: Session, instrument: str = "EUR_USD") -> dict:
    base = _load_h1_dataframe(db=db, instrument=instrument)
    if base.empty:
        return {"ready": False, "direction": "HOLD", "confidence": 0.0, "timeframes": {}}
    h1 = evaluate_timeframe_votes(base)
    h4_df = _resample(base, "4h")
    d1_df = _resample(base, "1d")
    h4 = evaluate_timeframe_votes(h4_df) if not h4_df.empty else {"direction": "HOLD", "normalized_score": 0.0, "votes": []}
    d1 = evaluate_timeframe_votes(d1_df) if not d1_df.empty else {"direction": "HOLD", "normalized_score": 0.0, "votes": []}

    # Top-down gating: only allow entry if lower timeframe direction agrees with higher timeframes.
    aligned = h1["direction"] != "HOLD" and h1["direction"] == h4.get("direction") == d1.get("direction")
    if not aligned:
        return {
            "ready": True,
            "direction": "HOLD",
            "confidence": round(abs(h1["normalized_score"]) * 0.5, 4),
            "top_down_aligned": False,
            "timeframes": {"D1": d1, "H4": h4, "H1": h1},
            "normalized_score": 0.0,
        }
    confidence = min(0.99, abs((d1["normalized_score"] + h4["normalized_score"] + h1["normalized_score"]) / 3))
    return {
        "ready": True,
        "direction": h1["direction"],
        "confidence": round(confidence, 4),
        "top_down_aligned": True,
        "timeframes": {"D1": d1, "H4": h4, "H1": h1},
        "normalized_score": round((d1["normalized_score"] + h4["normalized_score"] + h1["normalized_score"]) / 3, 4),
    }
