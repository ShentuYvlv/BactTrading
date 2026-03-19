#!/usr/bin/env python

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd


LOCAL_TZ = ZoneInfo("Asia/Shanghai")
EPSILON = 1e-8
SYMBOL_ALIASES = {
    "PUMPFUN": "PUMP",
}


@dataclass
class PositionState:
    side: str
    raw_symbol: str
    open_time: pd.Timestamp
    total_amount: float = 0.0
    remaining_amount: float = 0.0
    total_cost: float = 0.0
    trades: list[dict] = field(default_factory=list)
    close_pnl_keys: list[tuple[str, pd.Timestamp]] = field(default_factory=list)

    @property
    def avg_open_price(self) -> float:
        if self.total_amount <= EPSILON:
            return 0.0
        return self.total_cost / self.total_amount


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
        help="订单导出文本路径，仅用于校验，不参与仓位重建",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="输出 CSV 路径；默认写入 data/binance_variational_开始_结束.csv",
    )
    return parser.parse_args()


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
    trade = trade[["data", "data4", "local_time", "side", "price", "amount"]]
    return trade.sort_values(["data", "local_time", "data4"]).reset_index(drop=True)


def load_realized_pnl_map(path: Path) -> dict[tuple[str, pd.Timestamp], float]:
    pnl = pd.read_excel(path).drop_duplicates(subset=["data2"]).copy()
    pnl["local_time"] = pd.to_datetime(pnl["data4"])
    pnl["pnl"] = pd.to_numeric(pnl["phone"], errors="coerce")
    return pnl.groupby(["data", "local_time"])["pnl"].sum(min_count=1).to_dict()


def normalize_symbol(raw_symbol: str) -> str:
    base = raw_symbol.replace("-PERP", "")
    base = SYMBOL_ALIASES.get(base, base)
    return f"{base}/USDT:USDT"


def local_dt_to_epoch_ms(local_dt: pd.Timestamp) -> int:
    dt = pd.Timestamp(local_dt).to_pydatetime().replace(tzinfo=LOCAL_TZ)
    return int(dt.timestamp() * 1000)


def finalize_position(
    position: PositionState,
    close_time: pd.Timestamp,
    realized_pnl_map: dict[tuple[str, pd.Timestamp], float],
) -> dict:
    if position.side == "long":
        close_notional = sum(
            trade["amount"] * trade["price"]
            for trade in position.trades
            if trade["action"] == "close"
        )
        avg_close_price = close_notional / position.total_amount
        gross_pnl = close_notional - position.total_cost
    else:
        buyback_notional = sum(
            trade["amount"] * trade["price"]
            for trade in position.trades
            if trade["action"] == "close"
        )
        avg_close_price = buyback_notional / position.total_amount
        gross_pnl = position.total_cost - buyback_notional

    matched_pnl_values = [
        value
        for key in position.close_pnl_keys
        for value in [realized_pnl_map.get(key)]
        if pd.notna(value)
    ]
    pnl_value = sum(matched_pnl_values) if matched_pnl_values else gross_pnl

    return {
        "交易对": normalize_symbol(position.raw_symbol),
        "方向": "多头" if position.side == "long" else "空头",
        "数量": round(position.total_amount, 8),
        "开仓价格": round(position.avg_open_price, 8),
        "开仓时间_dt": position.open_time,
        "平仓价格": round(avg_close_price, 8),
        "平仓时间_dt": close_time,
        "状态": "已平仓",
        "PnL": round(pnl_value, 8),
        "交易次数": len(position.trades),
        "原始开仓时间戳": local_dt_to_epoch_ms(position.open_time),
        "原始平仓时间戳": local_dt_to_epoch_ms(close_time),
        "_raw_symbol": position.raw_symbol,
        "_matched_pnl_events": len(matched_pnl_values),
        "_gross_pnl": gross_pnl,
    }


def convert_to_positions(
    trades: pd.DataFrame,
    realized_pnl_map: dict[tuple[str, pd.Timestamp], float],
) -> pd.DataFrame:
    rows: list[dict] = []

    for raw_symbol, group in trades.groupby("data"):
        long_position: PositionState | None = None
        short_position: PositionState | None = None

        for trade in group.itertuples(index=False):
            trade_time = trade.local_time
            trade_side = trade.side
            trade_price = float(trade.price)
            trade_amount = float(trade.amount)
            trade_record = {
                "symbol": raw_symbol,
                "time": trade_time,
                "side": trade_side,
                "price": trade_price,
                "amount": trade_amount,
            }

            if trade_side == "buy":
                if short_position and short_position.remaining_amount > EPSILON:
                    close_amount = min(trade_amount, short_position.remaining_amount)
                    short_position.trades.append(
                        {**trade_record, "amount": close_amount, "action": "close"}
                    )
                    short_position.close_pnl_keys.append((raw_symbol, trade_time))
                    short_position.remaining_amount -= close_amount

                    if short_position.remaining_amount <= EPSILON:
                        short_position.remaining_amount = 0.0
                        rows.append(
                            finalize_position(
                                short_position,
                                close_time=trade_time,
                                realized_pnl_map=realized_pnl_map,
                            )
                        )
                        short_position = None

                    remaining = trade_amount - close_amount
                    if remaining > EPSILON:
                        if long_position is None:
                            long_position = PositionState(
                                side="long",
                                raw_symbol=raw_symbol,
                                open_time=trade_time,
                            )
                        long_position.total_amount += remaining
                        long_position.remaining_amount += remaining
                        long_position.total_cost += remaining * trade_price
                        long_position.trades.append(
                            {**trade_record, "amount": remaining, "action": "open"}
                        )
                else:
                    if long_position is None:
                        long_position = PositionState(
                            side="long",
                            raw_symbol=raw_symbol,
                            open_time=trade_time,
                        )
                    long_position.total_amount += trade_amount
                    long_position.remaining_amount += trade_amount
                    long_position.total_cost += trade_amount * trade_price
                    long_position.trades.append({**trade_record, "action": "open"})

            elif trade_side == "sell":
                if long_position and long_position.remaining_amount > EPSILON:
                    close_amount = min(trade_amount, long_position.remaining_amount)
                    long_position.trades.append(
                        {**trade_record, "amount": close_amount, "action": "close"}
                    )
                    long_position.close_pnl_keys.append((raw_symbol, trade_time))
                    long_position.remaining_amount -= close_amount

                    if long_position.remaining_amount <= EPSILON:
                        long_position.remaining_amount = 0.0
                        rows.append(
                            finalize_position(
                                long_position,
                                close_time=trade_time,
                                realized_pnl_map=realized_pnl_map,
                            )
                        )
                        long_position = None

                    remaining = trade_amount - close_amount
                    if remaining > EPSILON:
                        if short_position is None:
                            short_position = PositionState(
                                side="short",
                                raw_symbol=raw_symbol,
                                open_time=trade_time,
                            )
                        short_position.total_amount += remaining
                        short_position.remaining_amount += remaining
                        short_position.total_cost += remaining * trade_price
                        short_position.trades.append(
                            {**trade_record, "amount": remaining, "action": "open"}
                        )
                else:
                    if short_position is None:
                        short_position = PositionState(
                            side="short",
                            raw_symbol=raw_symbol,
                            open_time=trade_time,
                        )
                    short_position.total_amount += trade_amount
                    short_position.remaining_amount += trade_amount
                    short_position.total_cost += trade_amount * trade_price
                    short_position.trades.append({**trade_record, "action": "open"})

        for open_position in [long_position, short_position]:
            if open_position and open_position.total_amount > EPSILON:
                matched_pnl_values = [
                    value
                    for key in open_position.close_pnl_keys
                    for value in [realized_pnl_map.get(key)]
                    if pd.notna(value)
                ]
                rows.append(
                    {
                        "交易对": normalize_symbol(open_position.raw_symbol),
                        "方向": "多头" if open_position.side == "long" else "空头",
                        "数量": round(open_position.total_amount, 8),
                        "开仓价格": round(open_position.avg_open_price, 8),
                        "开仓时间_dt": open_position.open_time,
                        "平仓价格": None,
                        "平仓时间_dt": pd.NaT,
                        "状态": "持仓中",
                        "PnL": round(sum(matched_pnl_values), 8) if matched_pnl_values else 0.0,
                        "交易次数": len(open_position.trades),
                        "原始开仓时间戳": local_dt_to_epoch_ms(open_position.open_time),
                        "原始平仓时间戳": "",
                        "_raw_symbol": open_position.raw_symbol,
                        "_matched_pnl_events": len(matched_pnl_values),
                        "_gross_pnl": None,
                    }
                )

    positions = pd.DataFrame(rows).sort_values(["开仓时间_dt", "交易对"]).reset_index(drop=True)
    positions["仓位ID"] = [
        f"{row.交易对}_{row.原始开仓时间戳}"
        for row in positions.itertuples(index=False)
    ]
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


def validate_orders_file(orders_file: Path, trade_rows: pd.DataFrame) -> None:
    if not orders_file.exists():
        return

    orders = pd.read_csv(orders_file, sep="\t")
    print(
        f"[校验] 订单文件 {orders_file.name}: {len(orders)} 行，"
        f"成交文件去重后 {len(trade_rows)} 行"
    )
    if len(orders) != len(trade_rows):
        print("[校验] 订单列表和成交列表行数不同，已仅使用成交文件进行仓位重建。")


def main() -> None:
    args = parse_args()
    trade_file = Path(args.trade_file)
    pnl_file = Path(args.pnl_file)
    orders_file = Path(args.orders_file)

    trades = load_trade_rows(trade_file)
    realized_pnl_map = load_realized_pnl_map(pnl_file)
    validate_orders_file(orders_file, trades)

    positions = convert_to_positions(trades, realized_pnl_map)
    output_path = build_output_path(trades, args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    positions.to_csv(output_path, index=False, encoding="utf-8")

    print(f"[完成] 已生成标准复盘 CSV: {output_path}")
    print(f"[完成] 仓位数: {len(positions)}")
    print("[完成] 交易对分布:")
    print(positions["交易对"].value_counts().to_string())


if __name__ == "__main__":
    main()
