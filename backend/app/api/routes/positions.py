from fastapi import APIRouter, HTTPException

from backend.app.schemas.position import RebuildRequest, RebuildResponse
from backend.app.services.rebuild import run_rebuild


router = APIRouter()


@router.post("/rebuild", response_model=RebuildResponse)
def rebuild_positions(request: RebuildRequest) -> RebuildResponse:
    try:
        return RebuildResponse(**run_rebuild(request))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
