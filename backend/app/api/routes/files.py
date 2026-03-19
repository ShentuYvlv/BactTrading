from fastapi import APIRouter, Query

from backend.app.services.data_files import (
    get_data_files,
    get_latest_data_file,
    load_symbols_from_csv,
    resolve_data_file,
)


router = APIRouter()


@router.get("/data-files")
def list_data_files() -> dict:
    latest_file = get_latest_data_file()
    return {
        "items": get_data_files(),
        "latest": str(latest_file) if latest_file else None,
    }


@router.get("/symbols")
def list_symbols(
    data_file: str | None = Query(default=None),
    min_trades: int = Query(default=5, ge=1),
) -> dict:
    path = resolve_data_file(data_file)
    if path is None:
        return {"items": [], "total": 0}

    symbol_counts = load_symbols_from_csv(path, min_trades=min_trades)
    items = [
        {
            "symbol": symbol,
            "trade_count": trade_count,
        }
        for symbol, trade_count in symbol_counts.items()
    ]
    return {
        "items": items,
        "total": len(items),
        "data_file": str(path),
    }
