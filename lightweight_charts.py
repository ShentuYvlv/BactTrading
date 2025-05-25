import dash
from dash import html, dcc, callback, Input, Output, State, ClientsideFunction
import dash_bootstrap_components as dbc
import os
import pandas as pd
import numpy as np
import json
import ccxt
import logging
import time
from datetime import datetime, timedelta
import dotenv

# 加载.env文件中的环境变量
dotenv.load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def initialize_exchange():
    """初始化并返回配置好的交易所对象"""
    # 从环境变量中获取API密钥
    API_KEY = os.getenv('BINANCE_API_KEY')
    API_SECRET = os.getenv('BINANCE_API_SECRET')
    
    # 设置币安交易所配置
    config = {
        'enableRateLimit': True,
        'timeout': 60000,  # 超时时间设置为60秒
        'proxies': {
            'http': 'socks5://127.0.0.1:10808',
            'https': 'socks5://127.0.0.1:10808'
        },
        'options': {
            'defaultType': 'future',  # 使用U本位永续合约
            'adjustForTimeDifference': True,  # 自动调整时间差异
            'recvWindow': 60000,  # 增加接收窗口
            'warnOnFetchOHLCVLimitArgument': False,
            'createMarketBuyOrderRequiresPrice': False,
            'fetchOHLCVWarning': False,
            'ws': {
                'options': {
                    'proxy': {
                        'host': '127.0.0.1',
                        'port': 10808,
                        'protocol': 'socks5',
                    }
                }
            }
        },
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
    }
    
    # 如果提供了API密钥，添加到配置中
    if API_KEY and API_SECRET:
        config['apiKey'] = API_KEY
        config['secret'] = API_SECRET
        logger.info("使用API密钥认证")
    else:
        logger.warning("未提供API密钥，将以只读模式运行")
    
    # 创建交易所实例
    exchange = ccxt.binance(config)
    
    try:
        # 同步服务器时间
        logger.info("正在同步服务器时间...")
        exchange.load_time_difference()
        time_diff = exchange.options.get('timeDifference', 0)
        logger.info(f"服务器时间差: {time_diff} 毫秒")
        
        # 测试连接
        server_time = exchange.fetch_time()
        local_time = int(time.time() * 1000)
        logger.info(f"服务器时间: {server_time}, 本地时间: {local_time}, 差异: {abs(server_time - local_time)} 毫秒")
    except Exception as e:
        logger.error(f"同步服务器时间失败: {str(e)}")
    
    return exchange

def fetch_ohlcv_data(exchange, symbol='NXPC/USDT:USDT', timeframe='1h', limit=400):
    """获取K线历史数据"""
    try:
        logger.info(f"获取 {symbol} 的 {timeframe} K线数据, 数量: {limit}...")
        
        # 确保交易对格式正确
        if ':' not in symbol and symbol.endswith('USDT'):
            # 如果是U本位合约但没有正确格式，添加:USDT后缀
            symbol = f"{symbol}:USDT"
            logger.info(f"调整交易对格式为: {symbol}")
        
        # 检查交易对是否存在
        try:
            exchange.load_markets()
            if symbol not in exchange.markets:
                available_symbols = [s for s in exchange.markets.keys() if 'USDT' in s][:10]
                logger.warning(f"交易对 {symbol} 不存在! 可用的USDT交易对示例: {available_symbols}")
                # 尝试使用NXPC/USDT作为备选
                symbol = 'NXPC/USDT:USDT'
                logger.info(f"使用备选交易对: {symbol}")
        except Exception as e:
            logger.error(f"加载市场数据失败: {str(e)}")
        
        # 获取OHLCV数据 - 使用标准CCXT方法
        params = {
            'limit': limit,
        }
        
        # 使用标准的fetch_ohlcv方法
        ohlcv = exchange.fetch_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            limit=limit,
            params=params
        )
        
        if not ohlcv or len(ohlcv) == 0:
            logger.warning(f"未获取到 {symbol} 的K线数据")
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # 转换为DataFrame
        df_ohlc = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # 转换时间戳为日期时间
        df_ohlc['timestamp'] = pd.to_datetime(df_ohlc['timestamp'], unit='ms')
        
        # 添加计算技术指标
        df_ohlc = add_technical_indicators(df_ohlc)
        
        logger.info(f"成功获取 {len(df_ohlc)} 条K线数据")
        return df_ohlc
    
    except Exception as e:
        logger.error(f"获取K线数据失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        # 返回空DataFrame
        return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

def add_technical_indicators(df):
    """添加技术指标到DataFrame"""
    # 添加EMA20指标
    df['ema20'] = df['close'].ewm(span=20, adjust=False).mean()
    
    # 添加RSI指标
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    avg_gain = gain.rolling(window=14).mean()
    avg_loss = loss.rolling(window=14).mean()
    
    # 计算第一个有效值后的平均值
    for i in range(14, len(df)):
        avg_gain.iloc[i] = (avg_gain.iloc[i-1] * 13 + gain.iloc[i]) / 14
        avg_loss.iloc[i] = (avg_loss.iloc[i-1] * 13 + loss.iloc[i]) / 14
    
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # 添加布林带
    df['sma20'] = df['close'].rolling(window=20).mean()
    df['std20'] = df['close'].rolling(window=20).std()
    df['upper_band'] = df['sma20'] + (df['std20'] * 2)
    df['lower_band'] = df['sma20'] - (df['std20'] * 2)
    
    # 添加MACD
    df['ema12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['ema26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = df['ema12'] - df['ema26']
    df['signal'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['histogram'] = df['macd'] - df['signal']
    
    # 处理NaN值
    df = df.fillna(0)
    
    return df

def prepare_data_for_chart(df):
    """准备数据用于Lightweight Charts渲染"""
    # 转换时间戳为JavaScript时间戳（毫秒）
    # 修复类型转换问题：先转换为int64，再进行计算
    df['time'] = df['timestamp'].astype('int64') // 10**6  # 转换为毫秒
    
    # 准备K线数据
    candlestick_data = df[['time', 'open', 'high', 'low', 'close']].to_dict('records')
    
    # 准备成交量数据
    volume_data = df[['time', 'volume']].to_dict('records')
    
    # 准备EMA20数据
    ema20_data = df[['time', 'ema20']].rename(columns={'ema20': 'value'}).to_dict('records')
    
    # 准备RSI数据
    rsi_data = df[['time', 'rsi']].rename(columns={'rsi': 'value'}).to_dict('records')
    
    # 准备布林带数据
    upper_band_data = df[['time', 'upper_band']].rename(columns={'upper_band': 'value'}).to_dict('records')
    middle_band_data = df[['time', 'sma20']].rename(columns={'sma20': 'value'}).to_dict('records')
    lower_band_data = df[['time', 'lower_band']].rename(columns={'lower_band': 'value'}).to_dict('records')
    
    # 准备MACD数据
    macd_data = df[['time', 'macd']].rename(columns={'macd': 'value'}).to_dict('records')
    signal_data = df[['time', 'signal']].rename(columns={'signal': 'value'}).to_dict('records')
    histogram_data = df[['time', 'histogram']].rename(columns={'histogram': 'value'}).to_dict('records')
    
    return {
        'candlestick': candlestick_data,
        'volume': volume_data,
        'ema20': ema20_data,
        'rsi': rsi_data,
        'upper_band': upper_band_data,
        'middle_band': middle_band_data,
        'lower_band': lower_band_data,
        'macd': macd_data,
        'signal': signal_data,
        'histogram': histogram_data
    }

def fetch_trades(exchange, symbol='NXPC/USDT:USDT', since=None, until=None, limit=100):
    """获取个人交易记录，支持时间范围过滤"""
    try:
        # 检查是否有API密钥
        if not exchange.apiKey or not exchange.secret:
            logger.warning("未提供API密钥，无法获取交易记录")
            return pd.DataFrame()
        
        # 确保交易对格式正确
        if ':' not in symbol and symbol.endswith('USDT'):
            # 如果是U本位合约但没有正确格式，添加:USDT后缀
            symbol = f"{symbol}:USDT"
            logger.info(f"调整交易对格式为: {symbol}")
        
        logger.info(f"获取 {symbol} 的交易记录, 数量: {limit}, 开始时间: {since}, 结束时间: {until}")
        
        # 准备参数
        params = {}
        if since:
            # 转换为毫秒时间戳
            if isinstance(since, str):
                since = pd.to_datetime(since).timestamp() * 1000
            params['since'] = int(since)
        
        if until:
            # CCXT没有直接的until参数，我们需要在获取数据后进行过滤
            if isinstance(until, str):
                until = pd.to_datetime(until).timestamp() * 1000
            until = int(until)
        
        # 使用标准的CCXT方法获取交易记录
        trades = []
        try:
            # 使用正确的CCXT方法名 - 驼峰命名法
            logger.info("尝试使用fetchMyTrades方法获取交易记录")
            trades = exchange.fetchMyTrades(symbol=symbol, limit=limit, params=params)
        except Exception as e:
            logger.error(f"使用fetchMyTrades获取交易记录失败: {str(e)}")
            
            try:
                # 尝试使用fetchOrders获取订单记录
                logger.info("尝试使用fetchOrders方法...")
                orders = exchange.fetchOrders(symbol=symbol, limit=limit, params=params)
                
                # 如果获取到订单，尝试提取其中已成交的部分作为交易记录
                if orders:
                    logger.info(f"获取到 {len(orders)} 个订单，尝试提取已成交部分")
                    trades = []
                    for order in orders:
                        if order.get('status') in ['closed', 'filled'] and order.get('filled', 0) > 0:
                            # 提取订单中的交易信息
                            trade_info = {
                                'id': order.get('id'),
                                'timestamp': order.get('timestamp'),
                                'datetime': order.get('datetime'),
                                'symbol': order.get('symbol'),
                                'side': order.get('side'),
                                'price': order.get('price'),
                                'amount': order.get('filled'),
                                'cost': order.get('cost'),
                                'fee': order.get('fee'),
                                'info': order.get('info')
                            }
                            trades.append(trade_info)
                    logger.info(f"从订单中提取了 {len(trades)} 条交易记录")
            except Exception as e2:
                logger.error(f"使用fetchOrders获取订单记录失败: {str(e2)}")
                
                try:
                    # 再尝试使用fetchClosedOrders获取已完成的订单
                    logger.info("尝试使用fetchClosedOrders方法...")
                    closed_orders = exchange.fetchClosedOrders(symbol=symbol, limit=limit, params=params)
                    
                    # 处理已完成订单
                    if closed_orders:
                        logger.info(f"获取到 {len(closed_orders)} 个已完成订单，尝试提取交易记录")
                        trades = []
                        for order in closed_orders:
                            if order.get('filled', 0) > 0:
                                # 提取订单中的交易信息
                                trade_info = {
                                    'id': order.get('id'),
                                    'timestamp': order.get('timestamp'),
                                    'datetime': order.get('datetime'),
                                    'symbol': order.get('symbol'),
                                    'side': order.get('side'),
                                    'price': order.get('price'),
                                    'amount': order.get('filled'),
                                    'cost': order.get('cost'),
                                    'fee': order.get('fee'),
                                    'info': order.get('info')
                                }
                                trades.append(trade_info)
                        logger.info(f"从已完成订单中提取了 {len(trades)} 条交易记录")
                except Exception as e3:
                    logger.error(f"使用fetchClosedOrders获取已完成订单失败: {str(e3)}")
        
        # 如果没有交易记录，返回空DataFrame
        if not trades:
            logger.info("没有找到交易记录")
            return pd.DataFrame()
        
        # 转换为DataFrame
        df_trades = pd.DataFrame(trades)
        
        # 如果有until参数，过滤结束时间之后的数据
        if until and 'timestamp' in df_trades.columns:
            df_trades = df_trades[df_trades['timestamp'] <= until]
        
        # 转换时间戳为日期时间
        if 'timestamp' in df_trades.columns:
            df_trades['timestamp'] = pd.to_datetime(df_trades['timestamp'], unit='ms')
        
        logger.info(f"成功获取 {len(df_trades)} 条交易记录")
        return df_trades
    
    except Exception as e:
        logger.error(f"获取交易记录失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        # 返回空DataFrame
        return pd.DataFrame()

def create_app():
    """创建Dash应用"""
    # 初始化交易所
    exchange = initialize_exchange()
    
    # 创建应用
    app = dash.Dash(
        __name__, 
        external_stylesheets=[dbc.themes.DARKLY],
        meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}]
    )
    
    # 添加外部脚本
    app.index_string = '''
    <!DOCTYPE html>
    <html>
        <head>
            {%metas%}
            <title>{%title%}</title>
            {%favicon%}
            {%css%}
            <!-- 直接在HTML中加载TradingView Lightweight Charts库 -->
            <script src="https://unpkg.com/lightweight-charts@4.0.1/dist/lightweight-charts.standalone.production.js" crossorigin="anonymous"></script>
            <script>
                // 检查库是否加载成功
                window.addEventListener('DOMContentLoaded', function() {
                    if (typeof LightweightCharts !== 'undefined') {
                        console.log('Lightweight Charts 库加载成功!');
                    } else {
                        console.error('Lightweight Charts 库加载失败!');
                    }
                });
            </script>
        </head>
        <body>
            {%app_entry%}
            <footer>
                {%config%}
                {%scripts%}
                {%renderer%}
            </footer>
        </body>
    </html>
    '''
    
    # 可选的周期
    timeframe_options = [
        {'label': '1分钟', 'value': '1m'},
        {'label': '5分钟', 'value': '5m'},
        {'label': '15分钟', 'value': '15m'},
        {'label': '1小时', 'value': '1h'},
        {'label': '4小时', 'value': '4h'},
        {'label': '1天', 'value': '1d'},
    ]
    
    # 预设的时间范围
    time_range_options = [
        {'label': '今天', 'value': 'today'},
        {'label': '昨天', 'value': 'yesterday'},
        {'label': '最近7天', 'value': '7d'},
        {'label': '最近30天', 'value': '30d'},
        {'label': '本月', 'value': 'this_month'},
        {'label': '上月', 'value': 'last_month'},
        {'label': '全部', 'value': 'all'},
        {'label': '自定义', 'value': 'custom'},
    ]
    
    # 应用布局
    app.layout = dbc.Container([
        # 标题行
        dbc.Row([
            dbc.Col([
                html.H1("TradingView Lightweight Charts 示例", className="text-center my-4")
            ], width=12)
        ]),
        
        # 控制行
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            # 交易对选择
                            dbc.Col([
                                html.Label("交易对"),
                                dcc.Input(
                                    id="symbol-input",
                                    type="text",
                                    value="NXPC/USDT:USDT",
                                    className="form-control"
                                )
                            ], width=3),
                            
                            # 时间周期选择
                            dbc.Col([
                                html.Label("时间周期"),
                                dcc.Dropdown(
                                    id="timeframe-dropdown",
                                    options=timeframe_options,
                                    value="1h",
                                    clearable=False
                                )
                            ], width=2),
                            
                            # 时间范围选择
                            dbc.Col([
                                html.Label("时间范围"),
                                dcc.Dropdown(
                                    id="time-range-dropdown",
                                    options=time_range_options,
                                    value="30d",
                                    clearable=False
                                )
                            ], width=2),
                            
                            # 自定义日期选择（初始隐藏）
                            dbc.Col([
                                html.Label("开始日期"),
                                dcc.DatePickerSingle(
                                    id="start-date-picker",
                                    date=datetime.now().date() - timedelta(days=30),
                                    display_format="YYYY-MM-DD",
                                    className="w-100"
                                )
                            ], width=2, id="start-date-col", style={"display": "true"}),
                            
                            dbc.Col([
                                html.Label("结束日期"),
                                dcc.DatePickerSingle(
                                    id="end-date-picker",
                                    date=datetime.now().date(),
                                    display_format="YYYY-MM-DD",
                                    className="w-100"
                                )
                            ], width=2, id="end-date-col", style={"display": "true"}),
                            
                            # 加载按钮
                            dbc.Col([
                                html.Label("\u00A0"),  # 非断空格，用于对齐
                                dbc.Button(
                                    "加载数据",
                                    id="load-data-button",
                                    color="primary",
                                    className="w-100"
                                )
                            ], width=1),
                            
                            # 重置图表按钮
                            dbc.Col([
                                html.Label("\u00A0"),  # 非断空格，用于对齐
                                dbc.Button(
                                    "重置图表",
                                    id="reset-chart-button",
                                    color="secondary",
                                    className="w-100"
                                )
                            ], width=1),
                        ]),
                        
                        # 精确时间选择行
                        dbc.Row([
                            dbc.Col([
                                html.Label("精确开始时间"),
                                dbc.Row([
                                    dbc.Col([
                                        dcc.Input(
                                            id="start-hour-input",
                                            type="number",
                                            min=0,
                                            max=23,
                                            value=0,
                                            className="form-control",
                                            placeholder="时"
                                        )
                                    ], width=4),
                                    dbc.Col([
                                        dcc.Input(
                                            id="start-minute-input",
                                            type="number",
                                            min=0,
                                            max=59,
                                            value=0,
                                            className="form-control",
                                            placeholder="分"
                                        )
                                    ], width=4),
                                    dbc.Col([
                                        dcc.Input(
                                            id="start-second-input",
                                            type="number",
                                            min=0,
                                            max=59,
                                            value=0,
                                            className="form-control",
                                            placeholder="秒"
                                        )
                                    ], width=4),
                                ])
                            ], width=3, id="start-time-col", style={"display": "none"}),
                            
                            dbc.Col([
                                html.Label("精确结束时间"),
                                dbc.Row([
                                    dbc.Col([
                                        dcc.Input(
                                            id="end-hour-input",
                                            type="number",
                                            min=0,
                                            max=23,
                                            value=23,
                                            className="form-control",
                                            placeholder="时"
                                        )
                                    ], width=4),
                                    dbc.Col([
                                        dcc.Input(
                                            id="end-minute-input",
                                            type="number",
                                            min=0,
                                            max=59,
                                            value=59,
                                            className="form-control",
                                            placeholder="分"
                                        )
                                    ], width=4),
                                    dbc.Col([
                                        dcc.Input(
                                            id="end-second-input",
                                            type="number",
                                            min=0,
                                            max=59,
                                            value=59,
                                            className="form-control",
                                            placeholder="秒"
                                        )
                                    ], width=4),
                                ])
                            ], width=3, id="end-time-col", style={"display": "none"}),
                            
                            # 显示交易记录选项
                            dbc.Col([
                                dbc.Checkbox(
                                    id="show-trades-checkbox",
                                    className="form-check-input",
                                    value=True,
                                ),
                                html.Label(
                                    "显示交易记录",
                                    className="form-check-label ms-2"
                                ),
                            ], width=2, className="d-flex align-items-center"),
                            
                            # 显示EMA20选项
                            dbc.Col([
                                dbc.Checkbox(
                                    id="show-ema-checkbox",
                                    className="form-check-input",
                                    value=True,
                                ),
                                html.Label(
                                    "显示EMA20",
                                    className="form-check-label ms-2"
                                ),
                            ], width=2, className="d-flex align-items-center"),
                            
                            # 显示布林带选项
                            dbc.Col([
                                dbc.Checkbox(
                                    id="show-bollinger-checkbox",
                                    className="form-check-input",
                                    value=False,
                                ),
                                html.Label(
                                    "显示布林带",
                                    className="form-check-label ms-2"
                                ),
                            ], width=2, className="d-flex align-items-center"),
                            
                            # 显示RSI指标选项
                            dbc.Col([
                                dbc.Checkbox(
                                    id="show-rsi-checkbox",
                                    className="form-check-input",
                                    value=True,
                                ),
                                html.Label(
                                    "显示RSI",
                                    className="form-check-label ms-2"
                                ),
                            ], width=2, className="d-flex align-items-center"),
                            
                            # 显示MACD指标选项
                            dbc.Col([
                                dbc.Checkbox(
                                    id="show-macd-checkbox",
                                    className="form-check-input",
                                    value=False,
                                ),
                                html.Label(
                                    "显示MACD",
                                    className="form-check-label ms-2"
                                ),
                            ], width=2, className="d-flex align-items-center"),
                            
                            # 状态信息显示
                            dbc.Col([
                                html.Div(id="status-info")
                            ], width=2),
                        ], className="mt-3"),
                    ])
                ], className="mb-4")
            ], width=12)
        ]),
        
        # 图表行
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        # 图表容器
                        html.Div(
                            id="chart-container",
                            style={
                                "width": "100%",
                                "height": "600px",
                                "position": "relative"
                            }
                        ),
                        
                        # 数据存储
                        dcc.Store(id="chart-data-store"),
                        dcc.Store(id="trades-data-store"),
                        
                        # 添加chart-interaction元素到初始布局
                        html.Div(id="chart-interaction", style={"display": "none"}),
                        
                        # 交互信息显示区
                        html.Div(
                            id="chart-info",
                            className="mt-2"
                        )
                    ])
                ])
            ], width=12)
        ]),
        
        # 加载动画
        dbc.Spinner(html.Div(id="loading-spinner"), color="primary"),
        
    ], fluid=True, className="bg-dark text-light")
    
    # 注册客户端回调函数
    app.clientside_callback(
        ClientsideFunction(namespace="clientside", function_name="initializeChart"),
        Output("chart-container", "children"),
        [Input("chart-data-store", "data"), Input("trades-data-store", "data"),
         Input("show-ema-checkbox", "value"), Input("show-trades-checkbox", "value"),
         Input("show-bollinger-checkbox", "value"), Input("show-rsi-checkbox", "value"),
         Input("show-macd-checkbox", "value")],
        [State("chart-container", "id")]
    )
    
    # 控制自定义日期和时间选择器的显示/隐藏
    @app.callback(
        [Output("start-date-col", "style"), 
         Output("end-date-col", "style"),
         Output("start-time-col", "style"),
         Output("end-time-col", "style")],
        [Input("time-range-dropdown", "value")]
    )
    def toggle_date_time_pickers(time_range):
        if time_range == "custom":
            return {"display": "block"}, {"display": "block"}, {"display": "block"}, {"display": "block"}
        else:
            return {"display": "none"}, {"display": "none"}, {"display": "none"}, {"display": "none"}
    
    # 计算时间范围
    def calculate_time_range(time_range, start_date=None, end_date=None, 
                           start_hour=0, start_minute=0, start_second=0,
                           end_hour=23, end_minute=59, end_second=59):
        now = datetime.now()
        
        if time_range == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif time_range == "yesterday":
            start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(microseconds=1)
        elif time_range == "7d":
            start = now - timedelta(days=7)
            end = now
        elif time_range == "30d":
            start = now - timedelta(days=30)
            end = now
        elif time_range == "this_month":
            start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif time_range == "last_month":
            last_month = now.replace(day=1) - timedelta(days=1)
            start = last_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(microseconds=1)
        elif time_range == "custom" and start_date and end_date:
            # 自定义日期范围，包含精确时间
            try:
                # 转换时间输入为整数
                start_hour = int(start_hour) if start_hour is not None else 0
                start_minute = int(start_minute) if start_minute is not None else 0
                start_second = int(start_second) if start_second is not None else 0
                end_hour = int(end_hour) if end_hour is not None else 23
                end_minute = int(end_minute) if end_minute is not None else 59
                end_second = int(end_second) if end_second is not None else 59
                
                # 限制在有效范围内
                start_hour = max(0, min(23, start_hour))
                start_minute = max(0, min(59, start_minute))
                start_second = max(0, min(59, start_second))
                end_hour = max(0, min(23, end_hour))
                end_minute = max(0, min(59, end_minute))
                end_second = max(0, min(59, end_second))
                
                # 创建带精确时间的datetime对象
                start = datetime.combine(
                    start_date, 
                    datetime.min.time().replace(
                        hour=start_hour, 
                        minute=start_minute, 
                        second=start_second
                    )
                )
                
                end = datetime.combine(
                    end_date, 
                    datetime.min.time().replace(
                        hour=end_hour, 
                        minute=end_minute, 
                        second=end_second
                    )
                )
                
                logger.info(f"自定义时间范围: 从 {start} 到 {end}")
            except Exception as e:
                logger.error(f"处理自定义时间范围时出错: {e}")
                # 使用默认值
                start = datetime.combine(start_date, datetime.min.time())
                end = datetime.combine(end_date, datetime.max.time())
        else:  # "all" or default
            start = None
            end = None
        
        # 转换为时间戳（如果有值）
        start_ts = int(start.timestamp() * 1000) if start else None
        end_ts = int(end.timestamp() * 1000) if end else None
        
        return start_ts, end_ts
    
    # 加载数据回调
    @app.callback(
        [Output("chart-data-store", "data"), 
         Output("trades-data-store", "data"),
         Output("loading-spinner", "children"),
         Output("status-info", "children")],
        [Input("load-data-button", "n_clicks"), Input("reset-chart-button", "n_clicks")],
        [State("symbol-input", "value"), 
         State("timeframe-dropdown", "value"),
         State("time-range-dropdown", "value"),
         State("start-date-picker", "date"),
         State("end-date-picker", "date"),
         State("start-hour-input", "value"),
         State("start-minute-input", "value"),
         State("start-second-input", "value"),
         State("end-hour-input", "value"),
         State("end-minute-input", "value"),
         State("end-second-input", "value")]
    )
    def load_chart_data(load_clicks, reset_clicks, symbol, timeframe, time_range, 
                      start_date, end_date, start_hour, start_minute, start_second,
                      end_hour, end_minute, end_second):
        triggered_id = dash.callback_context.triggered[0]["prop_id"].split(".")[0]
        
        if triggered_id == "load-data-button" and load_clicks:
            try:
                # 计算时间范围
                since, until = calculate_time_range(
                    time_range, start_date, end_date,
                    start_hour, start_minute, start_second,
                    end_hour, end_minute, end_second
                )
                
                # 获取K线数据
                df = fetch_ohlcv_data(exchange, symbol, timeframe)
                
                if df.empty:
                    return dash.no_update, dash.no_update, "", html.Div("无法加载K线数据", className="text-danger")
                
                # 如果指定了时间范围，过滤数据
                if since:
                    since_dt = pd.to_datetime(since, unit='ms')
                    df = df[df['timestamp'] >= since_dt]
                    logger.info(f"过滤开始时间后剩余 {len(df)} 条数据")
                
                if until:
                    until_dt = pd.to_datetime(until, unit='ms')
                    df = df[df['timestamp'] <= until_dt]
                    logger.info(f"过滤结束时间后剩余 {len(df)} 条数据")
                
                if df.empty:
                    return dash.no_update, dash.no_update, "", html.Div("指定时间范围内没有K线数据", className="text-danger")
                
                # 准备图表数据
                chart_data = prepare_data_for_chart(df)
                
                # 获取交易记录
                df_trades = fetch_trades(exchange, symbol, since, until)
                trades_data = []
                
                if not df_trades.empty:
                    # 准备交易数据
                    for _, trade in df_trades.iterrows():
                        if 'timestamp' in trade and 'price' in trade and 'side' in trade and 'amount' in trade:
                            trade_time = int(pd.to_datetime(trade['timestamp']).timestamp() * 1000)
                            trades_data.append({
                                'time': trade_time,
                                'price': trade['price'],
                                'side': trade['side'],
                                'amount': trade['amount'],
                                'cost': trade['price'] * trade['amount'] if 'amount' in trade else 0
                            })
                
                # 返回数据和状态信息
                status_info = html.Div([
                    html.Span(f"已加载 {len(df)} 条K线数据", className="text-success me-3"),
                    html.Span(f"已加载 {len(trades_data)} 条交易记录", className="text-info")
                ])
                
                return json.dumps(chart_data), json.dumps(trades_data), "", status_info
                
            except Exception as e:
                logger.error(f"加载数据出错: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                return dash.no_update, dash.no_update, "", html.Div(f"加载数据出错: {str(e)}", className="text-danger")
        
        elif triggered_id == "reset-chart-button" and reset_clicks:
            # 发送一个空的数据集以重置图表
            return "{}", "[]", "", html.Div("图表已重置", className="text-warning")
        
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update
    
    # 注册交互回调
    @app.callback(
        Output("chart-info", "children"),
        Input("chart-interaction", "children"),
    )
    def update_interaction_info(interaction_json):
        if not interaction_json:
            return html.P("将鼠标悬停在图表上以查看详情")
        
        try:
            # 解析交互数据
            data = json.loads(interaction_json)
            
            # 创建信息显示
            return html.Div([
                html.P([
                    html.Strong("时间: "), html.Span(data.get("time", "N/A")), " | ",
                    html.Strong("价格: "), html.Span(f"{data.get('price', 0):.4f}"), " | ",
                    html.Strong("开盘: "), html.Span(f"{data.get('open', 0):.4f}"), " | ",
                    html.Strong("最高: "), html.Span(f"{data.get('high', 0):.4f}"), " | ",
                    html.Strong("最低: "), html.Span(f"{data.get('low', 0):.4f}"), " | ",
                    html.Strong("收盘: "), html.Span(f"{data.get('close', 0):.4f}"), " | ",
                    html.Strong("成交量: "), html.Span(f"{data.get('volume', 0):.2f}")
                ])
            ])
        except Exception as e:
            logger.error(f"解析交互数据错误: {str(e)}")
            return html.P("数据解析错误")
    
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=8051) 