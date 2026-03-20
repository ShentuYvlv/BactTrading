export type IndicatorKey =
  | 'showEma'
  | 'showVolume'
  | 'showRsi'
  | 'showMacd'
  | 'showTradeMarkers'

export type IndicatorState = Record<IndicatorKey, boolean>

export interface IndicatorSettings {
  ema: {
    periods: number[]
  }
  rsi: {
    period: number
  }
  macd: {
    fast_period: number
    slow_period: number
    signal_period: number
  }
}

export interface ConfigResponse {
  chart_defaults: {
    symbol: string
    fallback_symbol: string
    timeframe: string
    start_date: string
    end_date: string
    min_trades: number
  }
  timeframe_options: Array<{ label: string; value: string }>
  exchange_options: Array<{ label: string; value: string }>
  app_debug: boolean
}

export interface DataFileItem {
  filename: string
  path: string
  size: string
  modified: string
}

export interface DataFilesResponse {
  items: DataFileItem[]
  latest: string | null
}

export interface SymbolItem {
  symbol: string
  trade_count: number
  first_trade_date?: string | null
  last_trade_date?: string | null
}

export interface SymbolsResponse {
  items: SymbolItem[]
  total: number
  data_file?: string
  date_range?: {
    start_date: string
    end_date: string
  } | null
}

export interface CandlestickDatum {
  time: number
  open: number
  high: number
  low: number
  close: number
}

export interface ValueDatum {
  time: number
  value: number
}

export interface VolumeDatum {
  time: number
  volume: number
}

export interface ChartPayload {
  candlestick: CandlestickDatum[]
  volume: VolumeDatum[]
  ema_series: Array<{
    period: number
    data: ValueDatum[]
  }>
  rsi: ValueDatum[]
  macd: ValueDatum[]
  signal: ValueDatum[]
  histogram: ValueDatum[]
}

export interface PositionRecord {
  position_id: string
  side: 'long' | 'short'
  open_time: number
  close_time: number | null
  open_price: number
  close_price: number | null
  amount: number
  profit: number
  open_time_formatted: string
  close_time_formatted: string
  is_profit: boolean
  is_open?: boolean
}

export interface ChartSummary {
  time_range: string
  data_source: string
  file_name?: string | null
  candle_count: number
  position_count: number
}

export interface ChartResponse {
  chart: ChartPayload
  positions: PositionRecord[]
  summary: ChartSummary
  symbol: string
  timeframe: string
  exchange: string
  indicator_settings: IndicatorSettings
}

export interface ChartLoadRequest {
  symbol: string
  timeframe: string
  start_date: string
  end_date: string
  data_file?: string | null
  exchange?: string | null
  indicator_settings?: IndicatorSettings
}

export interface LoadMoreRequest {
  symbol: string
  timeframe: string
  last_timestamp: number
  candles_to_load: number
  exchange?: string | null
}

export interface LoadMoreResponse {
  chart: ChartPayload | null
  added: number
}

export interface RebuildRequest {
  exchange: string
  start_date: string
  end_date: string
  threads: number
  max_retries: number
}

export interface RebuildResponse {
  file_path: string
  exchange: string
  start_date: string
  end_date: string
}
