# FastAPI + React Refactor Checklist

## Goal

Replace the monolithic Dash app with a separated backend/frontend architecture:

- Backend: FastAPI
- Frontend: React + Vite + Tailwind CSS
- Preserve all existing user-facing functionality before removing the old page

## Existing Feature Inventory

### Data Sources

- [x] Read local CSV files from `data/`
- [x] List available CSV files ordered by latest modified time
- [x] Load symbols from a selected CSV file
- [x] Filter symbols by minimum trade count
- [x] Load position records from CSV
- [x] Fallback to exchange API when CSV has no matching positions

### Market Data

- [x] Load OHLCV from exchange by symbol, timeframe, and date range
- [x] Support cache read/write for OHLCV
- [x] Append more candles to existing cached series
- [x] Support "load more" chart history
- [x] Keep Binance futures symbol normalization behavior

### Indicators

- [x] EMA20
- [x] Bollinger Bands
- [x] RSI
- [x] MACD
- [x] Volume panel

### Chart UX

- [x] Main candlestick chart
- [x] TradingView-like multi-pane indicator layout
- [x] Show/hide indicators
- [x] Show/hide trade markers
- [x] Shared time axis across panes
- [x] Crosshair-driven legend/summary
- [x] Keyboard shortcuts
- [x] Toolbar actions
- [x] Context menu
- [x] Responsive resizing

### Position Review

- [x] Previous/next position navigation
- [x] Jump to position by number
- [x] Focus chart on selected position range
- [x] Position info panel

### Position Rebuild

- [x] Fetch trades from Binance
- [x] Fetch trades from OKX
- [x] Rebuild positions from trades
- [x] Save rebuilt positions to CSV
- [x] Retry failed symbols
- [x] Keep CLI entrypoint for rebuild task

### Configuration

- [x] Read runtime configuration from `.env`
- [x] Keep proxy support
- [x] Keep chart defaults
- [x] Keep server defaults
- [x] Keep position rebuild defaults

### Delivery

- [x] Replace old Dash page as primary app
- [x] Update docs
- [x] Verify backend starts
- [x] Verify frontend builds
- [x] Verify end-to-end local workflow

## Migration Strategy

1. Build new backend and frontend skeletons.
2. Move reusable Python logic into backend services.
3. Expose stable APIs for config, files, symbols, chart load, load more, and rebuild.
4. Rebuild the UI in React using the new APIs.
5. Remove/retire the old Dash page after parity is reached.
