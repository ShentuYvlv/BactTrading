import type { ChartResponse } from '../../types/api'
import { formatCompactNumber } from '../../lib/format'

interface StatusOverviewProps {
  chartData?: ChartResponse
  dataFileName: string | null
}

export function StatusOverview({ chartData, dataFileName }: StatusOverviewProps) {
  const summary = chartData?.summary
  const cards = [
    {
      label: '数据来源',
      value: summary?.data_source === 'csv' ? summary.file_name ?? dataFileName ?? 'CSV' : 'Exchange API',
    },
    {
      label: 'K线数量',
      value: summary ? formatCompactNumber(summary.candle_count, 1) : '--',
    },
    {
      label: '仓位数量',
      value: summary ? formatCompactNumber(summary.position_count, 1) : '--',
    },
    {
      label: '当前标的',
      value: chartData ? `${chartData.symbol} / ${chartData.timeframe}` : '--',
    },
  ]

  return (
    <div className="grid gap-3 md:grid-cols-4">
      {cards.map((card) => (
        <article
          key={card.label}
          className="rounded-[24px] border border-white/10 bg-panel/80 p-4 shadow-panel backdrop-blur"
        >
          <p className="text-[11px] uppercase tracking-[0.24em] text-slate-400">{card.label}</p>
          <p className="mt-3 text-lg font-semibold text-white">{card.value}</p>
        </article>
      ))}
    </div>
  )
}
