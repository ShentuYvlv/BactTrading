import type { ChartResponse } from '../../types/api'
import { formatCompactNumber } from '../../lib/format'

interface StatusOverviewProps {
  chartData?: ChartResponse
  dataFileName: string | null
}

export function StatusOverview({ chartData, dataFileName }: StatusOverviewProps) {
  const summary = chartData?.summary
  const items = [
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
    <section className="overflow-hidden rounded-[28px] border border-white/10 bg-[#101826] p-5 shadow-panel">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.24em] text-slate-400">概览</p>
          <h2 className="mt-2 text-lg font-semibold text-white">当前图表信息</h2>
        </div>
      </div>

      <div className="mt-4 divide-y divide-white/8 overflow-hidden rounded-[22px] border border-white/8 bg-[#0d1424]">
        {items.map((item) => (
          <div key={item.label} className="grid grid-cols-[5.5rem_minmax(0,1fr)] gap-3 px-4 py-4">
            <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">{item.label}</p>
            <p className="min-w-0 break-words text-sm font-medium text-white">{item.value}</p>
          </div>
        ))}
      </div>
    </section>
  )
}
