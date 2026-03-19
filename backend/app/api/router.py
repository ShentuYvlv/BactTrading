from fastapi import APIRouter

from backend.app.api.routes import chart, config, files, health, positions


api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(config.router, prefix="/config", tags=["config"])
api_router.include_router(files.router, tags=["files"])
api_router.include_router(chart.router, prefix="/chart", tags=["chart"])
api_router.include_router(positions.router, prefix="/positions", tags=["positions"])
