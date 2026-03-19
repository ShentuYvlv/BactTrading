import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  LineSeries,
  createSeriesMarkers,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type MouseEventParams,
  type SeriesMarker,
  type UTCTimestamp,
} from 'lightweight-charts'
import {
  ChevronDown,
  Clock3,
  Crosshair,
  Minus,
  MousePointer2,
  PanelLeftClose,
  PencilLine,
  RectangleHorizontal,
  RefreshCcw,
  Search,
  Slash,
  Square,
  Trash2,
  TrendingUp,
  ArrowUpRight,
} from 'lucide-react'
import { useEffect, useMemo, useRef, useState, type Dispatch, type MouseEvent as ReactMouseEvent, type MutableRefObject, type SetStateAction } from 'react'

import { cx, formatCompactNumber, formatNumber } from '../../lib/format'
import type {
  ChartPayload,
  IndicatorKey,
  IndicatorSettings,
  IndicatorState,
  PositionRecord,
} from '../../types/api'

interface TradingChartProps {
  chartData?: ChartPayload
  chartSymbol: string
  positions: PositionRecord[]
  indicators: IndicatorState
  indicatorSettings: IndicatorSettings
  selectedPositionId: string | null
  timeframe: string
  timeframeOptions: Array<{ label: string; value: string }>
  onSelectPosition: (positionId: string) => void
  onLoadMore: () => void
  onTimeframeShortcut: (timeframe: string) => void
  onIndicatorToggle: (indicator: IndicatorKey) => void
  onApplyIndicatorSettings: (settings: IndicatorSettings) => void
}

interface LegendState {
  time: string
  open: string
  high: string
  low: string
  close: string
  volume: string
  ema: string
  rsi: string
  macd: string
  signal: string
  delta: string
  deltaPct: string
  isUp: boolean
}

interface ChartRefs {
  chart: IChartApi
  candleSeries: ISeriesApi<'Candlestick'>
}

type SettingsPanelKey = 'ema' | 'bollinger' | 'rsi' | 'macd' | null
type DrawingTool = 'cursor' | 'select' | 'trendline' | 'arrow' | 'ray' | 'extendedLine' | 'horizontalLine' | 'verticalLine' | 'rectangle'
type DrawingPoint = { time: number; price: number }
type DrawingObject = {
  id: string
  tool: Exclude<DrawingTool, 'cursor' | 'select'>
  points: DrawingPoint[]
}
type DrawingDraft = {
  tool: Exclude<DrawingTool, 'cursor' | 'select'>
  start: DrawingPoint
  current: DrawingPoint
}
type DragState = {
  drawingId: string
  startX: number
  startY: number
  originalPoints: DrawingPoint[]
}

const QUICK_TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h', '1d']
const DEFAULT_PANEL_POSITION = { top: 96, right: 28 }
const DEFAULT_INDICATOR_SETTINGS: IndicatorSettings = {
  ema: { period: 20 },
  bollinger: { period: 20, std_dev: 2 },
  rsi: { period: 14 },
  macd: { fast_period: 12, slow_period: 26, signal_period: 9 },
}

export function TradingChart({
  chartData,
  chartSymbol,
  positions,
  indicators,
  indicatorSettings,
  selectedPositionId,
  timeframe,
  timeframeOptions,
  onSelectPosition,
  onLoadMore,
  onTimeframeShortcut,
  onIndicatorToggle,
  onApplyIndicatorSettings,
}: TradingChartProps) {
  const chartContainerRef = useRef<HTMLDivElement | null>(null)
  const chartRefs = useRef<ChartRefs | null>(null)
  const lastLegendKeyRef = useRef('')
  const rafRef = useRef<number | null>(null)
  const [legend, setLegend] = useState<LegendState | null>(null)
  const [menu, setMenu] = useState<{ x: number; y: number } | null>(null)
  const [panelPosition, setPanelPosition] = useState(DEFAULT_PANEL_POSITION)
  const [jumpValue, setJumpValue] = useState('1')
  const [settingsPanel, setSettingsPanel] = useState<SettingsPanelKey>(null)
  const [indicatorMenuOpen, setIndicatorMenuOpen] = useState(false)
  const [draftSettings, setDraftSettings] = useState<IndicatorSettings>(indicatorSettings)
  const [drawingTool, setDrawingTool] = useState<DrawingTool>('cursor')
  const [drawings, setDrawings] = useState<DrawingObject[]>([])
  const [draftDrawing, setDraftDrawing] = useState<DrawingDraft | null>(null)
  const [selectedDrawingId, setSelectedDrawingId] = useState<string | null>(null)
  const [overlayRevision, setOverlayRevision] = useState(0)
  const [pricePaneHeight, setPricePaneHeight] = useState(0)
  const dragStateRef = useRef<DragState | null>(null)

  const dataIndexes = useMemo(() => buildDataIndexes(chartData), [chartData])
  const selectedIndex = useMemo(
    () => positions.findIndex((position) => position.position_id === selectedPositionId),
    [positions, selectedPositionId],
  )
  const selectedPosition = selectedIndex >= 0 ? positions[selectedIndex] : positions[0]
  const paneOverlays = useMemo(
    () => buildPaneOverlays(indicators, indicatorSettings),
    [indicatorSettings, indicators],
  )
  const settingsError = useMemo(() => validateIndicatorSettings(draftSettings), [draftSettings])
  const activeIndicatorCount = useMemo(
    () =>
      [
        indicators.showEma,
        indicators.showBollinger,
        indicators.showVolume,
        indicators.showRsi,
        indicators.showMacd,
      ].filter(Boolean).length,
    [indicators],
  )
  const drawingStorageKey = useMemo(() => {
    if (!chartSymbol) {
      return null
    }
    return `bact_drawings_v1:${chartSymbol}`
  }, [chartSymbol])
  const renderedDrawings = useMemo(
    () =>
      drawings.flatMap((drawing) => {
        const projected = projectDrawing(drawing, chartRefs.current, pricePaneHeight, overlayRevision)
        return projected ? [projected] : []
      }),
    [drawings, overlayRevision, pricePaneHeight],
  )
  const renderedDraftDrawing = useMemo(() => {
    if (!draftDrawing) {
      return null
    }
    return projectDrawing(
      {
        id: 'draft',
        tool: draftDrawing.tool,
        points: [draftDrawing.start, draftDrawing.current],
      },
      chartRefs.current,
      pricePaneHeight,
      overlayRevision,
    )
  }, [draftDrawing, overlayRevision, pricePaneHeight])

  useEffect(() => {
    if (selectedIndex >= 0) {
      setJumpValue(String(selectedIndex + 1))
    }
  }, [selectedIndex])

  useEffect(() => {
    setDraftSettings(indicatorSettings)
  }, [indicatorSettings])

  useEffect(() => {
    if (!drawingStorageKey) {
      setDrawings([])
      return
    }

    try {
      const raw = window.localStorage.getItem(drawingStorageKey)
      if (!raw) {
        setDrawings([])
        return
      }
      const parsed = JSON.parse(raw) as DrawingObject[]
      setDrawings(Array.isArray(parsed) ? parsed : [])
    } catch {
      setDrawings([])
    }
    setDraftDrawing(null)
    setSelectedDrawingId(null)
    setDrawingTool('cursor')
  }, [drawingStorageKey])

  useEffect(() => {
    if (!drawingStorageKey) {
      return
    }
    window.localStorage.setItem(drawingStorageKey, JSON.stringify(drawings))
  }, [drawings, drawingStorageKey])

  useEffect(() => {
    if (!chartContainerRef.current || !chartData || chartData.candlestick.length === 0) {
      return undefined
    }

    const container = chartContainerRef.current
    container.innerHTML = ''

    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: '#101722' },
        textColor: '#c7d0e0',
        attributionLogo: false,
        panes: {
          separatorColor: 'rgba(148, 163, 184, 0.18)',
          separatorHoverColor: 'rgba(91, 212, 201, 0.28)',
        },
      },
      grid: {
        vertLines: { color: 'rgba(148, 163, 184, 0.18)' },
        horzLines: { color: 'rgba(148, 163, 184, 0.18)' },
      },
      crosshair: {
        mode: CrosshairMode.MagnetOHLC,
        vertLine: { color: 'rgba(91, 212, 201, 0.72)', width: 1, style: 2 },
        horzLine: { color: 'rgba(91, 212, 201, 0.3)', width: 1, style: 2 },
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: false,
      },
      handleScale: {
        mouseWheel: true,
        pinch: true,
        axisPressedMouseMove: true,
      },
      timeScale: {
        borderColor: '#263242',
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 10,
        barSpacing: 10,
      },
      rightPriceScale: {
        borderColor: '#263242',
        entireTextOnly: true,
        scaleMargins: { top: 0.08, bottom: 0.08 },
      },
    })

    const candleSeries = chart.addSeries(
      CandlestickSeries,
      {
        upColor: '#22c55e',
        downColor: '#ef4444',
        borderUpColor: '#22c55e',
        borderDownColor: '#ef4444',
        wickUpColor: '#22c55e',
        wickDownColor: '#ef4444',
        priceLineVisible: false,
      },
      0,
    )
    candleSeries.setData(toCandlestickSeriesData(chartData.candlestick))

    if (indicators.showEma) {
      const emaSeries = chart.addSeries(
        LineSeries,
        {
          color: '#f97316',
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: false,
        },
        0,
      )
      emaSeries.setData(toLineSeriesData(chartData.ema20))
    }

    if (indicators.showBollinger) {
      const upper = chart.addSeries(
        LineSeries,
        {
          color: 'rgba(125, 211, 252, 0.9)',
          lineWidth: 1,
          lineStyle: 2,
          priceLineVisible: false,
          lastValueVisible: false,
        },
        0,
      )
      const middle = chart.addSeries(
        LineSeries,
        {
          color: 'rgba(148, 163, 184, 0.8)',
          lineWidth: 1,
          priceLineVisible: false,
          lastValueVisible: false,
        },
        0,
      )
      const lower = chart.addSeries(
        LineSeries,
        {
          color: 'rgba(125, 211, 252, 0.9)',
          lineWidth: 1,
          lineStyle: 2,
          priceLineVisible: false,
          lastValueVisible: false,
        },
        0,
      )
      upper.setData(toLineSeriesData(chartData.upper_band))
      middle.setData(toLineSeriesData(chartData.middle_band))
      lower.setData(toLineSeriesData(chartData.lower_band))
    }

    let paneIndex = 1
    if (indicators.showVolume) {
      const volumeSeries = chart.addSeries(
        HistogramSeries,
        {
          priceFormat: { type: 'volume' },
          color: '#60a5fa',
          lastValueVisible: false,
          priceLineVisible: false,
        },
        paneIndex,
      )
      volumeSeries.setData(
        chartData.volume.map((item, index) => ({
          time: toUtcTime(item.time),
          value: item.volume,
          color:
            chartData.candlestick[index]?.close >= chartData.candlestick[index]?.open
              ? 'rgba(34, 197, 94, 0.65)'
              : 'rgba(239, 68, 68, 0.65)',
        })),
      )
      paneIndex += 1
    }

    if (indicators.showRsi) {
      const rsiSeries = chart.addSeries(
        LineSeries,
        {
          color: '#facc15',
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: false,
        },
        paneIndex,
      )
      rsiSeries.setData(toLineSeriesData(chartData.rsi))
      paneIndex += 1
    }

    if (indicators.showMacd) {
      const macdLine = chart.addSeries(
        LineSeries,
        {
          color: '#a78bfa',
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: false,
        },
        paneIndex,
      )
      const signalLine = chart.addSeries(
        LineSeries,
        {
          color: '#fb7185',
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: false,
        },
        paneIndex,
      )
      const histogram = chart.addSeries(
        HistogramSeries,
        {
          priceLineVisible: false,
          lastValueVisible: false,
        },
        paneIndex,
      )

      macdLine.setData(toLineSeriesData(chartData.macd))
      signalLine.setData(toLineSeriesData(chartData.signal))
      histogram.setData(
        chartData.histogram.map((item) => ({
          time: toUtcTime(item.time),
          value: item.value,
          color: item.value >= 0 ? 'rgba(34, 197, 94, 0.55)' : 'rgba(239, 68, 68, 0.55)',
        })),
      )
    }

    createSeriesMarkers(candleSeries, indicators.showTradeMarkers ? buildMarkers(positions) : [])

    chart.timeScale().fitContent()
    applyPaneWeights(chart, indicators)
    syncChartMetrics(chart, container, setPricePaneHeight, setOverlayRevision)
    updateLegendState(
      setLegend,
      lastLegendKeyRef,
      buildLegend(chartData, dataIndexes, chartData.candlestick[chartData.candlestick.length - 1]),
    )

    const handleCrosshair = (param: MouseEventParams) => {
      const candle = param.seriesData.get(candleSeries) as
        | {
            time: UTCTimestamp
            open: number
            high: number
            low: number
            close: number
          }
        | undefined
      if (!candle || candle.open === undefined) {
        return
      }
      const candleTime = Number(candle.time)
      const volume = findValueAtTime(chartData.volume, candleTime, dataIndexes?.volume)
      const ema = findValueAtTime(chartData.ema20, candleTime, dataIndexes?.ema20)
      const rsi = findValueAtTime(chartData.rsi, candleTime, dataIndexes?.rsi)
      const macd = findValueAtTime(chartData.macd, candleTime, dataIndexes?.macd)
      const signal = findValueAtTime(chartData.signal, candleTime, dataIndexes?.signal)
      const nextLegend = {
        time: formatEpoch(candleTime),
        open: formatNumber(candle.open),
        high: formatNumber(candle.high),
        low: formatNumber(candle.low),
        close: formatNumber(candle.close),
        volume: formatCompactNumber(volume, 2),
        ema: formatNumber(ema),
        rsi: formatNumber(rsi),
        macd: formatNumber(macd),
        signal: formatNumber(signal),
        delta: formatSignedNumber(candle.close - candle.open, 6),
        deltaPct: formatSignedPercent(((candle.close - candle.open) / candle.open) * 100),
        isUp: candle.close >= candle.open,
      }
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current)
      }
      rafRef.current = window.requestAnimationFrame(() => {
        updateLegendState(setLegend, lastLegendKeyRef, nextLegend)
      })
    }

    const handleClick = (param: MouseEventParams) => {
      const clickedTime = normalizeClickedTime(param.time)
      if (clickedTime === null) {
        return
      }

      const matchedPosition =
        positions.find((position) => position.open_time === clickedTime || position.close_time === clickedTime) ??
        findNearestPositionByTime(positions, clickedTime)

      if (matchedPosition) {
        onSelectPosition(matchedPosition.position_id)
      }
    }

    const scheduleOverlayRefresh = () => {
      setOverlayRevision((current) => current + 1)
      syncChartMetrics(chart, container, setPricePaneHeight)
    }

    const resizeObserver = new ResizeObserver(() => {
      chart.resize(container.clientWidth, container.clientHeight)
      scheduleOverlayRefresh()
    })
    resizeObserver.observe(container)
    chart.subscribeCrosshairMove(handleCrosshair)
    chart.subscribeClick(handleClick)
    chart.timeScale().subscribeVisibleLogicalRangeChange(scheduleOverlayRefresh)
    chart.timeScale().subscribeSizeChange(scheduleOverlayRefresh)

    const handleDoubleClick = () => chart.timeScale().fitContent()
    const handleContextMenu = (event: MouseEvent) => {
      event.preventDefault()
      setMenu({ x: event.clientX, y: event.clientY })
    }
    const handleWheel = () => scheduleOverlayRefresh()
    container.addEventListener('dblclick', handleDoubleClick)
    container.addEventListener('contextmenu', handleContextMenu)
    container.addEventListener('wheel', handleWheel)

    chartRefs.current = { chart, candleSeries }

    return () => {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current)
        rafRef.current = null
      }
      chart.unsubscribeCrosshairMove(handleCrosshair)
      chart.unsubscribeClick(handleClick)
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(scheduleOverlayRefresh)
      chart.timeScale().unsubscribeSizeChange(scheduleOverlayRefresh)
      resizeObserver.disconnect()
      container.removeEventListener('dblclick', handleDoubleClick)
      container.removeEventListener('contextmenu', handleContextMenu)
      container.removeEventListener('wheel', handleWheel)
      chart.remove()
      chartRefs.current = null
    }
  }, [chartData, dataIndexes, indicators, onSelectPosition, positions])

  useEffect(() => {
    if (!chartRefs.current || !chartData || !selectedPositionId) {
      return
    }
    const selected = positions.find((position) => position.position_id === selectedPositionId)
    if (!selected) {
      return
    }

    const candleSpacing =
      chartData.candlestick.length > 1
        ? Math.max(chartData.candlestick[1].time - chartData.candlestick[0].time, 60)
        : 3600
    const lastVisible = chartData.candlestick[chartData.candlestick.length - 1]?.time ?? selected.open_time
    chartRefs.current.chart.timeScale().setVisibleRange({
      from: toUtcTime(selected.open_time - candleSpacing * 24),
      to: toUtcTime((selected.close_time ?? lastVisible) + candleSpacing * 24),
    })
  }, [chartData, positions, selectedPositionId])

  useEffect(() => {
    setOverlayRevision((current) => current + 1)
  }, [drawings, draftDrawing, selectedDrawingId, pricePaneHeight, timeframe])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null
      if (target && ['INPUT', 'SELECT', 'TEXTAREA'].includes(target.tagName)) {
        return
      }

      if (event.key >= '1' && event.key <= '6') {
        const nextTimeframe = QUICK_TIMEFRAMES[Number(event.key) - 1]
        if (nextTimeframe) {
          onTimeframeShortcut(nextTimeframe)
        }
      }

      const lowerKey = event.key.toLowerCase()
      if (lowerKey === 'f') {
        chartRefs.current?.chart.timeScale().fitContent()
      } else if (lowerKey === 'l') {
        chartRefs.current?.chart.timeScale().scrollToRealTime()
      } else if (lowerKey === 'v') {
        setDrawingTool('cursor')
      } else if (lowerKey === 's') {
        setDrawingTool('select')
      } else if (lowerKey === 'g') {
        setDrawingTool('trendline')
      } else if (lowerKey === 'a') {
        setDrawingTool('arrow')
      } else if (lowerKey === 'r') {
        setDrawingTool('ray')
      } else if (lowerKey === 'x') {
        setDrawingTool('extendedLine')
      } else if (lowerKey === 'h') {
        setDrawingTool('horizontalLine')
      } else if (lowerKey === 'n') {
        setDrawingTool('verticalLine')
      } else if (lowerKey === 'o') {
        setDrawingTool('rectangle')
      } else if (lowerKey === 'e') {
        onIndicatorToggle('showEma')
      } else if (lowerKey === 'b') {
        onIndicatorToggle('showBollinger')
      } else if (lowerKey === 'i') {
        onIndicatorToggle('showRsi')
      } else if (lowerKey === 'm') {
        onIndicatorToggle('showMacd')
      } else if (lowerKey === 't') {
        onIndicatorToggle('showTradeMarkers')
      } else if (event.key === 'Escape') {
        setDraftDrawing(null)
        setSelectedDrawingId(null)
        setDrawingTool('cursor')
      } else if ((event.key === 'Delete' || event.key === 'Backspace') && selectedDrawingId) {
        setDrawings((current) => current.filter((drawing) => drawing.id !== selectedDrawingId))
        setSelectedDrawingId(null)
      }
    }

    const hideMenu = () => setMenu(null)
    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('click', hideMenu)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('click', hideMenu)
    }
  }, [onIndicatorToggle, onTimeframeShortcut, selectedDrawingId])

  const timeframeShortcutLabel = timeframeOptions
    .filter((option) => QUICK_TIMEFRAMES.includes(option.value))
    .map((option, index) => `${index + 1}:${option.label}`)
    .join(' / ')
  const preferredTimeframes = ['15m', '30m', '1h', '4h', '1d', '1w']
  const visibleTimeframes = timeframeOptions.filter((option) => preferredTimeframes.includes(option.value))

  return (
    <section className="relative overflow-hidden rounded-[26px] border border-white/10 bg-[#0b111b] shadow-panel">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/8 bg-[#131a24] px-4 py-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2">
            <Search className="h-4 w-4 text-slate-400" />
            <span className="text-lg font-semibold text-white">{toWorkspaceSymbol(chartSymbol)}</span>
          </div>

          <div className="flex flex-wrap items-center gap-1 rounded-full border border-white/10 bg-white/5 p-1">
            {visibleTimeframes.map((option) => (
              <button
                key={option.value}
                className={cx(
                  'rounded-full px-3 py-1.5 text-sm transition',
                  timeframe === option.value
                    ? 'bg-white/12 text-white'
                    : 'text-slate-300 hover:bg-white/8 hover:text-white',
                )}
                type="button"
                onClick={() => onTimeframeShortcut(option.value)}
              >
                {option.label}
              </button>
            ))}
            <button
              className="flex items-center gap-1 rounded-full px-3 py-1.5 text-sm text-slate-300 transition hover:bg-white/8 hover:text-white"
              type="button"
            >
              更多
              <ChevronDown className="h-4 w-4" />
            </button>
          </div>

          <button className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200">
            <Clock3 className="h-4 w-4" />
            {timeframe}
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 transition hover:border-slate-400"
            type="button"
            onClick={() => setIndicatorMenuOpen((current) => !current)}
          >
            <TrendingUp className="h-4 w-4" />
            指标 {activeIndicatorCount}
            <ChevronDown className="h-4 w-4" />
          </button>
          <IconToolbarButton icon={RefreshCcw} label="适应" onClick={() => chartRefs.current?.chart.timeScale().fitContent()} />
          <IconToolbarButton icon={Crosshair} label="最新" onClick={() => chartRefs.current?.chart.timeScale().scrollToRealTime()} />
          <IconToolbarButton icon={PanelLeftClose} label="更多K线" onClick={onLoadMore} />
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 border-b border-white/8 bg-[#0f1622] px-4 py-3 text-sm">
        <div className="flex items-center gap-2 text-white">
          <span className="inline-flex h-2.5 w-2.5 rounded-full bg-emerald-400/90" />
          <span className="font-medium">
            {chartSymbol} · {timeframe} · Review Workspace
          </span>
        </div>
        <span className={cx('font-medium', legend?.isUp ? 'text-emerald-400' : 'text-rose-400')}>
          开 {legend?.open ?? '--'} 高 {legend?.high ?? '--'} 低 {legend?.low ?? '--'} 收 {legend?.close ?? '--'} {legend?.delta ?? '--'} ({legend?.deltaPct ?? '--'})
        </span>
        <span className="text-slate-400">Vol {legend?.volume ?? '--'}</span>
        <span className="text-[#e1d35c]">EMA {legend?.ema ?? '--'}</span>
        <span className="text-[#2d60d8]">RSI {legend?.rsi ?? '--'}</span>
        <span className="text-[#53b36b]">MACD {legend?.macd ?? '--'}</span>
      </div>

      {indicatorMenuOpen ? (
        <div className="absolute right-4 top-[4.6rem] z-40 w-72 rounded-[22px] border border-white/10 bg-[#09111d]/96 p-3 shadow-2xl backdrop-blur">
          <div className="flex items-center justify-between">
            <p className="text-[11px] uppercase tracking-[0.24em] text-slate-500">Indicators</p>
            <button
              className="rounded-full border border-white/10 px-2 py-1 text-xs text-slate-300 transition hover:border-slate-400 hover:text-white"
              type="button"
              onClick={() => setIndicatorMenuOpen(false)}
            >
              关闭
            </button>
          </div>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <IndicatorToggleChip active={indicators.showEma} label="EMA" onClick={() => onIndicatorToggle('showEma')} />
            <IndicatorToggleChip active={indicators.showBollinger} label="布林带" onClick={() => onIndicatorToggle('showBollinger')} />
            <IndicatorToggleChip active={indicators.showVolume} label="成交量" onClick={() => onIndicatorToggle('showVolume')} />
            <IndicatorToggleChip active={indicators.showRsi} label="RSI" onClick={() => onIndicatorToggle('showRsi')} />
            <IndicatorToggleChip active={indicators.showMacd} label="MACD" onClick={() => onIndicatorToggle('showMacd')} />
            <IndicatorToggleChip active={indicators.showTradeMarkers} label="交易标记" onClick={() => onIndicatorToggle('showTradeMarkers')} />
          </div>
        </div>
      ) : null}

      <div className="px-2 pb-2 pt-2">
        <div className="relative">
          <div ref={chartContainerRef} className="h-[calc(100vh-11.75rem)] min-h-[46rem] w-full overflow-hidden rounded-[20px]" />

          <DrawingToolbar
            activeTool={drawingTool}
            drawingCount={drawings.length}
            onChangeTool={(tool) => {
              setDrawingTool(tool)
              if (tool === 'cursor') {
                setSelectedDrawingId(null)
              }
            }}
            onClearAll={() => {
              setDrawings([])
              setDraftDrawing(null)
              setSelectedDrawingId(null)
            }}
          />

          <div className="pointer-events-none absolute inset-0">
            {paneOverlays.map((overlay) => (
              <PaneHeader
                key={overlay.key}
                description={overlay.description}
                showSettings={overlay.showSettings}
                title={overlay.title}
                top={overlay.top}
                onSettings={() => {
                  setDraftSettings(indicatorSettings)
                  setSettingsPanel(overlay.settingsKey)
                }}
              />
            ))}
          </div>

          <div className="pointer-events-none absolute bottom-4 left-16 z-10 flex items-end gap-2 text-white/14">
            <span className="text-5xl font-black tracking-tight">BT</span>
            <span className="pb-1 text-xs uppercase tracking-[0.28em]">Review</span>
          </div>

          <div
            data-testid="drawing-overlay"
            className={cx(
              'absolute left-0 top-0 z-10 overflow-hidden rounded-t-[22px]',
              drawingTool === 'cursor' ? 'pointer-events-none' : 'pointer-events-auto',
            )}
            style={{
              width: '100%',
              height: pricePaneHeight > 0 ? `${pricePaneHeight}px` : undefined,
            }}
            onMouseDown={handleDrawingMouseDown({
              chartRefs,
              chartContainerRef,
              drawingTool,
              drawings,
              pricePaneHeight,
              setDraftDrawing,
              setDrawings,
              setOverlayRevision,
              setSelectedDrawingId,
              dragStateRef,
            })}
            onMouseMove={handleDrawingMouseMove({
              chartRefs,
              chartContainerRef,
              drawingTool,
              draftDrawing,
              pricePaneHeight,
              setDraftDrawing,
              setDrawings,
              setOverlayRevision,
              dragStateRef,
            })}
            onMouseUp={() => {
              dragStateRef.current = null
            }}
            onMouseLeave={() => {
              if (!draftDrawing) {
                dragStateRef.current = null
              }
            }}
          >
            <svg className="h-full w-full">
              {renderedDrawings.map((drawing) => (
                <DrawingShape
                  key={drawing.id}
                  drawing={drawing}
                  selected={drawing.id === selectedDrawingId}
                />
              ))}
              {renderedDraftDrawing ? <DrawingShape drawing={renderedDraftDrawing} selected={false} draft /> : null}
            </svg>
          </div>

          {settingsPanel ? (
            <IndicatorSettingsPanel
              draftSettings={draftSettings}
              error={settingsError}
              panel={settingsPanel}
              onApply={() => {
                if (settingsError) {
                  return
                }
                onApplyIndicatorSettings(draftSettings)
                setSettingsPanel(null)
              }}
              onChange={setDraftSettings}
              onClose={() => setSettingsPanel(null)}
              onReset={() => setDraftSettings(DEFAULT_INDICATOR_SETTINGS)}
            />
          ) : null}
        </div>
      </div>

      {positions.length > 0 && selectedPosition ? (
        <DraggableTradePanel
          jumpValue={jumpValue}
          panelPosition={panelPosition}
          positions={positions}
          selectedIndex={selectedIndex}
          selectedPosition={selectedPosition}
          setJumpValue={setJumpValue}
          setPanelPosition={setPanelPosition}
          onSelectPosition={onSelectPosition}
        />
      ) : null}

      <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400">
        <p>快捷键: {timeframeShortcutLabel} / F 适应 / L 最新 / V 游标 / S 选择 / G 趋势线 / A 箭头 / R 射线 / X 延长线 / H 水平 / N 垂直 / O 矩形</p>
        <div className="flex flex-wrap items-center gap-2">
          {positions.slice(0, 6).map((position, index) => (
            <button
              key={position.position_id}
              className={cx(
                'rounded-full border px-3 py-1 transition',
                position.position_id === selectedPositionId
                  ? 'border-accent bg-accent/15 text-white'
                  : 'border-line bg-panelAlt text-slate-300',
              )}
              type="button"
              onClick={() => onSelectPosition(position.position_id)}
            >
              #{index + 1}
            </button>
          ))}
        </div>
      </div>

      {menu && (
        <div
          className="fixed z-30 w-44 rounded-2xl border border-white/10 bg-[#08101d] p-2 shadow-2xl"
          style={{ left: menu.x, top: menu.y }}
        >
          <MenuItem label="适应内容" onClick={() => chartRefs.current?.chart.timeScale().fitContent()} />
          <MenuItem label="跳到最新" onClick={() => chartRefs.current?.chart.timeScale().scrollToRealTime()} />
          <MenuItem label="切换交易标记" onClick={() => onIndicatorToggle('showTradeMarkers')} />
          <MenuItem label="切换 RSI" onClick={() => onIndicatorToggle('showRsi')} />
          <MenuItem label="切换 MACD" onClick={() => onIndicatorToggle('showMacd')} />
        </div>
      )}
    </section>
  )
}

function DraggableTradePanel({
  jumpValue,
  panelPosition,
  positions,
  selectedIndex,
  selectedPosition,
  setJumpValue,
  setPanelPosition,
  onSelectPosition,
}: {
  jumpValue: string
  panelPosition: { top: number; right: number }
  positions: PositionRecord[]
  selectedIndex: number
  selectedPosition: PositionRecord
  setJumpValue: (value: string) => void
  setPanelPosition: Dispatch<SetStateAction<{ top: number; right: number }>>
  onSelectPosition: (positionId: string) => void
}) {
  const dragStateRef = useRef<{
    startX: number
    startY: number
    startTop: number
    startRight: number
  } | null>(null)

  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) => {
      if (!dragStateRef.current) {
        return
      }
      const deltaX = event.clientX - dragStateRef.current.startX
      const deltaY = event.clientY - dragStateRef.current.startY
      setPanelPosition({
        top: Math.max(12, dragStateRef.current.startTop + deltaY),
        right: Math.max(12, dragStateRef.current.startRight - deltaX),
      })
    }

    const handleMouseUp = () => {
      dragStateRef.current = null
    }

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [setPanelPosition])

  return (
    <div
      className="absolute z-20 w-64 rounded-[22px] border border-white/10 bg-[#0a1322]/95 shadow-2xl backdrop-blur"
      style={{
        top: panelPosition.top,
        right: panelPosition.right,
      }}
    >
      <div
        className="flex cursor-move items-center justify-between rounded-t-[22px] border-b border-white/10 bg-white/5 px-4 py-3"
        onMouseDown={(event) => {
          event.preventDefault()
          dragStateRef.current = {
            startX: event.clientX,
            startY: event.clientY,
            startTop: panelPosition.top,
            startRight: panelPosition.right,
          }
        }}
      >
        <span className="text-sm font-semibold text-white">仓位导航</span>
        <span className="text-xs text-slate-500">拖动</span>
      </div>

      <div className="space-y-4 p-4">
        <div className="rounded-2xl border border-white/8 bg-white/5 p-3">
          <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">
            仓位 {selectedIndex + 1}/{positions.length}
          </p>
          <p className="mt-2 text-sm font-semibold text-white">
            {selectedPosition.side === 'long' ? '多头' : '空头'}
          </p>
          <p className="mt-1 text-xs text-sky-300">{selectedPosition.open_time_formatted}</p>
          <p className="mt-1 text-xs text-amber-300">{selectedPosition.close_time_formatted}</p>
          <p
            className={cx(
              'mt-3 text-sm font-semibold',
              selectedPosition.is_profit ? 'text-emerald-400' : 'text-rose-400',
            )}
          >
            PnL {formatNumber(selectedPosition.profit, 2)}
          </p>
          <p className="mt-1 text-xs text-slate-400">
            开 {formatNumber(selectedPosition.open_price, 4)} / 平 {formatNumber(selectedPosition.close_price, 4)}
          </p>
        </div>

        <div className="flex items-center gap-2">
          <input
            className="h-10 flex-1 rounded-xl border border-line bg-panelAlt px-3 text-sm text-white outline-none focus:border-accent"
            min={1}
            max={positions.length}
            type="number"
            value={jumpValue}
            onChange={(event) => setJumpValue(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                const nextIndex = Number(jumpValue) - 1
                if (Number.isInteger(nextIndex) && nextIndex >= 0 && nextIndex < positions.length) {
                  onSelectPosition(positions[nextIndex].position_id)
                }
              }
            }}
          />
          <button
            className="rounded-xl bg-sky-500 px-3 py-2 text-sm font-medium text-white"
            type="button"
            onClick={() => {
              const nextIndex = Number(jumpValue) - 1
              if (Number.isInteger(nextIndex) && nextIndex >= 0 && nextIndex < positions.length) {
                onSelectPosition(positions[nextIndex].position_id)
              }
            }}
          >
            跳转
          </button>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <button
            className="rounded-xl border border-line bg-panelAlt px-3 py-2 text-sm text-white disabled:opacity-50"
            disabled={selectedIndex <= 0}
            type="button"
            onClick={() => onSelectPosition(positions[selectedIndex - 1].position_id)}
          >
            上一个
          </button>
          <button
            className="rounded-xl bg-accent px-3 py-2 text-sm font-medium text-ink disabled:opacity-50"
            disabled={selectedIndex < 0 || selectedIndex >= positions.length - 1}
            type="button"
            onClick={() => onSelectPosition(positions[selectedIndex + 1].position_id)}
          >
            下一个
          </button>
        </div>
      </div>
    </div>
  )
}

function IconToolbarButton({
  icon: Icon,
  label,
  onClick,
}: {
  icon: typeof RefreshCcw
  label: string
  onClick: () => void
}) {
  return (
    <button
      className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-sm text-slate-200 transition hover:border-slate-400 hover:text-white"
      type="button"
      onClick={onClick}
    >
      <Icon className="h-4 w-4" />
      {label}
    </button>
  )
}

function IndicatorToggleChip({ active, label, onClick }: { active: boolean; label: string; onClick: () => void }) {
  return (
    <button
      className={cx(
        'rounded-xl border px-3 py-2 text-sm transition',
        active
          ? 'border-sky-400 bg-sky-500/18 text-white'
          : 'border-white/8 bg-white/5 text-slate-300 hover:border-slate-400',
      )}
      type="button"
      onClick={onClick}
    >
      {label}
    </button>
  )
}

function DrawingToolbar({
  activeTool,
  drawingCount,
  onChangeTool,
  onClearAll,
}: {
  activeTool: DrawingTool
  drawingCount: number
  onChangeTool: (tool: DrawingTool) => void
  onClearAll: () => void
}) {
  const tools: Array<{ tool: DrawingTool; label: string; icon: typeof MousePointer2 }> = [
    { tool: 'cursor', label: '游标', icon: MousePointer2 },
    { tool: 'select', label: '选择', icon: Crosshair },
    { tool: 'trendline', label: '趋势线', icon: TrendingUp },
    { tool: 'arrow', label: '箭头线', icon: ArrowUpRight },
    { tool: 'ray', label: '射线', icon: PencilLine },
    { tool: 'extendedLine', label: '延长线', icon: Slash },
    { tool: 'horizontalLine', label: '水平线', icon: Minus },
    { tool: 'verticalLine', label: '垂直线', icon: RectangleHorizontal },
    { tool: 'rectangle', label: '矩形', icon: Square },
  ]

  return (
    <div className="absolute left-3 top-4 z-20 flex flex-col gap-2 rounded-[18px] border border-white/10 bg-[#0a111b]/94 p-2 shadow-2xl backdrop-blur">
      {tools.map((item) => (
        <button
          key={item.tool}
          className={cx(
            'group flex h-11 w-11 items-center justify-center rounded-xl border transition',
            activeTool === item.tool
              ? 'border-sky-400 bg-sky-500/18 text-white shadow-lg'
              : 'border-white/8 bg-transparent text-slate-300 hover:border-slate-400 hover:bg-white/6 hover:text-white',
          )}
          title={item.label}
          type="button"
          onClick={() => onChangeTool(item.tool)}
        >
          <item.icon className="h-5 w-5" />
        </button>
      ))}
      <button
        className="flex h-11 w-11 items-center justify-center rounded-xl border border-rose-400/20 bg-rose-500/8 text-rose-200 transition hover:border-rose-400/50"
        title={`清空 ${drawingCount}`}
        type="button"
        onClick={onClearAll}
      >
        <Trash2 className="h-5 w-5" />
      </button>
    </div>
  )
}

function DrawingShape({
  drawing,
  selected,
  draft,
}: {
  drawing: ProjectedDrawing
  selected: boolean
  draft?: boolean
}) {
  const stroke = draft ? 'rgba(125, 211, 252, 0.95)' : selected ? '#fbbf24' : '#7dd3fc'
  const strokeWidth = selected ? 2.5 : 1.75
  const fill = draft ? 'rgba(125, 211, 252, 0.12)' : selected ? 'rgba(251, 191, 36, 0.12)' : 'rgba(125, 211, 252, 0.08)'

  if (drawing.kind === 'line') {
    const angle = Math.atan2(drawing.y2 - drawing.y1, drawing.x2 - drawing.x1)
    const arrowSize = 10
    return (
      <g>
        <line x1={drawing.x1} x2={drawing.x2} y1={drawing.y1} y2={drawing.y2} stroke={stroke} strokeWidth={strokeWidth} />
        {drawing.arrowHead ? (
          <polygon
            fill={stroke}
            points={[
              `${drawing.x2},${drawing.y2}`,
              `${drawing.x2 - arrowSize * Math.cos(angle - Math.PI / 6)},${drawing.y2 - arrowSize * Math.sin(angle - Math.PI / 6)}`,
              `${drawing.x2 - arrowSize * Math.cos(angle + Math.PI / 6)},${drawing.y2 - arrowSize * Math.sin(angle + Math.PI / 6)}`,
            ].join(' ')}
          />
        ) : null}
        {selected ? (
          <>
            <circle cx={drawing.x1} cy={drawing.y1} fill="#0b1020" r="4" stroke={stroke} strokeWidth="1.5" />
            <circle cx={drawing.x2} cy={drawing.y2} fill="#0b1020" r="4" stroke={stroke} strokeWidth="1.5" />
          </>
        ) : null}
      </g>
    )
  }

  return (
    <g>
      <rect
        fill={fill}
        height={drawing.height}
        stroke={stroke}
        strokeWidth={strokeWidth}
        width={drawing.width}
        x={drawing.x}
        y={drawing.y}
      />
      {selected ? (
        <>
          <circle cx={drawing.x} cy={drawing.y} fill="#0b1020" r="4" stroke={stroke} strokeWidth="1.5" />
          <circle cx={drawing.x + drawing.width} cy={drawing.y + drawing.height} fill="#0b1020" r="4" stroke={stroke} strokeWidth="1.5" />
        </>
      ) : null}
    </g>
  )
}

function PaneHeader({
  title,
  description,
  top,
  showSettings,
  onSettings,
}: {
  title: string
  description: string
  top: string
  showSettings: boolean
  onSettings: () => void
}) {
  return (
    <div className="absolute left-3 right-3 z-20 flex items-start justify-between" style={{ top }}>
      <div className="pointer-events-auto inline-flex max-w-[70%] items-center gap-2 rounded-full border border-white/10 bg-[#08111d]/92 px-3 py-1.5 text-[11px] text-slate-200 shadow-lg backdrop-blur">
        <span className="font-semibold text-white">{title}</span>
        <span className="truncate text-slate-400">{description}</span>
      </div>
      {showSettings ? (
        <button
          className="pointer-events-auto rounded-full border border-white/10 bg-[#08111d]/92 px-3 py-1.5 text-[11px] font-medium text-slate-200 shadow-lg transition hover:border-sky-400/50 hover:text-white"
          type="button"
          onClick={onSettings}
        >
          设置
        </button>
      ) : null}
    </div>
  )
}

function IndicatorSettingsPanel({
  panel,
  draftSettings,
  error,
  onChange,
  onApply,
  onClose,
  onReset,
}: {
  panel: Exclude<SettingsPanelKey, null>
  draftSettings: IndicatorSettings
  error: string | null
  onChange: Dispatch<SetStateAction<IndicatorSettings>>
  onApply: () => void
  onClose: () => void
  onReset: () => void
}) {
  return (
    <div className="absolute right-4 top-4 z-20 w-[22rem] rounded-[24px] border border-white/10 bg-[#07101b]/95 p-4 shadow-2xl backdrop-blur">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">Indicator Settings</p>
          <h3 className="mt-2 text-base font-semibold text-white">{panelTitle(panel)}</h3>
        </div>
        <button
          className="rounded-full border border-white/10 px-3 py-1 text-xs text-slate-300 transition hover:border-slate-400 hover:text-white"
          type="button"
          onClick={onClose}
        >
          关闭
        </button>
      </div>

      <div className="mt-4 space-y-3">
        {panel === 'ema' ? (
          <>
            <NumericField
              label="EMA 周期"
              step={1}
              value={draftSettings.ema.period}
              onChange={(value) =>
                onChange((current) => ({
                  ...current,
                  ema: { ...current.ema, period: clampInteger(value, 1, 500) },
                }))
              }
            />
            <NumericField
              label="布林周期"
              step={1}
              value={draftSettings.bollinger.period}
              onChange={(value) =>
                onChange((current) => ({
                  ...current,
                  bollinger: { ...current.bollinger, period: clampInteger(value, 1, 500) },
                }))
              }
            />
            <NumericField
              label="布林标准差倍数"
              step={0.1}
              value={draftSettings.bollinger.std_dev}
              onChange={(value) =>
                onChange((current) => ({
                  ...current,
                  bollinger: { ...current.bollinger, std_dev: clampFloat(value, 0.1, 10) },
                }))
              }
            />
          </>
        ) : null}

        {panel === 'bollinger' ? (
          <>
            <NumericField
              label="布林周期"
              step={1}
              value={draftSettings.bollinger.period}
              onChange={(value) =>
                onChange((current) => ({
                  ...current,
                  bollinger: { ...current.bollinger, period: clampInteger(value, 1, 500) },
                }))
              }
            />
            <NumericField
              label="标准差倍数"
              step={0.1}
              value={draftSettings.bollinger.std_dev}
              onChange={(value) =>
                onChange((current) => ({
                  ...current,
                  bollinger: { ...current.bollinger, std_dev: clampFloat(value, 0.1, 10) },
                }))
              }
            />
          </>
        ) : null}

        {panel === 'rsi' ? (
          <NumericField
            label="RSI 周期"
            step={1}
            value={draftSettings.rsi.period}
            onChange={(value) =>
              onChange((current) => ({
                ...current,
                rsi: { ...current.rsi, period: clampInteger(value, 1, 500) },
              }))
            }
          />
        ) : null}

        {panel === 'macd' ? (
          <>
            <NumericField
              label="快线周期"
              step={1}
              value={draftSettings.macd.fast_period}
              onChange={(value) =>
                onChange((current) => ({
                  ...current,
                  macd: { ...current.macd, fast_period: clampInteger(value, 1, 500) },
                }))
              }
            />
            <NumericField
              label="慢线周期"
              step={1}
              value={draftSettings.macd.slow_period}
              onChange={(value) =>
                onChange((current) => ({
                  ...current,
                  macd: { ...current.macd, slow_period: clampInteger(value, 1, 500) },
                }))
              }
            />
            <NumericField
              label="信号线周期"
              step={1}
              value={draftSettings.macd.signal_period}
              onChange={(value) =>
                onChange((current) => ({
                  ...current,
                  macd: { ...current.macd, signal_period: clampInteger(value, 1, 500) },
                }))
              }
            />
          </>
        ) : null}
      </div>

      <div className="mt-4 rounded-2xl border border-white/8 bg-white/5 px-3 py-2 text-xs text-slate-400">
        {panelDescription(panel, draftSettings)}
      </div>

      {error ? (
        <div className="mt-3 rounded-2xl border border-rose-400/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-200">
          {error}
        </div>
      ) : null}

      <div className="mt-4 flex items-center justify-between gap-3">
        <button
          className="rounded-full border border-white/10 px-3 py-2 text-sm text-slate-300 transition hover:border-slate-400 hover:text-white"
          type="button"
          onClick={onReset}
        >
          恢复默认
        </button>
        <div className="flex items-center gap-2">
          <button
            className="rounded-full border border-white/10 px-3 py-2 text-sm text-slate-300 transition hover:border-slate-400 hover:text-white"
            type="button"
            onClick={onClose}
          >
            取消
          </button>
          <button
            className="rounded-full bg-sky-500 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-600"
            disabled={Boolean(error)}
            type="button"
            onClick={onApply}
          >
            应用
          </button>
        </div>
      </div>
    </div>
  )
}

function NumericField({
  label,
  value,
  step,
  onChange,
}: {
  label: string
  value: number
  step: number
  onChange: (value: number) => void
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs font-medium text-slate-300">{label}</span>
      <input
        className="h-11 w-full rounded-2xl border border-white/10 bg-[#0d1626] px-3 text-sm text-white outline-none transition focus:border-sky-400"
        step={step}
        type="number"
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
      />
    </label>
  )
}

function MenuItem({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      className="block w-full rounded-xl px-3 py-2 text-left text-sm text-slate-200 transition hover:bg-white/8"
      type="button"
      onClick={onClick}
    >
      {label}
    </button>
  )
}

type ProjectedDrawing =
  | { id: string; kind: 'line'; x1: number; y1: number; x2: number; y2: number; arrowHead?: boolean }
  | { id: string; kind: 'rect'; x: number; y: number; width: number; height: number }

function handleDrawingMouseDown({
  chartRefs,
  chartContainerRef,
  drawingTool,
  drawings,
  pricePaneHeight,
  setDraftDrawing,
  setDrawings,
  setOverlayRevision,
  setSelectedDrawingId,
  dragStateRef,
}: {
  chartRefs: MutableRefObject<ChartRefs | null>
  chartContainerRef: MutableRefObject<HTMLDivElement | null>
  drawingTool: DrawingTool
  drawings: DrawingObject[]
  pricePaneHeight: number
  setDraftDrawing: Dispatch<SetStateAction<DrawingDraft | null>>
  setDrawings: Dispatch<SetStateAction<DrawingObject[]>>
  setOverlayRevision: Dispatch<SetStateAction<number>>
  setSelectedDrawingId: Dispatch<SetStateAction<string | null>>
  dragStateRef: MutableRefObject<DragState | null>
}) {
  return (event: ReactMouseEvent<HTMLDivElement>) => {
    if (pricePaneHeight <= 0) {
      return
    }
    const point = resolveDrawingPoint(event, chartRefs.current, chartContainerRef.current, pricePaneHeight)
    if (!point) {
      return
    }

    if (drawingTool === 'select') {
      const hit = hitTestDrawings(drawings, chartRefs.current, point.x, point.y, pricePaneHeight)
      setSelectedDrawingId(hit?.id ?? null)
      if (hit) {
        dragStateRef.current = {
          drawingId: hit.id,
          startX: point.x,
          startY: point.y,
          originalPoints: hit.source.points,
        }
      }
      return
    }

    if (drawingTool === 'cursor') {
      return
    }

    if (drawingTool === 'horizontalLine') {
      const nextDrawing = createDrawingObject('horizontalLine', [point.data, point.data])
      setDrawings((current) => [...current, nextDrawing])
      setSelectedDrawingId(nextDrawing.id)
      setOverlayRevision((current) => current + 1)
      return
    }

    if (drawingTool === 'verticalLine') {
      const nextDrawing = createDrawingObject('verticalLine', [point.data, point.data])
      setDrawings((current) => [...current, nextDrawing])
      setSelectedDrawingId(nextDrawing.id)
      setOverlayRevision((current) => current + 1)
      return
    }

    setDraftDrawing((current) => {
      if (!current || current.tool !== drawingTool) {
        return {
          tool: drawingTool,
          start: point.data,
          current: point.data,
        }
      }

      const nextDrawing = createDrawingObject(current.tool, [current.start, point.data])
      setDrawings((items) => [...items, nextDrawing])
      setSelectedDrawingId(nextDrawing.id)
      return null
    })
  }
}

function handleDrawingMouseMove({
  chartRefs,
  chartContainerRef,
  drawingTool,
  draftDrawing,
  pricePaneHeight,
  setDraftDrawing,
  setDrawings,
  setOverlayRevision,
  dragStateRef,
}: {
  chartRefs: MutableRefObject<ChartRefs | null>
  chartContainerRef: MutableRefObject<HTMLDivElement | null>
  drawingTool: DrawingTool
  draftDrawing: DrawingDraft | null
  pricePaneHeight: number
  setDraftDrawing: Dispatch<SetStateAction<DrawingDraft | null>>
  setDrawings: Dispatch<SetStateAction<DrawingObject[]>>
  setOverlayRevision: Dispatch<SetStateAction<number>>
  dragStateRef: MutableRefObject<DragState | null>
}) {
  return (event: ReactMouseEvent<HTMLDivElement>) => {
    if (pricePaneHeight <= 0) {
      return
    }
    const point = resolveDrawingPoint(event, chartRefs.current, chartContainerRef.current, pricePaneHeight)
    if (!point) {
      return
    }

    if (draftDrawing && drawingTool !== 'cursor' && drawingTool !== 'select') {
      setDraftDrawing((current) => (current ? { ...current, current: point.data } : current))
      setOverlayRevision((current) => current + 1)
      return
    }

    if (!dragStateRef.current || !chartRefs.current) {
      return
    }

    const deltaX = point.x - dragStateRef.current.startX
    const deltaY = point.y - dragStateRef.current.startY
    setDrawings((current) =>
      current.map((drawing) => {
        if (drawing.id !== dragStateRef.current?.drawingId) {
          return drawing
        }
        const movedPoints = dragStateRef.current.originalPoints
          .map((originalPoint) => shiftDrawingPoint(originalPoint, deltaX, deltaY, chartRefs.current))
          .filter(Boolean) as DrawingPoint[]
        if (movedPoints.length !== drawing.points.length) {
          return drawing
        }
        return {
          ...drawing,
          points: movedPoints,
        }
      }),
    )
    setOverlayRevision((current) => current + 1)
  }
}

function resolveDrawingPoint(
  event: ReactMouseEvent<HTMLDivElement>,
  refs: ChartRefs | null,
  container: HTMLDivElement | null,
  pricePaneHeight: number,
) {
  if (!refs || !container) {
    return null
  }
  const rect = container.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top
  if (x < 0 || y < 0 || y > pricePaneHeight) {
    return null
  }
  const time = normalizeClickedTime(refs.chart.timeScale().coordinateToTime(x))
  const price = refs.candleSeries.coordinateToPrice(y)
  if (time === null || price === null) {
    return null
  }
  return {
    x,
    y,
    data: {
      time,
      price: Number(price),
    },
  }
}

function createDrawingObject(
  tool: Exclude<DrawingTool, 'cursor' | 'select'>,
  points: DrawingPoint[],
): DrawingObject {
  return {
    id: createDrawingId(),
    tool,
    points,
  }
}

function createDrawingId() {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `drawing_${Date.now()}_${Math.random().toString(16).slice(2)}`
}

function shiftDrawingPoint(point: DrawingPoint, deltaX: number, deltaY: number, refs: ChartRefs | null) {
  if (!refs) {
    return null
  }
  const x = refs.chart.timeScale().timeToCoordinate(toUtcTime(point.time))
  const y = refs.candleSeries.priceToCoordinate(point.price)
  if (x === null || y === null) {
    return null
  }
  const nextTime = normalizeClickedTime(refs.chart.timeScale().coordinateToTime(x + deltaX))
  const nextPrice = refs.candleSeries.coordinateToPrice(y + deltaY)
  if (nextTime === null || nextPrice === null) {
    return null
  }
  return {
    time: nextTime,
    price: Number(nextPrice),
  }
}

function projectDrawing(
  drawing: DrawingObject,
  refs: ChartRefs | null,
  pricePaneHeight: number,
  _revision: number,
): ProjectedDrawing | null {
  if (!refs || pricePaneHeight <= 0) {
    return null
  }

  const [firstPoint, secondPoint] = drawing.points
  const x1 = refs.chart.timeScale().timeToCoordinate(toUtcTime(firstPoint.time))
  const y1 = refs.candleSeries.priceToCoordinate(firstPoint.price)
  if (x1 === null || y1 === null) {
    return null
  }

  if (drawing.tool === 'horizontalLine') {
    return { id: drawing.id, kind: 'line', x1: 0, y1, x2: refs.chart.timeScale().width(), y2: y1 }
  }

  if (drawing.tool === 'verticalLine') {
    return { id: drawing.id, kind: 'line', x1, y1: 0, x2: x1, y2: pricePaneHeight }
  }

  const x2Base = refs.chart.timeScale().timeToCoordinate(toUtcTime(secondPoint.time))
  const y2Base = refs.candleSeries.priceToCoordinate(secondPoint.price)
  if (x2Base === null || y2Base === null) {
    return null
  }

  if (drawing.tool === 'rectangle') {
    return {
      id: drawing.id,
      kind: 'rect',
      x: Math.min(x1, x2Base),
      y: Math.min(y1, y2Base),
      width: Math.abs(x2Base - x1),
      height: Math.abs(y2Base - y1),
    }
  }

  if (drawing.tool === 'trendline') {
    return { id: drawing.id, kind: 'line', x1, y1, x2: x2Base, y2: y2Base }
  }

  if (drawing.tool === 'arrow') {
    return { id: drawing.id, kind: 'line', x1, y1, x2: x2Base, y2: y2Base, arrowHead: true }
  }

  const extended = extendLineToBounds(x1, y1, x2Base, y2Base, refs.chart.timeScale().width(), pricePaneHeight, drawing.tool)
  return extended ? { id: drawing.id, kind: 'line', ...extended } : null
}

function hitTestDrawings(
  drawings: DrawingObject[],
  refs: ChartRefs | null,
  x: number,
  y: number,
  pricePaneHeight: number,
) {
  const tolerance = 8
  for (let index = drawings.length - 1; index >= 0; index -= 1) {
    const source = drawings[index]
    const projected = projectDrawing(source, refs, pricePaneHeight, 0)
    if (!projected) {
      continue
    }

    if (projected.kind === 'line') {
      if (distanceToSegment(x, y, projected.x1, projected.y1, projected.x2, projected.y2) <= tolerance) {
        return { id: source.id, source }
      }
      continue
    }

    const withinRect =
      x >= projected.x - tolerance &&
      x <= projected.x + projected.width + tolerance &&
      y >= projected.y - tolerance &&
      y <= projected.y + projected.height + tolerance
    if (withinRect) {
      return { id: source.id, source }
    }
  }
  return null
}

function extendLineToBounds(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  width: number,
  height: number,
  tool: 'ray' | 'extendedLine',
) {
  const dx = x2 - x1
  const dy = y2 - y1
  if (Math.abs(dx) < 0.0001 && Math.abs(dy) < 0.0001) {
    return null
  }

  const intersections = collectLineIntersections(x1, y1, dx, dy, width, height)
  if (intersections.length < 2) {
    return null
  }

  if (tool === 'extendedLine') {
    return intersections[0].t <= intersections[1].t
      ? { x1: intersections[0].x, y1: intersections[0].y, x2: intersections[1].x, y2: intersections[1].y }
      : { x1: intersections[1].x, y1: intersections[1].y, x2: intersections[0].x, y2: intersections[0].y }
  }

  const forward = intersections.filter((item) => item.t >= 0).sort((left, right) => left.t - right.t)
  const furthest = forward.at(-1)
  if (!furthest) {
    return null
  }
  return { x1, y1, x2: furthest.x, y2: furthest.y }
}

function collectLineIntersections(
  x1: number,
  y1: number,
  dx: number,
  dy: number,
  width: number,
  height: number,
) {
  const candidates: Array<{ x: number; y: number; t: number }> = []
  const pushCandidate = (t: number) => {
    const x = x1 + dx * t
    const y = y1 + dy * t
    if (x >= -1 && x <= width + 1 && y >= -1 && y <= height + 1) {
      candidates.push({ x: clamp(x, 0, width), y: clamp(y, 0, height), t })
    }
  }

  if (Math.abs(dx) > 0.0001) {
    pushCandidate((0 - x1) / dx)
    pushCandidate((width - x1) / dx)
  }
  if (Math.abs(dy) > 0.0001) {
    pushCandidate((0 - y1) / dy)
    pushCandidate((height - y1) / dy)
  }

  return dedupeIntersections(candidates).sort((left, right) => left.t - right.t)
}

function dedupeIntersections(points: Array<{ x: number; y: number; t: number }>) {
  return points.filter(
    (point, index) =>
      points.findIndex((item) => Math.abs(item.x - point.x) < 0.5 && Math.abs(item.y - point.y) < 0.5) === index,
  )
}

function distanceToSegment(px: number, py: number, x1: number, y1: number, x2: number, y2: number) {
  const dx = x2 - x1
  const dy = y2 - y1
  if (dx === 0 && dy === 0) {
    return Math.hypot(px - x1, py - y1)
  }
  const t = clamp(((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy), 0, 1)
  const projectionX = x1 + dx * t
  const projectionY = y1 + dy * t
  return Math.hypot(px - projectionX, py - projectionY)
}

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value))
}

function syncChartMetrics(
  chart: IChartApi,
  container: HTMLDivElement,
  setPricePaneHeight: Dispatch<SetStateAction<number>>,
  setOverlayRevision?: Dispatch<SetStateAction<number>>,
) {
  const paneHeight = chart.panes()[0]?.getHeight() ?? Math.max(container.clientHeight - chart.timeScale().height(), 0)
  setPricePaneHeight(paneHeight)
  if (setOverlayRevision) {
    setOverlayRevision((current) => current + 1)
  }
}

function buildMarkers(positions: PositionRecord[]): SeriesMarker<UTCTimestamp>[] {
  return positions.flatMap((position, index) => {
    const openMarker: SeriesMarker<UTCTimestamp> = {
      time: toUtcTime(position.open_time),
      position: position.side === 'long' ? 'belowBar' : 'aboveBar',
      shape: position.side === 'long' ? 'arrowUp' : 'arrowDown',
      color: position.side === 'long' ? '#22c55e' : '#ef4444',
      text: `#${index + 1} Open`,
    }
    const closeMarkers =
      position.close_time === null
        ? []
        : [
            {
              time: toUtcTime(position.close_time),
              position: position.side === 'long' ? 'aboveBar' : 'belowBar',
              shape: 'circle',
              color: position.is_profit ? '#22c55e' : '#ef4444',
              text: `#${index + 1} Close`,
            } satisfies SeriesMarker<UTCTimestamp>,
          ]
    return [openMarker, ...closeMarkers]
  })
}

function toUtcTime(time: number) {
  return time as UTCTimestamp
}

function toLineSeriesData(rows: Array<{ time: number; value: number }>) {
  return rows.map((row) => ({
    time: toUtcTime(row.time),
    value: row.value,
  }))
}

function toCandlestickSeriesData(
  rows: Array<{ time: number; open: number; high: number; low: number; close: number }>,
) {
  return rows.map((row) => ({
    time: toUtcTime(row.time),
    open: row.open,
    high: row.high,
    low: row.low,
    close: row.close,
  }))
}

function findValueAtTime(
  rows: Array<{ time: number; value?: number; volume?: number }>,
  time: number,
  index?: Map<number, number>,
) {
  const indexedValue = index?.get(time)
  if (indexedValue !== undefined) {
    return indexedValue
  }
  const match = rows.find((row) => row.time === time)
  return match?.value ?? match?.volume ?? null
}

function formatEpoch(time: number) {
  return new Date(time * 1000).toLocaleString('zh-CN', {
    hour12: false,
  })
}

function formatSignedNumber(value: number, digits = 2) {
  if (!Number.isFinite(value)) {
    return '--'
  }
  const formatted = formatNumber(Math.abs(value), digits)
  return `${value >= 0 ? '+' : '-'}${formatted}`
}

function formatSignedPercent(value: number, digits = 2) {
  if (!Number.isFinite(value)) {
    return '--'
  }
  return `${value >= 0 ? '+' : '-'}${Math.abs(value).toFixed(digits)}%`
}

function toWorkspaceSymbol(symbol: string) {
  return symbol.replace('/USDT:USDT', 'USDT.P').replace(':USDT', '')
}

function buildLegend(
  chartData: ChartPayload,
  dataIndexes: ReturnType<typeof buildDataIndexes>,
  candle: { time: number; open: number; high: number; low: number; close: number },
): LegendState {
  const time = candle.time
  return {
    time: formatEpoch(time),
    open: formatNumber(candle.open),
    high: formatNumber(candle.high),
    low: formatNumber(candle.low),
    close: formatNumber(candle.close),
    volume: formatCompactNumber(findValueAtTime(chartData.volume, time, dataIndexes?.volume), 2),
    ema: formatNumber(findValueAtTime(chartData.ema20, time, dataIndexes?.ema20)),
    rsi: formatNumber(findValueAtTime(chartData.rsi, time, dataIndexes?.rsi)),
    macd: formatNumber(findValueAtTime(chartData.macd, time, dataIndexes?.macd)),
    signal: formatNumber(findValueAtTime(chartData.signal, time, dataIndexes?.signal)),
    delta: formatSignedNumber(candle.close - candle.open, 6),
    deltaPct: formatSignedPercent(((candle.close - candle.open) / candle.open) * 100),
    isUp: candle.close >= candle.open,
  }
}

function buildDataIndexes(chartData?: ChartPayload) {
  if (!chartData) {
    return null
  }

  return {
    volume: new Map(chartData.volume.map((row) => [row.time, row.volume])),
    ema20: new Map(chartData.ema20.map((row) => [row.time, row.value])),
    rsi: new Map(chartData.rsi.map((row) => [row.time, row.value])),
    macd: new Map(chartData.macd.map((row) => [row.time, row.value])),
    signal: new Map(chartData.signal.map((row) => [row.time, row.value])),
  }
}

function updateLegendState(
  setLegend: Dispatch<SetStateAction<LegendState | null>>,
  lastLegendKeyRef: MutableRefObject<string>,
  nextLegend: LegendState,
) {
  const nextKey = Object.values(nextLegend).join('|')
  if (lastLegendKeyRef.current === nextKey) {
    return
  }
  lastLegendKeyRef.current = nextKey
  setLegend(nextLegend)
}

function normalizeClickedTime(time: unknown) {
  if (typeof time === 'number') {
    return time
  }
  if (
    time &&
    typeof time === 'object' &&
    'year' in time &&
    'month' in time &&
    'day' in time
  ) {
    const businessDay = time as { year: number; month: number; day: number }
    return Math.floor(Date.UTC(businessDay.year, businessDay.month - 1, businessDay.day) / 1000)
  }
  return null
}

function findNearestPositionByTime(positions: PositionRecord[], clickedTime: number) {
  if (positions.length === 0) {
    return null
  }
  let nearest: PositionRecord | null = null
  let minDelta = Number.POSITIVE_INFINITY

  positions.forEach((position) => {
    const deltas = [
      Math.abs(position.open_time - clickedTime),
      position.close_time === null ? Number.POSITIVE_INFINITY : Math.abs(position.close_time - clickedTime),
    ]
    const delta = Math.min(...deltas)
    if (delta < minDelta && delta <= 2 * 60 * 60) {
      minDelta = delta
      nearest = position
    }
  })

  return nearest
}

function buildPaneOverlays(indicators: IndicatorState, indicatorSettings: IndicatorSettings) {
  const weights = buildPaneWeights(indicators)
  let cumulative = 0

  return weights.map((pane, index) => {
    const top = `calc(${(cumulative / 1) * 100}% + 10px)`
    cumulative += pane.weight
    return {
      ...pane,
      key: `${pane.key}-${index}`,
      top,
      title: paneTitle(pane.key, indicatorSettings),
      description: paneDescription(pane.key, indicatorSettings),
      showSettings: !['volume', 'price'].includes(pane.key),
      settingsKey: pane.key === 'volume' || pane.key === 'price' ? null : pane.key,
    }
  })
}

function buildPaneWeights(indicators: IndicatorState) {
  const panes: Array<{ key: 'price' | 'ema' | 'bollinger' | 'volume' | 'rsi' | 'macd'; weight: number }> = []
  panes.push({
    key: indicators.showEma ? 'ema' : indicators.showBollinger ? 'bollinger' : 'price',
    weight: 0.62,
  })
  if (indicators.showVolume) {
    panes.push({ key: 'volume', weight: 0.14 })
  }
  if (indicators.showRsi) {
    panes.push({ key: 'rsi', weight: 0.12 })
  }
  if (indicators.showMacd) {
    panes.push({ key: 'macd', weight: 0.12 })
  }
  return panes
}

function paneTitle(
  key: 'price' | 'ema' | 'bollinger' | 'volume' | 'rsi' | 'macd',
  indicatorSettings: IndicatorSettings,
) {
  if (key === 'price') {
    return 'PRICE'
  }
  if (key === 'ema' && indicatorSettings.ema) {
    const parts = [`EMA(${indicatorSettings.ema.period})`]
    if (indicatorSettings.bollinger) {
      parts.push(`BOLL(${indicatorSettings.bollinger.period}, ${indicatorSettings.bollinger.std_dev})`)
    }
    return parts.join('  ')
  }
  if (key === 'bollinger') {
    return `BOLL(${indicatorSettings.bollinger.period}, ${indicatorSettings.bollinger.std_dev})`
  }
  if (key === 'volume') {
    return 'VOL'
  }
  if (key === 'rsi') {
    return `RSI(${indicatorSettings.rsi.period})`
  }
  return `MACD(${indicatorSettings.macd.fast_period}, ${indicatorSettings.macd.slow_period}, ${indicatorSettings.macd.signal_period})`
}

function paneDescription(
  key: 'price' | 'ema' | 'bollinger' | 'volume' | 'rsi' | 'macd',
  indicatorSettings: IndicatorSettings,
) {
  if (key === 'price') {
    return '主图 K 线'
  }
  if (key === 'ema') {
    return '主图均线与布林带参数'
  }
  if (key === 'bollinger') {
    return `周期 ${indicatorSettings.bollinger.period} / 倍数 ${indicatorSettings.bollinger.std_dev}`
  }
  if (key === 'volume') {
    return '成交量副图'
  }
  if (key === 'rsi') {
    return `周期 ${indicatorSettings.rsi.period}`
  }
  return `快 ${indicatorSettings.macd.fast_period} / 慢 ${indicatorSettings.macd.slow_period} / 信号 ${indicatorSettings.macd.signal_period}`
}

function panelTitle(panel: Exclude<SettingsPanelKey, null>) {
  if (panel === 'ema') {
    return 'EMA 参数'
  }
  if (panel === 'bollinger') {
    return '布林带参数'
  }
  if (panel === 'rsi') {
    return 'RSI 参数'
  }
  return 'MACD 参数'
}

function panelDescription(panel: Exclude<SettingsPanelKey, null>, settings: IndicatorSettings) {
  if (panel === 'ema') {
    return `当前使用 EMA(${settings.ema.period})，主图会同步刷新均线位置。`
  }
  if (panel === 'bollinger') {
    return `当前使用 BOLL(${settings.bollinger.period}, ${settings.bollinger.std_dev})，会同步刷新上下轨和中轨。`
  }
  if (panel === 'rsi') {
    return `当前使用 RSI(${settings.rsi.period})，适合观察超买超卖节奏。`
  }
  return `当前使用 MACD(${settings.macd.fast_period}, ${settings.macd.slow_period}, ${settings.macd.signal_period})。`
}

function validateIndicatorSettings(settings: IndicatorSettings) {
  if (settings.ema.period < 1) {
    return 'EMA 周期必须大于 0'
  }
  if (settings.bollinger.period < 1 || settings.bollinger.std_dev <= 0) {
    return '布林带周期和标准差倍数都必须大于 0'
  }
  if (settings.rsi.period < 1) {
    return 'RSI 周期必须大于 0'
  }
  if (settings.macd.fast_period >= settings.macd.slow_period) {
    return 'MACD 快线周期必须小于慢线周期'
  }
  if (settings.macd.signal_period < 1) {
    return 'MACD 信号线周期必须大于 0'
  }
  return null
}

function clampInteger(value: number, min: number, max: number) {
  if (!Number.isFinite(value)) {
    return min
  }
  return Math.min(max, Math.max(min, Math.round(value)))
}

function clampFloat(value: number, min: number, max: number) {
  if (!Number.isFinite(value)) {
    return min
  }
  return Math.min(max, Math.max(min, Number(value.toFixed(2))))
}

function applyPaneWeights(chart: IChartApi, indicators: IndicatorState) {
  const panes = chart.panes()
  const weights = buildPaneWeights(indicators).map((pane) => pane.weight)
  panes.forEach((pane, index) => pane.setStretchFactor(weights[index] ?? 0.1))
}
