from __future__ import annotations

import hashlib
import logging
import pickle
import threading
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from backend.app.core.config import settings


logger = logging.getLogger(__name__)
settings.cache_dir.mkdir(parents=True, exist_ok=True)
cache_lock = threading.Lock()


def get_cache_key(
    symbol: str,
    timeframe: str,
    since: int | None,
    until: int | None,
    indicator_signature: str = "default",
) -> str:
    clean_symbol = symbol.replace("/", "_").replace(":", "_")
    hash_part = hashlib.md5(f"{since}_{until}_{indicator_signature}".encode()).hexdigest()[:8]
    return f"{clean_symbol}_{timeframe}_{hash_part}"


def get_cached_data(cache_key: str) -> pd.DataFrame | None:
    cache_file = settings.cache_dir / f"{cache_key}.pkl"
    if cache_file.exists():
        file_mod_time = cache_file.stat().st_mtime
        if time.time() - file_mod_time < 24 * 3600:
            try:
                with cache_file.open("rb") as file:
                    return pickle.load(file)
            except Exception as exc:
                logger.error("读取缓存失败: %s", exc)

    main_key = cache_key.rsplit("_", 1)[0] if "_" in cache_key else cache_key
    candidates: list[tuple[Path, float]] = []
    for file_path in settings.cache_dir.glob(f"{main_key}_*.pkl"):
        if time.time() - file_path.stat().st_mtime < 24 * 3600:
            candidates.append((file_path, file_path.stat().st_mtime))

    if candidates:
        candidates.sort(key=lambda item: item[1], reverse=True)
        with candidates[0][0].open("rb") as file:
            return pickle.load(file)

    return None


def save_to_cache(cache_key: str, data: pd.DataFrame) -> None:
    with cache_lock:
        cache_file = settings.cache_dir / f"{cache_key}.pkl"
        with cache_file.open("wb") as file:
            pickle.dump(data, file)


def append_to_cache(symbol: str, timeframe: str, new_data: pd.DataFrame) -> str | None:
    main_key = f"{symbol.replace('/', '_').replace(':', '_')}_{timeframe}"
    candidates: list[tuple[Path, float]] = []
    for file_path in settings.cache_dir.glob(f"{main_key}_*.pkl"):
        candidates.append((file_path, file_path.stat().st_mtime))

    if candidates:
        candidates.sort(key=lambda item: item[1], reverse=True)
        newest_file = candidates[0][0]
        with newest_file.open("rb") as file:
            existing_data = pickle.load(file)

        if not existing_data.empty and not new_data.empty:
            last_timestamp = existing_data["timestamp"].max()
            new_data = new_data[new_data["timestamp"] > last_timestamp]
            if new_data.empty:
                return newest_file.stem

        combined = pd.concat([existing_data, new_data], ignore_index=True).sort_values("timestamp").reset_index(drop=True)
        with cache_lock:
            with newest_file.open("wb") as file:
                pickle.dump(combined, file)
        return newest_file.stem

    cache_key = get_cache_key(
        symbol,
        timeframe,
        int(new_data["timestamp"].min().timestamp() * 1000),
        int(new_data["timestamp"].max().timestamp() * 1000),
    )
    save_to_cache(cache_key, new_data)
    return cache_key


def list_cache_files() -> dict[str, list[dict]]:
    cache_files_by_symbol: dict[str, list[dict]] = {}
    for file_path in settings.cache_dir.glob("*.pkl"):
        parts = file_path.stem.split("_")
        if len(parts) < 3:
            continue

        if len(parts) >= 4 and parts[1] == "USDT":
            symbol = f"{parts[0]}/USDT"
            timeframe = parts[2]
        else:
            symbol = f"{parts[0]}_{parts[1]}".replace("_", "/")
            timeframe = parts[2]

        cache_files_by_symbol.setdefault(symbol, []).append(
            {
                "filename": file_path.name,
                "timeframe": timeframe,
                "size": f"{file_path.stat().st_size / (1024 * 1024):.2f} MB",
                "modified": datetime.fromtimestamp(file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    return dict(sorted(cache_files_by_symbol.items()))
