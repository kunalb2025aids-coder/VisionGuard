import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.app.models.database import init_db
from backend.app.routers import (
    health_router,
    dashboard_router,
    detections_router,
    maintenance_router,
    alerts_router,
    reports_router,
    camera_router,
    assets_router,
    telemetry_router,
    predictions_router,
    copilot_router,
    ws_router,
)

# Configure Structured Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("visionguard.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing VisionGuard AI 2.0 Database...")
    init_db()
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("results", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    logger.info("VisionGuard AI 2.0 startup complete.")
    yield
    logger.info("VisionGuard AI 2.0 shutdown complete.")

app = FastAPI(
    title="VisionGuard AI 2.0",
    description=(
        "Computer Vision & ML-Driven Industrial AI Platform for Conveyor Belt "
        "Defect Detection, Predictive Maintenance, and Sensor Monitoring."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS - restrict in production via env
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers - existing (preserved)
app.include_router(health_router)
app.include_router(dashboard_router)
app.include_router(detections_router)
app.include_router(maintenance_router)
app.include_router(alerts_router)
app.include_router(reports_router)
app.include_router(camera_router)

# Include Routers - new v2.0
app.include_router(assets_router)
app.include_router(telemetry_router)
app.include_router(predictions_router)
app.include_router(copilot_router)
app.include_router(ws_router)  # WebSocket /ws/visionguard

# Mount Static Files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/results", StaticFiles(directory="results"), name="results")
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")

@app.get("/")
def read_root():
    index_path = os.path.join("frontend", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"message": "VisionGuard AI 2.0 API Service Running. Access /docs or /frontend."})

@app.get("/api/version")
def api_version():
    return {"version": "2.0.0", "name": "VisionGuard AI", "description": "Industrial AI Platform"}
