#!/usr/bin/env python

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd


LOCAL_TZ = ZoneInfo("Asia/Shanghai")
EPSILON = 1e-8
ORDER_TIME_TOLERANCE = pd.Timedelta(seconds=2)
PNL_TIME_TOLERANCE = pd.Timedelta(seconds=2)
SYMBOL_ALIASES = {
    "PUMPFUN": "PUMP",
}


@dataclass
class PositionState:
    side: str
    raw_symbol: str
    open_time: pd.Timestamp
    total_open_amount: float = 0.0
    remaining_amount: float = 0.0
    remaining_cost: float = 0.0
    total_close_amount: float = 0.0
    total_close_notional: float = 0.0
    realized_pnl_total: float = 0.0
    matched_pnl_events: int = 0
    open_trades: list[dict] = field(default_factory=list)
    close_trades: list[dict] = field(default_factory=list)
    synthetic: bool = False

    @property
    def avg_open_price(self) -> float:
        if self.total_open_amount <= EPSILON:
            return 0.0
        return (
            sum(trade["amount"] * trade["price"] for trade in self.open_trades)
            / self.total_open_amount
        )

    @property
    def avg_close_price(self) -> float | None:
        if self.total_close_amount <= EPSILON:
            return None
        return self.total_close_notional / self.total_close_amount

    def add_open_trade(self, trade_time: pd.Timestamp, price: float, amount: float) -> None:
        if amount <= EPSILON:
            return
        self.total_open_amount += amount
        self.remaining_amount += amount
        self.remaining_cost += price * amount
        self.open_trades.append(
            {
                "time": trade_time,
                "price": price,
                "amount": amount,
            }
        )

    def apply_close_trade(
        self,
        trade_time: pd.Timestamp,
        price: float,
        amount: float,
        matched_pnl: float | None,
    ) -> float:
        if amount <= EPSILON or self.remaining_amount <= EPSILON:
            return 0.0

        avg_open = self.remaining_cost / self.remaining_amount
        gross_pnl = (
            (price - avg_open) * amount
            if self.side == "long"
            else (avg_open - price) * amount
        )
        realized_pnl = matched_pnl if matched_pnl is not None else gross_pnl

        self.remaining_cost -= avg_open * amount
        self.remaining_amount -= amount
        self.total_close_amount += amount
        self.total_close_notional += price * amount
        self.realized_pnl_total += realized_pnl
        if matched_pnl is not None:
            self.matched_pnl_events += 1
        self.close_trades.append(
            {
                "time": trade_time,
                "price": price,
                "amount": amount,
                "gross_pnl": gross_pnl,
                "realized_pnl": realized_pnl,
                "matched_pnl": matched_pnl is not None,
            }
        )
        return realized_pnl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="将 Variational 30 天导出转换成复盘用标准 CSV")
    parser.add_argument(
        "--trade-file",
        default="data/30天trade数据.xlsx",
        help="逐笔成交 Excel 文件路径",
    )
    parser.add_argument(
        "--pnl-file",
        default="data/30天PNL.xlsx",
        help="Realized PNL Excel 文件路径",
    )
    parser.add_argument(
        "--orders-file",
        default="data/30天订单数据.txt",
        help="订单导出文本路径，用于辅助识别开平仓",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="输出 CSV 路径；默认写入 data/binance_variational_开始_结束.csv",
    )
    return parser.parse_args()


def normalize_symbol(raw_symbol: str) -> str:
    base = raw_symbol.replace("-PERP", "")
    base = SYMBOL_ALIASES.get(base, base)
    return f"{base}/USDT:USDT"


def local_dt_to_epoch_ms(local_dt: pd.Timestamp) -> int:
    dt = pd.Timestamp(local_dt).to_pydatetime().replace(tzinfo=LOCAL_TZ)
    return int(dt.timestamp() * 1000)


def load_trade_rows(path: Path) -> pd.DataFrame:
    trade = pd.read_excel(path).drop_duplicates(subset=["data4"]).copy()
    trade["side"] = trade["data9"].fillna("buy").astype(str).str.lower()
    trade["price"] = (
        trade["data5"]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .astype(float)
    )
    trade["amount"] = (
        trade["data6"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .astype(float)
    )
    trade["local_time"] = pd.to_datetime(trade["data3"])
    trade = trade.rename(columns={"data": "raw_symbol", "data4": "trade_id"})
    return trade[
        ["raw_symbol", "trade_id", "local_time", "side", "price", "amount"]
    ].sort_values(["raw_symbol", "local_time", "trade_id"]).reset_index(drop=True)


def load_orders(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(
            columns=[
                "symbol",
                "side",
                "order_type",
                "is_close",
                "price",
                "amount",
                "local_time",
            ]
        )

    orders = pd.read_csv(path, sep="\t").copy()
    orders.columns = [
        "image",
        "order_id",
        "url",
        "symbol",
        "side",
        "order_type",
        "price",
        "trigger_price",
        "size_pct",
        "is_close",
        "date",
        "time",
        "amount",
    ]
    orders["price"] = (
        orders["price"]
        .astype(str)
        .str.replace("$", "", regex=False)
        .str.replace(",", "", regex=False)
        .astype(float)
    )
    orders["amount"] = pd.to_numeric(
        orders["amount"].astype(str).str.replace(",", "", regex=False),
        errors="coerce",
    )
    orders["local_time"] = pd.to_datetime(
        orders["date"].astype(str) + " " + orders["time"].astype(str)
    )
    orders["side"] = orders["side"].astype(str).str.lower()
    return orders[
        ["order_id", "symbol", "side", "order_type", "is_close", "price", "amount", "local_time"]
    ].sort_values(["symbol", "local_time", "order_id"]).reset_index(drop=True)


def load_pnl_events(path: Path) -> pd.DataFrame:
    pnl = pd.read_excel(path).drop_duplicates(subset=["data2"]).copy()
    pnl["local_time"] = pd.to_datetime(pnl["data4"])
    pnl["pnl"] = pd.to_numeric(pnl["phone"], errors="coerce")
    grouped = (
        pnl.groupby(["data", "local_time"], as_index=False)
        .agg(
            pnl=("pnl", lambda values: values.sum(min_count=1)),
            event_count=("data2", "count"),
        )
        .rename(columns={"data": "raw_symbol"})
    )
    return grouped.sort_values(["raw_symbol", "local_time"]).reset_index(drop=True)


def match_order_hints(trades: pd.DataFrame, orders: pd.DataFrame) -> dict[str, dict[str, str | None]]:
    if orders.empty:
        return {}

    matched: dict[str, dict[str, str | None]] = {}
    used_order_indexes: set[int] = set()

    for trade in trades.itertuples(index=False):
        candidates = orders[
            (orders["symbol"] == trade.raw_symbol)
            & (orders["side"] == trade.side)
            & (orders["local_time"].sub(trade.local_time).abs() <= ORDER_TIME_TOLERANCE)
            & (orders["price"].sub(trade.price).abs() <= 1e-9)
        ]
        candidates = candidates[
            candidates["amount"].isna()
            | (candidates["amount"].sub(trade.amount).abs() <= 1e-6)
        ]
        candidates = candidates[~candidates.index.isin(used_order_indexes)]
        if candidates.empty:
            continue

        candidates = candidates.assign(
            score=(candidates["local_time"] - trade.local_time).abs().dt.total_seconds()
        )
        match = candidates.sort_values(["score", "order_id"]).iloc[0]
        used_order_indexes.add(int(match.name))
        matched[trade.trade_id] = {
            "is_close": match.is_close,
            "order_type": match.order_type,
        }

    return matched


def match_pnl_hints(trades: pd.DataFrame, pnl_events: pd.DataFrame) -> dict[str, dict[str, object]]:
    if pnl_events.empty:
        return {}

    matched: dict[str, dict[str, object]] = {}
    used_pnl_indexes: set[int] = set()

    for trade in trades.itertuples(index=False):
        candidates = pnl_events[
            (pnl_events["raw_symbol"] == trade.raw_symbol)
            & (pnl_events["local_time"].sub(trade.local_time).abs() <= PNL_TIME_TOLERANCE)
        ]
        candidates = candidates[~candidates.index.isin(used_pnl_indexes)]
        if candidates.empty:
            continue

        candidates = candidates.assign(
            score=(candidates["local_time"] - trade.local_time).abs().dt.total_seconds()
        )
        match = candidates.sort_values(["score", "local_time"]).iloc[0]
        used_pnl_indexes.add(int(match.name))
        matched[trade.trade_id] = {
            "event_time": match.local_time,
            "pnl": None if pd.isna(match.pnl) else float(match.pnl),
            "event_count": int(match.event_count),
        }

    return matched


def infer_entry_price_from_close(
    position_side: str,
    close_price: float,
    amount: float,
    realized_pnl: float | None,
) -> float:
    if amount <= EPSILON or realized_pnl is None:
        return close_price
    if position_side == "long":
        return close_price - realized_pnl / amount
    return close_price + realized_pnl / amount


def build_synthetic_position(
    raw_symbol: str,
    position_side: str,
    close_time: pd.Timestamp,
    close_price: float,
    amount: float,
    realized_pnl: float | None,
) -> PositionState:
    position = PositionState(
        side=position_side,
        raw_symbol=raw_symbol,
        open_time=close_time - pd.Timedelta(seconds=1),
        synthetic=True,
    )
    position.add_open_trade(
        trade_time=position.open_time,
        price=infer_entry_price_from_close(position_side, close_price, amount, realized_pnl),
        amount=amount,
    )
    return position


def finalize_closed_position(position: PositionState, close_time: pd.Timestamp) -> dict:
    return {
        "交易对": normalize_symbol(position.raw_symbol),
        "方向": "多头" if position.side == "long" else "空头",
        "数量": round(position.total_open_amount, 8),
        "开仓价格": round(position.avg_open_price, 8),
        "开仓时间_dt": position.open_time,
        "平仓价格": round(position.avg_close_price or 0.0, 8),
        "平仓时间_dt": close_time,
        "状态": "已平仓",
        "PnL": round(position.realized_pnl_total, 8),
        "交易次数": len(position.open_trades) + len(position.close_trades),
        "原始开仓时间戳": local_dt_to_epoch_ms(position.open_time),
        "原始平仓时间戳": local_dt_to_epoch_ms(close_time),
        "_raw_symbol": position.raw_symbol,
        "_matched_pnl_events": position.matched_pnl_events,
        "_synthetic": position.synthetic,
    }


def finalize_open_position(position: PositionState) -> dict:
    return {
        "交易对": normalize_symbol(position.raw_symbol),
        "方向": "多头" if position.side == "long" else "空头",
        "数量": round(position.total_open_amount, 8),
        "开仓价格": round(position.avg_open_price, 8),
        "开仓时间_dt": position.open_time,
        "平仓价格": None,
        "平仓时间_dt": pd.NaT,
        "状态": "持仓中",
        "PnL": round(position.realized_pnl_total, 8),
        "交易次数": len(position.open_trades) + len(position.close_trades),
        "原始开仓时间戳": local_dt_to_epoch_ms(position.open_time),
        "原始平仓时间戳": "",
        "_raw_symbol": position.raw_symbol,
        "_matched_pnl_events": position.matched_pnl_events,
        "_synthetic": position.synthetic,
    }


def append_closed_position(rows: list[dict], position: PositionState, close_time: pd.Timestamp) -> None:
    rows.append(finalize_closed_position(position, close_time))


def apply_unknown_trade_with_fallback(
    rows: list[dict],
    current_position: PositionState | None,
    trade_time: pd.Timestamp,
    trade_side: str,
    trade_price: float,
    trade_amount: float,
    raw_symbol: str,
) -> PositionState | None:
    if trade_amount <= EPSILON:
        return current_position

    if current_position is None:
        current_position = PositionState(
            side="long" if trade_side == "buy" else "short",
            raw_symbol=raw_symbol,
            open_time=trade_time,
        )
        current_position.add_open_trade(trade_time, trade_price, trade_amount)
        return current_position

    open_side = "long" if trade_side == "buy" else "short"
    if current_position.side == open_side:
        current_position.add_open_trade(trade_time, trade_price, trade_amount)
        return current_position

    remaining_to_close = trade_amount
    while remaining_to_close > EPSILON and current_position is not None:
        close_amount = min(remaining_to_close, current_position.remaining_amount)
        current_position.apply_close_trade(
            trade_time=trade_time,
            price=trade_price,
            amount=close_amount,
            matched_pnl=None,
        )
        remaining_to_close -= close_amount
        if current_position.remaining_amount <= EPSILON:
            append_closed_position(rows, current_position, trade_time)
            current_position = None

    if remaining_to_close > EPSILON:
        current_position = PositionState(
            side=open_side,
            raw_symbol=raw_symbol,
            open_time=trade_time,
        )
        current_position.add_open_trade(trade_time, trade_price, remaining_to_close)

    return current_position


def convert_to_positions(
    trades: pd.DataFrame,
    pnl_hints: dict[str, dict[str, object]],
    order_hints: dict[str, dict[str, str | None]],
) -> pd.DataFrame:
    rows: list[dict] = []

    for raw_symbol, group in trades.groupby("raw_symbol"):
        current_position: PositionState | None = None

        for trade in group.itertuples(index=False):
            pnl_hint = pnl_hints.get(trade.trade_id)
            order_hint = order_hints.get(trade.trade_id)

            close_by_pnl_event = pnl_hint is not None
            close_by_order = (order_hint or {}).get("is_close") == "Yes"
            open_by_order = (order_hint or {}).get("is_close") == "No"
            matched_pnl = None if pnl_hint is None else pnl_hint["pnl"]

            is_close = close_by_pnl_event or close_by_order
            open_side = "long" if trade.side == "buy" else "short"
            close_side = "short" if trade.side == "buy" else "long"

            if is_close:
                if current_position is not None and current_position.side != close_side:
                    rows.append(finalize_open_position(current_position))
                    current_position = None

                remaining_to_close = trade.amount
                while remaining_to_close > EPSILON:
                    if current_position is None:
                        current_position = build_synthetic_position(
                            raw_symbol=raw_symbol,
                            position_side=close_side,
                            close_time=trade.local_time,
                            close_price=trade.price,
                            amount=remaining_to_close,
                            realized_pnl=matched_pnl,
                        )

                    close_amount = min(remaining_to_close, current_position.remaining_amount)
                    apply_matched_pnl = (
                        matched_pnl
                        if matched_pnl is not None
                        and abs(close_amount - remaining_to_close) <= EPSILON
                        and abs(remaining_to_close - trade.amount) <= EPSILON
                        else None
                    )
                    current_position.apply_close_trade(
                        trade_time=trade.local_time,
                        price=trade.price,
                        amount=close_amount,
                        matched_pnl=apply_matched_pnl,
                    )
                    remaining_to_close -= close_amount

                    if current_position.remaining_amount <= EPSILON:
                        append_closed_position(rows, current_position, trade.local_time)
                        current_position = None

                continue

            if open_by_order or order_hint is None:
                current_position = apply_unknown_trade_with_fallback(
                    rows=rows,
                    current_position=current_position,
                    trade_time=trade.local_time,
                    trade_side=trade.side,
                    trade_price=trade.price,
                    trade_amount=trade.amount,
                    raw_symbol=raw_symbol,
                )
                continue

            if current_position is None:
                current_position = PositionState(
                    side=open_side,
                    raw_symbol=raw_symbol,
                    open_time=trade.local_time,
                )
            elif current_position.side != open_side:
                rows.append(finalize_open_position(current_position))
                current_position = PositionState(
                    side=open_side,
                    raw_symbol=raw_symbol,
                    open_time=trade.local_time,
                )

            current_position.add_open_trade(trade.local_time, trade.price, trade.amount)

        if current_position is not None and current_position.total_open_amount > EPSILON:
            rows.append(finalize_open_position(current_position))

    positions = pd.DataFrame(rows).sort_values(["开仓时间_dt", "交易对"]).reset_index(drop=True)

    id_counts: dict[str, int] = {}
    position_ids: list[str] = []
    for row in positions.itertuples(index=False):
        base = f"{row.交易对}_{row.原始开仓时间戳}"
        count = id_counts.get(base, 0) + 1
        id_counts[base] = count
        position_ids.append(base if count == 1 else f"{base}_{count}")

    positions["仓位ID"] = position_ids
    positions["开仓时间"] = positions["开仓时间_dt"].dt.strftime("%Y-%m-%d %H:%M:%S")
    positions["平仓时间"] = positions["平仓时间_dt"].apply(
        lambda value: value.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(value) else "持仓中"
    )

    return positions[
        [
            "仓位ID",
            "交易对",
            "方向",
            "数量",
            "开仓价格",
            "开仓时间",
            "平仓价格",
            "平仓时间",
            "状态",
            "PnL",
            "交易次数",
            "原始开仓时间戳",
            "原始平仓时间戳",
        ]
    ]


def build_output_path(trades: pd.DataFrame, output_arg: str | None) -> Path:
    if output_arg:
        return Path(output_arg)

    start_date = trades["local_time"].min().strftime("%Y-%m-%d")
    end_date = trades["local_time"].max().strftime("%Y-%m-%d")
    return Path("data") / f"binance_variational_{start_date}_{end_date}.csv"


def print_diagnostics(
    trades: pd.DataFrame,
    pnl_events: pd.DataFrame,
    orders: pd.DataFrame,
    pnl_hints: dict[str, dict[str, object]],
    order_hints: dict[str, dict[str, str | None]],
    positions: pd.DataFrame,
) -> None:
    pnl_non_null = pnl_events["pnl"].notna().sum()
    synthetic_count = 0
    if not positions.empty:
        synthetic_count = len(
            positions[positions["原始开仓时间戳"].duplicated(keep=False)]
        )

    print(f"[诊断] 成交行数: {len(trades)}")
    print(f"[诊断] 订单行数: {len(orders)}")
    print(f"[诊断] PnL 事件行数: {len(pnl_events)}，其中带数值: {pnl_non_null}")
    print(f"[诊断] 匹配到订单提示: {len(order_hints)}")
    print(f"[诊断] 匹配到 PnL 事件: {len(pnl_hints)}")
    print(
        "[诊断] 注意：Variational PNL 导出会丢失大量正盈利数值，"
        "因此脚本会把 PnL 事件当作平仓信号，再用成交均价补齐缺失的正向 realized PnL。"
    )
    if synthetic_count:
        print(f"[诊断] 存在 {synthetic_count} 条窗口外历史仓位的合成开仓记录。")


def main() -> None:
    args = parse_args()
    trade_file = Path(args.trade_file)
    pnl_file = Path(args.pnl_file)
    orders_file = Path(args.orders_file)

    trades = load_trade_rows(trade_file)
    orders = load_orders(orders_file)
    pnl_events = load_pnl_events(pnl_file)
    order_hints = match_order_hints(trades, orders)
    pnl_hints = match_pnl_hints(trades, pnl_events)
    positions = convert_to_positions(trades, pnl_hints, order_hints)

    output_path = build_output_path(trades, args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    positions.to_csv(output_path, index=False, encoding="utf-8")

    print_diagnostics(trades, pnl_events, orders, pnl_hints, order_hints, positions)
    print(f"[完成] 已生成标准复盘 CSV: {output_path}")
    print(f"[完成] 仓位数: {len(positions)}")
    print("[完成] 交易对分布:")
    print(positions["交易对"].value_counts().to_string())


if __name__ == "__main__":
    main()
