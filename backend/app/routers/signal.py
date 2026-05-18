import shutil
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.schemas import SignalRequest, SignalResponse
from app.services.modeling import train_model, versioned_artifact_name
from app.services.pipeline import build_signal, training_frame_from_db

router = APIRouter(prefix="/api/signal", tags=["signal"])


@router.get("/latest", response_model=SignalResponse)
def latest_signal(instrument: str = "EUR_USD", granularity: str = "H1", db: Session = Depends(get_db)):
    return build_signal(db=db, instrument=instrument, granularity=granularity)


@router.post("", response_model=SignalResponse)
def signal_from_request(payload: SignalRequest, db: Session = Depends(get_db)):
    return build_signal(db=db, instrument=payload.instrument, granularity=payload.granularity)


@router.post("/train")
def train_signal_model(instrument: str = "EUR_USD", granularity: str = "H1", db: Session = Depends(get_db)):
    frame = training_frame_from_db(db=db, instrument=instrument, granularity=granularity)
    if frame.empty:
        return {"status": "no_data"}
    artifact = versioned_artifact_name()
    result = train_model(frame, artifact_path=artifact)
    latest = Path(settings.model_path)
    latest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(result["artifact_path"], latest)
    return {
        "status": "ok",
        "artifact_path": result["artifact_path"],
        "latest_path": str(latest),
        "metrics": result["report"],
    }
