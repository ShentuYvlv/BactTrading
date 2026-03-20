from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from backend.app.core.config import settings


logger = logging.getLogger(__name__)


def resolve_data_file(data_file: str | None) -> Path | None:
    if not data_file:
        return get_latest_data_file()

    path = Path(data_file)
    if not path.is_absolute():
        path = settings.data_dir / data_file

    return path if path.exists() else None


def get_data_files() -> list[dict]:
    data_dir = settings.data_dir
    if not data_dir.exists():
        logger.warning("data目录不存在: %s", data_dir)
        return []

    files: list[dict] = []
    for file_path in data_dir.glob("*.csv"):
        modified = datetime.fromtimestamp(file_path.stat().st_mtime)
        files.append(
            {
                "filename": file_path.name,
                "path": str(file_path),
                "size": f"{file_path.stat().st_size / (1024 * 1024):.2f} MB",
                "modified": modified.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    return sorted(files, key=lambda item: item["modified"], reverse=True)


def get_latest_data_file() -> Path | None:
    files = get_data_files()
    if not files:
        return None
    return Path(files[0]["path"])


def load_symbols_from_csv(csv_file_path: str | Path, min_trades: int | None = None) -> dict[str, int]:
    min_trades = settings.chart_min_trades if min_trades is None else min_trades
    path = Path(csv_file_path)
    if not path.exists():
        logger.error("CSV文件不存在: %s", path)
        return {}

    try:
        df = pd.read_csv(path)
        required_columns = {"交易对", "交易次数"}
        if not required_columns.issubset(df.columns):
            logger.error("CSV文件缺少必要的列: %s", sorted(required_columns))
            return {}

        symbol_counts: dict[str, int] = {}
        for _, row in df.iterrows():
            symbol = row["交易对"]
            symbol_counts[symbol] = symbol_counts.get(symbol, 0) + int(row["交易次数"])

        filtered = {symbol: count for symbol, count in symbol_counts.items() if count >= min_trades}
        return dict(sorted(filtered.items(), key=lambda item: item[1], reverse=True))
    except Exception as exc:
        logger.exception("读取CSV文件失败: %s", exc)
        return {}


def load_positions_from_csv(
    csv_file_path: str | Path,
    symbol: str | None = None,
    since_ms: int | None = None,
    until_ms: int | None = None,
) -> list[dict]:
    path = Path(csv_file_path)
    if not path.exists():
        logger.error("CSV文件不存在: %s", path)
        return []

    try:
        df = pd.read_csv(path)
        if symbol:
            df = df[df["交易对"] == symbol]

        if df.empty:
            return []

        positions_data: list[dict] = []
        for index, row in df.iterrows():
            try:
                side = "long" if row["方向"] == "多头" else "short"

                if pd.notna(row.get("原始开仓时间戳")):
                    open_timestamp = int(row["原始开仓时间戳"]) // 1000
                else:
                    open_time_dt = pd.to_datetime(row["开仓时间"])
                    open_timestamp = int((open_time_dt - pd.Timedelta(hours=8)).timestamp())

                if "状态" in row and row["状态"] != "已平仓":
                    close_timestamp = None
                    close_time_formatted = "持仓中"
                elif pd.notna(row.get("原始平仓时间戳")):
                    close_timestamp = int(row["原始平仓时间戳"]) // 1000
                    close_time_formatted = row["平仓时间"]
                elif pd.notna(row.get("平仓时间")):
                    close_time_dt = pd.to_datetime(row["平仓时间"])
                    close_timestamp = int((close_time_dt - pd.Timedelta(hours=8)).timestamp())
                    close_time_formatted = row["平仓时间"]
                else:
                    close_timestamp = None
                    close_time_formatted = "持仓中"

                profit = float(row["PnL"]) if pd.notna(row.get("PnL")) else 0.0
                positions_data.append(
                    {
                        "position_id": str(row["仓位ID"]) if "仓位ID" in row else f"pos-{index}",
                        "side": side,
                        "open_time": open_timestamp,
                        "close_time": close_timestamp,
                        "open_price": float(row["开仓价格"]),
                        "close_price": float(row["平仓价格"]) if pd.notna(row.get("平仓价格")) else None,
                        "amount": float(row["数量"]) if pd.notna(row.get("数量")) else 0.0,
                        "profit": profit,
                        "open_time_formatted": row["开仓时间"],
                        "close_time_formatted": close_time_formatted,
                        "is_profit": profit >= 0,
                        "is_open": close_timestamp is None,
                    }
                )
            except Exception as exc:
                logger.error("处理仓位CSV记录失败: %s", exc)
                continue

        if since_ms is not None or until_ms is not None:
            lower_bound = (since_ms // 1000) if since_ms is not None else None
            upper_bound = (until_ms // 1000) if until_ms is not None else None

            def overlaps_range(position: dict) -> bool:
                open_time = position["open_time"]
                close_time = position["close_time"] if position["close_time"] is not None else open_time
                if lower_bound is not None and close_time < lower_bound:
                    return False
                if upper_bound is not None and open_time > upper_bound:
                    return False
                return True

            positions_data = [position for position in positions_data if overlaps_range(position)]

        return positions_data
    except Exception as exc:
        logger.exception("加载仓位CSV失败: %s", exc)
        return []


def infer_exchange_name(data_file: str | None, default_exchange: str = "binance") -> str:
    if not data_file:
        return default_exchange

    file_name = Path(data_file).name.lower()
    if file_name.startswith("okx_"):
        return "okx"
    if file_name.startswith("binance_"):
        return "binance"
    return default_exchange
