from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Candle(Base):
    __tablename__ = "candles"
    __table_args__ = (UniqueConstraint("instrument", "granularity", "time"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    instrument: Mapped[str] = mapped_column(String(32), index=True)
    granularity: Mapped[str] = mapped_column(String(16), index=True)
    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class NewsHeadline(Base):
    __tablename__ = "news_headlines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source: Mapped[str] = mapped_column(String(64), index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    title: Mapped[str] = mapped_column(String(512))
    url: Mapped[str] = mapped_column(String(1024), default="")
    sentiment_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class PredictionLog(Base):
    __tablename__ = "prediction_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    instrument: Mapped[str] = mapped_column(String(32), index=True)
    granularity: Mapped[str] = mapped_column(String(16), index=True)
    signal: Mapped[str] = mapped_column(String(16), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    payload_json: Mapped[str] = mapped_column(String(4096))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class TradeLog(Base):
    __tablename__ = "trade_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    instrument: Mapped[str] = mapped_column(String(32), index=True)
    direction: Mapped[str] = mapped_column(String(16))
    units: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float)
    auto_trade: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="submitted")
    broker_response_json: Mapped[str] = mapped_column(String(8192), default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
