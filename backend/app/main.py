from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api import api_router
from backend.app.core.config import settings
from backend.app.core.logging import configure_logging


configure_logging()

app = FastAPI(
    title="BactTrading API",
    version="2.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router, prefix="/api")

assets_dir = settings.frontend_dist_dir / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/")
def serve_index():
    if settings.frontend_index_file.exists():
        return FileResponse(settings.frontend_index_file)
    return JSONResponse(
        status_code=503,
        content={
            "message": "前端尚未构建，请先执行 frontend 构建。",
            "expected_file": str(settings.frontend_index_file),
        },
    )


@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    if full_path.startswith("api/"):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    candidate = settings.frontend_dist_dir / full_path
    if candidate.exists() and candidate.is_file():
        return FileResponse(candidate)
    if settings.frontend_index_file.exists():
        return FileResponse(settings.frontend_index_file)
    return JSONResponse(status_code=404, content={"detail": "前端资源不存在"})
