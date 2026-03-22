import {
  CandlestickSeries,
  ColorType,
  CrosshairMode,
  HistogramSeries,
  LineStyle,
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
  SlidersHorizontal,
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
  isLoading?: boolean
  loadingLabel?: string
  onSelectPosition: (positionId: string) => void
  onLoadMore: () => void
  onTimeframeShortcut: (timeframe: string) => void
  onIndicatorToggle: (indicator: IndicatorKey) => void
}

interface LegendState {
  time: string
  open: string
  high: string
  low: string
  close: string
  volume: string
  emaItems: Array<{ period: number; value: string; color: string }>
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

type DrawingTool =
  | 'cursor'
  | 'select'
  | 'trendline'
  | 'parallelChannel'
  | 'fibRetracement'
  | 'arrow'
  | 'ray'
  | 'extendedLine'
  | 'horizontalLine'
  | 'verticalLine'
  | 'rectangle'
type DrawingPoint = { time: number; price: number }
type DrawingSettingsTab = 'style' | 'text' | 'coordinates' | 'visibility'
type DrawingStatsPosition = 'left' | 'right'
type DrawingFibLevel = {
  value: number
  color: string
  visible: boolean
}
type DrawingSettings = {
  lineColor: string
  lineWidth: number
  lineStyle: LineStyle
  fillColor: string
  fillOpacity: number
  text: string
  textColor: string
  showText: boolean
  showPriceLabels: boolean
  showStats: boolean
  statsPosition: DrawingStatsPosition
  showMidpoint: boolean
  visible: boolean
  extendLeft: boolean
  extendRight: boolean
  fibLevels: DrawingFibLevel[]
}
type DrawingObject = {
  id: string
  tool: Exclude<DrawingTool, 'cursor' | 'select'>
  points: DrawingPoint[]
  settings: DrawingSettings
}
type DrawingDraft = {
  tool: Exclude<DrawingTool, 'cursor' | 'select'>
  points: DrawingPoint[]
  current: DrawingPoint
}
type DragState = {
  drawingId: string
  startX: number
  startY: number
  originalPoints: DrawingPoint[]
  handleIndex: number | null
}

const QUICK_TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h', '1d']
const DEFAULT_PANEL_POSITION = { top: 96, right: 28 }
const EMA_LINE_COLORS = ['#e1d35c', '#2d60d8', '#53b36b', '#f97316', '#a855f7', '#38bdf8']
const DEFAULT_FIB_LEVELS: DrawingFibLevel[] = [
  { value: 0, color: 'rgba(125, 211, 252, 0.88)', visible: true },
  { value: 0.236, color: 'rgba(94, 234, 212, 0.78)', visible: true },
  { value: 0.382, color: 'rgba(250, 204, 21, 0.78)', visible: true },
  { value: 0.5, color: 'rgba(248, 113, 113, 0.78)', visible: true },
  { value: 0.618, color: 'rgba(96, 165, 250, 0.78)', visible: true },
  { value: 0.786, color: 'rgba(192, 132, 252, 0.78)', visible: true },
  { value: 1, color: 'rgba(244, 114, 182, 0.84)', visible: true },
]

export function TradingChart({
  chartData,
  chartSymbol,
  positions,
  indicators,
  indicatorSettings,
  selectedPositionId,
  timeframe,
  timeframeOptions,
  isLoading = false,
  loadingLabel = '正在加载图表数据...',
  onSelectPosition,
  onLoadMore,
  onTimeframeShortcut,
  onIndicatorToggle,
}: TradingChartProps) {
  const chartContainerRef = useRef<HTMLDivElement | null>(null)
  const chartRefs = useRef<ChartRefs | null>(null)
  const lastLegendKeyRef = useRef('')
  const rafRef = useRef<number | null>(null)
  const [legend, setLegend] = useState<LegendState | null>(null)
  const [menu, setMenu] = useState<{ x: number; y: number } | null>(null)
  const [panelPosition, setPanelPosition] = useState(DEFAULT_PANEL_POSITION)
  const [jumpValue, setJumpValue] = useState('1')
  const [indicatorMenuOpen, setIndicatorMenuOpen] = useState(false)
  const [drawingTool, setDrawingTool] = useState<DrawingTool>('cursor')
  const [drawings, setDrawings] = useState<DrawingObject[]>([])
  const [draftDrawing, setDraftDrawing] = useState<DrawingDraft | null>(null)
  const [selectedDrawingId, setSelectedDrawingId] = useState<string | null>(null)
  const [hoveredDrawingId, setHoveredDrawingId] = useState<string | null>(null)
  const [hoveredMarkerPositionId, setHoveredMarkerPositionId] = useState<string | null>(null)
  const [drawingSettingsOpen, setDrawingSettingsOpen] = useState(false)
  const [drawingSettingsTab, setDrawingSettingsTab] = useState<DrawingSettingsTab>('style')
  const [overlayRevision, setOverlayRevision] = useState(0)
  const [pricePaneHeight, setPricePaneHeight] = useState(0)
  const dragStateRef = useRef<DragState | null>(null)

  const dataIndexes = useMemo(() => buildDataIndexes(chartData), [chartData])
  const markerPositionIndex = useMemo(
    () =>
      chartData
        ? buildMarkerPositionIndex(
            positions,
            chartData.candlestick.map((item) => item.time),
          )
        : new Map<number, string>(),
    [chartData, positions],
  )
  const displayedPositionId = hoveredMarkerPositionId ?? selectedPositionId
  const selectedIndex = useMemo(
    () => positions.findIndex((position) => position.position_id === displayedPositionId),
    [displayedPositionId, positions],
  )
  const selectedPosition = selectedIndex >= 0 ? positions[selectedIndex] : positions[0]
  const paneOverlays = useMemo(
    () => buildPaneOverlays(indicators, indicatorSettings),
    [indicatorSettings, indicators],
  )
  const activeIndicatorCount = useMemo(
    () =>
      [
        indicators.showEma,
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
  const selectedDrawing = useMemo(
    () => drawings.find((drawing) => drawing.id === selectedDrawingId) ?? null,
    [drawings, selectedDrawingId],
  )
  const renderedDraftDrawing = useMemo(() => {
    if (!draftDrawing) {
      return null
    }
    const preview = buildDraftDrawingObject(draftDrawing)
    return preview ? projectDrawing(preview, chartRefs.current, pricePaneHeight, overlayRevision) : null
  }, [draftDrawing, overlayRevision, pricePaneHeight])

  useEffect(() => {
    if (selectedIndex >= 0) {
      setJumpValue(String(selectedIndex + 1))
    }
  }, [selectedIndex])

  useEffect(() => {
    setDrawingSettingsOpen(Boolean(selectedDrawingId))
    if (!selectedDrawingId) {
      setDrawingSettingsTab('style')
    }
  }, [selectedDrawingId])

  useEffect(() => {
    const handleMouseMove = (event: MouseEvent) => {
      const dragState = dragStateRef.current
      if (!dragState || dragState.handleIndex === null) {
        return
      }
      const point = resolveDrawingPointFromClient(
        event.clientX,
        event.clientY,
        chartRefs.current,
        chartContainerRef.current,
        pricePaneHeight,
      )
      if (!point) {
        return
      }

      setDrawings((current) =>
        current.map((drawing) => {
          if (drawing.id !== dragState.drawingId) {
            return drawing
          }
          const nextPoints = [...drawing.points]
          const targetIndex: number =
            drawing.tool === 'horizontalLine' || drawing.tool === 'verticalLine' ? 0 : (dragState.handleIndex ?? -1)
          if (targetIndex < 0 || targetIndex >= nextPoints.length) {
            return drawing
          }
          nextPoints[targetIndex] = point.data
          return { ...drawing, points: nextPoints }
        }),
      )
      setOverlayRevision((current) => current + 1)
    }

    const handleMouseUp = () => {
      if (dragStateRef.current?.handleIndex !== null) {
        dragStateRef.current = null
      }
    }

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [pricePaneHeight])

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
      const parsed = JSON.parse(raw) as unknown[]
      setDrawings(Array.isArray(parsed) ? parsed.map(normalizeDrawingObject).filter(Boolean) as DrawingObject[] : [])
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
        mode: CrosshairMode.Normal,
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
      localization: {
        timeFormatter: (time: number | { year: number; month: number; day: number }) => formatChartTimeValue(time),
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
      const emaSeriesList = Array.isArray(chartData.ema_series) ? chartData.ema_series : []
      emaSeriesList.forEach((series, index) => {
        const emaSeries = chart.addSeries(
          LineSeries,
          {
            color: EMA_LINE_COLORS[index % EMA_LINE_COLORS.length],
            lineWidth: 2,
            lineStyle: LineStyle.Solid,
            priceLineVisible: false,
            lastValueVisible: false,
            crosshairMarkerVisible: false,
          },
          0,
        )
        emaSeries.setData(toLineSeriesData(series.data))
      })
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
          lineStyle: LineStyle.Solid,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        },
        paneIndex,
      )
      rsiSeries.setData(toLineSeriesData(chartData.rsi))
      rsiSeries.createPriceLine({
        price: 70,
        color: 'rgba(148, 163, 184, 0.58)',
        lineStyle: LineStyle.Dashed,
        lineWidth: 1,
        axisLabelVisible: true,
        title: 'Upper',
      })
      rsiSeries.createPriceLine({
        price: 30,
        color: 'rgba(148, 163, 184, 0.58)',
        lineStyle: LineStyle.Dashed,
        lineWidth: 1,
        axisLabelVisible: true,
        title: 'Lower',
      })
      paneIndex += 1
    }

    if (indicators.showMacd) {
      const macdLine = chart.addSeries(
        LineSeries,
        {
          color: '#a78bfa',
          lineWidth: 2,
          lineStyle: LineStyle.Solid,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
        },
        paneIndex,
      )
      const signalLine = chart.addSeries(
        LineSeries,
        {
          color: '#fb7185',
          lineWidth: 2,
          lineStyle: LineStyle.Solid,
          priceLineVisible: false,
          lastValueVisible: false,
          crosshairMarkerVisible: false,
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
          color:
            item.value >= 0
              ? 'rgba(34, 197, 94, 0.55)'
              : 'rgba(239, 68, 68, 0.55)',
        })),
      )
    }

    const markerTimes = chartData.candlestick.map((item) => item.time)
    createSeriesMarkers(candleSeries, indicators.showTradeMarkers ? buildMarkers(positions, markerTimes) : [])

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
        setHoveredMarkerPositionId(null)
        return
      }
      const candleTime = Number(candle.time)
      const hoveredMarkerId = markerPositionIndex.get(candleTime) ?? null
      setHoveredMarkerPositionId((current) => (current === hoveredMarkerId ? current : hoveredMarkerId))
      const volume = findValueAtTime(chartData.volume, candleTime, dataIndexes?.volume)
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
        emaItems: buildEmaLegendItems(chartData, dataIndexes, candleTime),
        ema: formatEmaLegend(chartData, dataIndexes, candleTime),
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
      const candleSpacing =
        chartData.candlestick.length > 1
          ? Math.max(chartData.candlestick[1].time - chartData.candlestick[0].time, 60)
          : 3600

      const matchedPosition =
        positions.find((position) => position.open_time === clickedTime || position.close_time === clickedTime) ??
        findNearestPositionByTime(positions, clickedTime, candleSpacing * 2)

      if (matchedPosition) {
        onSelectPosition(matchedPosition.position_id)
        return
      }
      setSelectedDrawingId(null)
      setDrawingSettingsOpen(false)
      setHoveredDrawingId(null)
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
  }, [chartData, dataIndexes, indicators, markerPositionIndex, onSelectPosition, positions])

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
      } else if (lowerKey === 'c') {
        setDrawingTool('parallelChannel')
      } else if (lowerKey === 'k') {
        setDrawingTool('fibRetracement')
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
        setDrawingSettingsOpen(false)
      } else if ((event.key === 'Delete' || event.key === 'Backspace') && selectedDrawingId) {
        setDrawings((current) => current.filter((drawing) => drawing.id !== selectedDrawingId))
        setSelectedDrawingId(null)
        setDrawingSettingsOpen(false)
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
  const indicatorRows: Array<{ key: IndicatorKey; label: string; active: boolean }> = [
    { key: 'showEma', label: `EMA ${indicatorSettings.ema.periods.join('/')}`, active: indicators.showEma },
    { key: 'showVolume', label: 'VOL', active: indicators.showVolume },
    { key: 'showRsi', label: `RSI ${indicatorSettings.rsi.period}`, active: indicators.showRsi },
    {
      key: 'showMacd',
      label: `MACD ${indicatorSettings.macd.fast_period}, ${indicatorSettings.macd.slow_period}, ${indicatorSettings.macd.signal_period}`,
      active: indicators.showMacd,
    },
    { key: 'showTradeMarkers', label: '交易标记', active: indicators.showTradeMarkers },
  ]
  const updateSelectedDrawing = (updater: (drawing: DrawingObject) => DrawingObject) => {
    if (!selectedDrawingId) {
      return
    }
    setDrawings((current) => current.map((drawing) => (drawing.id === selectedDrawingId ? updater(drawing) : drawing)))
    setOverlayRevision((current) => current + 1)
  }

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
                    ? 'bg-[#323d4f] text-white shadow-[inset_0_0_0_1px_rgba(255,255,255,0.08)]'
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

      <div className="flex min-h-[52px] items-center gap-3 overflow-x-auto overflow-y-hidden border-b border-white/8 bg-[#0f1622] px-4 py-3 text-sm whitespace-nowrap [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        <span className="shrink-0 font-mono tabular-nums text-slate-400">Vol {legend?.volume ?? '--'}</span>
        {legend?.emaItems?.length ? (
          legend.emaItems.map((item) => (
            <span key={item.period} className="shrink-0 font-mono tabular-nums" style={{ color: item.color }}>
              EMA {item.period} {item.value}
            </span>
          ))
        ) : (
          <span className="shrink-0 font-mono tabular-nums text-[#e1d35c]">EMA --</span>
        )}
        <span className="shrink-0 font-mono tabular-nums text-[#2d60d8]">RSI {legend?.rsi ?? '--'}</span>
        <span className="shrink-0 font-mono tabular-nums text-[#53b36b]">MACD {legend?.macd ?? '--'}</span>
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
          <div className="mt-3 space-y-2">
            {indicatorRows.map((row) => (
              <IndicatorMenuRow
                key={row.key}
                active={row.active}
                label={row.label}
                onToggle={() => onIndicatorToggle(row.key)}
              />
            ))}
          </div>
        </div>
      ) : null}

      <div className="px-2 pb-2 pt-2">
        <div className="relative">
          <div ref={chartContainerRef} className="h-[calc(100vh-11.75rem)] min-h-[46rem] w-full overflow-hidden rounded-[20px]" />

          {isLoading ? (
            <div className="pointer-events-none absolute inset-0 z-50 flex items-center justify-center rounded-[20px] bg-[#07101b]/72 backdrop-blur-[2px]">
              <div className="flex min-w-[18rem] items-center gap-4 rounded-[22px] border border-white/10 bg-[#08111d]/94 px-5 py-4 shadow-2xl">
                <div className="h-10 w-10 animate-spin rounded-full border-2 border-slate-600 border-t-sky-400" />
                <div>
                  <p className="text-sm font-medium text-white">{loadingLabel}</p>
                  <p className="mt-1 text-xs text-slate-400">K线和指标正在同步，请稍等。</p>
                </div>
              </div>
            </div>
          ) : null}

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

          {selectedDrawing ? (
            <div className="pointer-events-none absolute left-1/2 top-4 z-40 flex w-[min(100%-7rem,42rem)] -translate-x-1/2 flex-col items-center gap-2">
              <DrawingQuickToolbar
                drawing={selectedDrawing}
                expanded={drawingSettingsOpen}
                onDelete={() => {
                  setDrawings((current) => current.filter((drawing) => drawing.id !== selectedDrawing.id))
                  setSelectedDrawingId(null)
                  setDrawingSettingsOpen(false)
                }}
                onOpenSettings={() => setDrawingSettingsOpen((current) => !current)}
                onUpdate={(updater) => updateSelectedDrawing(updater)}
              />

              {drawingSettingsOpen ? (
                <DrawingObjectSettingsPanel
                  drawing={selectedDrawing}
                  compact
                  tab={drawingSettingsTab}
                  onClose={() => setDrawingSettingsOpen(false)}
                  onDelete={() => {
                    setDrawings((current) => current.filter((drawing) => drawing.id !== selectedDrawing.id))
                    setSelectedDrawingId(null)
                    setDrawingSettingsOpen(false)
                  }}
                  onSelectTab={setDrawingSettingsTab}
                  onUpdate={(updater) => updateSelectedDrawing(updater)}
                />
              ) : null}
            </div>
          ) : null}

          <div className="pointer-events-none absolute inset-0">
            {paneOverlays
              .filter(
                (overlay) =>
                  overlay.settingsKey === 'volume' || overlay.settingsKey === 'rsi' || overlay.settingsKey === 'macd',
              )
              .map((overlay) => (
                <PaneHeader
                  key={overlay.key}
                  description={overlay.description}
                  title={overlay.title}
                  top={overlay.top}
                />
              ))}
          </div>

          <div className="pointer-events-none absolute bottom-4 left-16 z-10 flex items-end gap-2 text-white/14">
            <span className="text-5xl font-black tracking-tight">BT</span>
            <span className="pb-1 text-xs uppercase tracking-[0.28em]">Review</span>
          </div>

          <div
            data-testid="drawing-overlay"
            className="pointer-events-none absolute left-0 top-0 z-10 overflow-hidden rounded-t-[22px]"
            style={{
              width: '100%',
              height: pricePaneHeight > 0 ? `${pricePaneHeight}px` : undefined,
            }}
          >
            <svg className="h-full w-full">
              {renderedDrawings.map((drawing) => (
                <DrawingShape
                  key={drawing.id}
                  drawing={drawing}
                  hovered={drawing.id === hoveredDrawingId}
                  selected={drawing.id === selectedDrawingId}
                  onHandleMouseDown={(handleIndex, event) => {
                    event.stopPropagation()
                    setSelectedDrawingId(drawing.id)
                    setDrawingSettingsOpen(true)
                    setDrawingTool('cursor')
                    dragStateRef.current = {
                      drawingId: drawing.id,
                      startX: event.clientX,
                      startY: event.clientY,
                      originalPoints:
                        drawings.find((source) => source.id === drawing.id)?.points ?? [],
                      handleIndex,
                    }
                  }}
                  onSelect={() => {
                    setSelectedDrawingId(drawing.id)
                    setDrawingSettingsOpen(true)
                    setDrawingTool('cursor')
                  }}
                  onHoverChange={(active) => {
                    if (active) {
                      setHoveredDrawingId(drawing.id)
                    } else {
                      setHoveredDrawingId((current) => (current === drawing.id ? null : current))
                    }
                  }}
                />
              ))}
              {renderedDraftDrawing ? <DrawingShape drawing={renderedDraftDrawing} hovered={false} selected={false} draft /> : null}
            </svg>
            <div
              className={cx('absolute inset-0', drawingTool === 'cursor' ? 'pointer-events-none' : 'pointer-events-auto')}
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
                setDrawingSettingsOpen,
                setDrawingTool,
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
            />
          </div>

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
        <p>快捷键: {timeframeShortcutLabel} / F 适应 / L 最新 / V 游标 / S 选择 / G 趋势线 / C 通道线 / K 斐波那契 / A 箭头 / R 射线 / X 延长线 / H 水平 / N 垂直 / O 矩形</p>
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
          {selectedDrawing ? <MenuItem label="对象设置" onClick={() => setDrawingSettingsOpen(true)} /> : null}
          {selectedDrawing ? <MenuItem label="删除对象" onClick={() => {
            setDrawings((current) => current.filter((drawing) => drawing.id !== selectedDrawing.id))
            setSelectedDrawingId(null)
            setDrawingSettingsOpen(false)
          }} /> : null}
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
      className="fixed z-[120] w-64 rounded-[22px] border border-white/10 bg-[#0a1322]/95 shadow-2xl backdrop-blur"
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

function IndicatorMenuRow({
  active,
  label,
  onToggle,
}: {
  active: boolean
  label: string
  onToggle: () => void
}) {
  return (
    <div className="flex items-center gap-2 rounded-xl border border-white/8 bg-white/5 px-3 py-2">
      <button
        className={cx(
          'rounded-full border px-2.5 py-1 text-xs transition',
          active
            ? 'border-sky-400 bg-sky-500/18 text-white'
            : 'border-white/8 bg-[#101926] text-slate-300 hover:border-slate-400',
        )}
        type="button"
        onClick={onToggle}
      >
        {active ? '已开' : '已关'}
      </button>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm text-white">{label}</p>
      </div>
    </div>
  )
}

function DrawingQuickToolbar({
  drawing,
  expanded,
  onOpenSettings,
  onDelete,
  onUpdate,
}: {
  drawing: DrawingObject
  expanded: boolean
  onOpenSettings: () => void
  onDelete: () => void
  onUpdate: (updater: (drawing: DrawingObject) => DrawingObject) => void
}) {
  const canFill = drawing.tool === 'rectangle' || drawing.tool === 'parallelChannel' || drawing.tool === 'fibRetracement'
  return (
    <div className="pointer-events-auto inline-flex max-w-full items-center gap-2 rounded-[16px] border border-white/10 bg-[#15181e]/94 px-3 py-2 shadow-2xl backdrop-blur">
      <span className="max-w-[9rem] truncate px-1 text-sm font-medium text-slate-200">{drawingToolLabel(drawing.tool)}</span>

      <label
        className="flex h-9 w-10 cursor-pointer items-center justify-center rounded-[10px] border border-white/12 bg-[#1d2129] transition hover:border-white/30"
        title="线条颜色"
      >
        <span
          className="h-5 w-5 rounded-md border border-white/25"
          style={{ backgroundColor: normalizeColorInput(drawing.settings.lineColor) }}
        />
        <input
          className="sr-only"
          type="color"
          value={normalizeColorInput(drawing.settings.lineColor)}
          onChange={(event) =>
            onUpdate((current) => ({
              ...current,
              settings: { ...current.settings, lineColor: event.target.value },
            }))
          }
        />
      </label>

      <button
        className="inline-flex h-9 items-center justify-center rounded-[10px] border border-white/12 bg-[#1d2129] px-3 text-sm text-slate-200 transition hover:border-white/30 hover:text-white"
        title="线型"
        type="button"
        onClick={() =>
          onUpdate((current) => ({
            ...current,
            settings: {
              ...current.settings,
              lineStyle: nextLineStyle(current.settings.lineStyle),
            },
          }))
        }
      >
        <span className={cx('w-9 border-t-2', drawing.settings.lineStyle === LineStyle.Dashed ? 'border-dashed' : drawing.settings.lineStyle === LineStyle.Dotted ? 'border-dotted' : 'border-solid')} />
      </button>

      <button
        className="inline-flex h-9 items-center justify-center rounded-[10px] border border-white/12 bg-[#1d2129] px-3 text-sm text-slate-200 transition hover:border-white/30 hover:text-white"
        title="线宽"
        type="button"
        onClick={() =>
          onUpdate((current) => ({
            ...current,
            settings: {
              ...current.settings,
              lineWidth: nextLineWidth(current.settings.lineWidth),
            },
          }))
        }
      >
        {drawing.settings.lineWidth}px
      </button>

      {canFill ? (
        <label
          className="flex h-9 w-10 cursor-pointer items-center justify-center rounded-[10px] border border-white/12 bg-[#1d2129] transition hover:border-white/30"
          title="填充颜色"
        >
          <span
            className="h-5 w-5 rounded-md border border-white/25"
            style={{ backgroundColor: normalizeColorInput(drawing.settings.fillColor) }}
          />
          <input
            className="sr-only"
            type="color"
            value={normalizeColorInput(drawing.settings.fillColor)}
            onChange={(event) =>
              onUpdate((current) => ({
                ...current,
                settings: { ...current.settings, fillColor: event.target.value },
              }))
            }
          />
        </label>
      ) : null}

      <button
        className={cx(
          'inline-flex h-9 w-10 items-center justify-center rounded-[10px] border bg-[#1d2129] transition hover:text-white',
          expanded ? 'border-sky-400/70 text-white' : 'border-white/12 text-slate-200 hover:border-white/30',
        )}
        title="详细设置"
        type="button"
        onClick={onOpenSettings}
      >
        <SlidersHorizontal className="h-4 w-4" />
      </button>

      <button
        className="inline-flex h-9 w-10 items-center justify-center rounded-[10px] border border-rose-400/20 bg-[#1d2129] text-rose-200 transition hover:border-rose-400/50"
        title="删除对象"
        type="button"
        onClick={onDelete}
      >
        <Trash2 className="h-4 w-4" />
      </button>
    </div>
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
    { tool: 'parallelChannel', label: '通道线', icon: RectangleHorizontal },
    { tool: 'fibRetracement', label: '斐波那契回撤', icon: Search },
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
  hovered,
  selected,
  draft,
  onSelect,
  onHandleMouseDown,
  onHoverChange,
}: {
  drawing: ProjectedDrawing
  hovered: boolean
  selected: boolean
  draft?: boolean
  onSelect?: () => void
  onHandleMouseDown?: (handleIndex: number, event: ReactMouseEvent<SVGCircleElement>) => void
  onHoverChange?: (active: boolean) => void
}) {
  const stroke = draft ? 'rgba(125, 211, 252, 0.95)' : selected ? '#fbbf24' : hovered ? '#93c5fd' : drawing.lineColor
  const strokeWidth =
    draft ? drawing.lineWidth : selected ? Math.max(drawing.lineWidth, 2.5) : hovered ? Math.max(drawing.lineWidth, 2.2) : drawing.lineWidth
  const dashArray = lineStyleToDashArray(drawing.lineStyle)
  return (
    <g
      className={draft ? undefined : 'cursor-pointer'}
      pointerEvents={draft ? 'none' : 'visiblePainted'}
      onMouseEnter={draft || !onHoverChange ? undefined : () => onHoverChange(true)}
      onMouseLeave={draft || !onHoverChange ? undefined : () => onHoverChange(false)}
      onMouseDown={
        draft || !onSelect
          ? undefined
          : (event) => {
              event.stopPropagation()
              onSelect()
            }
      }
    >
      {drawing.fills.map((fill, index) => (
        <polygon key={`fill-${index}`} fill={fill.fill} points={fill.points} />
      ))}
      {drawing.rects.map((rect, index) => (
        <rect
          key={`rect-${index}`}
          fill={rect.fill}
          height={rect.height}
          stroke={rect.stroke ?? stroke}
          strokeDasharray={dashArray}
          strokeWidth={strokeWidth}
          width={rect.width}
          x={rect.x}
          y={rect.y}
        />
      ))}
      {drawing.segments.map((segment, index) => (
        <g key={`segment-${index}`}>
          <line
            x1={segment.x1}
            x2={segment.x2}
            y1={segment.y1}
            y2={segment.y2}
            stroke={segment.color ?? stroke}
            strokeDasharray={dashArray}
            strokeWidth={strokeWidth}
          />
          {segment.arrowHeadStart ? (
            <ArrowHead x1={segment.x2} x2={segment.x1} y1={segment.y2} y2={segment.y1} stroke={segment.color ?? stroke} />
          ) : null}
          {segment.arrowHeadEnd ? (
            <ArrowHead x1={segment.x1} x2={segment.x2} y1={segment.y1} y2={segment.y2} stroke={segment.color ?? stroke} />
          ) : null}
        </g>
      ))}
      {drawing.labels.map((label, index) => (
        <g key={`label-${index}`} transform={`translate(${label.x}, ${label.y})`}>
          {label.background ? (
            <rect
              fill={label.background}
              height="18"
              rx="5"
              width={Math.max(label.text.length * 7.4, 36)}
              x={label.anchor === 'end' ? -Math.max(label.text.length * 7.4, 36) - 6 : label.anchor === 'middle' ? -Math.max(label.text.length * 7.4, 36) / 2 - 3 : -2}
              y="-13"
            />
          ) : null}
          <text
            dominantBaseline="middle"
            fill={label.color ?? stroke}
            fontSize="11"
            textAnchor={label.anchor ?? 'start'}
            y="0"
          >
            {label.text}
          </text>
        </g>
      ))}
      {drawing.midpoints?.map((point, index) => (
        <circle
          key={`midpoint-${index}`}
          cx={point.x}
          cy={point.y}
          fill="#0b1020"
          r="3.5"
          stroke={stroke}
          strokeWidth="1.25"
        />
      ))}
      {selected
        ? drawing.handles.map((handle, index) => (
            <circle
              key={`handle-${index}`}
              cx={handle.x}
              cy={handle.y}
              fill="#0b1020"
              r="4"
              stroke={stroke}
              strokeWidth="1.5"
              onMouseDown={
                onHandleMouseDown
                  ? (event) => {
                      onHandleMouseDown(index, event)
                    }
                  : undefined
              }
              pointerEvents="all"
            />
          ))
        : null}
    </g>
  )
}

function ArrowHead({
  x1,
  y1,
  x2,
  y2,
  stroke,
}: {
  x1: number
  y1: number
  x2: number
  y2: number
  stroke: string
}) {
  const angle = Math.atan2(y2 - y1, x2 - x1)
  const arrowSize = 10
  return (
    <polygon
      fill={stroke}
      points={[
        `${x2},${y2}`,
        `${x2 - arrowSize * Math.cos(angle - Math.PI / 6)},${y2 - arrowSize * Math.sin(angle - Math.PI / 6)}`,
        `${x2 - arrowSize * Math.cos(angle + Math.PI / 6)},${y2 - arrowSize * Math.sin(angle + Math.PI / 6)}`,
      ].join(' ')}
    />
  )
}

function PaneHeader({
  title,
  description,
  top,
}: {
  title: string
  description: string
  top: string
}) {
  return (
    <div className="absolute left-3 right-3 z-20 flex items-start justify-between" style={{ top }}>
      <div className="pointer-events-auto inline-flex max-w-[70%] items-center gap-2 rounded-full border border-white/10 bg-[#08111d]/92 px-3 py-1.5 text-[11px] text-slate-200 shadow-lg backdrop-blur">
        <span className="font-semibold text-white">{title}</span>
        <span className="truncate text-slate-400">{description}</span>
      </div>
    </div>
  )
}

function DrawingObjectSettingsPanel({
  drawing,
  tab,
  onClose,
  onDelete,
  onSelectTab,
  onUpdate,
  compact = false,
}: {
  drawing: DrawingObject
  tab: DrawingSettingsTab
  onClose: () => void
  onDelete: () => void
  onSelectTab: (tab: DrawingSettingsTab) => void
  onUpdate: (updater: (drawing: DrawingObject) => DrawingObject) => void
  compact?: boolean
}) {
  const updateSettings = (updater: (settings: DrawingSettings) => DrawingSettings) => {
    onUpdate((current) => ({
      ...current,
      settings: updater(current.settings),
    }))
  }
  const canFill = drawing.tool === 'rectangle' || drawing.tool === 'parallelChannel' || drawing.tool === 'fibRetracement'
  const canExtend =
    drawing.tool === 'trendline' || drawing.tool === 'parallelChannel' || drawing.tool === 'ray' || drawing.tool === 'extendedLine'

  return (
    <div
      className={cx(
        'pointer-events-auto border border-white/10 bg-[#07101b]/96 shadow-2xl backdrop-blur',
        compact
          ? 'max-h-[24rem] w-[20rem] overflow-y-auto rounded-[18px] p-3'
          : 'w-[25rem] rounded-[24px] p-4',
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-[0.22em] text-slate-500">Drawing Settings</p>
          <h3 className={cx('font-semibold text-white', compact ? 'mt-1 text-sm' : 'mt-2 text-base')}>
            {drawingToolLabel(drawing.tool)}
          </h3>
        </div>
        <button
          className={cx(
            'rounded-full border border-white/10 text-xs text-slate-300 transition hover:border-slate-400 hover:text-white',
            compact ? 'px-2.5 py-1' : 'px-3 py-1',
          )}
          type="button"
          onClick={onClose}
        >
          关闭
        </button>
      </div>

      <div className={cx('flex items-center gap-2 rounded-2xl border border-white/8 bg-white/5 p-1', compact ? 'mt-3' : 'mt-4')}>
        {(['style', 'text', 'coordinates', 'visibility'] as DrawingSettingsTab[]).map((item) => (
          <button
            key={item}
            className={cx(
              'rounded-xl capitalize transition',
              compact ? 'px-2.5 py-1.5 text-xs' : 'px-3 py-2 text-sm',
              tab === item ? 'bg-sky-500/20 text-white' : 'text-slate-300 hover:bg-white/8',
            )}
            type="button"
            onClick={() => onSelectTab(item)}
          >
            {drawingTabLabel(item)}
          </button>
        ))}
      </div>

      <div className={cx('space-y-3', compact ? 'mt-3' : 'mt-4')}>
        {tab === 'style' ? (
          <>
            <ColorField
              label="线条颜色"
              value={drawing.settings.lineColor}
              onChange={(value) => updateSettings((current) => ({ ...current, lineColor: value }))}
            />
            <NumericField
              label="线宽"
              step={1}
              value={drawing.settings.lineWidth}
              onChange={(value) => updateSettings((current) => ({ ...current, lineWidth: clampInteger(value, 1, 6) }))}
            />
            <LineStyleField
              label="线型"
              value={drawing.settings.lineStyle}
              onChange={(value) => updateSettings((current) => ({ ...current, lineStyle: value }))}
            />
            {canFill ? (
              <>
                <ColorField
                  label="填充颜色"
                  value={drawing.settings.fillColor}
                  onChange={(value) => updateSettings((current) => ({ ...current, fillColor: value }))}
                />
                <NumericField
                  label="填充透明度 (%)"
                  step={5}
                  value={Math.round(drawing.settings.fillOpacity * 100)}
                  onChange={(value) =>
                    updateSettings((current) => ({ ...current, fillOpacity: clampFloat(value, 0, 100) / 100 }))
                  }
                />
              </>
            ) : null}
            {drawing.tool === 'fibRetracement' ? (
              <div className="space-y-2 rounded-2xl border border-white/10 bg-[#0d1626] p-3">
                <p className="text-xs font-medium text-slate-300">斐波那契层级</p>
                {drawing.settings.fibLevels.map((level, index) => (
                  <div key={`${drawing.id}-fib-${index}`} className="grid grid-cols-[auto_1fr_auto] items-center gap-2">
                    <input
                      checked={level.visible}
                      type="checkbox"
                      onChange={(event) =>
                        updateSettings((current) => ({
                          ...current,
                          fibLevels: current.fibLevels.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, visible: event.target.checked } : item,
                          ),
                        }))
                      }
                    />
                    <input
                      className="h-10 rounded-xl border border-white/10 bg-[#111a2a] px-3 text-sm text-white outline-none transition focus:border-sky-400"
                      step={0.01}
                      type="number"
                      value={level.value}
                      onChange={(event) =>
                        updateSettings((current) => ({
                          ...current,
                          fibLevels: current.fibLevels.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, value: clampFloat(Number(event.target.value), -5, 5) } : item,
                          ),
                        }))
                      }
                    />
                    <input
                      className="h-10 w-12 rounded-xl border border-white/10 bg-transparent"
                      type="color"
                      value={normalizeColorInput(level.color)}
                      onChange={(event) =>
                        updateSettings((current) => ({
                          ...current,
                          fibLevels: current.fibLevels.map((item, itemIndex) =>
                            itemIndex === index ? { ...item, color: event.target.value } : item,
                          ),
                        }))
                      }
                    />
                  </div>
                ))}
              </div>
            ) : null}
            {canExtend ? (
              <label className="block">
                <span className="mb-2 block text-xs font-medium text-slate-300">延伸</span>
                <select
                  className="h-11 w-full rounded-2xl border border-white/10 bg-[#0d1626] px-3 text-sm text-white outline-none transition focus:border-sky-400"
                  value={drawing.settings.extendLeft ? (drawing.settings.extendRight ? 'both' : 'left') : drawing.settings.extendRight ? 'right' : 'none'}
                  onChange={(event) => {
                    const value = event.target.value
                    updateSettings((current) => ({
                      ...current,
                      extendLeft: value === 'left' || value === 'both',
                      extendRight: value === 'right' || value === 'both',
                    }))
                  }}
                >
                  <option value="none">不要扩大</option>
                  <option value="right">向右延伸</option>
                  <option value="left">向左延伸</option>
                  <option value="both">双向延伸</option>
                </select>
              </label>
            ) : null}
            <label className="flex items-center gap-3 rounded-2xl border border-white/10 bg-[#0d1626] px-3 py-3 text-sm text-white">
              <input
                checked={drawing.settings.showMidpoint}
                type="checkbox"
                onChange={(event) => updateSettings((current) => ({ ...current, showMidpoint: event.target.checked }))}
              />
              中点
            </label>
          </>
        ) : null}

        {tab === 'text' ? (
          <>
            <label className="flex items-center gap-3 rounded-2xl border border-white/10 bg-[#0d1626] px-3 py-3 text-sm text-white">
              <input
                checked={drawing.settings.showText}
                type="checkbox"
                onChange={(event) => updateSettings((current) => ({ ...current, showText: event.target.checked }))}
              />
              显示文本
            </label>
            <label className="block">
              <span className="mb-2 block text-xs font-medium text-slate-300">文本</span>
              <textarea
                className="min-h-[5.5rem] w-full rounded-2xl border border-white/10 bg-[#0d1626] px-3 py-3 text-sm text-white outline-none transition focus:border-sky-400"
                value={drawing.settings.text}
                onChange={(event) => updateSettings((current) => ({ ...current, text: event.target.value }))}
              />
            </label>
            <ColorField
              label="文字颜色"
              value={drawing.settings.textColor}
              onChange={(value) => updateSettings((current) => ({ ...current, textColor: value }))}
            />
          </>
        ) : null}

        {tab === 'coordinates' ? (
          <>
            {drawing.points.map((point, index) => (
              <div key={`${drawing.id}-${index}`} className="rounded-2xl border border-white/10 bg-[#0d1626] p-3">
                <p className="mb-3 text-xs uppercase tracking-[0.18em] text-slate-500">Point {index + 1}</p>
                <div className="space-y-3">
                  <NumericField
                    label="时间戳"
                    step={1}
                    value={point.time}
                    onChange={(value) =>
                      onUpdate((current) => ({
                        ...current,
                        points: current.points.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, time: clampInteger(value, 1, 9999999999) } : item,
                        ),
                      }))
                    }
                  />
                  <NumericField
                    label="价格"
                    step={0.0001}
                    value={point.price}
                    onChange={(value) =>
                      onUpdate((current) => ({
                        ...current,
                        points: current.points.map((item, itemIndex) =>
                          itemIndex === index ? { ...item, price: clampFloat(value, 0.0000001, 99999999) } : item,
                        ),
                      }))
                    }
                  />
                </div>
              </div>
            ))}
          </>
        ) : null}

        {tab === 'visibility' ? (
          <>
            <label className="flex items-center gap-3 rounded-2xl border border-white/10 bg-[#0d1626] px-3 py-3 text-sm text-white">
              <input
                checked={drawing.settings.visible}
                type="checkbox"
                onChange={(event) => updateSettings((current) => ({ ...current, visible: event.target.checked }))}
              />
              可见
            </label>
            <label className="flex items-center gap-3 rounded-2xl border border-white/10 bg-[#0d1626] px-3 py-3 text-sm text-white">
              <input
                checked={drawing.settings.showPriceLabels}
                type="checkbox"
                onChange={(event) =>
                  updateSettings((current) => ({ ...current, showPriceLabels: event.target.checked }))
                }
              />
              价格标签
            </label>
            <label className="flex items-center gap-3 rounded-2xl border border-white/10 bg-[#0d1626] px-3 py-3 text-sm text-white">
              <input
                checked={drawing.settings.showStats}
                type="checkbox"
                onChange={(event) => updateSettings((current) => ({ ...current, showStats: event.target.checked }))}
              />
              统计数据
            </label>
            <label className="block">
              <span className="mb-2 block text-xs font-medium text-slate-300">统计位置</span>
              <select
                className="h-11 w-full rounded-2xl border border-white/10 bg-[#0d1626] px-3 text-sm text-white outline-none transition focus:border-sky-400"
                value={drawing.settings.statsPosition}
                onChange={(event) =>
                  updateSettings((current) => ({
                    ...current,
                    statsPosition: event.target.value as DrawingStatsPosition,
                  }))
                }
              >
                <option value="right">右</option>
                <option value="left">左</option>
              </select>
            </label>
          </>
        ) : null}
      </div>

      <div className={cx('flex items-center justify-between gap-3', compact ? 'mt-3' : 'mt-4')}>
        <button
          className={cx(
            'rounded-full border border-rose-400/20 text-rose-200 transition hover:border-rose-400/50',
            compact ? 'px-2.5 py-1.5 text-xs' : 'px-3 py-2 text-sm',
          )}
          type="button"
          onClick={onDelete}
        >
          删除
        </button>
        <button
          className={cx(
            'rounded-full border border-white/10 text-slate-300 transition hover:border-slate-400 hover:text-white',
            compact ? 'px-2.5 py-1.5 text-xs' : 'px-3 py-2 text-sm',
          )}
          type="button"
          onClick={onClose}
        >
          完成
        </button>
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

function ColorField({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (value: string) => void
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs font-medium text-slate-300">{label}</span>
      <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-[#0d1626] px-3 py-2">
        <input className="h-8 w-10 rounded border border-white/10 bg-transparent" type="color" value={normalizeColorInput(value)} onChange={(event) => onChange(event.target.value)} />
        <input
          className="flex-1 bg-transparent text-sm text-white outline-none"
          type="text"
          value={value}
          onChange={(event) => onChange(event.target.value)}
        />
      </div>
    </label>
  )
}

function LineStyleField({
  label,
  value,
  onChange,
}: {
  label: string
  value: LineStyle
  onChange: (value: LineStyle) => void
}) {
  return (
    <label className="block">
      <span className="mb-2 block text-xs font-medium text-slate-300">{label}</span>
      <select
        className="h-11 w-full rounded-2xl border border-white/10 bg-[#0d1626] px-3 text-sm text-white outline-none transition focus:border-sky-400"
        value={String(value)}
        onChange={(event) => onChange(Number(event.target.value) as LineStyle)}
      >
        <option value={String(LineStyle.Solid)}>实线</option>
        <option value={String(LineStyle.Dotted)}>点线</option>
        <option value={String(LineStyle.Dashed)}>虚线</option>
      </select>
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

type ProjectedSegment = {
  x1: number
  y1: number
  x2: number
  y2: number
  arrowHeadStart?: boolean
  arrowHeadEnd?: boolean
  color?: string
}
type ProjectedRect = {
  x: number
  y: number
  width: number
  height: number
  fill: string
  stroke?: string
}
type ProjectedLabel = {
  x: number
  y: number
  text: string
  anchor?: 'start' | 'middle' | 'end'
  background?: string
  color?: string
}
type ProjectedDrawing = {
  id: string
  lineColor: string
  lineWidth: number
  lineStyle: LineStyle
  segments: ProjectedSegment[]
  rects: ProjectedRect[]
  fills: Array<{ points: string; fill: string }>
  labels: ProjectedLabel[]
  handles: Array<{ x: number; y: number }>
  midpoints?: Array<{ x: number; y: number }>
}

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
  setDrawingSettingsOpen,
  setDrawingTool,
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
  setDrawingSettingsOpen: Dispatch<SetStateAction<boolean>>
  setDrawingTool: Dispatch<SetStateAction<DrawingTool>>
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
      setDrawingSettingsOpen(Boolean(hit))
      if (hit) {
        dragStateRef.current = {
          drawingId: hit.id,
          startX: point.x,
          startY: point.y,
          originalPoints: hit.source.points,
          handleIndex: null,
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
      setDrawingSettingsOpen(true)
      setDrawingTool('cursor')
      setOverlayRevision((current) => current + 1)
      return
    }

    if (drawingTool === 'verticalLine') {
      const nextDrawing = createDrawingObject('verticalLine', [point.data, point.data])
      setDrawings((current) => [...current, nextDrawing])
      setSelectedDrawingId(nextDrawing.id)
      setDrawingSettingsOpen(true)
      setDrawingTool('cursor')
      setOverlayRevision((current) => current + 1)
      return
    }

    setDraftDrawing((current) => {
      if (!current || current.tool !== drawingTool) {
        return {
          tool: drawingTool,
          points: [point.data],
          current: point.data,
        }
      }

      if (current.tool === 'parallelChannel' && current.points.length === 1) {
        return {
          ...current,
          points: [...current.points, point.data],
          current: point.data,
        }
      }

      const points =
        current.tool === 'parallelChannel'
          ? [...current.points, point.data]
          : [current.points[0] ?? point.data, point.data]
      const nextDrawing = createDrawingObject(current.tool, points)
      setDrawings((items) => [...items, nextDrawing])
      setSelectedDrawingId(nextDrawing.id)
      setDrawingSettingsOpen(true)
      setDrawingTool('cursor')
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
  return resolveDrawingPointFromClient(event.clientX, event.clientY, refs, container, pricePaneHeight)
}

function resolveDrawingPointFromClient(
  clientX: number,
  clientY: number,
  refs: ChartRefs | null,
  container: HTMLDivElement | null,
  pricePaneHeight: number,
) {
  if (!refs || !container) {
    return null
  }
  const rect = container.getBoundingClientRect()
  const x = clientX - rect.left
  const y = clientY - rect.top
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
    settings: getDefaultDrawingSettings(tool),
  }
}

function buildDraftDrawingObject(draft: DrawingDraft): DrawingObject | null {
  if (draft.tool === 'parallelChannel') {
    if (draft.points.length === 1) {
      return {
        id: 'draft',
        tool: 'trendline',
        points: [draft.points[0], draft.current],
        settings: getDefaultDrawingSettings('trendline'),
      }
    }
    return {
      id: 'draft',
      tool: 'parallelChannel',
      points: [draft.points[0], draft.points[1], draft.current],
      settings: getDefaultDrawingSettings('parallelChannel'),
    }
  }

  if (draft.points.length === 0) {
    return null
  }

  return {
    id: 'draft',
    tool: draft.tool,
    points: [draft.points[0], draft.current],
    settings: getDefaultDrawingSettings(draft.tool),
  }
}

function getDefaultDrawingSettings(tool: Exclude<DrawingTool, 'cursor' | 'select'>): DrawingSettings {
  return {
    lineColor: tool === 'fibRetracement' ? '#facc15' : '#7dd3fc',
    lineWidth: 2,
    lineStyle: tool === 'fibRetracement' ? LineStyle.Dashed : LineStyle.Solid,
    fillColor:
      tool === 'rectangle'
        ? 'rgba(125, 211, 252, 0.18)'
        : tool === 'parallelChannel'
          ? 'rgba(96, 165, 250, 0.14)'
          : tool === 'fibRetracement'
            ? 'rgba(250, 204, 21, 0.08)'
            : 'rgba(125, 211, 252, 0.08)',
    fillOpacity: tool === 'rectangle' || tool === 'parallelChannel' || tool === 'fibRetracement' ? 0.18 : 0.08,
    text: '',
    textColor: '#e2e8f0',
    showText: false,
    showPriceLabels: tool === 'fibRetracement',
    showStats: tool === 'trendline' || tool === 'parallelChannel' || tool === 'fibRetracement',
    statsPosition: 'right',
    showMidpoint: false,
    visible: true,
    extendLeft: tool === 'extendedLine',
    extendRight: tool === 'ray' || tool === 'extendedLine',
    fibLevels: DEFAULT_FIB_LEVELS,
  }
}

function normalizeDrawingObject(raw: unknown): DrawingObject | null {
  if (!raw || typeof raw !== 'object') {
    return null
  }

  const candidate = raw as {
    id?: unknown
    tool?: unknown
    points?: unknown
    settings?: Partial<DrawingSettings>
  }

  if (typeof candidate.id !== 'string' || typeof candidate.tool !== 'string' || !Array.isArray(candidate.points)) {
    return null
  }

  const points = candidate.points
    .map((point) => {
      if (!point || typeof point !== 'object') {
        return null
      }
      const value = point as { time?: unknown; price?: unknown }
      if (typeof value.time !== 'number' || typeof value.price !== 'number') {
        return null
      }
      return { time: value.time, price: value.price }
    })
    .filter(Boolean) as DrawingPoint[]

  if (points.length < 2) {
    return null
  }

  const tool = candidate.tool as Exclude<DrawingTool, 'cursor' | 'select'>
  const defaults = getDefaultDrawingSettings(tool)
  return {
    id: candidate.id,
    tool,
    points,
    settings: {
      ...defaults,
      ...candidate.settings,
      fibLevels: Array.isArray(candidate.settings?.fibLevels)
        ? candidate.settings.fibLevels.map((level) => ({
            value: typeof level.value === 'number' ? level.value : 0,
            color: typeof level.color === 'string' ? level.color : defaults.lineColor,
            visible: typeof level.visible === 'boolean' ? level.visible : true,
          }))
        : defaults.fibLevels,
    },
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
  if (!refs || pricePaneHeight <= 0 || !drawing.settings.visible || drawing.points.length < 2) {
    return null
  }

  const style = drawing.settings
  const [firstPoint, secondPoint] = drawing.points
  const x1 = refs.chart.timeScale().timeToCoordinate(toUtcTime(firstPoint.time))
  const y1 = refs.candleSeries.priceToCoordinate(firstPoint.price)
  if (x1 === null || y1 === null) {
    return null
  }

  if (drawing.tool === 'horizontalLine') {
    return buildProjectedDrawing(drawing, {
      segments: [{ x1: 0, y1, x2: refs.chart.timeScale().width(), y2: y1 }],
      handles: [{ x: x1, y: y1 }],
      labels: style.showPriceLabels ? [buildPriceLabel(refs.chart.timeScale().width() - 6, y1, firstPoint.price)] : [],
    })
  }

  if (drawing.tool === 'verticalLine') {
    return buildProjectedDrawing(drawing, {
      segments: [{ x1, y1: 0, x2: x1, y2: pricePaneHeight }],
      handles: [{ x: x1, y: y1 }],
      labels: [],
    })
  }

  const x2Base = refs.chart.timeScale().timeToCoordinate(toUtcTime(secondPoint.time))
  const y2Base = refs.candleSeries.priceToCoordinate(secondPoint.price)
  if (x2Base === null || y2Base === null) {
    return null
  }

  if (drawing.tool === 'rectangle') {
    const x = Math.min(x1, x2Base)
    const y = Math.min(y1, y2Base)
    const width = Math.abs(x2Base - x1)
    const height = Math.abs(y2Base - y1)
    return buildProjectedDrawing(drawing, {
      rects: [
        {
          x,
          y,
          width,
          height,
          fill: applyAlpha(style.fillColor, style.fillOpacity),
          stroke: style.lineColor,
        },
      ],
      handles: [
        { x: x1, y: y1 },
        { x: x2Base, y: y2Base },
      ],
      labels: buildDrawingLabels(drawing, firstPoint, secondPoint, x + width / 2, y + height / 2),
    })
  }

  if (drawing.tool === 'parallelChannel' && drawing.points.length >= 3) {
    const thirdPoint = drawing.points[2]
    const x3 = refs.chart.timeScale().timeToCoordinate(toUtcTime(thirdPoint.time))
    const y3 = refs.candleSeries.priceToCoordinate(thirdPoint.price)
    if (x3 === null || y3 === null) {
      return null
    }
    const dx = x2Base - x1
    const dy = y2Base - y1
    const x4 = x3 + dx
    const y4 = y3 + dy
    const primary = resolveLineSegmentForStyle(x1, y1, x2Base, y2Base, refs.chart.timeScale().width(), pricePaneHeight, drawing)
    const secondary = resolveLineSegmentForStyle(x3, y3, x4, y4, refs.chart.timeScale().width(), pricePaneHeight, drawing)
    if (!primary || !secondary) {
      return null
    }
    return buildProjectedDrawing(drawing, {
      segments: [
        { ...primary },
        { ...secondary },
        { x1, y1, x2: x3, y2: y3 },
      ],
      fills: [
        {
          points: `${x1},${y1} ${x2Base},${y2Base} ${x4},${y4} ${x3},${y3}`,
          fill: applyAlpha(style.fillColor, style.fillOpacity),
        },
      ],
      handles: [
        { x: x1, y: y1 },
        { x: x2Base, y: y2Base },
        { x: x3, y: y3 },
      ],
      midpoints: style.showMidpoint
        ? [
            { x: (x1 + x2Base) / 2, y: (y1 + y2Base) / 2 },
            { x: (x3 + x4) / 2, y: (y3 + y4) / 2 },
          ]
        : [],
      labels: buildDrawingLabels(drawing, firstPoint, secondPoint, style.statsPosition === 'right' ? x4 : x3, (y1 + y3) / 2),
    })
  }

  if (drawing.tool === 'fibRetracement') {
    const minX = Math.min(x1, x2Base)
    const maxX = Math.max(x1, x2Base)
    const labels = drawing.settings.fibLevels
      .filter((level) => level.visible)
      .map((level, index, list) => {
        const y = y1 + (y2Base - y1) * level.value
        const nextY =
          list[index + 1] && list[index + 1].visible
            ? y1 + (y2Base - y1) * list[index + 1].value
            : null
        return {
          segment: { x1: minX, y1: y, x2: maxX, y2: y, color: level.color },
          fill:
            nextY !== null
              ? {
                  points: `${minX},${y} ${maxX},${y} ${maxX},${nextY} ${minX},${nextY}`,
                  fill: applyAlpha(level.color, 0.08),
                }
              : null,
          label: {
            x: maxX + 8,
            y,
            text: `${(level.value * 100).toFixed(level.value === 0 || level.value === 1 ? 0 : 1)}% ${formatNumber(firstPoint.price + (secondPoint.price - firstPoint.price) * level.value)}`,
            color: level.color,
          } satisfies ProjectedLabel,
        }
      })
    return {
      id: drawing.id,
      lineColor: style.lineColor,
      lineWidth: style.lineWidth,
      lineStyle: style.lineStyle,
      segments: [
        { x1: minX, y1, x2: minX, y2: y2Base },
        { x1: maxX, y1, x2: maxX, y2: y2Base },
        ...labels.map((item) => item.segment),
      ],
      rects: [],
      fills: labels.flatMap((item) => (item.fill ? [item.fill] : [])),
      labels: [
        ...labels.map((item) => item.label),
        ...buildDrawingLabels(drawing, firstPoint, secondPoint, maxX, (y1 + y2Base) / 2),
      ],
      handles: [
        { x: x1, y: y1 },
        { x: x2Base, y: y2Base },
      ],
      midpoints: style.showMidpoint ? [{ x: (x1 + x2Base) / 2, y: (y1 + y2Base) / 2 }] : [],
    }
  }

  const segment = resolveLineSegmentForStyle(x1, y1, x2Base, y2Base, refs.chart.timeScale().width(), pricePaneHeight, drawing)
  if (!segment) {
    return null
  }

  return buildProjectedDrawing(drawing, {
    segments: [
      {
        ...segment,
        arrowHeadEnd: drawing.tool === 'arrow',
      },
    ],
    handles: [
      { x: x1, y: y1 },
      { x: x2Base, y: y2Base },
    ],
    midpoints: style.showMidpoint ? [{ x: (x1 + x2Base) / 2, y: (y1 + y2Base) / 2 }] : [],
    labels: buildDrawingLabels(
      drawing,
      firstPoint,
      secondPoint,
      style.statsPosition === 'right' ? x2Base : x1,
      style.statsPosition === 'right' ? y2Base : y1,
    ),
  })
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

    const hitLine = projected.segments.some(
      (segment) => distanceToSegment(x, y, segment.x1, segment.y1, segment.x2, segment.y2) <= tolerance,
    )
    const hitRect = projected.rects.some(
      (rect) =>
        x >= rect.x - tolerance &&
        x <= rect.x + rect.width + tolerance &&
        y >= rect.y - tolerance &&
        y <= rect.y + rect.height + tolerance,
    )
    const hitFill = projected.fills.some((fill) => pointNearPolygonBounds(x, y, fill.points, tolerance))
    if (hitLine || hitRect || hitFill) {
      return { id: source.id, source }
    }
  }
  return null
}

function buildProjectedDrawing(
  drawing: DrawingObject,
  parts: {
    segments?: ProjectedSegment[]
    rects?: ProjectedRect[]
    fills?: Array<{ points: string; fill: string }>
    labels?: ProjectedLabel[]
    handles?: Array<{ x: number; y: number }>
    midpoints?: Array<{ x: number; y: number }>
  },
): ProjectedDrawing {
  return {
    id: drawing.id,
    lineColor: drawing.settings.lineColor,
    lineWidth: drawing.settings.lineWidth,
    lineStyle: drawing.settings.lineStyle,
    segments: parts.segments ?? [],
    rects: parts.rects ?? [],
    fills: parts.fills ?? [],
    labels: parts.labels ?? [],
    handles: parts.handles ?? [],
    midpoints: parts.midpoints ?? [],
  }
}

function resolveLineSegmentForStyle(
  x1: number,
  y1: number,
  x2: number,
  y2: number,
  width: number,
  height: number,
  drawing: DrawingObject,
) {
  const mode = getDrawingExtendMode(drawing)
  if (mode === 'segment') {
    return { x1, y1, x2, y2 }
  }
  if (mode === 'right') {
    return extendLineToBounds(x1, y1, x2, y2, width, height, 'ray')
  }
  if (mode === 'both') {
    return extendLineToBounds(x1, y1, x2, y2, width, height, 'extendedLine')
  }

  const reversed = extendLineToBounds(x2, y2, x1, y1, width, height, 'ray')
  return reversed ? { x1: reversed.x2, y1: reversed.y2, x2, y2 } : { x1, y1, x2, y2 }
}

function getDrawingExtendMode(drawing: DrawingObject) {
  if (drawing.tool === 'ray') {
    return 'right'
  }
  if (drawing.tool === 'extendedLine') {
    return 'both'
  }
  if (drawing.settings.extendLeft && drawing.settings.extendRight) {
    return 'both'
  }
  if (drawing.settings.extendRight) {
    return 'right'
  }
  if (drawing.settings.extendLeft) {
    return 'left'
  }
  return 'segment'
}

function buildDrawingLabels(
  drawing: DrawingObject,
  firstPoint: DrawingPoint,
  secondPoint: DrawingPoint,
  anchorX: number,
  anchorY: number,
): ProjectedLabel[] {
  const labels: ProjectedLabel[] = []
  const xOffset = drawing.settings.statsPosition === 'right' ? 12 : -12
  const anchor: ProjectedLabel['anchor'] = drawing.settings.statsPosition === 'right' ? 'start' : 'end'

  if (drawing.settings.showStats) {
    const delta = secondPoint.price - firstPoint.price
    const deltaPct = firstPoint.price !== 0 ? (delta / firstPoint.price) * 100 : 0
    const bars = Math.max(Math.round(Math.abs(secondPoint.time - firstPoint.time) / 60), 1)
    labels.push({
      x: anchorX + xOffset,
      y: anchorY - 12,
      text: `${formatSignedNumber(delta, 6)} (${formatSignedPercent(deltaPct)}) · ${bars}m`,
      anchor,
      background: 'rgba(8, 17, 29, 0.88)',
      color: drawing.settings.lineColor,
    })
  }

  if (drawing.settings.showText && drawing.settings.text.trim()) {
    labels.push({
      x: anchorX + xOffset,
      y: anchorY + 10,
      text: drawing.settings.text.trim(),
      anchor,
      background: 'rgba(8, 17, 29, 0.88)',
      color: drawing.settings.textColor,
    })
  }

  if (drawing.settings.showPriceLabels) {
    labels.push(buildPriceLabel(anchorX + xOffset, anchorY + 28, secondPoint.price, anchor, drawing.settings.lineColor))
  }

  return labels
}

function buildPriceLabel(
  x: number,
  y: number,
  price: number,
  anchor: ProjectedLabel['anchor'] = 'end',
  color = '#cbd5e1',
): ProjectedLabel {
  return {
    x,
    y,
    text: formatNumber(price),
    anchor,
    background: 'rgba(8, 17, 29, 0.88)',
    color,
  }
}

function pointNearPolygonBounds(x: number, y: number, points: string, tolerance: number) {
  const values = points
    .split(' ')
    .map((point) => point.split(',').map(Number))
    .filter((pair) => pair.length === 2 && Number.isFinite(pair[0]) && Number.isFinite(pair[1]))
  if (values.length < 2) {
    return false
  }

  for (let index = 0; index < values.length; index += 1) {
    const [x1, y1] = values[index]
    const [x2, y2] = values[(index + 1) % values.length]
    if (distanceToSegment(x, y, x1, y1, x2, y2) <= tolerance) {
      return true
    }
  }
  return false
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

function buildMarkers(positions: PositionRecord[], candleTimes: number[]): SeriesMarker<UTCTimestamp>[] {
  return positions.flatMap((position, index) => {
    const openMarkerTime = alignMarkerTime(position.open_time, candleTimes)
    const openMarker: SeriesMarker<UTCTimestamp> = {
      time: toUtcTime(openMarkerTime),
      position: position.side === 'long' ? 'belowBar' : 'aboveBar',
      shape: position.side === 'long' ? 'arrowUp' : 'arrowDown',
      color: position.side === 'long' ? '#22c55e' : '#ef4444',
      text: `#${index + 1} 开仓`,
    }
    const closeMarkers =
      position.close_time === null
        ? []
        : [
            {
              time: toUtcTime(alignMarkerTime(position.close_time, candleTimes)),
              position: position.side === 'long' ? 'aboveBar' : 'belowBar',
              shape: 'circle',
              color: position.is_profit ? '#22c55e' : '#ef4444',
              text: `#${index + 1} 平仓`,
            } satisfies SeriesMarker<UTCTimestamp>,
          ]
    return [openMarker, ...closeMarkers]
  })
}

function buildMarkerPositionIndex(positions: PositionRecord[], candleTimes: number[]) {
  const index = new Map<number, string>()
  positions.forEach((position) => {
    index.set(alignMarkerTime(position.open_time, candleTimes), position.position_id)
    if (position.close_time !== null) {
      index.set(alignMarkerTime(position.close_time, candleTimes), position.position_id)
    }
  })
  return index
}

function alignMarkerTime(targetTime: number, candleTimes: number[]) {
  if (candleTimes.length === 0) {
    return targetTime
  }
  if (targetTime <= candleTimes[0]) {
    return candleTimes[0]
  }
  const lastTime = candleTimes[candleTimes.length - 1]
  if (targetTime >= lastTime) {
    return lastTime
  }

  for (let index = 0; index < candleTimes.length; index += 1) {
    const current = candleTimes[index]
    if (current >= targetTime) {
      if (index === 0) {
        return current
      }
      const previous = candleTimes[index - 1]
      return Math.abs(current - targetTime) < Math.abs(targetTime - previous) ? current : previous
    }
  }

  return lastTime
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
  return formatChartTimeValue(time)
}

function formatChartTimeValue(
  time:
    | number
    | {
        year: number
        month: number
        day: number
      },
) {
  const date =
    typeof time === 'number'
      ? new Date(time * 1000)
      : new Date(Date.UTC(time.year, time.month - 1, time.day))
  const shanghaiText = new Intl.DateTimeFormat('sv-SE', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(date)
  const [datePart = '----/--/--', timePart = '--:--'] = shanghaiText.replace(' ', 'T').split('T')
  const [year = '----', month = '--', day = '--'] = datePart.split('-')
  const weekdayIndex = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Shanghai',
    weekday: 'short',
  }).format(date)
  const weekdayMap: Record<string, string> = {
    Sun: '周日',
    Mon: '周一',
    Tue: '周二',
    Wed: '周三',
    Thu: '周四',
    Fri: '周五',
    Sat: '周六',
  }
  return `${weekdayMap[weekdayIndex] ?? '周--'} ${year}-${month}-${day} ${timePart}`
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

function lineStyleToDashArray(style: LineStyle) {
  if (style === LineStyle.Dashed) {
    return '8 6'
  }
  if (style === LineStyle.Dotted) {
    return '2 5'
  }
  return undefined
}

function nextLineStyle(style: LineStyle) {
  if (style === LineStyle.Solid) {
    return LineStyle.Dashed
  }
  if (style === LineStyle.Dashed) {
    return LineStyle.Dotted
  }
  return LineStyle.Solid
}

function nextLineWidth(width: number) {
  return width >= 5 ? 1 : width + 1
}

function applyAlpha(value: string, opacity: number) {
  if (value.startsWith('rgba(')) {
    const rgbaParts = value.match(/rgba\((\d+),\s*(\d+),\s*(\d+),\s*([^)]+)\)/)
    if (rgbaParts) {
      return `rgba(${rgbaParts[1]}, ${rgbaParts[2]}, ${rgbaParts[3]}, ${opacity})`
    }
  }
  if (value.startsWith('rgb(')) {
    const rgbParts = value.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/)
    if (rgbParts) {
      return `rgba(${rgbParts[1]}, ${rgbParts[2]}, ${rgbParts[3]}, ${opacity})`
    }
  }
  if (value.startsWith('#')) {
    const color = normalizeColorInput(value).replace('#', '')
    const normalized = color.length === 3 ? color.split('').map((item) => item + item).join('') : color
    const r = Number.parseInt(normalized.slice(0, 2), 16)
    const g = Number.parseInt(normalized.slice(2, 4), 16)
    const b = Number.parseInt(normalized.slice(4, 6), 16)
    return `rgba(${r}, ${g}, ${b}, ${opacity})`
  }
  return value
}

function normalizeColorInput(value: string) {
  return value.startsWith('#') ? value : '#94a3b8'
}

function drawingToolLabel(tool: Exclude<DrawingTool, 'cursor' | 'select'>) {
  switch (tool) {
    case 'trendline':
      return '趋势线'
    case 'parallelChannel':
      return '通道线'
    case 'fibRetracement':
      return '斐波那契回撤'
    case 'arrow':
      return '箭头线'
    case 'ray':
      return '射线'
    case 'extendedLine':
      return '延长线'
    case 'horizontalLine':
      return '水平线'
    case 'verticalLine':
      return '垂直线'
    case 'rectangle':
      return '矩形'
  }
}

function drawingTabLabel(tab: DrawingSettingsTab) {
  switch (tab) {
    case 'style':
      return '样式'
    case 'text':
      return '文本'
    case 'coordinates':
      return '坐标'
    case 'visibility':
      return '可见范围'
  }
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
    emaItems: buildEmaLegendItems(chartData, dataIndexes, time),
    ema: formatEmaLegend(chartData, dataIndexes, time),
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

  const emaSeriesList = Array.isArray(chartData.ema_series) ? chartData.ema_series : []

  return {
    volume: new Map(chartData.volume.map((row) => [row.time, row.volume])),
    ema: new Map(
      emaSeriesList.map((series) => [
        series.period,
        new Map(series.data.map((row) => [row.time, row.value])),
      ]),
    ),
    rsi: new Map(chartData.rsi.map((row) => [row.time, row.value])),
    macd: new Map(chartData.macd.map((row) => [row.time, row.value])),
    signal: new Map(chartData.signal.map((row) => [row.time, row.value])),
  }
}

function formatEmaLegend(
  chartData: ChartPayload,
  dataIndexes: ReturnType<typeof buildDataIndexes>,
  time: number,
) {
  const items = buildEmaLegendItems(chartData, dataIndexes, time)
  if (!items.length) {
    return '--'
  }
  return items.map((item) => `${item.period}: ${item.value}`).join('  ')
}

function buildEmaLegendItems(
  chartData: ChartPayload,
  dataIndexes: ReturnType<typeof buildDataIndexes>,
  time: number,
) {
  const emaSeriesList = Array.isArray(chartData.ema_series) ? chartData.ema_series : []
  return emaSeriesList
    .map((series, index) => {
      const seriesIndex = dataIndexes?.ema.get(series.period)
      const value = findValueAtTime(series.data, time, seriesIndex)
      if (value === null || value === undefined) {
        return null
      }
      return {
        period: series.period,
        value: formatNumber(value),
        color: EMA_LINE_COLORS[index % EMA_LINE_COLORS.length],
      }
    })
    .filter((item): item is { period: number; value: string; color: string } => Boolean(item))
}

function updateLegendState(
  setLegend: Dispatch<SetStateAction<LegendState | null>>,
  lastLegendKeyRef: MutableRefObject<string>,
  nextLegend: LegendState,
) {
  const nextKey = JSON.stringify(nextLegend)
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

function findNearestPositionByTime(positions: PositionRecord[], clickedTime: number, maxDeltaSeconds = 2 * 60 * 60) {
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
    if (delta < minDelta && delta <= maxDeltaSeconds) {
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
      showSettings: pane.key !== 'price',
      settingsKey: pane.key === 'price' ? null : pane.key,
    }
  })
}

function buildPaneWeights(indicators: IndicatorState) {
  const panes: Array<{ key: 'price' | 'ema' | 'volume' | 'rsi' | 'macd'; weight: number }> = []
  panes.push({
    key: indicators.showEma ? 'ema' : 'price',
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
  key: 'price' | 'ema' | 'volume' | 'rsi' | 'macd',
  indicatorSettings: IndicatorSettings,
) {
  if (key === 'price') {
    return 'PRICE'
  }
  if (key === 'ema') {
    return `EMA(${indicatorSettings.ema.periods.join(', ')})`
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
  key: 'price' | 'ema' | 'volume' | 'rsi' | 'macd',
  indicatorSettings: IndicatorSettings,
) {
  if (key === 'price') {
    return '主图 K 线'
  }
  if (key === 'ema') {
    return `周期 ${indicatorSettings.ema.periods.join(' / ')}`
  }
  if (key === 'volume') {
    return '成交量副图'
  }
  if (key === 'rsi') {
    return `周期 ${indicatorSettings.rsi.period}`
  }
  return `快 ${indicatorSettings.macd.fast_period} / 慢 ${indicatorSettings.macd.slow_period} / 信号 ${indicatorSettings.macd.signal_period}`
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
