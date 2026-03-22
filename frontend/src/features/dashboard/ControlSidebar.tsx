import type { ReactNode } from 'react'

import type {
  ConfigResponse,
  DataFileItem,
  IndicatorSettings,
  IndicatorState,
  SymbolItem,
} from '../../types/api'
import { cx } from '../../lib/format'

interface ControlSidebarProps {
  config?: ConfigResponse
  dataFiles: DataFileItem[]
  symbols: SymbolItem[]
  exchange: string
  dataFile: string | null
  symbol: string
  timeframe: string
  startDate: string
  endDate: string
  minTrades: number
  indicators: IndicatorState
  indicatorSettings: IndicatorSettings
  loadingChart: boolean
  loadingMore: boolean
  onFieldChange: (field: 'exchange' | 'dataFile' | 'symbol' | 'timeframe' | 'startDate' | 'endDate' | 'minTrades', value: string | number) => void
  onIndicatorToggle: (key: keyof IndicatorState) => void
  onIndicatorSettingsChange: (settings: IndicatorSettings) => void
  onLoadChart: () => void
  onLoadMore: () => void
}

const indicatorLabels: Array<{ key: keyof IndicatorState; label: string }> = [
  { key: 'showEma', label: 'EMA' },
  { key: 'showVolume', label: '成交量' },
  { key: 'showRsi', label: 'RSI' },
  { key: 'showMacd', label: 'MACD' },
  { key: 'showTradeMarkers', label: '交易标记' },
]

function Field({
  label,
  children,
}: {
  label: string
  children: ReactNode
}) {
  return (
    <label className="flex flex-col gap-2">
      <span className="text-[11px] uppercase tracking-[0.22em] text-slate-400">{label}</span>
      {children}
    </label>
  )
}

function inputClassName() {
  return 'w-full rounded-2xl border border-line bg-panelAlt px-3 py-2.5 text-sm text-slate-100 outline-none transition focus:border-accent focus:ring-2 focus:ring-accent/20'
}

function parsePeriodsInput(value: string) {
  const parsed = value
    .split(',')
    .map((item) => Number(item.trim()))
    .filter((item) => Number.isFinite(item) && item > 0)
    .map((item) => Math.round(item))
  return parsed.length > 0 ? parsed.slice(0, 6) : [20, 50, 200]
}

export function ControlSidebar({
  config,
  dataFiles,
  symbols,
  exchange,
  dataFile,
  symbol,
  timeframe,
  startDate,
  endDate,
  minTrades,
  indicators,
  indicatorSettings,
  loadingChart,
  loadingMore,
  onFieldChange,
  onIndicatorToggle,
  onIndicatorSettingsChange,
  onLoadChart,
  onLoadMore,
}: ControlSidebarProps) {
  return (
    <aside className="flex h-full flex-col gap-6 rounded-[28px] border border-white/10 bg-panel/90 p-5 shadow-panel backdrop-blur">
      <section className="space-y-4">
        <Field label="交易所">
          <select
            className={inputClassName()}
            value={exchange}
            onChange={(event) => onFieldChange('exchange', event.target.value)}
          >
            {(config?.exchange_options ?? []).map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </Field>

        <Field label="数据文件">
          <select
            className={inputClassName()}
            value={dataFile ?? ''}
            onChange={(event) => onFieldChange('dataFile', event.target.value)}
          >
            <option value="">不使用 CSV</option>
            {dataFiles.map((item) => (
              <option key={item.path} value={item.path}>
                {item.filename}
              </option>
            ))}
          </select>
        </Field>

        <Field label="交易对">
          <select
            className={inputClassName()}
            value={symbol}
            onChange={(event) => onFieldChange('symbol', event.target.value)}
          >
            {symbols.map((item) => (
              <option key={item.symbol} value={item.symbol}>
                {item.symbol} ({item.trade_count})
              </option>
            ))}
          </select>
        </Field>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="周期">
            <select
              className={inputClassName()}
              value={timeframe}
              onChange={(event) => onFieldChange('timeframe', event.target.value)}
            >
              {(config?.timeframe_options ?? []).map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </Field>

          <Field label="最少交易次数">
            <input
              className={inputClassName()}
              min={1}
              type="number"
              value={minTrades}
              onChange={(event) => onFieldChange('minTrades', Number(event.target.value))}
            />
          </Field>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="开始日期">
            <input
              className={inputClassName()}
              type="date"
              value={startDate}
              onChange={(event) => onFieldChange('startDate', event.target.value)}
            />
          </Field>
          <Field label="结束日期">
            <input
              className={inputClassName()}
              type="date"
              value={endDate}
              onChange={(event) => onFieldChange('endDate', event.target.value)}
            />
          </Field>
        </div>

        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {indicatorLabels.map((item) => (
            <button
              key={item.key}
              className={cx(
                'rounded-2xl border px-3 py-2 text-sm transition',
                indicators[item.key]
                  ? 'border-accent bg-accent/15 text-white'
                  : 'border-line bg-panelAlt text-slate-300 hover:border-slate-500',
              )}
              type="button"
              onClick={() => onIndicatorToggle(item.key)}
            >
              {item.label}
            </button>
          ))}
        </div>

        <section className="space-y-3 rounded-[24px] border border-white/8 bg-[#0d1424] p-4">
          <p className="text-[11px] uppercase tracking-[0.24em] text-slate-400">指标设置</p>

          <Field label="EMA 周期">
            <input
              className={inputClassName()}
              type="text"
              value={indicatorSettings.ema.periods.join(', ')}
              onChange={(event) =>
                onIndicatorSettingsChange({
                  ...indicatorSettings,
                  ema: {
                    periods: parsePeriodsInput(event.target.value),
                  },
                })
              }
            />
          </Field>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="RSI 周期">
              <input
                className={inputClassName()}
                min={1}
                type="number"
                value={indicatorSettings.rsi.period}
                onChange={(event) =>
                  onIndicatorSettingsChange({
                    ...indicatorSettings,
                    rsi: { period: Number(event.target.value) || 14 },
                  })
                }
              />
            </Field>

            <Field label="MACD 快线">
              <input
                className={inputClassName()}
                min={1}
                type="number"
                value={indicatorSettings.macd.fast_period}
                onChange={(event) =>
                  onIndicatorSettingsChange({
                    ...indicatorSettings,
                    macd: { ...indicatorSettings.macd, fast_period: Number(event.target.value) || 12 },
                  })
                }
              />
            </Field>
          </div>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="MACD 慢线">
              <input
                className={inputClassName()}
                min={1}
                type="number"
                value={indicatorSettings.macd.slow_period}
                onChange={(event) =>
                  onIndicatorSettingsChange({
                    ...indicatorSettings,
                    macd: { ...indicatorSettings.macd, slow_period: Number(event.target.value) || 26 },
                  })
                }
              />
            </Field>

            <Field label="MACD 信号">
              <input
                className={inputClassName()}
                min={1}
                type="number"
                value={indicatorSettings.macd.signal_period}
                onChange={(event) =>
                  onIndicatorSettingsChange({
                    ...indicatorSettings,
                    macd: { ...indicatorSettings.macd, signal_period: Number(event.target.value) || 9 },
                  })
                }
              />
            </Field>
          </div>
        </section>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <button
            className="rounded-2xl bg-accent px-4 py-3 text-sm font-medium text-ink transition hover:bg-accentSoft disabled:cursor-not-allowed disabled:opacity-60"
            disabled={loadingChart || !symbol}
            type="button"
            onClick={onLoadChart}
          >
            {loadingChart ? '加载中...' : '加载图表'}
          </button>
          <button
            className="rounded-2xl border border-line bg-panelAlt px-4 py-3 text-sm font-medium text-white transition hover:border-slate-400 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={loadingMore || !symbol}
            type="button"
            onClick={onLoadMore}
          >
            {loadingMore ? '同步中...' : '同步更多'}
          </button>
        </div>
      </section>
    </aside>
  )
}
