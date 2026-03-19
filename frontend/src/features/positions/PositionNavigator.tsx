import { useEffect, useState } from 'react'

import { cx, formatNumber } from '../../lib/format'
import type { PositionRecord } from '../../types/api'

interface PositionNavigatorProps {
  positions: PositionRecord[]
  selectedPositionId: string | null
  onSelectPosition: (positionId: string) => void
}

export function PositionNavigator({
  positions,
  selectedPositionId,
  onSelectPosition,
}: PositionNavigatorProps) {
  const [jumpIndex, setJumpIndex] = useState('1')
  const selectedIndex = positions.findIndex((position) => position.position_id === selectedPositionId)
  const selectedPosition = selectedIndex >= 0 ? positions[selectedIndex] : positions[0]

  useEffect(() => {
    if (selectedIndex >= 0) {
      setJumpIndex(String(selectedIndex + 1))
    }
  }, [selectedIndex])

  if (positions.length === 0) {
    return (
      <section className="rounded-[28px] border border-white/10 bg-panel/80 p-5 shadow-panel">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">仓位导航</h2>
          <span className="rounded-full border border-line px-3 py-1 text-xs text-slate-400">0 条仓位</span>
        </div>
        <p className="mt-4 text-sm text-slate-400">当前时间范围内没有匹配仓位。可以换 CSV、日期区间或交易对。</p>
      </section>
    )
  }

  return (
    <section className="rounded-[28px] border border-white/10 bg-panel/80 p-5 shadow-panel">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white">仓位导航</h2>
          <p className="mt-1 text-sm text-slate-400">上一笔 / 下一笔 / 序号跳转都保留。</p>
        </div>
        <span className="rounded-full border border-line px-3 py-1 text-xs text-slate-400">
          {positions.length} 条仓位
        </span>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          className="rounded-2xl border border-line bg-panelAlt px-4 py-2 text-sm text-white transition hover:border-slate-400 disabled:opacity-50"
          disabled={selectedIndex <= 0}
          type="button"
          onClick={() => onSelectPosition(positions[selectedIndex - 1].position_id)}
        >
          上一笔
        </button>
        <button
          className="rounded-2xl border border-line bg-panelAlt px-4 py-2 text-sm text-white transition hover:border-slate-400 disabled:opacity-50"
          disabled={selectedIndex < 0 || selectedIndex >= positions.length - 1}
          type="button"
          onClick={() => onSelectPosition(positions[selectedIndex + 1].position_id)}
        >
          下一笔
        </button>
        <div className="flex items-center gap-2 rounded-2xl border border-line bg-panelAlt px-3 py-2">
          <span className="text-sm text-slate-400">跳转</span>
          <input
            className="w-16 bg-transparent text-right text-sm text-white outline-none"
            min={1}
            max={positions.length}
            type="number"
            value={jumpIndex}
            onChange={(event) => setJumpIndex(event.target.value)}
          />
          <button
            className="rounded-xl bg-accent px-3 py-1 text-xs font-medium text-ink"
            type="button"
            onClick={() => {
              const nextIndex = Number(jumpIndex) - 1
              if (Number.isInteger(nextIndex) && nextIndex >= 0 && nextIndex < positions.length) {
                onSelectPosition(positions[nextIndex].position_id)
              }
            }}
          >
            跳转
          </button>
        </div>
      </div>

      {selectedPosition && (
        <div className="mt-4 grid gap-3 rounded-[24px] border border-white/8 bg-[#0d1424] p-4 md:grid-cols-4">
          <InfoItem label="方向" value={selectedPosition.side === 'long' ? '多头' : '空头'} />
          <InfoItem label="开仓时间" value={selectedPosition.open_time_formatted} />
          <InfoItem label="平仓时间" value={selectedPosition.close_time_formatted} />
          <InfoItem
            label="PnL"
            value={formatNumber(selectedPosition.profit, 2)}
            accent={selectedPosition.is_profit ? 'up' : 'down'}
          />
        </div>
      )}

      <div className="mt-4 max-h-[22rem] space-y-2 overflow-auto pr-1">
        {positions.map((position, index) => (
          <button
            key={position.position_id}
            className={cx(
              'w-full rounded-[22px] border px-4 py-3 text-left transition',
              position.position_id === selectedPositionId
                ? 'border-accent bg-accent/10'
                : 'border-white/8 bg-panelAlt hover:border-slate-500',
            )}
            type="button"
            onClick={() => onSelectPosition(position.position_id)}
          >
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-white">
                  #{index + 1} {position.side === 'long' ? '多头' : '空头'}
                </p>
                <p className="mt-1 text-xs text-slate-400">
                  {position.open_time_formatted} {'->'} {position.close_time_formatted}
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm text-slate-300">数量 {formatNumber(position.amount, 4)}</p>
                <p
                  className={cx(
                    'mt-1 text-sm font-medium',
                    position.is_profit ? 'text-emerald-400' : 'text-rose-400',
                  )}
                >
                  {formatNumber(position.profit, 2)}
                </p>
              </div>
            </div>
          </button>
        ))}
      </div>
    </section>
  )
}

function InfoItem({
  label,
  value,
  accent,
}: {
  label: string
  value: string
  accent?: 'up' | 'down'
}) {
  const colorClassName =
    accent === 'up' ? 'text-emerald-400' : accent === 'down' ? 'text-rose-400' : 'text-white'

  return (
    <div>
      <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">{label}</p>
      <p className={cx('mt-2 text-sm font-medium', colorClassName)}>{value}</p>
    </div>
  )
}
