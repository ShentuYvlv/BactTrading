import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { loadChart, loadMoreChart, rebuildPositions, fetchConfig, fetchDataFiles, fetchSymbols } from './lib/api'
import type {
  IndicatorKey,
  IndicatorSettings,
  IndicatorState,
  PositionRecord,
  RebuildRequest,
} from './types/api'
import { ControlSidebar } from './features/dashboard/ControlSidebar'
import { StatusOverview } from './features/dashboard/StatusOverview'
import { TradingChart } from './features/chart/TradingChart'
import { PositionNavigator } from './features/positions/PositionNavigator'

const DEFAULT_INDICATORS: IndicatorState = {
  showEma: true,
  showBollinger: true,
  showVolume: true,
  showRsi: true,
  showMacd: false,
  showTradeMarkers: true,
}

const DEFAULT_INDICATOR_SETTINGS: IndicatorSettings = {
  ema: { period: 20 },
  bollinger: { period: 20, std_dev: 2 },
  rsi: { period: 14 },
  macd: { fast_period: 12, slow_period: 26, signal_period: 9 },
}

function App() {
  const queryClient = useQueryClient()
  const [exchange, setExchange] = useState('binance')
  const [dataFile, setDataFile] = useState<string | null>(null)
  const [symbol, setSymbol] = useState('')
  const [timeframe, setTimeframe] = useState('1h')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [minTrades, setMinTrades] = useState(5)
  const [indicators, setIndicators] = useState(DEFAULT_INDICATORS)
  const [indicatorSettings, setIndicatorSettings] = useState(DEFAULT_INDICATOR_SETTINGS)
  const [selectedPositionId, setSelectedPositionId] = useState<string | null>(null)
  const [statusMessage, setStatusMessage] = useState('准备就绪')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [hasAutoLoaded, setHasAutoLoaded] = useState(false)
  const [rebuildForm, setRebuildForm] = useState<RebuildRequest>({
    exchange: 'binance',
    start_date: '',
    end_date: '',
    threads: 5,
    max_retries: 3,
  })

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
      setErrorMessage(null)
      setSelectedPositionId(data.positions[0]?.position_id ?? null)
    },
    onError: (error: Error) => {
      setErrorMessage(error.message)
      setStatusMessage('图表加载失败')
    },
  })

  const loadMoreMutation = useMutation({
    mutationFn: loadMoreChart,
    onSuccess: (data) => {
      if (!data.chart || !chartMutation.data) {
        setStatusMessage('没有新增K线')
        return
      }

      chartMutation.reset()
      chartMutation.mutate({
        symbol,
        timeframe,
        start_date: startDate,
        end_date: endDate,
        data_file: dataFile,
        exchange,
        indicator_settings: indicatorSettings,
      })
    },
    onError: (error: Error) => {
      setErrorMessage(error.message)
      setStatusMessage('同步更多K线失败')
    },
  })

  const rebuildMutation = useMutation({
    mutationFn: rebuildPositions,
    onSuccess: async (data) => {
      setStatusMessage(`仓位重建完成: ${data.file_path}`)
      setErrorMessage(null)
      await queryClient.invalidateQueries({ queryKey: ['data-files'] })
      setDataFile(data.file_path)
    },
    onError: (error: Error) => {
      setErrorMessage(error.message)
      setStatusMessage('仓位重建失败')
    },
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
    setRebuildForm((current) => ({
      ...current,
      exchange,
      start_date: current.start_date || defaults.start_date,
      end_date: current.end_date || defaults.end_date,
    }))
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
    if (chartMutation.data) {
      setStatusMessage(`图表已加载: ${chartMutation.data.symbol} ${chartMutation.data.timeframe}`)
    }
  }, [chartMutation.data])

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

  const positions = chartMutation.data?.positions ?? []
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
    const lastTimestamp = chartMutation.data?.chart.candlestick.at(-1)?.time
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
      setRebuildForm((current) => ({ ...current, exchange: String(value) }))
      setHasAutoLoaded(false)
      return
    }
    if (field === 'dataFile') {
      setDataFile(String(value) || null)
      setHasAutoLoaded(false)
      return
    }
    if (field === 'symbol') {
      setSymbol(String(value))
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

  function handleApplyIndicatorSettings(nextSettings: IndicatorSettings) {
    setIndicatorSettings(nextSettings)
    if (!symbol || !timeframe || !startDate || !endDate) {
      return
    }
    chartMutation.mutate({
      symbol,
      timeframe,
      start_date: startDate,
      end_date: endDate,
      data_file: dataFile,
      exchange,
      indicator_settings: nextSettings,
    })
  }

  function handleRebuildFieldChange(field: keyof RebuildRequest, value: string | number) {
    setRebuildForm((current) => ({
      ...current,
      [field]: value,
    }))
  }

  function handleRebuild() {
    rebuildMutation.mutate(rebuildForm)
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
              rebuildForm={rebuildForm}
              loadingChart={chartMutation.isPending}
              loadingMore={loadMoreMutation.isPending}
              rebuilding={rebuildMutation.isPending}
              onFieldChange={handleFieldChange}
              onIndicatorToggle={handleIndicatorToggle}
              onLoadChart={() => handleLoadChart()}
              onLoadMore={handleLoadMore}
              onRebuildFieldChange={handleRebuildFieldChange}
              onRebuild={handleRebuild}
            />

            <StatusOverview
              chartData={chartMutation.data}
              dataFileName={dataFile ? dataFile.split('/').at(-1) ?? null : null}
            />

            <PositionNavigator
              positions={positions}
              selectedPositionId={selectedPosition?.position_id ?? null}
              onSelectPosition={setSelectedPositionId}
            />
          </aside>

          <div className="space-y-3">
            <section className="rounded-[24px] border border-white/10 bg-panel/78 px-5 py-4 shadow-panel backdrop-blur">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Workspace</p>
                  <p className="mt-2 text-sm text-white">{statusMessage}</p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="rounded-full border border-white/8 bg-[#0d1424] px-3 py-1.5 text-xs text-slate-300">
                    {chartMutation.data ? `${chartMutation.data.symbol} / ${chartMutation.data.timeframe}` : '等待加载'}
                  </span>
                  <span className="rounded-full border border-white/8 bg-[#0d1424] px-3 py-1.5 text-xs text-slate-300">
                    {dataFile ? dataFile.split('/').at(-1) ?? 'CSV' : 'Exchange API'}
                  </span>
                  {errorMessage ? (
                    <p className="rounded-full border border-rose-400/30 bg-rose-500/10 px-4 py-2 text-sm text-rose-300">
                      {errorMessage}
                    </p>
                  ) : (
                    <p className="rounded-full border border-emerald-400/30 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-300">
                      运行正常
                    </p>
                  )}
                </div>
              </div>
            </section>

            <TradingChart
              chartData={chartMutation.data?.chart}
              chartSymbol={chartMutation.data?.symbol ?? symbol}
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
              onApplyIndicatorSettings={handleApplyIndicatorSettings}
            />
          </div>
        </div>
      </div>
    </main>
  )
}

export default App
