import { useMutation, useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'

import { loadChart, loadMoreChart, fetchConfig, fetchDataFiles, fetchSymbols } from './lib/api'
import type {
  ChartPayload,
  ChartResponse,
  IndicatorKey,
  IndicatorSettings,
  IndicatorState,
  PositionRecord,
} from './types/api'
import { ControlSidebar } from './features/dashboard/ControlSidebar'
import { StatusOverview } from './features/dashboard/StatusOverview'
import { TradingChart } from './features/chart/TradingChart'
import { PositionNavigator } from './features/positions/PositionNavigator'

const DEFAULT_INDICATORS: IndicatorState = {
  showEma: true,
  showVolume: true,
  showRsi: false,
  showMacd: false,
  showTradeMarkers: true,
}

const DEFAULT_INDICATOR_SETTINGS: IndicatorSettings = {
  ema: { periods: [20, 50, 200] },
  rsi: { period: 14 },
  macd: { fast_period: 12, slow_period: 26, signal_period: 9 },
}

function App() {
  const [exchange, setExchange] = useState('binance')
  const [dataFile, setDataFile] = useState<string | null>(null)
  const [symbol, setSymbol] = useState('')
  const [timeframe, setTimeframe] = useState('30m')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [minTrades, setMinTrades] = useState(5)
  const [indicators, setIndicators] = useState(DEFAULT_INDICATORS)
  const [indicatorSettings, setIndicatorSettings] = useState(DEFAULT_INDICATOR_SETTINGS)
  const [selectedPositionId, setSelectedPositionId] = useState<string | null>(null)
  const [chartResult, setChartResult] = useState<ChartResponse | null>(null)
  const [hasAutoLoaded, setHasAutoLoaded] = useState(false)
  const lastAppliedDateRangeFileRef = useRef<string | null>(null)
  const lastAppliedSymbolWindowRef = useRef<string | null>(null)

  const configQuery = useQuery({
    queryKey: ['config'],
    queryFn: fetchConfig,
  })
  const dataFilesQuery = useQuery({
    queryKey: ['data-files'],
    queryFn: fetchDataFiles,
  })
  const symbolsQuery = useQuery({
    queryKey: ['symbols', dataFile, minTrades],
    queryFn: () => fetchSymbols(dataFile, minTrades),
    enabled: dataFile !== null,
  })

  const chartMutation = useMutation({
    mutationFn: loadChart,
    onSuccess: (data) => {
      setChartResult(data)
      setSelectedPositionId(data.positions[0]?.position_id ?? null)
    },
    onError: () => {},
  })

  const loadMoreMutation = useMutation({
    mutationFn: loadMoreChart,
    onSuccess: (data) => {
      const incomingChart = data.chart
      if (!incomingChart) {
        return
      }
      setChartResult((current) => {
        if (!current) {
          return current
        }
        const mergedChart = mergeChartPayload(current.chart, incomingChart)
        return {
          ...current,
          chart: mergedChart,
          summary: {
            ...current.summary,
            candle_count: mergedChart.candlestick.length,
          },
        }
      })
    },
    onError: () => {},
  })

  useEffect(() => {
    const defaults = configQuery.data?.chart_defaults
    if (!defaults) {
      return
    }
    setTimeframe((current) => current || defaults.timeframe)
    setStartDate((current) => current || defaults.start_date)
    setEndDate((current) => current || defaults.end_date)
    setMinTrades((current) => current || defaults.min_trades)
    setSymbol((current) => current || defaults.symbol)
  }, [configQuery.data, exchange])

  useEffect(() => {
    if (dataFilesQuery.data?.latest && !dataFile) {
      setDataFile(dataFilesQuery.data.latest)
    }
  }, [dataFile, dataFilesQuery.data])

  useEffect(() => {
    const firstSymbol = symbolsQuery.data?.items[0]?.symbol
    if (firstSymbol && !symbolsQuery.data?.items.some((item) => item.symbol === symbol)) {
      setSymbol(firstSymbol)
    }
  }, [symbol, symbolsQuery.data])

  useEffect(() => {
    const dateRange = symbolsQuery.data?.date_range
    if (!dataFile || !dateRange) {
      return
    }
    if (lastAppliedDateRangeFileRef.current === dataFile) {
      return
    }

    setStartDate(dateRange.start_date)
    setEndDate(dateRange.end_date)
    setHasAutoLoaded(false)
    lastAppliedDateRangeFileRef.current = dataFile
  }, [dataFile, symbolsQuery.data?.date_range])

  useEffect(() => {
    if (!dataFile || !symbol || !symbolsQuery.data?.items.length) {
      return
    }
    const symbolMeta = symbolsQuery.data.items.find((item) => item.symbol === symbol)
    if (!symbolMeta?.first_trade_date) {
      return
    }

    const symbolWindowKey = `${dataFile}:${symbol}`
    if (lastAppliedSymbolWindowRef.current === symbolWindowKey) {
      return
    }

    const start = shiftDate(symbolMeta.first_trade_date, -5)
    const end = symbolMeta.last_trade_date ?? symbolsQuery.data.date_range?.end_date ?? symbolMeta.first_trade_date
    setStartDate(start)
    setEndDate(end)
    setHasAutoLoaded(false)
    lastAppliedSymbolWindowRef.current = symbolWindowKey
  }, [dataFile, symbol, symbolsQuery.data])

  useEffect(() => {
    const dataFilesReady =
      dataFilesQuery.status === 'success' &&
      ((dataFilesQuery.data?.items.length ?? 0) === 0 || dataFile !== null)
    const symbolsReady = dataFile === null || symbolsQuery.status === 'success'
    const symbolReady =
      dataFile === null ||
      (symbolsQuery.data?.items.length ?? 0) === 0 ||
      symbolsQuery.data?.items.some((item) => item.symbol === symbol)

    if (
      !hasAutoLoaded &&
      dataFilesReady &&
      symbolsReady &&
      symbolReady &&
      symbol &&
      timeframe &&
      startDate &&
      endDate
    ) {
      handleLoadChart()
      setHasAutoLoaded(true)
    }
  }, [
    dataFile,
    dataFilesQuery.data,
    dataFilesQuery.status,
    endDate,
    exchange,
    hasAutoLoaded,
    startDate,
    symbol,
    symbolsQuery.data,
    symbolsQuery.status,
    timeframe,
  ])

  const positions = chartResult?.positions ?? []
  const selectedPosition: PositionRecord | undefined = positions.find(
    (position) => position.position_id === selectedPositionId,
  )
  const chartLoadingLabel = loadMoreMutation.isPending ? '正在同步更多K线...' : '正在加载图表...'

  function handleLoadChart(overrides?: Partial<{ timeframe: string }>) {
    if (!symbol || !timeframe || !startDate || !endDate) {
      return
    }
    const nextTimeframe = overrides?.timeframe ?? timeframe
    setTimeframe(nextTimeframe)
    chartMutation.mutate({
      symbol,
      timeframe: nextTimeframe,
      start_date: startDate,
      end_date: endDate,
      data_file: dataFile,
      exchange,
      indicator_settings: indicatorSettings,
    })
  }

  function handleLoadMore() {
    const lastTimestamp = chartResult?.chart.candlestick.at(-1)?.time
    if (!lastTimestamp) {
      return
    }
    loadMoreMutation.mutate({
      symbol,
      timeframe,
      last_timestamp: lastTimestamp,
      candles_to_load: 500,
      exchange,
    })
  }

  function handleFieldChange(
    field: 'exchange' | 'dataFile' | 'symbol' | 'timeframe' | 'startDate' | 'endDate' | 'minTrades',
    value: string | number,
  ) {
    if (field === 'exchange') {
      setExchange(String(value))
      setHasAutoLoaded(false)
      return
    }
    if (field === 'dataFile') {
      const nextFile = String(value) || null
      setDataFile(nextFile)
      lastAppliedDateRangeFileRef.current = null
      lastAppliedSymbolWindowRef.current = null
      setHasAutoLoaded(false)
      return
    }
    if (field === 'symbol') {
      setSymbol(String(value))
      lastAppliedSymbolWindowRef.current = null
      setHasAutoLoaded(false)
      return
    }
    if (field === 'timeframe') {
      setTimeframe(String(value))
      return
    }
    if (field === 'startDate') {
      setStartDate(String(value))
      return
    }
    if (field === 'endDate') {
      setEndDate(String(value))
      return
    }
    setMinTrades(Number(value))
  }

  function handleIndicatorToggle(key: IndicatorKey) {
    setIndicators((current) => ({
      ...current,
      [key]: !current[key],
    }))
  }

  function handleIndicatorSettingsChange(nextSettings: IndicatorSettings) {
    setIndicatorSettings(nextSettings)
    setHasAutoLoaded(false)
  }

  return (
    <main className="min-h-screen bg-ink bg-grid bg-[size:36px_36px] text-slate-100">
      <div className="mx-auto min-h-screen max-w-[1920px] px-3 py-3">
        <div className="grid min-h-screen gap-4 xl:grid-cols-[minmax(22rem,1fr)_minmax(0,3fr)]">
          <aside className="space-y-5 xl:sticky xl:top-3 xl:h-[calc(100vh-1.5rem)] xl:overflow-y-auto xl:pr-1">
            <ControlSidebar
              config={configQuery.data}
              dataFiles={dataFilesQuery.data?.items ?? []}
              symbols={symbolsQuery.data?.items ?? []}
              exchange={exchange}
              dataFile={dataFile}
              symbol={symbol}
              timeframe={timeframe}
              startDate={startDate}
              endDate={endDate}
              minTrades={minTrades}
              indicators={indicators}
              indicatorSettings={indicatorSettings}
              loadingChart={chartMutation.isPending}
              loadingMore={loadMoreMutation.isPending}
              onFieldChange={handleFieldChange}
              onIndicatorToggle={handleIndicatorToggle}
              onIndicatorSettingsChange={handleIndicatorSettingsChange}
              onLoadChart={() => handleLoadChart()}
              onLoadMore={handleLoadMore}
            />

            <StatusOverview
              chartData={chartResult ?? undefined}
              dataFileName={dataFile ? dataFile.split('/').at(-1) ?? null : null}
            />

            <PositionNavigator
              positions={positions}
              selectedPositionId={selectedPosition?.position_id ?? null}
              onSelectPosition={setSelectedPositionId}
            />
          </aside>

          <div>
            <TradingChart
              chartData={chartResult?.chart}
              chartSymbol={chartResult?.symbol ?? symbol}
              positions={positions}
              indicators={indicators}
              indicatorSettings={indicatorSettings}
              selectedPositionId={selectedPositionId}
              timeframe={timeframe}
              timeframeOptions={configQuery.data?.timeframe_options ?? []}
              isLoading={chartMutation.isPending || loadMoreMutation.isPending}
              loadingLabel={chartLoadingLabel}
              onSelectPosition={setSelectedPositionId}
              onLoadMore={handleLoadMore}
              onTimeframeShortcut={(nextTimeframe) => handleLoadChart({ timeframe: nextTimeframe })}
              onIndicatorToggle={handleIndicatorToggle}
            />
          </div>
        </div>
      </div>
    </main>
  )
}

export default App

function shiftDate(value: string, offsetDays: number) {
  const date = new Date(`${value}T00:00:00`)
  date.setDate(date.getDate() + offsetDays)
  return date.toISOString().slice(0, 10)
}

function mergeChartPayload(current: ChartPayload, incoming: ChartPayload): ChartPayload {
  return {
    candlestick: appendSeriesByTime(current.candlestick, incoming.candlestick),
    volume: appendSeriesByTime(current.volume, incoming.volume),
    ema_series: current.ema_series.map((series, index) => ({
      ...series,
      data: appendSeriesByTime(series.data, incoming.ema_series[index]?.data ?? []),
    })),
    rsi: appendSeriesByTime(current.rsi, incoming.rsi),
    macd: appendSeriesByTime(current.macd, incoming.macd),
    signal: appendSeriesByTime(current.signal, incoming.signal),
    histogram: appendSeriesByTime(current.histogram, incoming.histogram),
  }
}

function appendSeriesByTime<T extends { time: number }>(current: T[], incoming: T[]): T[] {
  if (incoming.length === 0) {
    return current
  }
  const merged = [...current]
  const seen = new Set(current.map((item) => item.time))
  incoming.forEach((item) => {
    if (!seen.has(item.time)) {
      merged.push(item)
      seen.add(item.time)
    }
  })
  return merged
}
