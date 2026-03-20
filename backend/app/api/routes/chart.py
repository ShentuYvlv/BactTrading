from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException

from backend.app.core.constants import TIMEFRAME_INCREMENT_MS
from backend.app.schemas.chart import ChartLoadRequest, ChartLoadResponse, LoadMoreRequest, SummaryResponse
from backend.app.services.chart import fetch_ohlcv_data, load_more_ohlcv, prepare_chart_payload
from backend.app.services.data_files import infer_exchange_name, load_positions_from_csv, resolve_data_file
from backend.app.services.positions import fetch_trades, merge_trades_to_positions, positions_df_to_chart_positions


router = APIRouter()


@router.post("/load", response_model=ChartLoadResponse)
def load_chart_data(request: ChartLoadRequest) -> ChartLoadResponse:
    exchange_name = request.exchange or infer_exchange_name(request.data_file)
    since_ms, until_ms = _date_range_to_ms(request.start_date, request.end_date)

    chart_frame = fetch_ohlcv_data(
        exchange_name=exchange_name,
        symbol=request.symbol,
        timeframe=request.timeframe,
        since=since_ms,
        until=until_ms,
        indicator_settings=request.indicator_settings,
    )
    if chart_frame.empty:
        raise HTTPException(status_code=404, detail="未获取到K线数据")

    positions = _load_positions(
        exchange_name=exchange_name,
        data_file=request.data_file,
        symbol=request.symbol,
        since_ms=since_ms,
        until_ms=until_ms,
    )
    data_file_path = resolve_data_file(request.data_file)

    return ChartLoadResponse(
        chart=prepare_chart_payload(chart_frame),
        positions=positions,
        summary=SummaryResponse(
            time_range=f"{request.start_date} -> {request.end_date}",
            data_source="csv" if data_file_path else "exchange",
            file_name=data_file_path.name if data_file_path else None,
            candle_count=len(chart_frame),
            position_count=len(positions),
        ),
        symbol=request.symbol,
        timeframe=request.timeframe,
        exchange=exchange_name,
        indicator_settings=request.indicator_settings,
    )


@router.post("/load-more")
def load_more_chart_data(request: LoadMoreRequest) -> dict:
    exchange_name = request.exchange or "binance"
    timeframe_increment_ms = TIMEFRAME_INCREMENT_MS.get(request.timeframe)
    if timeframe_increment_ms is None:
        raise HTTPException(status_code=400, detail="不支持的周期")

    return load_more_ohlcv(
        exchange_name=exchange_name,
        symbol=request.symbol,
        timeframe=request.timeframe,
        last_timestamp=request.last_timestamp,
        candles_to_load=request.candles_to_load,
        timeframe_increment_ms=timeframe_increment_ms,
    )


def _load_positions(
    exchange_name: str,
    data_file: str | None,
    symbol: str,
    since_ms: int,
    until_ms: int,
) -> list[dict]:
    data_file_path = resolve_data_file(data_file)
    if data_file_path:
        positions = load_positions_from_csv(
            data_file_path,
            symbol=symbol,
            since_ms=since_ms,
            until_ms=until_ms,
        )
        if positions:
            return positions

    trades_df = fetch_trades(
        exchange_name=exchange_name,
        symbol=symbol,
        since=since_ms,
        until=until_ms,
    )
    if trades_df.empty:
        return []

    positions_df = merge_trades_to_positions(trades_df)
    return positions_df_to_chart_positions(positions_df)


def _date_range_to_ms(start_date: str, end_date: str) -> tuple[int, int]:
    try:
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date) + timedelta(days=1) - timedelta(milliseconds=1)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="日期格式必须是 YYYY-MM-DD") from exc
    return int(start_dt.timestamp() * 1000), int(end_dt.timestamp() * 1000)
