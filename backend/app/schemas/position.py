from __future__ import annotations

from pydantic import BaseModel


class RebuildRequest(BaseModel):
    exchange: str = "binance"
    start_date: str
    end_date: str
    threads: int = 5
    max_retries: int = 3


class RebuildResponse(BaseModel):
    file_path: str
    exchange: str
    start_date: str
    end_date: str
