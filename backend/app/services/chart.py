from __future__ import annotations

import logging
import time
from datetime import datetime

import pandas as pd

from backend.app.core.config import settings
from backend.app.schemas.chart import IndicatorSettings
from backend.app.services.cache import append_to_cache, get_cache_key, get_cached_data, save_to_cache
from backend.app.services.exchange import create_exchange


logger = logging.getLogger(__name__)


def add_technical_indicators(df: pd.DataFrame, indicator_settings: IndicatorSettings | None = None) -> pd.DataFrame:
    indicator_settings = indicator_settings or IndicatorSettings()
    df = df.copy()
    ema_period = indicator_settings.ema.period
    bollinger_period = indicator_settings.bollinger.period
    bollinger_std_dev = indicator_settings.bollinger.std_dev
    rsi_period = indicator_settings.rsi.period
    macd_fast = indicator_settings.macd.fast_period
    macd_slow = indicator_settings.macd.slow_period
    macd_signal = indicator_settings.macd.signal_period

    df["ema20"] = df["close"].ewm(span=ema_period, adjust=False).mean()

    delta = df["close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=rsi_period).mean()
    avg_loss = loss.rolling(window=rsi_period).mean()

    for i in range(rsi_period, len(df)):
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (rsi_period - 1) + gain.iloc[i]) / rsi_period
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (rsi_period - 1) + loss.iloc[i]) / rsi_period

    rs = avg_gain / avg_loss
    df["rsi"] = 100 - (100 / (1 + rs))

    df["sma20"] = df["close"].rolling(window=bollinger_period).mean()
    df["std20"] = df["close"].rolling(window=bollinger_period).std()
    df["upper_band"] = df["sma20"] + (df["std20"] * bollinger_std_dev)
    df["lower_band"] = df["sma20"] - (df["std20"] * bollinger_std_dev)

    df["ema12"] = df["close"].ewm(span=macd_fast, adjust=False).mean()
    df["ema26"] = df["close"].ewm(span=macd_slow, adjust=False).mean()
    df["macd"] = df["ema12"] - df["ema26"]
    df["signal"] = df["macd"].ewm(span=macd_signal, adjust=False).mean()
    df["histogram"] = df["macd"] - df["signal"]

    return df.fillna(0)


def prepare_chart_payload(df: pd.DataFrame) -> dict:
    frame = df.copy()
    frame["time"] = frame["timestamp"].map(lambda ts: int(pd.Timestamp(ts).timestamp()))
    return {
        "candlestick": frame[["time", "open", "high", "low", "close"]].to_dict("records"),
        "volume": frame[["time", "volume"]].to_dict("records"),
        "ema20": frame[["time", "ema20"]].rename(columns={"ema20": "value"}).to_dict("records"),
        "rsi": frame[["time", "rsi"]].rename(columns={"rsi": "value"}).to_dict("records"),
        "upper_band": frame[["time", "upper_band"]].rename(columns={"upper_band": "value"}).to_dict("records"),
        "middle_band": frame[["time", "sma20"]].rename(columns={"sma20": "value"}).to_dict("records"),
        "lower_band": frame[["time", "lower_band"]].rename(columns={"lower_band": "value"}).to_dict("records"),
        "macd": frame[["time", "macd"]].rename(columns={"macd": "value"}).to_dict("records"),
        "signal": frame[["time", "signal"]].rename(columns={"signal": "value"}).to_dict("records"),
        "histogram": frame[["time", "histogram"]].rename(columns={"histogram": "value"}).to_dict("records"),
    }


def normalize_symbol(exchange, symbol: str) -> str:
    exchange.load_markets()
    if symbol in exchange.markets:
        return symbol
    if ":" not in symbol and symbol.endswith("USDT"):
        normalized = f"{symbol}:USDT"
        if normalized in exchange.markets:
            return normalized
    if settings.chart_fallback_symbol in exchange.markets:
        return settings.chart_fallback_symbol
    return symbol


def fetch_ohlcv_data(
    exchange_name: str,
    symbol: str,
    timeframe: str,
    since: int | None,
    until: int | None,
    indicator_settings: IndicatorSettings | None = None,
) -> pd.DataFrame:
    exchange = create_exchange(exchange_name, require_auth=False)
    symbol = normalize_symbol(exchange, symbol)
    indicator_settings = indicator_settings or IndicatorSettings()
    indicator_signature = (
        f"ema{indicator_settings.ema.period}_"
        f"bb{indicator_settings.bollinger.period}_{indicator_settings.bollinger.std_dev}_"
        f"rsi{indicator_settings.rsi.period}_"
        f"macd{indicator_settings.macd.fast_period}_{indicator_settings.macd.slow_period}_{indicator_settings.macd.signal_period}"
    )
    cache_key = get_cache_key(symbol, timeframe, since, until, indicator_signature=indicator_signature)
    cached = get_cached_data(cache_key)
    if cached is not None and not cached.empty:
        return cached

    all_ohlcv = []
    batch_limit = 1000
    if since and until:
        try:
            all_ohlcv = exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=batch_limit,
                params={"startTime": since, "endTime": until},
            )
        except Exception:
            current_since = since
            while current_since < until:
                batch = exchange.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=batch_limit, params={"since": current_since})
                if not batch:
                    break
                batch = [candle for candle in batch if candle[0] <= until]
                all_ohlcv.extend(batch)
                if len(batch) < batch_limit:
                    break
                current_since = batch[-1][0] + 1
                time.sleep(0.5)
    else:
        all_ohlcv = exchange.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=batch_limit)

    if not all_ohlcv:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

    df = pd.DataFrame(all_ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = add_technical_indicators(df, indicator_settings=indicator_settings)
    save_to_cache(cache_key, df)
    return df


def load_more_ohlcv(
    exchange_name: str,
    symbol: str,
    timeframe: str,
    last_timestamp: int,
    candles_to_load: int,
    timeframe_increment_ms: int,
) -> dict:
    since = last_timestamp * 1000 + 1 if last_timestamp < 10_000_000_000 else last_timestamp + 1
    until = min(since + timeframe_increment_ms * candles_to_load, int(datetime.now().timestamp() * 1000))
    exchange = create_exchange(exchange_name, require_auth=False)
    symbol = normalize_symbol(exchange, symbol)
    ohlcv = exchange.fetch_ohlcv(symbol=symbol, timeframe=timeframe, limit=1000, params={"startTime": since, "endTime": until})
    if not ohlcv:
        return {"chart": None, "added": 0}

    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = add_technical_indicators(df)
    append_to_cache(symbol, timeframe, df)
    payload = prepare_chart_payload(df)
    added = max(len(payload["candlestick"]) - 1, 0)
    for key in payload:
        payload[key] = payload[key][1:]
    return {"chart": payload, "added": added}
