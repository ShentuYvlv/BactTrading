TIMEFRAME_OPTIONS = [
    {"label": "1分钟", "value": "1m"},
    {"label": "5分钟", "value": "5m"},
    {"label": "15分钟", "value": "15m"},
    {"label": "30分钟", "value": "30m"},
    {"label": "1小时", "value": "1h"},
    {"label": "4小时", "value": "4h"},
    {"label": "8小时", "value": "8h"},
    {"label": "1天", "value": "1d"},
    {"label": "1周", "value": "1w"},
]

TIMEFRAME_INCREMENT_MS = {
    "1m": 1 * 60 * 1000,
    "5m": 5 * 60 * 1000,
    "15m": 15 * 60 * 1000,
    "30m": 30 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "8h": 8 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
    "1w": 7 * 24 * 60 * 60 * 1000,
}
