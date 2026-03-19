import type {
  ChartLoadRequest,
  ChartResponse,
  ConfigResponse,
  DataFilesResponse,
  LoadMoreRequest,
  LoadMoreResponse,
  RebuildRequest,
  RebuildResponse,
  SymbolsResponse,
} from '../types/api'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? ''

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.ok) {
    return (await response.json()) as T
  }

  let detail = `Request failed: ${response.status}`
  try {
    const payload = (await response.json()) as { detail?: string }
    if (payload.detail) {
      detail = payload.detail
    }
  } catch {
    // Ignore JSON parse errors and use the default message.
  }
  throw new Error(detail)
}

function withQuery(path: string, params?: Record<string, string | number | null | undefined>) {
  const search = new URLSearchParams()
  Object.entries(params ?? {}).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      search.set(key, String(value))
    }
  })
  const suffix = search.toString()
  return `${API_BASE}${path}${suffix ? `?${suffix}` : ''}`
}

export function fetchConfig() {
  return fetch(withQuery('/api/config')).then(parseResponse<ConfigResponse>)
}

export function fetchDataFiles() {
  return fetch(withQuery('/api/data-files')).then(parseResponse<DataFilesResponse>)
}

export function fetchSymbols(dataFile: string | null, minTrades: number) {
  return fetch(
    withQuery('/api/symbols', {
      data_file: dataFile,
      min_trades: minTrades,
    }),
  ).then(parseResponse<SymbolsResponse>)
}

export function loadChart(request: ChartLoadRequest) {
  return fetch(withQuery('/api/chart/load'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  }).then(parseResponse<ChartResponse>)
}

export function loadMoreChart(request: LoadMoreRequest) {
  return fetch(withQuery('/api/chart/load-more'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  }).then(parseResponse<LoadMoreResponse>)
}

export function rebuildPositions(request: RebuildRequest) {
  return fetch(withQuery('/api/positions/rebuild'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  }).then(parseResponse<RebuildResponse>)
}
