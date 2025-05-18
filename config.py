import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置代理环境变量
os.environ['HTTP_PROXY'] = 'socks5://127.0.0.1:10808'
os.environ['HTTPS_PROXY'] = 'socks5://127.0.0.1:10808'
os.environ['ALL_PROXY'] = 'socks5://127.0.0.1:10808'

# 币安API设置
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_API_SECRET = os.getenv('BINANCE_API_SECRET')

# 代理设置
PROXY_ENABLED = True  # 设置为False可以禁用代理
PROXY_HOST = '127.0.0.1'
PROXY_PORT = 10808
PROXY_CONFIG = {
    'http': f'socks5://{PROXY_HOST}:{PROXY_PORT}',
    'https': f'socks5://{PROXY_HOST}:{PROXY_PORT}'
} if PROXY_ENABLED else None

# 应用设置
APP_PORT = 8050
APP_HOST = '127.0.0.1'
DEBUG_MODE = True

# 时间周期设置
TIMEFRAMES = {
    '1分钟': '1m',
    '5分钟': '5m',
    '15分钟': '15m',
    '1小时': '1h',
    '4小时': '4h',
    '1天': '1d'
}

# 交易对
DEFAULT_SYMBOL = 'BTC/USDT'
SYMBOLS = [
    'BTC/USDT',
    'ETH/USDT',
    'BNB/USDT',
    'SOL/USDT',
    'XRP/USDT',
    'ADA/USDT',
    'DOGE/USDT',
    'DOT/USDT',
    'AVAX/USDT',
    'SHIB/USDT',
    'LINK/USDT',
    'LTC/USDT',
    'UNI/USDT',
    'MATIC/USDT',
    'TRX/USDT'
]

# 合约交易对可能会有.P后缀，具体取决于币安API的返回格式
FUTURES_SYMBOLS = [
    'BTC/USDT',
    'ETH/USDT',
    'BNB/USDT',
    'SOL/USDT',
    'XRP/USDT',
    'ADA/USDT',
    'DOGE/USDT',
    'DOT/USDT',
    'AVAX/USDT',
    'LINK/USDT',
    'LTC/USDT',
    'MATIC/USDT'
]

# 图表设置
CHART_STYLE = {
    'background_color': '#f8f9fa',
    'plot_bgcolor': 'white',
    'paper_bgcolor': 'white',
    'font_color': '#2c3e50',
    'grid_color': '#ecf0f1',
    'buy_color': '#27ae60',
    'sell_color': '#e74c3c',
    'price_line_color': '#3498db'
} 