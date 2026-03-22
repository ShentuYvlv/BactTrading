from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_host: str = "0.0.0.0"
    app_port: int = 8051
    app_debug: bool = True
    app_use_reloader: bool = False

    exchange_proxy_url: str | None = None
    ccxt_enable_rate_limit: bool = True
    ccxt_timeout_ms: int = 60000
    ccxt_recv_window: int = 60000
    ccxt_verify_ssl: bool = False
    ccxt_user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )

    binance_api_key: str | None = None
    binance_api_secret: str | None = None
    binance_default_type: str = "future"

    okx_api_key: str | None = None
    okx_api_secret: str | None = None
    okx_api_passphrase: str | None = None
    okx_default_type: str = "swap"

    chart_default_symbol: str = "NXPC/USDT:USDT"
    chart_fallback_symbol: str = "NXPC/USDT:USDT"
    chart_default_timeframe: str = "30m"
    chart_default_start_date: date | None = None
    chart_default_end_date: date | None = None
    chart_min_trades: int = 5

    position_default_exchange: str = "binance"
    position_default_threads: int = 5
    position_max_retries: int = 3

    @property
    def data_dir(self) -> Path:
        return BASE_DIR / "data"

    @property
    def cache_dir(self) -> Path:
        return BASE_DIR / "cache"

    @property
    def frontend_dist_dir(self) -> Path:
        return BASE_DIR / "frontend" / "dist"

    @property
    def frontend_index_file(self) -> Path:
        return self.frontend_dist_dir / "index.html"

    @property
    def chart_defaults(self) -> dict[str, str | int]:
        today = datetime.now().date()
        default_start = self.chart_default_start_date or (today - timedelta(days=1))
        default_end = self.chart_default_end_date or today
        return {
            "symbol": self.chart_default_symbol,
            "fallback_symbol": self.chart_fallback_symbol,
            "timeframe": self.chart_default_timeframe,
            "start_date": default_start.isoformat(),
            "end_date": default_end.isoformat(),
            "min_trades": self.chart_min_trades,
        }


settings = Settings()
