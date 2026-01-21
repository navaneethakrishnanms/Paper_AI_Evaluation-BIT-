"""
AI Exam Evaluation System - FastAPI Backend

Production-ready system for evaluating student exam papers using OCR and LLM.
"""
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .api import upload, status, result


# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown tasks."""
    # Startup: Create necessary directories
    config_dir = Path(__file__).parent / "config"
    
    # Load paths from config
    import yaml
    config_path = config_dir / "config.yaml"
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        uploads_dir = Path(config.get("paths", {}).get("uploads", "./uploads"))
        outputs_dir = Path(config.get("paths", {}).get("outputs", "./outputs"))
        
        uploads_dir.mkdir(parents=True, exist_ok=True)
        outputs_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"[DIR] Uploads directory: {uploads_dir.absolute()}")
        print(f"[DIR] Outputs directory: {outputs_dir.absolute()}")
    
    # Check for API keys
    if not os.getenv("GROQ_API_KEY"):
        print("[WARNING] GROQ_API_KEY not set in environment!")
    else:
        print("[OK] GROQ_API_KEY loaded (Maverick OCR)")
    
    if not os.getenv("FIREWORKS_API_KEY"):
        print("[WARNING] FIREWORKS_API_KEY not set in environment!")
    else:
        print("[OK] FIREWORKS_API_KEY loaded (Qwen3-VL Evaluation)")
    
    print("[STARTED] AI Exam Evaluation System started!")
    
    yield
    
    # Shutdown
    print("[SHUTDOWN] AI Exam Evaluation System shutting down...")


# Create FastAPI application
app = FastAPI(
    title="AI Exam Evaluation System",
    description="Production-ready system for evaluating student exam papers using OCR and LLM",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(status.router, prefix="/api", tags=["Status"])
app.include_router(result.router, prefix="/api", tags=["Result"])


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "status": "healthy",
        "service": "AI Exam Evaluation System",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}
