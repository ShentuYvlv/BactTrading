from fastapi import APIRouter

from backend.app.core.config import settings
from backend.app.core.constants import TIMEFRAME_OPTIONS
from backend.app.schemas.chart import ConfigResponse


router = APIRouter()


@router.get("", response_model=ConfigResponse)
def get_config() -> ConfigResponse:
    return ConfigResponse(
        chart_defaults=settings.chart_defaults,
        timeframe_options=TIMEFRAME_OPTIONS,
        app_debug=settings.app_debug,
        exchange_options=[
            {"label": "Binance", "value": "binance"},
            {"label": "OKX", "value": "okx"},
        ],
    )
