from __future__ import annotations

import logging
import time

import pandas as pd

from backend.app.services.exchange import create_exchange


logger = logging.getLogger(__name__)


def fetch_trades(exchange_name: str, symbol: str, since: int | None, until: int | None, limit: int = 100) -> pd.DataFrame:
    try:
        exchange = create_exchange(exchange_name, require_auth=True)
    except ValueError:
        return pd.DataFrame()
    if not getattr(exchange, "apiKey", None) or not getattr(exchange, "secret", None):
        return pd.DataFrame()

    exchange.load_markets()
    original_symbol = symbol
    if ":" not in symbol and symbol.endswith("USDT") and exchange.options.get("defaultType") in {"future", "futures"}:
        symbol = f"{symbol}:USDT"
    if symbol not in exchange.markets and original_symbol in exchange.markets:
        symbol = original_symbol

    current_time = int(time.time() * 1000)
    until = until or current_time
    since = since or (until - 30 * 24 * 60 * 60 * 1000)
    seven_days_ms = 7 * 24 * 60 * 60 * 1000

    all_trades = []
    current_since = since
    while current_since < until:
        current_until = min(current_since + seven_days_ms - 1, until)
        params = {
            "startTime": current_since,
            "endTime": current_until,
            "recvWindow": 60000,
        }
        try:
            batch_trades = exchange.fetch_my_trades(symbol=symbol, limit=limit, params=params)
            if batch_trades:
                all_trades.extend(batch_trades)
        except Exception:
            try:
                orders = exchange.fetch_orders(symbol=symbol, limit=limit, params=params)
                for order in orders:
                    if order.get("status") in ["closed", "filled"] and order.get("filled", 0) > 0:
                        all_trades.append(
                            {
                                "id": order.get("id"),
                                "timestamp": order.get("timestamp"),
                                "datetime": order.get("datetime"),
                                "symbol": order.get("symbol"),
                                "side": order.get("side"),
                                "price": order.get("price"),
                                "amount": order.get("filled"),
                                "cost": order.get("cost"),
                                "fee": order.get("fee"),
                                "info": order.get("info"),
                            }
                        )
            except Exception as exc:
                logger.warning("获取交易记录失败: %s", exc)
        current_since = current_until + 1

    if not all_trades:
        return pd.DataFrame()

    df = pd.DataFrame(all_trades)
    if "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.sort_values("timestamp")
    return df


def merge_trades_to_positions(trades_df: pd.DataFrame) -> pd.DataFrame:
    if trades_df.empty:
        return pd.DataFrame()

    trades_df = trades_df.sort_values("timestamp")
    positions = []
    long_position = {"total_amount": 0, "remaining_amount": 0, "total_cost": 0, "trades": [], "open_time": None}
    short_position = {"total_amount": 0, "remaining_amount": 0, "total_cost": 0, "trades": [], "open_time": None}

    for _, trade in trades_df.iterrows():
        side = trade.get("side", "")
        amount = float(trade.get("amount", 0))
        price = float(trade.get("price", 0))
        cost = price * amount
        timestamp = trade.get("timestamp")
        beijing_timestamp = timestamp + pd.Timedelta(hours=8) if pd.notna(timestamp) else timestamp
        trade_info = {
            "timestamp": beijing_timestamp,
            "side": side,
            "amount": amount,
            "price": price,
            "cost": cost,
        }

        if side == "buy":
            if short_position["remaining_amount"] > 0:
                close_amount = min(amount, short_position["remaining_amount"])
                close_trade = trade_info.copy()
                close_trade["amount"] = close_amount
                close_trade["cost"] = close_amount * price
                short_position["trades"].append(close_trade)
                short_position["remaining_amount"] -= close_amount

                if short_position["remaining_amount"] == 0:
                    total_close_cost = sum(t["cost"] for t in short_position["trades"] if t["side"] == "buy")
                    positions.append(
                        {
                            "open_time": short_position["open_time"],
                            "close_time": beijing_timestamp,
                            "side": "short",
                            "open_price": short_position["total_cost"] / short_position["total_amount"] if short_position["total_amount"] else 0,
                            "close_price": total_close_cost / short_position["total_amount"] if short_position["total_amount"] else 0,
                            "amount": short_position["total_amount"],
                            "profit": short_position["total_cost"] - total_close_cost,
                            "trades": short_position["trades"],
                        }
                    )
                    short_position = {"total_amount": 0, "remaining_amount": 0, "total_cost": 0, "trades": [], "open_time": None}
                    remaining_amount = amount - close_amount
                    if remaining_amount > 0:
                        if long_position["open_time"] is None:
                            long_position["open_time"] = beijing_timestamp
                        long_position["total_amount"] += remaining_amount
                        long_position["remaining_amount"] += remaining_amount
                        long_position["total_cost"] += remaining_amount * price
                        open_trade = trade_info.copy()
                        open_trade["amount"] = remaining_amount
                        open_trade["cost"] = remaining_amount * price
                        long_position["trades"].append(open_trade)
            else:
                if long_position["open_time"] is None:
                    long_position["open_time"] = beijing_timestamp
                long_position["total_amount"] += amount
                long_position["remaining_amount"] += amount
                long_position["total_cost"] += cost
                long_position["trades"].append(trade_info)

        elif side == "sell":
            if long_position["remaining_amount"] > 0:
                close_amount = min(amount, long_position["remaining_amount"])
                close_trade = trade_info.copy()
                close_trade["amount"] = close_amount
                close_trade["cost"] = close_amount * price
                long_position["trades"].append(close_trade)
                long_position["remaining_amount"] -= close_amount

                if long_position["remaining_amount"] == 0:
                    total_close_revenue = sum(t["cost"] for t in long_position["trades"] if t["side"] == "sell")
                    positions.append(
                        {
                            "open_time": long_position["open_time"],
                            "close_time": beijing_timestamp,
                            "side": "long",
                            "open_price": long_position["total_cost"] / long_position["total_amount"] if long_position["total_amount"] else 0,
                            "close_price": total_close_revenue / long_position["total_amount"] if long_position["total_amount"] else 0,
                            "amount": long_position["total_amount"],
                            "profit": total_close_revenue - long_position["total_cost"],
                            "trades": long_position["trades"],
                        }
                    )
                    long_position = {"total_amount": 0, "remaining_amount": 0, "total_cost": 0, "trades": [], "open_time": None}
                    remaining_amount = amount - close_amount
                    if remaining_amount > 0:
                        if short_position["open_time"] is None:
                            short_position["open_time"] = beijing_timestamp
                        short_position["total_amount"] += remaining_amount
                        short_position["remaining_amount"] += remaining_amount
                        short_position["total_cost"] += remaining_amount * price
                        open_trade = trade_info.copy()
                        open_trade["amount"] = remaining_amount
                        open_trade["cost"] = remaining_amount * price
                        short_position["trades"].append(open_trade)
            else:
                if short_position["open_time"] is None:
                    short_position["open_time"] = beijing_timestamp
                short_position["total_amount"] += amount
                short_position["remaining_amount"] += amount
                short_position["total_cost"] += cost
                short_position["trades"].append(trade_info)

    if long_position["remaining_amount"] > 0:
        last_price = trades_df["price"].iloc[-1] if "price" in trades_df.columns else 0
        positions.append(
            {
                "open_time": long_position["open_time"],
                "close_time": None,
                "side": "long",
                "open_price": long_position["total_cost"] / long_position["total_amount"] if long_position["total_amount"] else 0,
                "close_price": last_price,
                "amount": long_position["total_amount"],
                "profit": (last_price * long_position["remaining_amount"]) - long_position["total_cost"],
                "trades": long_position["trades"],
                "is_open": True,
            }
        )

    if short_position["remaining_amount"] > 0:
        last_price = trades_df["price"].iloc[-1] if "price" in trades_df.columns else 0
        positions.append(
            {
                "open_time": short_position["open_time"],
                "close_time": None,
                "side": "short",
                "open_price": short_position["total_cost"] / short_position["total_amount"] if short_position["total_amount"] else 0,
                "close_price": last_price,
                "amount": short_position["total_amount"],
                "profit": short_position["total_cost"] - (last_price * short_position["remaining_amount"]),
                "trades": short_position["trades"],
                "is_open": True,
            }
        )

    return pd.DataFrame(positions) if positions else pd.DataFrame()


def positions_df_to_chart_positions(positions_df: pd.DataFrame) -> list[dict]:
    if positions_df.empty:
        return []

    chart_positions = []
    for _, pos in positions_df.iterrows():
        if pd.notna(pos["open_time"]) and pd.notna(pos.get("close_time")):
            open_timestamp = int(pd.to_datetime(pos["open_time"]).timestamp())
            close_timestamp = int(pd.to_datetime(pos["close_time"]).timestamp())
            chart_positions.append(
                {
                    "position_id": str(pos.name),
                    "side": pos["side"],
                    "open_time": open_timestamp,
                    "close_time": close_timestamp,
                    "open_price": float(pos["open_price"]),
                    "close_price": float(pos["close_price"]),
                    "amount": float(pos["amount"]),
                    "profit": float(pos["profit"]),
                    "open_time_formatted": pos["open_time"].strftime("%Y-%m-%d %H:%M:%S"),
                    "close_time_formatted": pos["close_time"].strftime("%Y-%m-%d %H:%M:%S"),
                    "is_profit": float(pos["profit"]) >= 0,
                }
            )
        elif pd.notna(pos["open_time"]) and pos.get("is_open", False):
            open_timestamp = int(pd.to_datetime(pos["open_time"]).timestamp())
            chart_positions.append(
                {
                    "position_id": str(pos.name),
                    "side": pos["side"],
                    "open_time": open_timestamp,
                    "close_time": None,
                    "open_price": float(pos["open_price"]),
                    "close_price": None,
                    "amount": float(pos["amount"]),
                    "profit": float(pos["profit"]),
                    "open_time_formatted": pos["open_time"].strftime("%Y-%m-%d %H:%M:%S"),
                    "close_time_formatted": "持仓中",
                    "is_open": True,
                    "is_profit": float(pos["profit"]) >= 0,
                }
            )
    return chart_positions
