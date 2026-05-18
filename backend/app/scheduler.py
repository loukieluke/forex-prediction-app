import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from app.db import SessionLocal
from app.services.alerts import emit_alert
from app.tasks import run_pipeline_cycle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = BlockingScheduler()


@scheduler.scheduled_job("interval", minutes=60)
def scheduled_forex_job():
    db = SessionLocal()
    try:
        result = run_pipeline_cycle(db=db, instrument="EUR_USD", granularity="H1", units=1000)
        logger.info("pipeline_cycle=%s", result)
    except Exception:
        logger.exception("scheduled pipeline failed")
        emit_alert("Scheduled forex pipeline failed. Check worker logs.")
    finally:
        db.close()


if __name__ == "__main__":
    scheduler.start()
