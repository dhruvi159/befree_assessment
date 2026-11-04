"""FastAPI main application entry point for StatementIQ."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import init_db
from app.routers import statements, dashboard, rules, model, health, settings as settings_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting StatementIQ backend...")

    # Initialize database
    init_db()
    logger.info("Database initialized")

    # Pre-load ML model if available
    from app.classification.ml_classifier import load_model, is_model_available
    load_model()

    # Train model on real statement transactions if available in database
    if not is_model_available():
        try:
            from ml.train import train_on_real_data
            train_on_real_data()
        except Exception as e:
            logger.info("No real statement transactions available yet for ML training.")

    yield

    logger.info("StatementIQ backend shutting down")


app = FastAPI(
    title="StatementIQ API",
    description="Intelligent Bank Statement Processing API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please check server logs."},
    )


# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
app.include_router(statements.router, prefix="/api", tags=["statements"])
app.include_router(rules.router, prefix="/api", tags=["rules"])
app.include_router(model.router, prefix="/api", tags=["model"])
app.include_router(settings_router.router, prefix="/api", tags=["settings"])


# Serve frontend static assets if dist exists (e.g. in Docker / Production)
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

dist_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if not dist_dir.exists():
    dist_dir = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend_spa(full_path: str):
        if full_path.startswith("api"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        target_file = dist_dir / full_path
        if target_file.exists() and target_file.is_file():
            return FileResponse(target_file)
        return FileResponse(dist_dir / "index.html")
else:
    @app.get("/")
    def root():
        return {"message": "StatementIQ API v1.0.0", "docs": "/docs"}

