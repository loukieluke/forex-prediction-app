from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import Base, engine
from app.routers.data import router as data_router
from app.routers.health import router as health_router
from app.routers.signal import router as signal_router
from app.routers.system import router as system_router
from app.routers.trading import router as trading_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.app_name)
origins = [origin.strip() for origin in settings.cors_allow_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(data_router)
app.include_router(signal_router)
app.include_router(trading_router)
app.include_router(system_router)
