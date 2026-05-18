"""
MedBridge Ukraine — FastAPI Application Entry Point

AI-Assisted Medical Continuity Reconstruction Platform
for War-Displaced Refugees & Humanitarian Healthcare Support

Powered by Gemma 4 (multimodal) + Google ADK (agent orchestration)
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

from database.init_db import init_db
from routers import upload, pipeline, passport, export, pages


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    # ── Startup ──────────────────────────────────────────────────────
    init_db()
    print("[DB] Database initialised")

    upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
    os.makedirs(upload_dir, exist_ok=True)
    os.makedirs("./data", exist_ok=True)
    print(f"[Files] Upload directory ready: {upload_dir}")

    print("[MedBridge] 🇺🇦 MedBridge Ukraine starting...")
    print("[MedBridge] Powered by Gemma 4 multimodal + Google ADK")

    yield

    print("[MedBridge] Shutting down...")


app = FastAPI(
    title="MedBridge Ukraine API",
    description=(
        "AI-Assisted Medical Continuity Reconstruction Platform "
        "for War-Displaced Refugees. Powered by Gemma 4 multimodal intelligence."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files ──────────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

upload_dir = os.getenv("UPLOAD_DIR", "./uploads")
os.makedirs(upload_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

# ── API Routers ───────────────────────────────────────────────────────
app.include_router(upload.router,    prefix="/api/upload",    tags=["Upload"])
app.include_router(pipeline.router,  prefix="/api/pipeline",  tags=["Pipeline"])
app.include_router(passport.router,  prefix="/api/passport",  tags=["Passport"])
app.include_router(export.router,    prefix="/api/export",    tags=["Export"])

# ── Page Routers (HTML) ────────────────────────────────────────────────
app.include_router(pages.router)


# ── Health check ──────────────────────────────────────────────────────
@app.get("/api/health", tags=["Health"])
async def health():
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "MedBridge Ukraine",
        "version": "1.0.0",
        "model": os.getenv("GEMMA_MODEL", "gemma-4-31b-it"),
        "agent_model": os.getenv("AGENT_MODEL", "gemini-2.0-flash-exp"),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        reload=False,
        log_level="info",
    )
