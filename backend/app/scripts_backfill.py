import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db import SessionLocal
from app.models import Candle
from app.services.pipeline import ingest_candles


def run_backfill(days: int = 365, chunk_sleep_seconds: int = 15):
    db = SessionLocal()
    try:
        horizon = datetime.now(timezone.utc) - timedelta(days=days)
        while True:
            upserted = ingest_candles(db=db, instrument="EUR_USD", granularity="H1")
            oldest = db.scalars(select(Candle.time).order_by(Candle.time.asc()).limit(1)).first()
            if oldest and oldest <= horizon:
                break
            if upserted == 0:
                break
            time.sleep(chunk_sleep_seconds)
    finally:
        db.close()


if __name__ == "__main__":
    run_backfill()
