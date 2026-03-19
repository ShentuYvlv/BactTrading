# Variational 30 天导出转换说明

## 输入文件结论

### `data/30天trade数据.xlsx`

- 这是仓位重建的主数据源。
- 记录的是实际成交。
- 存在 20 条重复记录，需要按 `data4` 去重。
- `data9` 只有 `sell` 和空值两种情况。
- 结合 `data/30天订单数据.txt` 校验后，可以确认空值应解释为 `buy`。

### `data/30天PNL.xlsx`

- 这是 realized pnl 事件流，不是完整仓位表。
- 存在 20 条重复记录，需要按 `data2` 去重。
- `phone` 列是 realized pnl 数值。
- 它更接近“平仓成交对应的盈亏事件”，适合在仓位重建后按 `symbol + 平仓时间` 回填。

### `data/30天订单数据.txt`

- 这是订单列表，不适合作为主成交源直接重建仓位。
- 但它包含明确的 `buy/sell` 字段，可用于校验 `trade.xlsx` 的方向推断。
- 行数与 `trade.xlsx` 去重后的成交数一致，说明可以作为辅助验证源。

## 转换规则

1. 主成交源使用 `30天trade数据.xlsx`。
2. 按 `data4` 去重。
3. `data9 == sell` 记为卖出，其余空值记为买入。
4. 采用加权均价 + 部分平仓 + 反手开仓的仓位重建逻辑。
5. 使用 `30天PNL.xlsx` 的 `symbol + local_time` 聚合结果回填已实现盈亏。
6. 没有匹配到 realized pnl 的仓位，回退为按成交均价计算的毛 PnL。
7. 平台合约符号转换为 Binance 复盘格式：
   - `ETH-PERP -> ETH/USDT:USDT`
   - `SOL-PERP -> SOL/USDT:USDT`
   - `PUMPFUN-PERP -> PUMP/USDT:USDT`
   - 其余默认 `BASE-PERP -> BASE/USDT:USDT`
8. 导出的展示时间保留为东八区字符串，同时写入 UTC epoch 毫秒到 `原始开仓时间戳 / 原始平仓时间戳`。

## 输出结果

- 标准复盘 CSV:
  `data/binance_variational_2026-02-18_2026-03-17.csv`
- 转换脚本:
  `scripts/convert_variational_exports.py`

## 注意

- 这份输出是“复盘兼容格式”，不是 Binance 官方原始交割单的逐字段 1:1 复制。
- 但它已经满足当前复盘系统所需的仓位级 CSV 结构，并且可以正常联动 K 线与仓位导航。
