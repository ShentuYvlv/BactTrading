from __future__ import annotations

from pydantic import BaseModel, Field


class EmaSettings(BaseModel):
    period: int = Field(default=20, ge=1, le=500)


class BollingerSettings(BaseModel):
    period: int = Field(default=20, ge=1, le=500)
    std_dev: float = Field(default=2.0, gt=0, le=10)


class RsiSettings(BaseModel):
    period: int = Field(default=14, ge=1, le=500)


class MacdSettings(BaseModel):
    fast_period: int = Field(default=12, ge=1, le=500)
    slow_period: int = Field(default=26, ge=1, le=500)
    signal_period: int = Field(default=9, ge=1, le=500)


class IndicatorSettings(BaseModel):
    ema: EmaSettings = Field(default_factory=EmaSettings)
    bollinger: BollingerSettings = Field(default_factory=BollingerSettings)
    rsi: RsiSettings = Field(default_factory=RsiSettings)
    macd: MacdSettings = Field(default_factory=MacdSettings)


class ChartLoadRequest(BaseModel):
    symbol: str
    timeframe: str
    start_date: str
    end_date: str
    data_file: str | None = None
    exchange: str | None = None
    indicator_settings: IndicatorSettings = Field(default_factory=IndicatorSettings)


class LoadMoreRequest(BaseModel):
    symbol: str
    timeframe: str
    last_timestamp: int
    candles_to_load: int = 1000
    exchange: str | None = None


class SummaryResponse(BaseModel):
    time_range: str
    data_source: str
    file_name: str | None = None
    candle_count: int
    position_count: int


class ChartLoadResponse(BaseModel):
    chart: dict
    positions: list[dict]
    summary: SummaryResponse
    symbol: str
    timeframe: str
    exchange: str
    indicator_settings: IndicatorSettings


class ConfigResponse(BaseModel):
    chart_defaults: dict
    timeframe_options: list[dict]
    app_debug: bool
    exchange_options: list[dict]
