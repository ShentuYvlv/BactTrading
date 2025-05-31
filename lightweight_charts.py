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
import hashlib
import pickle
import threading
import urllib3

# 加载.env文件中的环境变量
dotenv.load_dotenv()

# 添加函数：从CSV文件加载币种数据
def load_symbols_from_csv(csv_file_path, min_trades=5):
    """从CSV文件中加载币种数据，并按交易次数过滤
    
    Args:
        csv_file_path (str): CSV文件路径
        min_trades (int): 最小交易次数，小于此值的币种会被过滤掉
        
    Returns:
        dict: 币种列表及其交易次数，按交易次数降序排序
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(csv_file_path):
            logger.error(f"CSV文件不存在: {csv_file_path}")
            return {}
        
        # 读取CSV文件
        df = pd.read_csv(csv_file_path)
        logger.info(f"成功读取CSV文件，共 {len(df)} 条交易记录")
        
        # 确保必要的列存在
        required_columns = ['交易对', '交易次数']
        if not all(col in df.columns for col in required_columns):
            logger.error(f"CSV文件缺少必要的列: {required_columns}")
            return {}
        
        # 统计每个币种的交易次数
        symbol_counts = {}
        for _, row in df.iterrows():
            symbol = row['交易对']
            trades = row['交易次数']
            
            # 累计交易次数
            if symbol in symbol_counts:
                symbol_counts[symbol] += trades
            else:
                symbol_counts[symbol] = trades
        
        # 过滤交易次数小于min_trades的币种
        filtered_symbols = {symbol: count for symbol, count in symbol_counts.items() if count >= min_trades}
        
        # 按交易次数降序排序
        sorted_symbols = dict(sorted(filtered_symbols.items(), key=lambda item: item[1], reverse=True))
        
        logger.info(f"过滤后的币种: {len(sorted_symbols)}/{len(symbol_counts)}")
        return sorted_symbols
    
    except Exception as e:
        logger.error(f"读取CSV文件时发生错误: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {}

# 添加函数：直接从CSV加载仓位数据
def load_positions_from_csv(csv_file_path, symbol=None):
    """从CSV文件中直接加载仓位数据
    
    Args:
        csv_file_path (str): CSV文件路径
        symbol (str, optional): 过滤指定交易对的仓位，如果为None则加载所有仓位
        
    Returns:
        list: 仓位数据列表，格式适合图表标记使用
    """
    try:
        # 检查文件是否存在
        if not os.path.exists(csv_file_path):
            logger.error(f"CSV文件不存在: {csv_file_path}")
            return []
        
        # 读取CSV文件
        df = pd.read_csv(csv_file_path)
        logger.info(f"成功读取CSV仓位文件，共 {len(df)} 条记录")
        
        # 检查必要的列是否存在
        required_columns = ['仓位ID', '交易对', '方向', '数量', '开仓价格', '开仓时间', 
                           '平仓价格', '平仓时间', 'PnL', '原始开仓时间戳', '原始平仓时间戳']
        
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.warning(f"CSV文件缺少列: {missing_columns}，将尝试使用可用列")
        
        # 如果指定了交易对，过滤数据
        if symbol:
            df = df[df['交易对'] == symbol]
            logger.info(f"过滤 {symbol} 的仓位数据，剩余 {len(df)} 条记录")
        
        if df.empty:
            logger.warning(f"没有找到符合条件的仓位数据")
            return []
        
        # 转换为适合图表标记的格式
        positions_data = []
        
        for _, row in df.iterrows():
            try:
                # 处理方向
                side = 'long' if row['方向'] == '多头' else 'short'
                
                # 处理时间戳 - 优先使用原始时间戳
                if 'original_open_time' in row and pd.notna(row['原始开仓时间戳']):
                    open_timestamp = int(row['原始开仓时间戳']) // 1000  # 转换为秒级时间戳
                else:
                    # 否则尝试解析时间字符串
                    open_timestamp = int(pd.to_datetime(row['开仓时间']).timestamp())
                
                # 处理平仓时间
                if '状态' in row and row['状态'] != '已平仓':
                    # 未平仓的仓位
                    close_timestamp = None
                    close_time_formatted = '持仓中'
                elif 'original_close_time' in row and pd.notna(row['原始平仓时间戳']):
                    close_timestamp = int(row['原始平仓时间戳']) // 1000  # 转换为秒级时间戳
                    close_time_formatted = row['平仓时间']
                else:
                    # 尝试解析时间字符串
                    close_timestamp = int(pd.to_datetime(row['平仓时间']).timestamp()) if pd.notna(row['平仓时间']) else None
                    close_time_formatted = row['平仓时间'] if pd.notna(row['平仓时间']) else '持仓中'
                
                # 计算是否盈利
                profit = float(row['PnL']) if pd.notna(row['PnL']) else 0
                is_profit = profit >= 0
                
                # 创建仓位数据对象
                position_data = {
                    'position_id': str(row['仓位ID']) if '仓位ID' in row else f"pos-{_}",
                    'side': side,
                    'open_time': open_timestamp,
                    'close_time': close_timestamp,
                    'open_price': float(row['开仓价格']),
                    'close_price': float(row['平仓价格']) if pd.notna(row['平仓价格']) else None,
                    'amount': float(row['数量']) if pd.notna(row['数量']) else 0,
                    'profit': profit,
                    'open_time_formatted': row['开仓时间'],
                    'close_time_formatted': close_time_formatted,
                    'is_profit': is_profit,
                    'is_open': close_timestamp is None
                }
                
                positions_data.append(position_data)
            except Exception as e:
                logger.error(f"处理仓位行数据时出错: {str(e)}, 行: {row}")
                continue
        
        logger.info(f"成功加载 {len(positions_data)} 个仓位数据")
        return positions_data
    
    except Exception as e:
        logger.error(f"加载仓位数据时发生错误: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return []

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建缓存目录
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)

# 缓存锁，防止多线程同时写入缓存
cache_lock = threading.Lock()

def get_cache_key(symbol, timeframe, since, until):
    """生成缓存键"""
    # 将参数转换为字符串并连接
    key_str = f"{symbol}_{timeframe}_{since}_{until}"
    # 使用哈希函数生成唯一键
    return hashlib.md5(key_str.encode()).hexdigest()

def get_cached_data(cache_key):
    """从缓存获取数据"""
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.pkl")
    
    # 检查缓存文件是否存在且未过期
    if os.path.exists(cache_file):
        # 检查文件修改时间，如果在24小时内则使用缓存
        file_mod_time = os.path.getmtime(cache_file)
        if time.time() - file_mod_time < 24 * 3600:  # 24小时缓存
            try:
                with open(cache_file, 'rb') as f:
                    data = pickle.load(f)
                logger.info(f"从缓存加载数据: {cache_key}")
                return data
            except Exception as e:
                logger.error(f"读取缓存失败: {str(e)}")
    
    return None

def save_to_cache(cache_key, data):
    """保存数据到缓存"""
    try:
        with cache_lock:
            cache_file = os.path.join(CACHE_DIR, f"{cache_key}.pkl")
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            logger.info(f"数据已保存到缓存: {cache_key}")
    except Exception as e:
        logger.error(f"保存缓存失败: {str(e)}")

def initialize_exchange():
    """初始化并返回配置好的交易所对象"""
    # 从环境变量中获取API密钥
    API_KEY = os.getenv('BINANCE_API_KEY')
    API_SECRET = os.getenv('BINANCE_API_SECRET')
    
    # 设置币安交易所配置 - 与TEST_ca.py中成功的代理配置保持一致
    config = {
        'enableRateLimit': True,
        'timeout': 60000,
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
        },
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        },
        'verify': False,  # 禁用SSL证书验证
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

def fetch_ohlcv_data(exchange, symbol='NXPC/USDT:USDT', timeframe='1h', since=None, until=None):
    """获取K线历史数据"""
    try:
        logger.info(f"获取 {symbol} 的 {timeframe} K线数据, 时间范围: {since} - {until}")
        
        # 处理时间参数，确保格式正确
        formatted_since = since
        formatted_until = until
        
        if since:
            # 转换为毫秒时间戳
            if isinstance(since, str):
                formatted_since = int(pd.to_datetime(since).timestamp() * 1000)
            elif since < 10000000000:  # 如果是秒级时间戳，转换为毫秒
                formatted_since = int(since * 1000)
            else:
                formatted_since = int(since)
        
        if until:
            # 转换为毫秒时间戳
            if isinstance(until, str):
                formatted_until = int(pd.to_datetime(until).timestamp() * 1000)
            elif until < 10000000000:  # 如果是秒级时间戳，转换为毫秒
                formatted_until = int(until * 1000)
            else:
                formatted_until = int(until)
        
        # 生成缓存键
        cache_key = get_cache_key(symbol, timeframe, formatted_since, formatted_until)
        
        # 尝试从缓存加载数据
        cached_data = get_cached_data(cache_key)
        if cached_data is not None and not cached_data.empty:
            logger.info(f"使用缓存的K线数据: {len(cached_data)} 条记录")
            return cached_data
        
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
        
        # 使用单一请求策略获取数据
        all_ohlcv = []
        batch_limit = 1000  # 每批获取的数据量
        
        # 如果指定了时间范围，直接获取该范围的数据
        if formatted_since and formatted_until:
            try:
                logger.info(f"直接获取指定时间范围的数据: {pd.to_datetime(formatted_since, unit='ms')} 到 {pd.to_datetime(formatted_until, unit='ms')}")
                
                # 设置参数
                params = {
                    'startTime': formatted_since,
                    'endTime': formatted_until
                }
                
                # 获取数据
                all_ohlcv = exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=batch_limit,
                    params=params
                )
                
                logger.info(f"获取了 {len(all_ohlcv)} 条K线数据")
            except Exception as e:
                logger.error(f"获取指定时间范围数据失败: {str(e)}")
                # 如果直接获取失败，尝试分批获取
                logger.info("尝试分批获取数据...")
                
                current_since = formatted_since
                while current_since < formatted_until:
                    try:
                        params = {'since': current_since}
                        batch = exchange.fetch_ohlcv(
                            symbol=symbol,
                            timeframe=timeframe,
                            limit=batch_limit,
                            params=params
                        )
                        
                        if not batch or len(batch) == 0:
                            break
                            
                        # 过滤结束时间之后的数据
                        batch = [candle for candle in batch if candle[0] <= formatted_until]
                        
                        all_ohlcv.extend(batch)
                        logger.info(f"已获取 {len(all_ohlcv)} 条K线数据")
                        
                        # 如果返回的数据量小于请求的限制，说明已经获取了所有数据
                        if len(batch) < batch_limit:
                            break
                            
                        # 更新since为最后一条数据的时间加1毫秒，继续获取下一批
                        current_since = batch[-1][0] + 1
                        
                        # 短暂等待避免超过API速率限制
                        time.sleep(0.5)
                    except Exception as e:
                        logger.error(f"获取K线批次失败: {str(e)}")
                        time.sleep(2)
                        break  # 出错时停止循环，避免无限重试
        else:
            # 没有指定时间范围，获取最近的数据
            try:
                all_ohlcv = exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=batch_limit
                )
                logger.info(f"获取了 {len(all_ohlcv)} 条最近的K线数据")
            except Exception as e:
                logger.error(f"获取K线数据失败: {str(e)}")
        
        if not all_ohlcv or len(all_ohlcv) == 0:
            logger.warning(f"未获取到 {symbol} 的K线数据")
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # 转换为DataFrame
        df_ohlc = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # 转换时间戳为日期时间
        df_ohlc['timestamp'] = pd.to_datetime(df_ohlc['timestamp'], unit='ms')
        
        # 添加计算技术指标
        df_ohlc = add_technical_indicators(df_ohlc)
        
        # 保存到缓存
        save_to_cache(cache_key, df_ohlc)
        
        logger.info(f"成功获取 {len(df_ohlc)} 条K线数据，时间范围: {df_ohlc['timestamp'].min()} - {df_ohlc['timestamp'].max()}")
        return df_ohlc
    
    except Exception as e:
        logger.error(f"获取K线数据失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        # 返回空DataFrame
        return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

def add_technical_indicators(df):
    """添加技术指标到DataFrame"""
    # 添加EMA20指标   刻录机
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
    # 转换时间戳为JavaScript时间戳（秒）
    # Lightweight Charts期望秒级时间戳
    df['time'] = df['timestamp'].astype('int64') // 10**9  # 转换为秒
    
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
    """获取个人交易记录，支持时间范围过滤，自动分批查询"""
    try:
        # 检查是否有API密钥
        if not exchange.apiKey or not exchange.secret:
            logger.warning("未提供API密钥，无法获取交易记录")
            return pd.DataFrame()
        
        # 处理交易对格式，确保与Binance API兼容
        # 获取交易所的实际设置
        exchange_type = exchange.options.get('defaultType', 'spot')
        logger.info(f"当前交易所设置的交易类型: {exchange_type}")
        
        # 检查交易对格式是否需要调整
        original_symbol = symbol
        
        # 根据交易类型调整符号格式
        if exchange_type == 'future' or exchange_type == 'futures':
            # U本位合约
            if ':' not in symbol and symbol.endswith('USDT'):
                # 尝试使用没有后缀的标准格式
                symbol = symbol.replace(':USDT', '')
                logger.info(f"调整U本位合约交易对格式为: {symbol}")
        elif exchange_type == 'delivery':
            # 币本位合约
            if '/USD:' not in symbol and '/USDT:' not in symbol:
                base = symbol.split('/')[0]
                if base:
                    symbol = f"{base}/USD:{base}"
                    logger.info(f"调整币本位合约交易对格式为: {symbol}")
        else:
            # 现货交易
            if ':' in symbol:
                symbol = symbol.split(':')[0]
                logger.info(f"调整现货交易对格式为: {symbol}")
        
        logger.info(f"获取 {symbol} 的交易记录, 原始格式: {original_symbol}, 数量: {limit}, 开始时间: {since}, 结束时间: {until}")
        
        try:
            # 验证交易对是否存在
            markets = exchange.loadMarkets()
            if symbol not in markets:
                logger.warning(f"交易对 {symbol} 在市场中不存在，尝试其他格式")
                
                # 尝试不同的格式
                alternative_formats = [
                    original_symbol,                      # 原始格式
                    original_symbol.replace(':USDT', ''), # 移除后缀
                    f"{original_symbol.split('/')[0]}/USDT" # 只保留基础货币
                ]
                
                for alt_symbol in alternative_formats:
                    if alt_symbol != symbol and alt_symbol in markets:
                        symbol = alt_symbol
                        logger.info(f"找到有效的替代交易对格式: {symbol}")
                        break
                
                # 检查是否找到有效交易对
                if symbol not in markets:
                    available_symbols = [s for s in markets.keys() if 'USDT' in s][:5]
                    logger.warning(f"未找到有效交易对! 可用USDT交易对示例: {available_symbols}")
        except Exception as e:
            logger.error(f"验证交易对时出错: {str(e)}")
        
        # 处理时间参数
        current_time = int(time.time() * 1000)  # 当前时间戳（毫秒）
        
        # 如果没有指定结束时间，使用当前时间
        if not until:
            until = current_time
        else:
            # 确保until是毫秒时间戳
            if isinstance(until, str):
                until = int(pd.to_datetime(until).timestamp() * 1000)
            else:
                until = int(until)
                # 确保时间戳是毫秒级别
                if until < 10000000000:
                    until *= 1000
        
        # 如果没有指定开始时间，默认查询最近30天
        if not since:
            since = until - (30 * 24 * 60 * 60 * 1000)  # 30天前（毫秒）
        else:
            # 确保since是毫秒时间戳
            if isinstance(since, str):
                since = int(pd.to_datetime(since).timestamp() * 1000)
            else:
                since = int(since)
                # 确保时间戳是毫秒级别
                if since < 10000000000:
                    since *= 1000
        
        logger.info(f"处理后的时间范围: 从 {pd.to_datetime(since, unit='ms')} 到 {pd.to_datetime(until, unit='ms')}")
        
        # Binance API限制每次查询最多7天数据
        SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000  # 7天的毫秒数
        
        # 分批查询，每次查询7天数据
        all_trades = []
        current_since = since
        
        while current_since < until:
            # 计算当前批次的结束时间
            current_until = min(current_since + SEVEN_DAYS_MS - 1, until)
            
            logger.info(f"查询时间段: {pd.to_datetime(current_since, unit='ms')} 到 {pd.to_datetime(current_until, unit='ms')}")
            
            # 准备查询参数
            params = {
                'startTime': current_since,
                'endTime': current_until,
                'recvWindow': 60000
            }
            
            try:
                # 尝试获取交易记录
                logger.info(f"使用fetchMyTrades查询: symbol={symbol}, limit={limit}, 时间范围={current_since}-{current_until}")
                batch_trades = exchange.fetchMyTrades(symbol=symbol, limit=limit, params=params)
                
                if batch_trades:
                    logger.info(f"成功获取 {len(batch_trades)} 条交易记录")
                    all_trades.extend(batch_trades)
                    
                    # 如果返回的记录数等于限制数，可能还有更多记录
                    if len(batch_trades) == limit:
                        logger.info("达到查询限制，尝试使用fromId参数获取更多记录")
                        
                        # 获取最后一条记录的ID和时间
                        last_id = batch_trades[-1].get('id')
                        last_time = batch_trades[-1].get('timestamp')
                        
                        if last_id and last_time and last_time < current_until:
                            # 使用fromId参数继续查询
                            more_params = params.copy()
                            more_params['fromId'] = last_id
                            
                            try:
                                more_trades = exchange.fetchMyTrades(symbol=symbol, limit=limit, params=more_params)
                                if more_trades:
                                    logger.info(f"额外获取了 {len(more_trades)} 条交易记录")
                                    # 过滤掉重复的记录
                                    new_trades = [t for t in more_trades if t.get('id') != last_id]
                                    all_trades.extend(new_trades)
                            except Exception as e:
                                logger.error(f"获取额外交易记录失败: {str(e)}")
                else:
                    logger.info(f"该时间段内没有交易记录")
            except Exception as e:
                logger.error(f"查询时间段 {current_since}-{current_until} 失败: {str(e)}")
                
                # 如果是因为没有交易记录导致的错误，继续下一个时间段
                if "No records found" in str(e):
                    logger.info("该时间段内没有交易记录，继续查询下一个时间段")
                else:
                    # 尝试使用fetchOrders作为备选方法
                    try:
                        logger.info(f"尝试使用fetchOrders获取订单记录")
                        orders = exchange.fetchOrders(symbol=symbol, limit=limit, params=params)
                        
                        if orders:
                            logger.info(f"获取到 {len(orders)} 个订单")
                            # 提取已成交的订单
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
                                    all_trades.append(trade_info)
                            logger.info(f"从订单中提取了 {len(all_trades)} 条交易记录")
                    except Exception as e2:
                        logger.error(f"使用fetchOrders获取订单记录失败: {str(e2)}")
            
            # 移动到下一个时间段
            current_since = current_until + 1
        
        # 如果没有交易记录，返回空DataFrame
        if not all_trades:
            logger.info(f"在指定时间范围内没有找到{symbol}的交易记录")
            return pd.DataFrame()
        
        # 转换为DataFrame
        df_trades = pd.DataFrame(all_trades)
        
        # 转换时间戳为日期时间
        if 'timestamp' in df_trades.columns:
            df_trades['timestamp'] = pd.to_datetime(df_trades['timestamp'], unit='ms')
        
        # 按时间排序
        if 'timestamp' in df_trades.columns:
            df_trades = df_trades.sort_values('timestamp')
        
        logger.info(f"成功获取总计 {len(df_trades)} 条交易记录")
        return df_trades
    
    except Exception as e:
        logger.error(f"获取交易记录失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        # 返回空DataFrame
        return pd.DataFrame()

def merge_trades_to_positions(trades_df):
    """将交易记录合并为仓位信息
    
    一个仓位由开仓交易和平仓交易组成
    开仓交易可能是一笔或多笔
    平仓交易也可能是一笔或多笔
    """
    if trades_df.empty:
        return pd.DataFrame()
    
    logger.info(f"开始合并 {len(trades_df)} 条交易记录为仓位信息")
    
    # 确保交易记录按时间排序
    trades_df = trades_df.sort_values('timestamp')
    
    # 创建仓位列表
    positions = []
    
    # 分别记录多头和空头持仓
    long_position = {
        'total_amount': 0,      # 开仓总量
        'remaining_amount': 0,  # 剩余持仓
        'total_cost': 0,        # 开仓总成本
        'trades': [],
        'open_time': None
    }
    
    short_position = {
        'total_amount': 0,      # 开仓总量  
        'remaining_amount': 0,  # 剩余持仓
        'total_cost': 0,        # 开仓总成本
        'trades': [],
        'open_time': None
    }
    
    # 处理每一笔交易
    for _, trade in trades_df.iterrows():
        # 获取基本交易信息
        side = trade.get('side', '')
        amount = float(trade.get('amount', 0))
        price = float(trade.get('price', 0))
        cost = price * amount
        timestamp = trade.get('timestamp')
        
        # 转换为北京时区（UTC+8）
        if pd.notna(timestamp):
            beijing_timestamp = timestamp + pd.Timedelta(hours=8)
        else:
            beijing_timestamp = timestamp
        
        # 创建交易信息对象
        trade_info = {
            'timestamp': beijing_timestamp,
            'side': side,
            'amount': amount,
            'price': price,
            'cost': cost
        }
        
        # 根据交易方向和当前持仓情况更新仓位
        if side == 'buy':
            # 检查是否平空头仓位
            if short_position['remaining_amount'] > 0:
                # 计算此次平仓的数量
                close_amount = min(amount, short_position['remaining_amount'])
                
                # 记录平仓交易
                close_trade = trade_info.copy()
                close_trade['amount'] = close_amount
                close_trade['cost'] = close_amount * price
                short_position['trades'].append(close_trade)
                
                # 更新剩余持仓
                short_position['remaining_amount'] -= close_amount
                
                # 检查是否完全平仓
                if short_position['remaining_amount'] == 0:
                    # 计算平仓总收入（所有平仓交易的成本之和）
                    total_close_cost = sum(t['cost'] for t in short_position['trades'] if t['side'] == 'buy')
                    
                    # 空头仓位的利润 = 开仓收入 - 平仓成本
                    profit = short_position['total_cost'] - total_close_cost
                    
                    # 创建平仓的仓位记录
                    position = {
                        'open_time': short_position['open_time'],
                        'close_time': beijing_timestamp,
                        'side': 'short',
                        'open_price': short_position['total_cost'] / short_position['total_amount'] if short_position['total_amount'] > 0 else 0,
                        'close_price': total_close_cost / short_position['total_amount'] if short_position['total_amount'] > 0 else 0,
                        'amount': short_position['total_amount'],  # 记录开仓总量
                        'profit': profit,
                        'trades': short_position['trades']
                    }
                    positions.append(position)
                    
                    # 重置空头仓位
                    short_position = {
                        'total_amount': 0,
                        'remaining_amount': 0,
                        'total_cost': 0,
                        'trades': [],
                        'open_time': None
                    }
                    
                    # 如果买入数量大于平仓数量，剩余部分开多头
                    remaining_amount = amount - close_amount
                    if remaining_amount > 0:
                        if long_position['open_time'] is None:
                            long_position['open_time'] = beijing_timestamp
                        
                        long_position['total_amount'] += remaining_amount
                        long_position['remaining_amount'] += remaining_amount
                        long_position['total_cost'] += remaining_amount * price
                        
                        # 记录开仓交易
                        open_trade = trade_info.copy()
                        open_trade['amount'] = remaining_amount
                        open_trade['cost'] = remaining_amount * price
                        long_position['trades'].append(open_trade)
            else:
                # 没有空头仓位，直接开多头
                if long_position['open_time'] is None:
                    long_position['open_time'] = beijing_timestamp
                
                long_position['total_amount'] += amount
                long_position['remaining_amount'] += amount
                long_position['total_cost'] += cost
                long_position['trades'].append(trade_info)
        
        elif side == 'sell':
            # 检查是否平多头仓位
            if long_position['remaining_amount'] > 0:
                # 计算此次平仓的数量
                close_amount = min(amount, long_position['remaining_amount'])
                
                # 记录平仓交易
                close_trade = trade_info.copy()
                close_trade['amount'] = close_amount
                close_trade['cost'] = close_amount * price
                long_position['trades'].append(close_trade)
                
                # 更新剩余持仓
                long_position['remaining_amount'] -= close_amount
                
                # 检查是否完全平仓
                if long_position['remaining_amount'] == 0:
                    # 计算平仓总收入（所有平仓交易的成本之和）
                    total_close_revenue = sum(t['cost'] for t in long_position['trades'] if t['side'] == 'sell')
                    
                    # 多头仓位的利润 = 平仓收入 - 开仓成本
                    profit = total_close_revenue - long_position['total_cost']
                    
                    # 创建平仓的仓位记录
                    position = {
                        'open_time': long_position['open_time'],
                        'close_time': beijing_timestamp,
                        'side': 'long',
                        'open_price': long_position['total_cost'] / long_position['total_amount'] if long_position['total_amount'] > 0 else 0,
                        'close_price': total_close_revenue / long_position['total_amount'] if long_position['total_amount'] > 0 else 0,
                        'amount': long_position['total_amount'],  # 记录开仓总量
                        'profit': profit,
                        'trades': long_position['trades']
                    }
                    positions.append(position)
                    
                    # 重置多头仓位
                    long_position = {
                        'total_amount': 0,
                        'remaining_amount': 0,
                        'total_cost': 0,
                        'trades': [],
                        'open_time': None
                    }
                    
                    # 如果卖出数量大于平仓数量，剩余部分开空头
                    remaining_amount = amount - close_amount
                    if remaining_amount > 0:
                        if short_position['open_time'] is None:
                            short_position['open_time'] = beijing_timestamp
                        
                        short_position['total_amount'] += remaining_amount
                        short_position['remaining_amount'] += remaining_amount
                        short_position['total_cost'] += remaining_amount * price
                        
                        # 记录开仓交易
                        open_trade = trade_info.copy()
                        open_trade['amount'] = remaining_amount
                        open_trade['cost'] = remaining_amount * price
                        short_position['trades'].append(open_trade)
            else:
                # 没有多头仓位，直接开空头
                if short_position['open_time'] is None:
                    short_position['open_time'] = beijing_timestamp
                
                short_position['total_amount'] += amount
                short_position['remaining_amount'] += amount
                short_position['total_cost'] += cost
                short_position['trades'].append(trade_info)
    
    # 检查是否还有未平仓的仓位（当前持仓）
    if long_position['remaining_amount'] > 0:
        # 添加当前持有的多头仓位，使用最后一个价格作为"未平仓"价格
        last_price = trades_df['price'].iloc[-1] if 'price' in trades_df.columns else 0
        
        position = {
            'open_time': long_position['open_time'],
            'close_time': None,  # 未平仓
            'side': 'long',
            'open_price': long_position['total_cost'] / long_position['total_amount'] if long_position['total_amount'] > 0 else 0,
            'close_price': last_price,  # 当前价格
            'amount': long_position['total_amount'],  # 开仓总量
            'profit': (last_price * long_position['remaining_amount']) - long_position['total_cost'],
            'trades': long_position['trades'],
            'is_open': True  # 标记为未平仓
        }
        positions.append(position)
    
    if short_position['remaining_amount'] > 0:
        # 添加当前持有的空头仓位，使用最后一个价格作为"未平仓"价格
        last_price = trades_df['price'].iloc[-1] if 'price' in trades_df.columns else 0
        
        position = {
            'open_time': short_position['open_time'],
            'close_time': None,  # 未平仓
            'side': 'short',
            'open_price': short_position['total_cost'] / short_position['total_amount'] if short_position['total_amount'] > 0 else 0,
            'close_price': last_price,  # 当前价格
            'amount': short_position['total_amount'],  # 开仓总量
            'profit': short_position['total_cost'] - (last_price * short_position['remaining_amount']),
            'trades': short_position['trades'],
            'is_open': True  # 标记为未平仓
        }
        positions.append(position)
    
    # 转换为DataFrame
    if positions:
        positions_df = pd.DataFrame(positions)
        logger.info(f"成功合并为 {len(positions_df)} 个仓位")
        positions_df.to_excel("positions.xlsx", index=False)
        print("文件已保存为 positions.xlsx")
        return positions_df
    else:
        logger.info("没有找到有效的仓位")
        return pd.DataFrame()

def create_app():
    """创建Dash应用"""
    # 初始化交易所
    exchange = initialize_exchange()
    
    # 加载币种数据
    csv_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'positions_realtime_20240701_20250530.csv')
    symbols_data = load_symbols_from_csv(csv_file_path)
    
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
                
                // 添加拖动功能
                window.addEventListener('load', function() {
                    // 导航控制器拖动功能 - 优化版本
                    function makeElementDraggable(element) {
                        if (!element) return;
                        
                        let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
                        
                        const dragHeader = element.querySelector('.drag-header') || element;
                        
                        if (dragHeader) {
                            dragHeader.onmousedown = dragMouseDown;
                        }
                        
                        function dragMouseDown(e) {
                            e = e || window.event;
                            e.preventDefault();
                            // 获取鼠标位置
                            pos3 = e.clientX;
                            pos4 = e.clientY;
                            
                            // 直接添加事件监听器到document对象
                            document.addEventListener('mousemove', elementDrag);
                            document.addEventListener('mouseup', closeDragElement);
                            
                            // 添加拖动中的样式 - 禁用过渡效果以提高性能
                            element.classList.add('dragging');
                            
                            // 禁用可能影响性能的CSS属性
                            element.style.transition = 'none';
                            element.style.willChange = 'transform';
                        }
                        
                        function elementDrag(e) {
                            e = e || window.event;
                            e.preventDefault();
                            
                            // 计算新位置 - 直接使用当前鼠标位置与上一位置的差值
                            const dx = e.clientX - pos3;
                            const dy = e.clientY - pos4;
                            pos3 = e.clientX;
                            pos4 = e.clientY;
                            
                            // 设置元素的新位置 - 使用transform而不是top/left以提高性能
                            const currentTop = (element.offsetTop + dy);
                            const currentLeft = (element.offsetLeft + dx);
                            
                            // 应用新位置 - 使用translate3d触发GPU加速
                            element.style.top = currentTop + 'px';
                            element.style.left = currentLeft + 'px';
                        }
                        
                        function closeDragElement() {
                            // 移除事件监听器
                            document.removeEventListener('mousemove', elementDrag);
                            document.removeEventListener('mouseup', closeDragElement);
                            
                            // 移除拖动中的样式，恢复过渡效果
                            element.classList.remove('dragging');
                            element.style.transition = '';
                            element.style.willChange = 'auto';
                        }
                    }
                    
                    // 应用拖动功能到导航控制器 - 确保DOM完全加载
                    setTimeout(function() {
                        const navigationController = document.getElementById('navigation-controller');
                        if (navigationController) {
                            makeElementDraggable(navigationController);
                            console.log('已添加导航控制器拖动功能');
                        }
                        
                        // 为仓位编号输入框添加回车键监听
                        const positionInput = document.getElementById('position-number-input');
                        if (positionInput) {
                            positionInput.addEventListener('keydown', function(e) {
                                if (e.key === 'Enter') {
                                    e.preventDefault();
                                    // 触发跳转按钮点击
                                    const jumpButton = document.getElementById('jump-to-position-button');
                                    if (jumpButton) {
                                        jumpButton.click();
                                    }
                                }
                            });
                            console.log('已添加仓位编号输入框回车键监听');
                        }
                    }, 500);
                });
            </script>
            <style>
                /* 全局样式 */
                body {
                    background-color: #0a0e17;
                    color: #e0e3eb;
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                }
                
                /* 容器样式 */
                .container-fluid {
                    padding: 1rem;
                    width: 100%;        /* 宽度自适应 */
                    height: 100%;       /* 高度自适应父元素 */
                    box-sizing: border-box; /* 包含内边距和边框 */
                    margin: 0 auto;
                }
                
                /* 卡片样式 */
                .card {
                    background-color: #131722;
                    border-radius: 8px;
                    border: 1px solid #2B2B43;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    transition: all 0.3s ease;
                }
                
                .card:hover {
                    box-shadow: 0 6px 10px rgba(0, 0, 0, 0.15);
                }
                
                /* 按钮样式 */
                .btn {
                    border-radius: 6px;
                    font-weight: 500;
                    transition: all 0.2s ease;
                }
                
                .btn-primary {
                    background-color: #2962ff;
                    border-color: #2962ff;
                }
                
                .btn-primary:hover {
                    background-color: #1546e0;
                    border-color: #1546e0;
                }
                
                .btn-secondary {
                    background-color: #363a45;
                    border-color: #363a45;
                }
                
                .btn-secondary:hover {
                    background-color: #2a2e39;
                    border-color: #2a2e39;
                }
                
                /* 表单控件样式 */
                .form-control, .form-control-sm {
                    background-color: #1c2030;
                    border: 1px solid #2B2B43;
                    color: #e0e3eb;
                    border-radius: 6px;
                    transition: all 0.2s ease;
                }
                
                .form-control:focus, .form-control-sm:focus {
                    background-color: #232838;
                    border-color: #2962ff;
                    box-shadow: 0 0 0 0.2rem rgba(41, 98, 255, 0.25);
                    color: #ffffff;
                }
                
                /* 标签样式 */
                label {
                    font-weight: 500;
                    color: #9aa1b9;
                    font-size: 0.9rem;
                }
                
                /* 下拉框自定义样式 */
                .dash-dropdown .Select-control {
                    background-color: #1c2030 !important;
                    color: #e0e3eb !important;
                    border-color: #2B2B43 !important;
                    border-radius: 6px !important;
                    transition: all 0.2s ease !important;
                }
                
                .dash-dropdown .Select-control:hover {
                    border-color: #3a3f50 !important;
                }
                
                .dash-dropdown.is-focused .Select-control {
                    background-color: #232838 !important;
                    border-color: #2962ff !important;
                    box-shadow: 0 0 0 0.2rem rgba(41, 98, 255, 0.25) !important;
                }
                
                .dash-dropdown .Select-menu-outer {
                    background-color: #1c2030 !important;
                    color: #e0e3eb !important;
                    border-color: #2B2B43 !important;
                    border-radius: 0 0 6px 6px !important;
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2) !important;
                }
                
                .dash-dropdown .Select-value-label {
                    color: #e0e3eb !important;
                }
                
                .dash-dropdown .Select-menu-outer .VirtualizedSelectOption {
                    background-color: #1c2030 !important;
                    color: #e0e3eb !important;
                }
                
                .dash-dropdown .Select-menu-outer .VirtualizedSelectOption:hover,
                .dash-dropdown .Select-menu-outer .VirtualizedSelectFocusedOption {
                    background-color: #232838 !important;
                }
                
                .dash-dropdown .Select-value {
                    border-color: #2B2B43 !important;
                }
                
                .dash-dropdown .Select-arrow {
                    border-color: #9aa1b9 transparent transparent !important;
                }
                
                .dash-dropdown .is-open .Select-arrow {
                    border-color: transparent transparent #9aa1b9 !important;
                }
                
                /* 日期选择器样式 */
                .SingleDatePickerInput {
                    background-color: #1c2030 !important;
                    border: 1px solid #2B2B43 !important;
                    border-radius: 6px !important;
                    transition: all 0.2s ease !important;
                }
                
                .SingleDatePickerInput:hover {
                    border-color: #3a3f50 !important;
                }
                
                .SingleDatePickerInput .DateInput {
                    background: transparent !important;
                }
                
                .SingleDatePickerInput .DateInput_input {
                    background: transparent !important;
                    color: #e0e3eb !important;
                    font-size: 0.9rem !important;
                }
                
                .SingleDatePickerInput .DateInput_fang {
                    margin-top: -5px !important;
                }
                
                .DayPicker {
                    background-color: #1c2030 !important;
                    border-radius: 6px !important;
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2) !important;
                }
                
                .DayPicker_weekHeader {
                    color: #9aa1b9 !important;
                }
                
                .CalendarMonth_caption {
                    color: #e0e3eb !important;
                }
                
                .DayPicker_day {
                    color: #e0e3eb !important;
                    border-radius: 4px !important;
                }
                
                .DayPicker_day--selected, .DayPicker_day--selected:hover {
                    background-color: #2962ff !important;
                    color: white !important;
                }
                
                .DayPicker_day--outside {
                    color: #5d6484 !important;
                }
                
                .DayPicker_day:hover {
                    background-color: #232838 !important;
                }
                
                /* 复选框样式 */
                .form-check-input {
                    background-color: #1c2030;
                    border: 1px solid #2B2B43;
                }
                
                .form-check-input:checked {
                    background-color: #2962ff;
                    border-color: #2962ff;
                }
                
                .form-check-input:focus {
                    box-shadow: 0 0 0 0.2rem rgba(41, 98, 255, 0.25);
                }
                
                /* 图表容器样式 */
                #chart-container {
                    border-radius: 6px;
                    overflow: hidden;
                    background-color: #131722;
                    transition: all 0.3s ease;
                }
                
                /* 状态信息样式 */
                #status-info {
                    padding: 0.5rem;
                    border-radius: 6px;
                    background-color: rgba(28, 32, 48, 0.5);
                }
                
                /* 工具提示样式 */
                #trade-tooltip {
                    background-color: rgba(28, 32, 48, 0.9) !important;
                    border-radius: 6px !important;
                    border: 1px solid #2B2B43 !important;
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3) !important;
                }
                
                /* 进度条样式 */
                .progress {
                    background-color: #232838;
                    border-radius: 6px;
                }
                
                .progress-bar {
                    background-color: #2962ff;
                }
                
                /* 辅助类 */
                .text-success {
                    color: #26a69a !important;
                }
                
                .text-danger {
                    color: #ef5350 !important;
                }
                
                .text-warning {
                    color: #ffb74d !important;
                }
                
                .text-info {
                    color: #42a5f5 !important;
                }
                
                /* 币种选择框样式 */
                .symbol-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
                    gap: 8px;
                    max-height: 200px;
                    overflow-y: auto;
                    padding: 10px;
                    margin-bottom: 10px;
                }
                
                .symbol-item {
                    background-color: #1c2030;
                    border: 1px solid #2B2B43;
                    border-radius: 6px;
                    padding: 8px;
                    text-align: center;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    user-select: none;
                }
                
                .symbol-item:hover {
                    background-color: #232838;
                    border-color: #3a3f50;
                }
                
                .symbol-item.active {
                    background-color: #2962ff;
                    border-color: #2962ff;
                    color: white;
                }
                
                .symbol-name {
                    font-size: 12px;
                    font-weight: 500;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                
                .symbol-count {
                    font-size: 10px;
                    color: #9aa1b9;
                }
                
                .symbol-item.active .symbol-count {
                    color: rgba(255, 255, 255, 0.8);
                }
                
                /* 加载指示器样式 */
                .symbol-item.loading {
                    position: relative;
                }
                
                .loading-indicator {
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background-color: rgba(19, 23, 34, 0.9);
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    font-size: 10px;
                    color: #fff;
                    border-radius: 6px;
                    animation: pulse 1.5s infinite;
                }
                
                @keyframes pulse {
                    0% { opacity: 0.6; }
                    50% { opacity: 1; }
                    100% { opacity: 0.6; }
                }
                
                /* 导航控制器样式 */
                #navigation-controller {
                    position: fixed;
                    top: 80px;
                    right: 30px;
                    width: 180px;
                    background-color: rgba(19, 23, 34, 0.95);
                    border: 1px solid #2B2B43;
                    border-radius: 8px;
                    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4);
                    z-index: 1000;
                    backdrop-filter: blur(6px);
                    transition: all 0.3s ease;
                    cursor: move;
                    transform: translate3d(0, 0, 0);
                    will-change: transform;
                    touch-action: none;
                    user-select: none;
                }
                
                #navigation-controller.dragging {
                    opacity: 0.95;
                    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.4);
                    transition: none !important; /* 拖动时禁用过渡效果 */
                    pointer-events: none; /* 拖动时忽略指针事件 */
                }
                
                .drag-header {
                    padding: 8px 12px;
                    background-color: rgba(28, 32, 48, 0.8);
                    border-bottom: 1px solid #2B2B43;
                    border-radius: 8px 8px 0 0;
                    cursor: move;
                    user-select: none;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }
                
                .nav-controls {
                    padding: 12px;
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }
                
                /* 修改高亮标记样式 - 适用于TradingView Lightweight Charts 4.0.1版本 */
                .highlighted-marker {
                    filter: drop-shadow(0 0 6px rgba(255, 215, 0, 0.9)) !important;
                    transform: scale(1.3) !important;
                    transition: all 0.3s ease !important;
                    z-index: 1000 !important;
                }
                
                .highlighted-marker text {
                    fill: #FFEB3B !important; 
                    font-weight: bold !important;
                    text-shadow: 0px 0px 4px rgba(0, 0, 0, 0.7) !important;
                }
                
                .highlighted-marker path {
                    stroke: #FFD700 !important; 
                    stroke-width: 2px !important;
                }
                
                /* 添加一个动画效果 */
                @keyframes markerPulse {
                    0% { transform: scale(1.2); }
                    50% { transform: scale(1.4); }
                    100% { transform: scale(1.2); }
                }
                
                .highlighted-marker {
                    animation: markerPulse 1.5s infinite ease-in-out !important;
                }
                
                /* 左侧控制面板样式 */
                .control-panel {
                    height: 100%;
                    overflow-y: auto;
                }
                
                /* 调整币种网格在左侧面板中的显示 */
                .symbol-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(80px, 1fr));
                    gap: 6px;
                    max-height: 250px;
                    overflow-y: auto;
                    padding: 8px;
                    margin-bottom: 5px;
                }
                
                .symbol-item {
                    font-size: 11px;
                    padding: 6px 4px;
                }
                
                .symbol-count {
                    font-size: 9px;
                }
                
                /* 调整图表容器样式 */
                .chart-wrapper {
                    height: calc(100vh - 120px);
                    min-height: 600px;
                }
                
                #chart-container {
                    height: 100% !important;
                }
                
                /* 调整导航控制器位置 */
                #navigation-controller {
                    top: 80px;
                    right: 30px;
                }
                
                /* 让图表区域充满整个空间 */
                .chart-card {
                    height: 100%;
                }
                
                .chart-card .card-body {
                    height: 100%;
                    padding: 0;
                }
                
                /* 响应式调整 */
                @media (max-width: 1200px) {
                    .symbol-grid {
                        grid-template-columns: repeat(auto-fill, minmax(70px, 1fr));
                    }
                }
                
                @media (max-width: 992px) {
                    .form-label {
                        font-size: 0.8rem;
                    }
                    
                    .btn {
                        font-size: 0.8rem;
                    }
                    
                    .symbol-grid {
                        grid-template-columns: repeat(auto-fill, minmax(60px, 1fr));
                        max-height: 180px;
                    }
                    
                    #navigation-controller {
                        width: 150px;
                    }
                }
            </style>
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
    
    # 将币种数据转换为选项列表
    symbol_items = []
    for symbol, count in symbols_data.items():
        symbol_items.append(
            html.Div([
                html.Div(symbol, className="symbol-name"),
                html.Div(f"交易: {count}", className="symbol-count")
            ], id=f"symbol-{symbol.replace('/', '-').replace(':', '_')}",
                className="symbol-item",
                n_clicks=0,
                title=f"{symbol} - 交易次数: {count}")
        )
    
    # 添加客户端脚本，处理币种选择项的点击事件
    symbol_item_click_js = """
    function symbolItemClick() {
        // 获取所有币种选择项
        const symbolItems = document.querySelectorAll('.symbol-item');
        
        // 为每个币种选择项添加点击事件
        symbolItems.forEach(item => {
            item.addEventListener('click', function() {
                // 移除所有项的active类
                symbolItems.forEach(i => i.classList.remove('active'));
                
                // 为当前点击项添加active类
                this.classList.add('active');
                
                // 添加加载中样式
                this.classList.add('loading');
                this.innerHTML += '<div class="loading-indicator">加载中...</div>';
                
                // 点击事件由Dash回调处理
            });
        });
    }
    
    // 页面加载完成后执行
    document.addEventListener('DOMContentLoaded', symbolItemClick);
    """
    
    # 应用布局
    app.layout = dbc.Container([
        # 添加客户端脚本
        html.Script(symbol_item_click_js),
        
        # 使用行布局，分为左右两部分
        dbc.Row([
            # 左侧区域 - 控制面板（20%宽度）
            dbc.Col([
                html.Div([
                    # 币种选择卡片
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("交易币种 (交易次数 ≥ 5)", className="mb-3 text-center"),
                            html.Div(
                                symbol_items,
                                id="symbol-grid",
                                className="symbol-grid"
                            )
                        ], className="p-2")
                    ], className="mb-3 border-secondary"),
                    
                    # 控制面板卡片
                    dbc.Card([
                        dbc.CardBody([
                            # 交易对选择
                            dbc.Row([
                                dbc.Col([
                                    html.Label("交易对", className="form-label mb-1"),
                                    dcc.Input(
                                        id="symbol-input",
                                        type="text",
                                        value="NXPC/USDT:USDT",
                                        className="form-control form-control-sm w-100"
                                    )
                                ], width=12, className="mb-2"),
                                
                                # 时间周期选择
                                dbc.Col([
                                    html.Label("时间周期", className="form-label mb-1"),
                                    dcc.Dropdown(
                                        id="timeframe-dropdown",
                                        options=timeframe_options,
                                        value="1h",
                                        clearable=False,
                                        className="dash-dropdown-sm"
                                    )
                                ], width=12, className="mb-2"),
                                
                                # 开始日期选择
                                dbc.Col([
                                    html.Label("开始日期", className="form-label mb-1"),
                                    dcc.DatePickerSingle(
                                        id="start-date-picker",
                                        date=datetime(2025, 5, 15).date(),
                                        display_format="YYYY-MM-DD",
                                        className="w-100"
                                    )
                                ], width=12, className="mb-2"),
                                
                                # 结束日期选择
                                dbc.Col([
                                    html.Label("结束日期", className="form-label mb-1"),
                                    dcc.DatePickerSingle(
                                        id="end-date-picker",
                                        date=datetime(2025, 5, 16).date(),
                                        display_format="YYYY-MM-DD",
                                        className="w-100"
                                    )
                                ], width=12, className="mb-3"),
                                
                                # 按钮组
                                dbc.Col([
                                    dbc.ButtonGroup([
                                        dbc.Button(
                                            "加载数据", 
                                            id="load-data-button", 
                                            color="primary", 
                                            size="sm",
                                            className="me-1"
                                        ),
                                        dbc.Button(
                                            "重置图表", 
                                            id="reset-chart-button", 
                                            color="secondary", 
                                            size="sm"
                                        )
                                    ], className="w-100")
                                ], width=12, className="mb-3"),
                                
                                # 指标选项区域
                                dbc.Col([
                                    html.Label("指标选项", className="form-label mb-1"),
                                    dbc.Card([
                                        dbc.CardBody([
                                            # 显示交易记录选项
                                            dbc.Row([
                                                dbc.Col([
                                                    dbc.Checkbox(
                                                        id="show-trades-checkbox",
                                                        className="form-check-input",
                                                        value=True,
                                                    ),
                                                    html.Label(
                                                        "交易记录",
                                                        className="form-check-label ms-2 small"
                                                    ),
                                                ], width=12, className="d-flex align-items-center mb-1"),
                                                
                                                # 显示EMA20选项
                                                dbc.Col([
                                                    dbc.Checkbox(
                                                        id="show-ema-checkbox",
                                                        className="form-check-input",
                                                        value=True,
                                                    ),
                                                    html.Label(
                                                        "EMA20",
                                                        className="form-check-label ms-2 small"
                                                    ),
                                                ], width=12, className="d-flex align-items-center mb-1"),
                                                
                                                # 显示布林带选项
                                                dbc.Col([
                                                    dbc.Checkbox(
                                                        id="show-bollinger-checkbox",
                                                        className="form-check-input",
                                                        value=False,
                                                    ),
                                                    html.Label(
                                                        "布林带",
                                                        className="form-check-label ms-2 small"
                                                    ),
                                                ], width=12, className="d-flex align-items-center mb-1"),
                                                
                                                # 显示RSI指标选项
                                                dbc.Col([
                                                    dbc.Checkbox(
                                                        id="show-rsi-checkbox",
                                                        className="form-check-input",
                                                        value=True,
                                                    ),
                                                    html.Label(
                                                        "RSI",
                                                        className="form-check-label ms-2 small"
                                                    ),
                                                ], width=12, className="d-flex align-items-center mb-1"),
                                                
                                                # 显示MACD指标选项
                                                dbc.Col([
                                                    dbc.Checkbox(
                                                        id="show-macd-checkbox",
                                                        className="form-check-input",
                                                        value=False,
                                                    ),
                                                    html.Label(
                                                        "MACD",
                                                        className="form-check-label ms-2 small"
                                                    ),
                                                ], width=12, className="d-flex align-items-center"),
                                            ])
                                        ], className="py-2 px-3")
                                    ], className="border-light bg-dark")
                                ], width=12, className="mb-3"),
                                
                                # 状态信息区域
                                dbc.Col([
                                    html.Label("状态信息", className="form-label mb-1"),
                                    html.Div(id="status-info", className="small p-2 border border-secondary rounded bg-dark")
                                ], width=12),
                            ]),
                        ], className="p-3")
                    ], className="border-secondary"),
                ], className="control-panel"),
            ], width=3, className="pe-2"),
            
            # 右侧区域 - 图表（80%宽度）
            dbc.Col([
                # 图表卡片
                dbc.Card([
                    dbc.CardBody([
                        # 图表容器
                        html.Div(
                            id="chart-container",
                            className="chart-wrapper",
                            style={
                                "width": "100%",
                                "position": "relative"
                            }
                        ),
                        
                        # 交互信息显示区
                        html.Div(
                            id="chart-info",
                            className="mt-2"
                        )
                    ], className="p-0")
                ], className="border-secondary chart-card"),
            ], width=9, className="ps-2"),
        ], className="g-0"),  # 去除行间距
        
        # 数据存储
        dcc.Store(id="chart-data-store"),
        dcc.Store(id="trades-data-store"),
        dcc.Store(id="positions-data-store"),
        
        # 添加chart-interaction元素到初始布局
        html.Div(id="chart-interaction", style={"display": "none"}),
        
        # 导航控制器（可拖动）
        html.Div([
            html.Div([
                html.Span("仓位导航", className="fw-bold text-light small"),
                html.Span("✥", className="text-muted small", title="拖动")
            ], className="drag-header"),
            
            html.Div([
                dbc.Row([
                    dbc.Col([
                        html.Div(id="position-info", className="mb-2 text-center small")
                    ], width=12),
                    
                    # 添加编号输入框和跳转按钮
                    dbc.Col([
                        dbc.InputGroup(
                            [
                                dbc.Input(
                                    id="position-number-input",
                                    type="number",
                                    placeholder="编号",
                                    min=1,
                                    step=1,
                                    size="sm"
                                ),
                                dbc.Button(
                                    "跳转",
                                    id="jump-to-position-button",
                                    color="info",
                                    size="sm",
                                    className="px-2"
                                ),
                            ],
                            size="sm",
                            className="mb-2"
                        ),
                    ], width=12),
                    
                    dbc.Col([
                        dbc.Button("上一个", id="prev-position-button", color="secondary", size="sm", className="w-100 mb-2")
                    ], width=12),
                    
                    dbc.Col([
                        dbc.Button("下一个", id="next-position-button", color="primary", size="sm", className="w-100")
                    ], width=12)
                ])
            ], className="nav-controls")
        ], id="navigation-controller"),
        
        # 加载动画
        dbc.Spinner(html.Div(id="loading-spinner"), color="primary"),
        
    ], fluid=True, className="bg-dark text-light p-3")
    
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
    
    # 简化后的时间范围计算函数
    def calculate_time_range(start_date, end_date):
        """计算开始和结束时间的时间戳
        
        使用用户提供的日期，设置开始日期为0点，结束日期为23:59:59
        """
        try:
            # 创建带精确时间的datetime对象
            start = datetime.combine(
                datetime.strptime(start_date, '%Y-%m-%d').date(), 
                datetime.min.time()  # 00:00:00
            )
            
            end = datetime.combine(
                datetime.strptime(end_date, '%Y-%m-%d').date(), 
                datetime.min.time().replace(hour=23, minute=59, second=59)  # 23:59:59
            )
            
            logger.info(f"计算的时间范围: 从 {start} 到 {end}")
        except Exception as e:
            logger.error(f"处理时间范围时出错: {e}")
            # 使用默认值 - 2024年7月1日到2025年5月1日
            start = datetime(2024, 7, 1)
            end = datetime(2025, 5, 1, 23, 59, 59)
            logger.info(f"使用默认时间范围: 从 {start} 到 {end}")
        
        # 转换为时间戳（毫秒）
        start_ts = int(start.timestamp() * 1000)
        end_ts = int(end.timestamp() * 1000)
        
        return start_ts, end_ts

    # 加载数据回调
    @app.callback(
        [Output("chart-data-store", "data", allow_duplicate=True), 
         Output("trades-data-store", "data", allow_duplicate=True),
         Output("loading-spinner", "children", allow_duplicate=True),
         Output("status-info", "children", allow_duplicate=True)],
        [Input("load-data-button", "n_clicks"), Input("reset-chart-button", "n_clicks")],
        [State("symbol-input", "value"), 
         State("timeframe-dropdown", "value"),
         State("start-date-picker", "date"),
         State("end-date-picker", "date")],
        prevent_initial_call=True
    )
    def load_chart_data(load_clicks, reset_clicks, symbol, timeframe, start_date, end_date):
        triggered_id = dash.callback_context.triggered[0]["prop_id"].split(".")[0]
        
        if triggered_id == "load-data-button" and load_clicks:
            try:
                # 计算时间范围
                since, until = calculate_time_range(
                    start_date, end_date
                )
                
                # 创建人类可读的时间范围字符串
                since_str = pd.to_datetime(since, unit='ms').strftime('%Y-%m-%d %H:%M:%S')
                until_str = pd.to_datetime(until, unit='ms').strftime('%Y-%m-%d %H:%M:%S')
                time_range_str = f"{since_str} 至 {until_str}"
                
                # 获取K线数据
                df = fetch_ohlcv_data(exchange, symbol, timeframe, since, until)
                
                if df.empty:
                    return dash.no_update, dash.no_update, "", html.Div("无法加载K线数据", className="text-danger")
                
                # 准备图表数据
                chart_data = prepare_data_for_chart(df)
                
                # 获取交易记录
                df_trades = fetch_trades(exchange, symbol, since, until)
                df_trades.to_excel("trades.xlsx", index=False)
                print("原始交易文件已保存为 df_trades.xlsx")
                # 合并交易记录为仓位信息
                if not df_trades.empty:
                    positions_df = merge_trades_to_positions(df_trades)
                    
                    # 准备仓位数据用于图表展示 - 新的格式
                    positions_data = []
                    
                    if not positions_df.empty:
                        logger.info(f"处理 {len(positions_df)} 个仓位用于图表展示")
                        
                        for _, pos in positions_df.iterrows():
                            # 检查仓位是否有有效的开仓和平仓时间
                            if pd.notna(pos['open_time']) and pd.notna(pos['close_time']):
                                # 将时间转换为Unix时间戳（秒）以匹配K线数据的 time 格式
                                # 明确指定时区为UTC+8（北京时间），然后转换为Unix时间戳
                                open_timestamp = int(pd.to_datetime(pos['open_time']).tz_localize('Asia/Shanghai').timestamp())
                                close_timestamp = int(pd.to_datetime(pos['close_time']).tz_localize('Asia/Shanghai').timestamp())
                                
                                # 创建仓位数据对象，包含开仓和平仓的完整信息
                                position_data = {
                                    'position_id': str(pos.name),  # 使用DataFrame索引作为唯一标识
                                    'side': pos['side'],  # 'long' 或 'short'
                                    'open_time': open_timestamp,
                                    'close_time': close_timestamp,
                                    'open_price': float(pos['open_price']),
                                    'close_price': float(pos['close_price']),
                                    'amount': float(pos['amount']),
                                    'profit': float(pos['profit']),
                                    # 格式化的时间字符串（北京时间）
                                    'open_time_formatted': pos['open_time'].strftime('%Y-%m-%d %H:%M:%S'),
                                    'close_time_formatted': pos['close_time'].strftime('%Y-%m-%d %H:%M:%S'),
                                    'is_profit': pos['profit'] >= 0
                                }
                                
                                positions_data.append(position_data)
                            elif pd.notna(pos['open_time']) and pos.get('is_open', False):
                                # 仅有开仓信息的持仓，时间同样使用秒级并指定时区
                                open_timestamp = int(pd.to_datetime(pos['open_time']).tz_localize('Asia/Shanghai').timestamp())
                                
                                position_data = {
                                    'position_id': str(pos.name),
                                    'side': pos['side'],
                                    'open_time': open_timestamp,
                                    'close_time': None,  # 未平仓
                                    'open_price': float(pos['open_price']),
                                    'close_price': None,
                                    'amount': float(pos['amount']),
                                    'profit': float(pos['profit']),
                                    'open_time_formatted': pos['open_time'].strftime('%Y-%m-%d %H:%M:%S'),
                                    'close_time_formatted': '持仓中',
                                    'is_open': True,
                                    'is_profit': pos['profit'] >= 0
                                }
                                
                                positions_data.append(position_data)
                else:
                    positions_df = pd.DataFrame()
                    positions_data = []
                
                # 返回更美观的状态信息
                status_info = html.Div([
                    dbc.Row([
                        dbc.Col([
                            html.Div([
                                html.Span("时间范围: ", className="fw-bold small"),
                                html.Span(f"{time_range_str}", className="text-warning small")
                            ], className="d-flex align-items-center mb-1")
                        ], width=12),
                        dbc.Col([
                            html.Div([
                                html.Span("K线数据: ", className="fw-bold small me-1"),
                                html.Span(f"{len(df)} 条", className="text-success small"),
                                html.Span(" | 交易标记: ", className="fw-bold small mx-1"),
                                html.Span(f"{len(positions_data)} 个", className="text-info small"),
                                html.Span(" | 合并仓位: ", className="fw-bold small mx-1"),
                                html.Span(f"{len(positions_df)} 个", className="text-primary small")
                            ], className="d-flex align-items-center")
                        ], width=12)
                    ])
                ], className="p-2 border border-secondary rounded bg-dark")
                
                return json.dumps(chart_data), json.dumps(positions_data), "", status_info
                
            except Exception as e:
                logger.error(f"加载数据出错: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                return dash.no_update, dash.no_update, "", html.Div(f"加载数据出错: {str(e)}", className="text-danger p-2 border border-danger rounded")
        
        elif triggered_id == "reset-chart-button" and reset_clicks:
            # 发送一个空的数据集以重置图表
            return "{}", "[]", "", html.Div("图表已重置", className="text-warning p-2 border border-warning rounded")
        
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
    
    # 仓位导航回调
    @app.callback(
        [Output("position-info", "children")],
        [Input("prev-position-button", "n_clicks"),
         Input("next-position-button", "n_clicks"),
         Input("jump-to-position-button", "n_clicks")],
        [State("position-number-input", "value"),
         State("trades-data-store", "data")]
    )
    def navigate_positions(prev_clicks, next_clicks, jump_clicks, position_number, positions_json):
        ctx = dash.callback_context
        if not ctx.triggered:
            return [html.Div("请先加载数据", className="text-muted small")]
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # 全局变量用于跟踪当前位置
        if not hasattr(navigate_positions, 'current_index'):
            navigate_positions.current_index = 0
        
        try:
            # 解析仓位数据
            if not positions_json:
                return [html.Div("暂无仓位数据", className="text-muted small")]
            
            positions = json.loads(positions_json)
            if not positions or len(positions) == 0:
                return [html.Div("暂无仓位数据", className="text-muted small")]
            
            # 确定导航方向
            if trigger_id == "prev-position-button" and prev_clicks:
                navigate_positions.current_index = (navigate_positions.current_index - 1) % len(positions)
            elif trigger_id == "next-position-button" and next_clicks:
                navigate_positions.current_index = (navigate_positions.current_index + 1) % len(positions)
            elif trigger_id == "jump-to-position-button" and jump_clicks and position_number:
                # 确保编号在有效范围内（1到positions.length）
                target_index = max(1, min(int(position_number), len(positions))) - 1
                navigate_positions.current_index = target_index
            
            # 获取当前仓位
            current_position = positions[navigate_positions.current_index]
            
            # 创建仓位信息显示
            position_side = "多头" if current_position.get('side') == 'long' else "空头"
            profit = current_position.get('profit', 0)
            profit_class = "text-success" if profit >= 0 else "text-danger"
            
            return [html.Div([
                html.Div([
                    html.Span(f"仓位 ", className="small text-muted"),
                    html.Span(f"{navigate_positions.current_index + 1}/{len(positions)}", className="fw-bold")
                ]),
                html.Div([
                    html.Span(f"{position_side} ", className="fw-bold"),
                    html.Span(f"{current_position.get('open_time_formatted', '')}", className="small text-info d-block")
                ]),
                html.Div([
                    html.Span(f"{current_position.get('close_time_formatted', '持仓中')}", className="small text-warning d-block")
                ]) if current_position.get('close_time_formatted') else None,
                html.Div([
                    html.Span(f"盈亏: ", className="small text-muted"),
                    html.Span(f"{profit:.2f}", className=f"{profit_class} fw-bold")
                ], className="mt-1")
            ])]
        
        except Exception as e:
            logger.error(f"导航仓位时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return [html.Div(f"导航出错: {str(e)}", className="text-danger small")]
    
    # 修改客户端回调，使用正确的命名空间和添加新函数到clientside命名空间
    app.clientside_callback(
        ClientsideFunction(namespace="clientside", function_name="navigateToPosition"),
        Output("chart-container", "n_clicks", allow_duplicate=True),  # 使用一个不重要的属性
        [Input("prev-position-button", "n_clicks"),
         Input("next-position-button", "n_clicks")],
        [State("trades-data-store", "data")],
        prevent_initial_call=True
    )
    
    # 添加编号输入跳转功能
    app.clientside_callback(
        ClientsideFunction(namespace="clientside", function_name="jumpToPositionByNumber"),
        Output("chart-container", "n_clicks", allow_duplicate=True),  # 使用一个不重要的属性
        [Input("jump-to-position-button", "n_clicks")],
        [State("position-number-input", "value"),
         State("trades-data-store", "data")],
        prevent_initial_call=True
    )
    
    # 币种点击加载数据回调
    @app.callback(
        [Output("chart-data-store", "data", allow_duplicate=True), 
         Output("trades-data-store", "data", allow_duplicate=True),
         Output("loading-spinner", "children", allow_duplicate=True),
         Output("status-info", "children", allow_duplicate=True),
         Output("symbol-input", "value"),  # 更新交易对输入框
         Output("start-date-picker", "date"),  # 更新开始日期
         Output("end-date-picker", "date"),  # 更新结束日期
         Output("timeframe-dropdown", "value")],  # 更新周期选择器
        [Input(f"symbol-{symbol.replace('/', '-').replace(':', '_')}", "n_clicks") for symbol in symbols_data.keys()],
        prevent_initial_call=True
    )
    def load_data_from_symbol_click(*args):
        """处理币种点击事件，加载数据"""
        ctx = dash.callback_context
        if not ctx.triggered:
            return [dash.no_update] * 8
        
        # 获取被点击的组件ID
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # 从组件ID中提取币种
        if triggered_id.startswith('symbol-'):
            symbol_str = triggered_id.replace('symbol-', '').replace('-', '/').replace('_', ':')
            clicked_symbol = symbol_str
        else:
            return [dash.no_update] * 8
        
        logger.info(f"币种 {clicked_symbol} 被点击，开始加载数据...")
        
        try:
            # 设置默认的日期范围（2024.7-2025.5）
            default_start_date = datetime(2024, 11, 20)
            default_end_date = datetime(2025, 5, 30)
            
            # 设置默认的K线周期
            default_timeframe = '15m'
            
            # 转换为时间戳（毫秒）
            since = int(default_start_date.timestamp() * 1000)
            until = int(default_end_date.timestamp() * 1000)
            
            # 创建人类可读的时间范围字符串
            since_str = default_start_date.strftime('%Y-%m-%d %H:%M:%S')
            until_str = default_end_date.strftime('%Y-%m-%d %H:%M:%S')
            time_range_str = f"{since_str} 至 {until_str}"
            
            # 显示加载中状态
            loading_status = html.Div("正在加载数据，请稍候...", className="text-warning p-2 border border-warning rounded")
            
            # 获取K线数据 - 使用5分钟周期
            df = fetch_ohlcv_data(exchange, clicked_symbol, default_timeframe, since, until)
            
            if df.empty:
                return (
                    dash.no_update, 
                    dash.no_update, 
                    "", 
                    html.Div(f"无法加载 {clicked_symbol} 的K线数据", className="text-danger p-2 border border-danger rounded"),
                    clicked_symbol,
                    default_start_date.date(),
                    default_end_date.date(),
                    default_timeframe
                )
            
            # 准备图表数据
            chart_data = prepare_data_for_chart(df)
            
            # 从CSV直接加载仓位数据
            csv_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'positions_realtime_20240701_20250530.csv')
            positions_data = load_positions_from_csv(csv_file_path, symbol=clicked_symbol)
            
            # 返回更美观的状态信息
            status_info = html.Div([
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.Span("币种: ", className="fw-bold small"),
                            html.Span(f"{clicked_symbol}", className="text-success small"),
                            html.Span(" | 时间范围: ", className="fw-bold small mx-1"),
                            html.Span(f"{time_range_str}", className="text-warning small")
                        ], className="d-flex align-items-center mb-1")
                    ], width=12),
                    dbc.Col([
                        html.Div([
                            html.Span("K线数据: ", className="fw-bold small me-1"),
                            html.Span(f"{len(df)} 条", className="text-success small"),
                            html.Span(" | 仓位标记: ", className="fw-bold small mx-1"),
                            html.Span(f"{len(positions_data)} 个", className="text-info small")
                        ], className="d-flex align-items-center")
                    ], width=12)
                ])
            ], className="p-2 border border-secondary rounded bg-dark")
            
            return (
                json.dumps(chart_data), 
                json.dumps(positions_data), 
                "", 
                status_info, 
                clicked_symbol,
                default_start_date.date(),
                default_end_date.date(),
                default_timeframe
            )
            
        except Exception as e:
            logger.error(f"币种点击加载数据出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return (
                dash.no_update, 
                dash.no_update, 
                "", 
                html.Div(f"加载数据出错: {str(e)}", className="text-danger p-2 border border-danger rounded"),
                clicked_symbol if clicked_symbol else dash.no_update,
                dash.no_update,
                dash.no_update,
                dash.no_update
            )
    
    # 清除币种加载状态的客户端回调
    app.clientside_callback(
        """
        function(chartData, tradesData) {
            // 在数据加载完成后，清除所有加载指示器
            if (chartData || tradesData) {
                setTimeout(() => {
                    const loadingItems = document.querySelectorAll('.symbol-item.loading');
                    loadingItems.forEach(item => {
                        item.classList.remove('loading');
                        // 移除加载中文字
                        const indicator = item.querySelector('.loading-indicator');
                        if (indicator) {
                            indicator.remove();
                        }
                    });
                }, 500);
            }
            return null;
        }
        """,
        Output("symbol-grid", "title"),  # 使用一个不影响UI的属性
        [Input("chart-data-store", "data"),
         Input("trades-data-store", "data")],
        prevent_initial_call=True
    )
    
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=8051) 