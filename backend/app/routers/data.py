from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Candle, NewsHeadline
from app.schemas import CandleOut
from app.services.pipeline import ingest_candles, ingest_news

router = APIRouter(prefix="/api/data", tags=["data"])


@router.post("/ingest/candles")
def ingest_candles_endpoint(instrument: str = "EUR_USD", granularity: str = "H1", db: Session = Depends(get_db)):
    count = ingest_candles(db=db, instrument=instrument, granularity=granularity)
    return {"status": "ok", "rows_upserted": count}


@router.post("/ingest/news")
def ingest_news_endpoint(db: Session = Depends(get_db)):
    count = ingest_news(db=db)
    return {"status": "ok", "rows_inserted": count}


@router.get("/candles", response_model=list[CandleOut])
def list_candles(instrument: str = "EUR_USD", granularity: str = "H1", limit: int = 200, db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Candle)
        .where(Candle.instrument == instrument, Candle.granularity == granularity)
        .order_by(Candle.time.desc())
        .limit(limit)
    ).all()
    rows = list(reversed(rows))
    return [
        CandleOut(
            instrument=row.instrument,
            granularity=row.granularity,
            time=row.time,
            open=row.open,
            high=row.high,
            low=row.low,
            close=row.close,
            volume=row.volume,
        )
        for row in rows
    ]


@router.get("/news/latest")
def latest_news(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.scalars(select(NewsHeadline).order_by(NewsHeadline.published_at.desc()).limit(limit)).all()
    return [
        {
            "source": row.source,
            "published_at": row.published_at,
            "title": row.title,
            "url": row.url,
            "sentiment_score": row.sentiment_score,
        }
        for row in rows
    ]
