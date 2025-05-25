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

# 加载.env文件中的环境变量
dotenv.load_dotenv()

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
        
        # 增大批处理参数以提高性能
        batch_limit = 1500  # 增加每批获取的数据量，减少API调用次数
        
        # 一些交易所可能有数据量限制，分批获取以克服限制
        all_ohlcv = []
        
        # 保存并行任务
        threads = []
        results = {}
        
        # 如果指定了时间范围，计算合适的分段
        if formatted_since and formatted_until:
            # 计算时间范围的毫秒数
            time_range_ms = formatted_until - formatted_since
            
            # 根据K线周期估算需要获取的K线数量
            timeframe_ms = {
                '1m': 60 * 1000,
                '3m': 3 * 60 * 1000,
                '5m': 5 * 60 * 1000,
                '15m': 15 * 60 * 1000,
                '30m': 30 * 60 * 1000,
                '1h': 60 * 60 * 1000,
                '2h': 2 * 60 * 60 * 1000,
                '4h': 4 * 60 * 60 * 1000,
                '6h': 6 * 60 * 60 * 1000,
                '8h': 8 * 60 * 60 * 1000,
                '12h': 12 * 60 * 60 * 1000,
                '1d': 24 * 60 * 60 * 1000,
                '3d': 3 * 24 * 60 * 60 * 1000,
                '1w': 7 * 24 * 60 * 60 * 1000,
                '1M': 30 * 24 * 60 * 60 * 1000,
            }
            
            timeframe_duration = timeframe_ms.get(timeframe, 60 * 60 * 1000)  # 默认1小时
            estimated_candles = time_range_ms / timeframe_duration
            
            logger.info(f"估计需要获取 {estimated_candles:.0f} 条K线")
            
            # 如果预计数量超过阈值，使用并行获取
            if estimated_candles > 5000:
                # 将时间范围分为多个段
                segments = []
                segment_size_ms = batch_limit * timeframe_duration  # 每个段的时间跨度
                
                # 根据时间范围划分段
                current_start = formatted_since
                while current_start < formatted_until:
                    current_end = min(current_start + segment_size_ms, formatted_until)
                    segments.append((current_start, current_end))
                    current_start = current_end + 1
                
                logger.info(f"将时间范围分为 {len(segments)} 个段并行获取")
                
                # 定义获取单个段的函数
                def fetch_segment(segment_index, start_time, end_time):
                    segment_params = {'since': start_time}
                    segment_data = []
                    
                    try:
                        logger.info(f"获取段 {segment_index+1}/{len(segments)}: {pd.to_datetime(start_time, unit='ms')} - {pd.to_datetime(end_time, unit='ms')}")
                        segment_batch = exchange.fetch_ohlcv(
                            symbol=symbol,
                            timeframe=timeframe,
                            limit=batch_limit,
                            params=segment_params
                        )
                        
                        if segment_batch:
                            # 过滤结束时间之后的数据
                            segment_data = [candle for candle in segment_batch if candle[0] <= end_time]
                            logger.info(f"段 {segment_index+1} 获取了 {len(segment_data)} 条K线")
                    except Exception as e:
                        logger.error(f"获取段 {segment_index+1} 失败: {str(e)}")
                    
                    # 存储结果
                    results[segment_index] = segment_data
                
                # 创建并启动线程
                for i, (start, end) in enumerate(segments):
                    thread = threading.Thread(target=fetch_segment, args=(i, start, end))
                    threads.append(thread)
                    thread.start()
                    # 不要启动太多线程，避免API限制
                    if len(threads) >= 5:
                        for t in threads:
                            t.join()
                        threads = []
                
                # 等待所有线程完成
                for thread in threads:
                    thread.join()
                
                # 按顺序合并结果
                for i in range(len(segments)):
                    segment_data = results.get(i, [])
                    all_ohlcv.extend(segment_data)
                
                logger.info(f"并行获取完成，总共获取 {len(all_ohlcv)} 条K线")
                
            else:
                # 数据量较小，使用标准方式获取
                logger.info(f"使用标准方式获取数据")
                
                # 根据时间范围分批获取数据
                current_since = formatted_since
                
                while True:
                    # 更新参数中的since
                    params = {}
                    if current_since:
                        params = {'since': current_since}
                        
                    # 获取一批数据
                    try:
                        batch = exchange.fetch_ohlcv(
                            symbol=symbol,
                            timeframe=timeframe,
                            limit=batch_limit,
                            params=params
                        )
                        
                        # 如果没有返回数据，则退出循环
                        if not batch or len(batch) == 0:
                            break
                            
                        # 将此批次数据添加到结果中
                        all_ohlcv.extend(batch)
                        
                        # 记录进度
                        logger.info(f"已获取 {len(all_ohlcv)} 条K线数据")
                        
                        # 检查是否达到结束时间
                        if formatted_until and batch[-1][0] >= formatted_until:
                            break
                            
                        # 如果返回的数据量小于请求的限制，说明已经获取了所有数据
                        if len(batch) < batch_limit:
                            break
                            
                        # 更新since为最后一条数据的时间加1毫秒，继续获取下一批
                        current_since = batch[-1][0] + 1
                        
                        # 短暂等待避免超过API速率限制
                        time.sleep(0.5)
                        
                    except Exception as e:
                        logger.error(f"获取K线批次失败: {str(e)}")
                        # 短暂等待后重试
                        time.sleep(2)
                        continue
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
        
        # 如果有until参数，过滤结束时间之后的数据
        if formatted_until and all_ohlcv:
            all_ohlcv = [candle for candle in all_ohlcv if candle[0] <= formatted_until]
        
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
        'amount': 0,
        'cost': 0,
        'trades': [],
        'open_time': None
    }
    
    short_position = {
        'amount': 0,
        'cost': 0,
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
        
        # 创建交易信息对象
        trade_info = {
            'timestamp': timestamp,
            'side': side,
            'amount': amount,
            'price': price,
            'cost': cost
        }
        
        # 根据交易方向和当前持仓情况更新仓位
        if side == 'buy':
            # 检查是否平空头仓位
            if short_position['amount'] > 0:
                # 计算此次平仓的数量和成本
                close_amount = min(amount, short_position['amount'])
                close_cost = close_amount * price
                
                if close_amount == short_position['amount']:
                    # 完全平仓
                    open_cost = short_position['cost']
                    open_price = open_cost / short_position['amount']
                    profit = open_cost - close_cost
                    
                    # 创建平仓的仓位记录
                    position = {
                        'open_time': short_position['open_time'],
                        'close_time': timestamp,
                        'side': 'short',
                        'open_price': open_price,
                        'close_price': price,
                        'amount': short_position['amount'],
                        'profit': profit,
                        'profit_percent': (profit / open_cost) * 100 if open_cost else 0,
                        'trades': short_position['trades'] + [trade_info]
                    }
                    positions.append(position)
                    
                    # 重置空头仓位
                    short_position = {
                        'amount': 0,
                        'cost': 0,
                        'trades': [],
                        'open_time': None
                    }
                    
                    # 如果买入数量大于平仓数量，剩余部分开多头
                    remaining_amount = amount - close_amount
                    if remaining_amount > 0:
                        long_position['amount'] += remaining_amount
                        long_position['cost'] += remaining_amount * price
                        
                        # 记录开仓时间
                        if long_position['open_time'] is None:
                            long_position['open_time'] = timestamp
                        
                        # 记录交易
                        remaining_trade = trade_info.copy()
                        remaining_trade['amount'] = remaining_amount
                        remaining_trade['cost'] = remaining_amount * price
                        long_position['trades'].append(remaining_trade)
                else:
                    # 部分平仓，更新空头仓位
                    short_position['amount'] -= close_amount
                    short_position['cost'] -= (short_position['cost'] / (short_position['amount'] + close_amount)) * close_amount
                    
                    # 记录此次平仓交易
                    trade_info['amount'] = close_amount
                    trade_info['cost'] = close_amount * price
                    short_position['trades'].append(trade_info)
            else:
                # 没有空头仓位，直接开多头
                if long_position['open_time'] is None:
                    long_position['open_time'] = timestamp
                
                long_position['amount'] += amount
                long_position['cost'] += cost
                long_position['trades'].append(trade_info)
        
        elif side == 'sell':
            # 检查是否平多头仓位
            if long_position['amount'] > 0:
                # 计算此次平仓的数量和成本
                close_amount = min(amount, long_position['amount'])
                close_cost = close_amount * price
                
                if close_amount == long_position['amount']:
                    # 完全平仓
                    open_cost = long_position['cost']
                    open_price = open_cost / long_position['amount'] if long_position['amount'] > 0 else 0
                    profit = close_cost - open_cost
                    
                    # 创建平仓的仓位记录
                    position = {
                        'open_time': long_position['open_time'],
                        'close_time': timestamp,
                        'side': 'long',
                        'open_price': open_price,
                        'close_price': price,
                        'amount': long_position['amount'],
                        'profit': profit,
                        'profit_percent': (profit / open_cost) * 100 if open_cost else 0,
                        'trades': long_position['trades'] + [trade_info]
                    }
                    positions.append(position)
                    
                    # 重置多头仓位
                    long_position = {
                        'amount': 0,
                        'cost': 0,
                        'trades': [],
                        'open_time': None
                    }
                    
                    # 如果卖出数量大于平仓数量，剩余部分开空头
                    remaining_amount = amount - close_amount
                    if remaining_amount > 0:
                        short_position['amount'] += remaining_amount
                        short_position['cost'] += remaining_amount * price
                        
                        # 记录开仓时间
                        if short_position['open_time'] is None:
                            short_position['open_time'] = timestamp
                        
                        # 记录交易
                        remaining_trade = trade_info.copy()
                        remaining_trade['amount'] = remaining_amount
                        remaining_trade['cost'] = remaining_amount * price
                        short_position['trades'].append(remaining_trade)
                else:
                    # 部分平仓，更新多头仓位
                    long_position['amount'] -= close_amount
                    long_position['cost'] -= (long_position['cost'] / (long_position['amount'] + close_amount)) * close_amount
                    
                    # 记录此次平仓交易
                    trade_info['amount'] = close_amount
                    trade_info['cost'] = close_amount * price
                    long_position['trades'].append(trade_info)
            else:
                # 没有多头仓位，直接开空头
                if short_position['open_time'] is None:
                    short_position['open_time'] = timestamp
                
                short_position['amount'] += amount
                short_position['cost'] += cost
                short_position['trades'].append(trade_info)
    
    # 检查是否还有未平仓的仓位（当前持仓）
    if long_position['amount'] > 0:
        # 添加当前持有的多头仓位，使用最后一个价格作为"未平仓"价格
        last_price = trades_df['price'].iloc[-1] if 'price' in trades_df.columns else 0
        
        position = {
            'open_time': long_position['open_time'],
            'close_time': None,  # 未平仓
            'side': 'long',
            'open_price': long_position['cost'] / long_position['amount'] if long_position['amount'] > 0 else 0,
            'close_price': last_price,  # 当前价格
            'amount': long_position['amount'],
            'profit': (last_price * long_position['amount']) - long_position['cost'],
            'profit_percent': ((last_price * long_position['amount'] - long_position['cost']) / long_position['cost']) * 100 if long_position['cost'] else 0,
            'trades': long_position['trades'],
            'is_open': True  # 标记为未平仓
        }
        positions.append(position)
    
    if short_position['amount'] > 0:
        # 添加当前持有的空头仓位，使用最后一个价格作为"未平仓"价格
        last_price = trades_df['price'].iloc[-1] if 'price' in trades_df.columns else 0
        
        position = {
            'open_time': short_position['open_time'],
            'close_time': None,  # 未平仓
            'side': 'short',
            'open_price': short_position['cost'] / short_position['amount'] if short_position['amount'] > 0 else 0,
            'close_price': last_price,  # 当前价格
            'amount': short_position['amount'],
            'profit': short_position['cost'] - (last_price * short_position['amount']),
            'profit_percent': ((short_position['cost'] - last_price * short_position['amount']) / short_position['cost']) * 100 if short_position['cost'] else 0,
            'trades': short_position['trades'],
            'is_open': True  # 标记为未平仓
        }
        positions.append(position)
    
    # 转换为DataFrame
    if positions:
        positions_df = pd.DataFrame(positions)
        logger.info(f"成功合并为 {len(positions_df)} 个仓位")
        return positions_df
    else:
        logger.info("没有找到有效的仓位")
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
            <style>
                /* 自定义样式 - 黑色背景下拉框 */
                .dash-dropdown .Select-control {
                    background-color: #121212 !important;
                    color: white !important;
                    border-color: #2B2B43 !important;
                }
                .dash-dropdown .Select-menu-outer {
                    background-color: #121212 !important;
                    color: white !important;
                    border-color: #2B2B43 !important;
                }
                .dash-dropdown .Select-value-label {
                    color: white !important;
                }
                .dash-dropdown .Select-menu-outer .VirtualizedSelectOption {
                    background-color: #121212 !important;
                    color: white !important;
                }
                .dash-dropdown .Select-menu-outer .VirtualizedSelectOption:hover {
                    background-color: #2B2B43 !important;
                }
                .dash-dropdown .Select-value {
                    border-color: #2B2B43 !important;
                }
                .dash-dropdown .Select-arrow {
                    border-color: white transparent transparent !important;
                }
                .dash-dropdown .is-open .Select-arrow {
                    border-color: transparent transparent white !important;
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
                            ], width=2, id="start-date-col", style={"display": "block"}),
                            
                            dbc.Col([
                                html.Label("结束日期"),
                                dcc.DatePickerSingle(
                                    id="end-date-picker",
                                    date=datetime.now().date(),
                                    display_format="YYYY-MM-DD",
                                    className="w-100"
                                )
                            ], width=2, id="end-date-col", style={"display": "block"}),
                            
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
                            ], width=3, id="start-time-col", style={"display": "block"}),
                            
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
                            ], width=3, id="end-time-col", style={"display": "block"}),
                            
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
                
                # 创建人类可读的时间范围字符串
                if since:
                    since_str = pd.to_datetime(since, unit='ms').strftime('%Y-%m-%d %H:%M:%S')
                else:
                    since_str = "全部历史"
                
                if until:
                    until_str = pd.to_datetime(until, unit='ms').strftime('%Y-%m-%d %H:%M:%S')
                else:
                    until_str = "现在"
                
                time_range_str = f"{since_str} 至 {until_str}"
                
                # 获取K线数据
                df = fetch_ohlcv_data(exchange, symbol, timeframe, since, until)
                
                if df.empty:
                    return dash.no_update, dash.no_update, "", html.Div("无法加载K线数据", className="text-danger")
                
                # 准备图表数据
                chart_data = prepare_data_for_chart(df)
                
                # 获取交易记录
                df_trades = fetch_trades(exchange, symbol, since, until)
                
                # 合并交易记录为仓位信息
                if not df_trades.empty:
                    positions_df = merge_trades_to_positions(df_trades)
                    
                    # 准备交易数据用于图表展示
                    positions_data = []
                    
                    if not positions_df.empty:
                        logger.info(f"处理 {len(positions_df)} 个仓位用于图表展示")
                        
                        for _, pos in positions_df.iterrows():
                            # 开仓标记
                            if pd.notna(pos['open_time']):
                                # 将开仓时间转换为时间戳（秒）
                                open_time = int(pd.to_datetime(pos['open_time']).timestamp())
                                
                                # 创建开仓标记
                                positions_data.append({
                                    'time': open_time,
                                    'price': pos['open_price'],
                                    'side': 'buy' if pos['side'] == 'long' else 'sell',
                                    'amount': pos['amount'],
                                    'cost': pos['amount'] * pos['open_price'],
                                    'position_type': 'open',
                                    'position_id': str(pos.name)  # 使用DataFrame索引作为唯一标识
                                })
                            
                            # 平仓标记(如果已平仓)
                            if pd.notna(pos['close_time']):
                                # 将平仓时间转换为时间戳（秒）
                                close_time = int(pd.to_datetime(pos['close_time']).timestamp())
                                
                                # 创建平仓标记
                                positions_data.append({
                                    'time': close_time,
                                    'price': pos['close_price'],
                                    'side': 'sell' if pos['side'] == 'long' else 'buy',
                                    'amount': pos['amount'],
                                    'cost': pos['amount'] * pos['close_price'],
                                    'position_type': 'close',
                                    'position_id': str(pos.name),
                                    'profit': pos['profit'],
                                    'profit_percent': pos['profit_percent']
                                })
                else:
                    positions_df = pd.DataFrame()
                    positions_data = []
                
                # 返回数据和状态信息
                status_info = html.Div([
                    html.Span(f"时间范围: {time_range_str}", className="text-warning me-3"),
                    html.Span(f"已加载 {len(df)} 条K线数据", className="text-success me-3"),
                    html.Span(f"已加载 {len(positions_data)} 个交易标记", className="text-info me-3"),
                    html.Span(f"已合并 {len(positions_df)} 个仓位", className="text-primary")
                ])
                
                return json.dumps(chart_data), json.dumps(positions_data), "", status_info
                
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