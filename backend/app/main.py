from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import BACKEND_DIR, settings
from .database import Base, SessionLocal, engine
from .routers import cameras, classifications, device, hardware_events
from .predictor import model_status
from .schemas import ModelStatusResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        cameras.restore_orientations(db)
    app.state.backend_dir = BACKEND_DIR
    try:
        yield
    finally:
        cameras.manager.shutdown()


app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description=(
        "Phân loại 5 lớp cam bằng EfficientNet-B0 V3, ánh xạ về 3 loại/khay theo AI_handover."
    ),
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
settings.upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
app.include_router(classifications.router)
app.include_router(device.router)
app.include_router(hardware_events.router)
app.include_router(cameras.router)


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/model", response_model=ModelStatusResponse, tags=["model"])
def ai_model_status():
    return model_status()

