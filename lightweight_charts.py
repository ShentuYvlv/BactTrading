import dash
from dash import html, dcc, callback, Input, Output, State, ClientsideFunction, callback_context
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
import glob

# 加载.env文件中的环境变量
dotenv.load_dotenv()

def get_latest_csv_file():
    """获取data目录中最新的CSV文件"""
    try:
        # 获取data目录路径
        data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')

        if not os.path.exists(data_dir):
            logger.warning(f"data目录不存在: {data_dir}")
            return None

        # 查找所有CSV文件
        csv_files = glob.glob(os.path.join(data_dir, '*.csv'))

        if not csv_files:
            logger.warning("data目录中没有找到CSV文件")
            return None

        # 按修改时间排序，返回最新的文件
        latest_file = max(csv_files, key=os.path.getmtime)
        logger.info(f"找到最新的CSV文件: {os.path.basename(latest_file)}")
        return latest_file

    except Exception as e:
        logger.error(f"获取最新CSV文件时出错: {e}")
        return None

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
                    # 添加utc=True参数，确保时间被当作北京时区处理并转换为UTC时间戳
                    # 或者明确指定时区为上海时区后转换为UTC
                    open_time_dt = pd.to_datetime(row['开仓时间'])
                    open_timestamp = int((open_time_dt - pd.Timedelta(hours=8)).timestamp())
                
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
                    if pd.notna(row['平仓时间']):
                        close_time_dt = pd.to_datetime(row['平仓时间'])
                        close_timestamp = int((close_time_dt - pd.Timedelta(hours=8)).timestamp())
                        close_time_formatted = row['平仓时间']
                    else:
                        close_timestamp = None
                        close_time_formatted = '持仓中'
                
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
    """生成缓存键，包含币种和时间范围信息"""
    # 处理symbol，移除特殊字符
    clean_symbol = symbol.replace('/', '_').replace(':', '_')
    
    # 将时间戳转换为更易读的格式
    since_date = datetime.fromtimestamp(since / 1000).strftime('%Y%m%d') if since else 'none'
    until_date = datetime.fromtimestamp(until / 1000).strftime('%Y%m%d') if until else 'none'
    
    # 主键部分：包含币种和时间周期
    main_key = f"{clean_symbol}_{timeframe}"
    
    # 完整键：用于缓存文件名
    full_key_str = f"{main_key}_{since_date}_{until_date}"
    
    # 为防止文件名过长，对完整键生成哈希值，但保留主键作为前缀
    hash_part = hashlib.md5(f"{since}_{until}".encode()).hexdigest()[:8]
    
    return f"{main_key}_{hash_part}"

def get_cached_data(cache_key):
    """从缓存获取数据，支持模糊匹配"""
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.pkl")
    
    # 检查精确匹配的缓存文件是否存在且未过期
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
    
    # 如果没有精确匹配，尝试查找同一币种和时间周期的缓存文件
    if "_" in cache_key:
        # 提取主键部分（币种和时间周期）
        main_key = cache_key.rsplit('_', 1)[0]
        
        # 查找所有匹配的缓存文件
        matching_files = []
        for filename in os.listdir(CACHE_DIR):
            if filename.startswith(f"{main_key}_") and filename.endswith(".pkl"):
                full_path = os.path.join(CACHE_DIR, filename)
                # 检查文件是否过期
                file_mod_time = os.path.getmtime(full_path)
                if time.time() - file_mod_time < 24 * 3600:  # 24小时缓存
                    matching_files.append((full_path, file_mod_time))
        
        # 如果找到匹配的文件，使用最新的那个
        if matching_files:
            # 按修改时间排序，最新的在前
            matching_files.sort(key=lambda x: x[1], reverse=True)
            newest_file = matching_files[0][0]
            try:
                with open(newest_file, 'rb') as f:
                    data = pickle.load(f)
                cache_key_used = os.path.basename(newest_file).replace('.pkl', '')
                logger.info(f"使用模糊匹配的缓存: {cache_key_used} (请求的键: {cache_key})")
                return data
            except Exception as e:
                logger.error(f"读取模糊匹配缓存失败: {str(e)}")
    
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

def append_to_cache(symbol, timeframe, new_data):
    """将新数据追加到现有缓存文件中"""
    try:
        # 查找该币种和时间周期的所有缓存文件
        main_key = f"{symbol.replace('/', '_').replace(':', '_')}_{timeframe}"
        matching_files = []
        
        for filename in os.listdir(CACHE_DIR):
            if filename.startswith(f"{main_key}_") and filename.endswith(".pkl"):
                full_path = os.path.join(CACHE_DIR, filename)
                file_mod_time = os.path.getmtime(full_path)
                matching_files.append((full_path, file_mod_time))
        
        # 如果找到匹配的文件，使用最新的那个
        if matching_files:
            # 按修改时间排序，最新的在前
            matching_files.sort(key=lambda x: x[1], reverse=True)
            newest_file = matching_files[0][0]
            cache_key = os.path.basename(newest_file).replace('.pkl', '')
            
            # 读取现有数据
            with open(newest_file, 'rb') as f:
                existing_data = pickle.load(f)
            
            # 防止数据重复，检查时间戳
            if not existing_data.empty and not new_data.empty:
                # 确定现有数据的最后时间戳
                last_timestamp = existing_data['timestamp'].max()
                
                # 过滤掉新数据中早于或等于最后时间戳的记录
                new_data = new_data[new_data['timestamp'] > last_timestamp]
                
                if new_data.empty:
                    logger.info(f"没有新数据需要追加到缓存")
                    return None
            
            # 合并数据
            combined_data = pd.concat([existing_data, new_data], ignore_index=True)
            
            # 确保时间排序
            combined_data = combined_data.sort_values('timestamp').reset_index(drop=True)
            
            # 重新保存到同一文件
            with cache_lock:
                with open(newest_file, 'wb') as f:
                    pickle.dump(combined_data, f)
            
            logger.info(f"新数据已追加到缓存文件: {cache_key}, 总计 {len(combined_data)} 条记录")
            return cache_key
        else:
            # 如果没有找到匹配的文件，创建新的缓存文件
            cache_key = get_cache_key(symbol, timeframe, 
                                      int(new_data['timestamp'].min().timestamp() * 1000),
                                      int(new_data['timestamp'].max().timestamp() * 1000))
            save_to_cache(cache_key, new_data)
            logger.info(f"未找到现有缓存，已创建新缓存: {cache_key}")
            return cache_key
    except Exception as e:
        logger.error(f"追加到缓存失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

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

def list_cache_files():
    """列出所有可用的缓存文件，按币种分组"""
    if not os.path.exists(CACHE_DIR):
        logger.warning(f"缓存目录不存在: {CACHE_DIR}")
        return {}
    
    # 按币种分组的缓存文件字典
    cache_files_by_symbol = {}
    
    for filename in os.listdir(CACHE_DIR):
        if filename.endswith(".pkl"):
            try:
                # 尝试从文件名解析币种信息
                parts = filename.replace(".pkl", "").split("_")
                if len(parts) >= 3:  # 至少应该有币种、交易对后缀和时间周期
                    # 推断币种
                    if len(parts) >= 4 and parts[1] == "USDT":  # 形如 BTC_USDT_1h_xxx
                        symbol = f"{parts[0]}/USDT"
                        timeframe = parts[2]
                    else:  # 形如 BTC_USDT_USDT_1h_xxx
                        symbol = f"{parts[0]}_{parts[1]}"
                        timeframe = parts[2]
                    
                    # 获取文件大小和修改时间
                    file_path = os.path.join(CACHE_DIR, filename)
                    file_size = os.path.getsize(file_path) / (1024 * 1024)  # 转换为MB
                    file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                    
                    # 添加到字典
                    key = symbol.replace("_", "/")
                    if key not in cache_files_by_symbol:
                        cache_files_by_symbol[key] = []
                    
                    cache_files_by_symbol[key].append({
                        "filename": filename,
                        "timeframe": timeframe,
                        "size": f"{file_size:.2f} MB",
                        "modified": file_time.strftime("%Y-%m-%d %H:%M:%S")
                    })
            except Exception as e:
                logger.debug(f"解析缓存文件名出错 {filename}: {str(e)}")
                continue
    
    # 按币种排序
    return dict(sorted(cache_files_by_symbol.items()))

def print_cache_info():
    """打印缓存信息摘要"""
    try:
        cache_files = list_cache_files()
        
        if not cache_files:
            logger.info("当前没有缓存文件")
            return
        
        total_size = 0
        total_files = 0
        for symbol, files in cache_files.items():
            for file_info in files:
                total_files += 1
                total_size += float(file_info["size"].split()[0])
        
        logger.info(f"缓存统计: {total_files} 个文件, {total_size:.2f} MB, {len(cache_files)} 个币种")
        
        # 打印前5个币种的详细信息
        top_symbols = list(cache_files.keys())[:5]
        for symbol in top_symbols:
            files = cache_files[symbol]
            logger.info(f"  {symbol}: {len(files)} 个缓存文件")
            for file_info in files[:2]:  # 只显示每个币种的前2个文件
                logger.info(f"    - {file_info['filename']} ({file_info['timeframe']}, {file_info['size']})")
            if len(files) > 2:
                logger.info(f"    - ... 等 {len(files)-2} 个文件")
    except Exception as e:
        logger.error(f"打印缓存信息时出错: {str(e)}")

def get_data_files():
    """获取data文件夹中的所有CSV文件"""
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    if not os.path.exists(data_dir):
        logger.warning(f"data文件夹不存在: {data_dir}")
        return []

    csv_files = []
    for filename in os.listdir(data_dir):
        if filename.endswith('.csv'):
            file_path = os.path.join(data_dir, filename)
            file_size = os.path.getsize(file_path) / (1024 * 1024)  # 转换为MB
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))

            csv_files.append({
                'filename': filename,
                'path': file_path,
                'size': f"{file_size:.2f} MB",
                'modified': file_time.strftime("%Y-%m-%d %H:%M:%S")
            })

    # 按修改时间排序，最新的在前
    csv_files.sort(key=lambda x: x['modified'], reverse=True)
    return csv_files

def create_app():
    """创建Dash应用"""
    # 初始化交易所
    exchange = initialize_exchange()

    # 打印缓存信息
    print_cache_info()

    # 获取data文件夹中的CSV文件
    data_files = get_data_files()

    # 默认选择第一个文件（最新的）
    default_file = data_files[0]['path'] if data_files else None
    symbols_data = load_symbols_from_csv(default_file) if default_file else {}

    # 创建币种加载状态字典，保存每个币种的最后加载时间和参数
    symbol_load_states = {}
    
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

                // 定义客户端回调函数
                window.dash_clientside = Object.assign({}, window.dash_clientside, {
                    clientside: {
                        initializeChart: function(chartData, tradesData, showEma, showTrades, showBollinger, showRsi, showMacd) {
                            console.log('🔄 initializeChart 被调用', {
                                chartDataLength: chartData ? chartData.length : 0,
                                tradesDataLength: tradesData ? tradesData.length : 0,
                                showEma, showTrades, showBollinger, showRsi, showMacd
                            });

                            // 创建图表容器HTML
                            const chartHtml = `
                                <div id="tradingview-chart" style="
                                    width: 100%;
                                    height: 600px;
                                    background-color: #1c2030;
                                    border: 1px solid #2B2B43;
                                    border-radius: 8px;
                                    position: relative;
                                "></div>
                            `;

                            // 使用setTimeout确保DOM更新后再初始化图表
                            setTimeout(function() {
                                const chartElement = document.getElementById('tradingview-chart');
                                if (chartElement && typeof LightweightCharts !== 'undefined') {
                                    console.log('📊 开始创建图表...');

                                    // 清除之前的图表
                                    if (chartElement._chart) {
                                        chartElement._chart.remove();
                                    }

                                    // 如果没有数据，显示提示信息
                                    if (!chartData || chartData.length === 0) {
                                        chartElement.innerHTML = `
                                            <div style="
                                                width: 100%;
                                                height: 100%;
                                                display: flex;
                                                align-items: center;
                                                justify-content: center;
                                                color: #9aa1b9;
                                                font-size: 16px;
                                            ">暂无图表数据</div>
                                        `;
                                        return;
                                    }

                                    // 创建新图表
                                    const chart = LightweightCharts.createChart(chartElement, {
                                        width: chartElement.clientWidth,
                                        height: 600,
                                        layout: {
                                            background: { color: '#1c2030' },
                                            textColor: '#d1d4dc',
                                        },
                                        grid: {
                                            vertLines: { color: '#2B2B43' },
                                            horzLines: { color: '#2B2B43' },
                                        },
                                        crosshair: {
                                            mode: LightweightCharts.CrosshairMode.Normal,
                                        },
                                        rightPriceScale: {
                                            borderColor: '#2B2B43',
                                        },
                                        timeScale: {
                                            borderColor: '#2B2B43',
                                            timeVisible: true,
                                            secondsVisible: false,
                                        },
                                    });

                                    // 添加K线数据
                                    const candlestickSeries = chart.addCandlestickSeries({
                                        upColor: '#26a69a',
                                        downColor: '#ef5350',
                                        borderVisible: false,
                                        wickUpColor: '#26a69a',
                                        wickDownColor: '#ef5350',
                                    });

                                    console.log('📈 设置K线数据，数据量:', chartData.length);
                                    candlestickSeries.setData(chartData);

                                    // 添加交易标记
                                    if (showTrades && tradesData && tradesData.length > 0) {
                                        console.log('🎯 添加交易标记，标记数量:', tradesData.length);
                                        const markers = tradesData.map(trade => ({
                                            time: trade.open_time,
                                            position: trade.side === 'long' ? 'belowBar' : 'aboveBar',
                                            color: trade.side === 'long' ? '#26a69a' : '#ef5350',
                                            shape: trade.side === 'long' ? 'arrowUp' : 'arrowDown',
                                            text: `${trade.side.toUpperCase()} @${trade.open_price}`
                                        }));
                                        candlestickSeries.setMarkers(markers);
                                    }

                                    // 响应式调整
                                    const resizeObserver = new ResizeObserver(entries => {
                                        if (entries.length === 0 || entries[0].target !== chartElement) return;
                                        const newRect = entries[0].contentRect;
                                        chart.applyOptions({ width: newRect.width });
                                    });
                                    resizeObserver.observe(chartElement);

                                    // 存储图表实例
                                    chartElement._chart = chart;

                                    console.log('✅ 图表创建完成');
                                } else {
                                    console.error('❌ 图表元素或LightweightCharts库未找到');
                                }
                            }, 100);

                            return chartHtml;
                        }
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
                    height: calc(100vh - 60px);  /* 进一步减少顶部和底部间距 */
                    min-height: 900px;  /* 进一步增加最小高度 */
                }
                
                #chart-container {
                    height: 100% !important;
                }
                
                /* 优化RSI和MACD容器样式 */
                .tv-lightweight-charts {
                    margin-bottom: 0 !important;
                    padding-bottom: 0 !important;
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
                
                /* 自定义左侧栏样式 */
                
                /* 修改控制面板的滚动行为 */

                
                .control-panel::-webkit-scrollbar {
                    width: 6px;
                }
                
                .control-panel::-webkit-scrollbar-track {
                    background: #121722;
                }
                
                .control-panel::-webkit-scrollbar-thumb {
                    background-color: #2B2B43;
                    border-radius: 6px;
                }
                
                /* 美化卡片样式 */
                .custom-card {
                    background-color: rgba(19, 23, 34, 0.6);
                    border-radius: 8px;
                    border: 1px solid rgba(43, 43, 67, 0.8);
                    transition: all 0.3s ease;
                }
                
                .custom-card:hover {
                    border-color: rgba(43, 43, 67, 1);
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
                }
                
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

                /* 时间周期按钮样式 */
                .timeframe-btn {
                    min-width: 50px;
                    font-size: 0.85rem;
                    font-weight: 500;
                    transition: all 0.2s ease;
                }

                .timeframe-btn:hover {
                    transform: translateY(-1px);
                    box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                }

                .timeframe-btn.active {
                    background-color: #0d6efd !important;
                    border-color: #0d6efd !important;
                    color: white !important;
                    box-shadow: 0 2px 8px rgba(13, 110, 253, 0.3);
                }

                /* 响应式时间周期按钮 */
                @media (max-width: 768px) {
                    .timeframe-btn {
                        min-width: 40px;
                        font-size: 0.75rem;
                        padding: 0.25rem 0.5rem;
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
        {'label': '30分钟', 'value': '30m'},
        {'label': '1小时', 'value': '1h'},
        {'label': '4小时', 'value': '4h'},
        {'label': '8小时', 'value': '8h'},
        {'label': '1天', 'value': '1d'},
        {'label': '1周', 'value': '1w'},
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
                    ], className="mb-3 border-secondary custom-card"),
                    
                    # 控制面板卡片
                    dbc.Card([
                        dbc.CardBody([
                    # 数据文件选择
                            dbc.Row([
                    dbc.Col([
                        html.Label("数据文件", className="form-label mb-1"),
                        dcc.Dropdown(
                            id="data-file-dropdown",
                            options=[
                                {'label': f"{file['filename']} ({file['size']}, {file['modified']})",
                                 'value': file['path']}
                                for file in data_files
                            ],
                            value=default_file,
                            clearable=False,
                            className="dash-dropdown-sm"
                        )
                                ], width=12, className="mb-2"),

                    # 交易对选择
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
                                    ], className="border-light bg-dark custom-card")
                                ], width=12, className="mb-3"),
                    
                                # 状态信息区域
                    dbc.Col([
                                    html.Label("状态信息", className="form-label mb-1"),
                                    html.Div(id="status-info", className="small p-2 border border-secondary rounded bg-dark")
                                ], width=12),
                    
                                # 添加隐藏的加载更多K线触发器
                                html.Div(dbc.Input(id="load-more-trigger", type="hidden", value=0), style={"display": "none"}),
                                
                                # 添加辅助按钮，用于确保加载更多功能可以触发
                                html.Button(id="load-more-helper-button", style={"display": "none"}),
                                
                    # 添加调试按钮
                    dbc.Col([
                        html.Label("调试工具", className="form-label mb-1"),
                        dbc.Button(
                            "检查标记元素", 
                            id="debug-markers-button", 
                            color="warning", 
                            size="sm",
                            className="w-100 mb-2"
                        ),
                        dcc.Store(id="debug-info-store"),
                        html.Div(id="debug-info-output", className="small text-muted mt-1")
                    ], width=12, className="mb-3"),
                            ]) # 关闭 dbc.Row 内部
                        ], className="p-2") # 关闭 dbc.CardBody
                    ], className="custom-card") # 关闭 dbc.Card (控制面板卡片)
                ], className="control-panel", style={"padding-right": "10px"}) # 关闭 html.Div (左侧Col内部)
            ], id="left-sidebar", width=2, className="pe-2 custom-sidebar", style={"box-shadow": "2px 0 10px rgba(0, 0, 0, 0.2)"}), # 关闭 dbc.Col (左侧)
        
            # 右侧区域 - 图表（80%宽度）
            dbc.Col([
                # 时间周期选择栏
                dbc.Card([
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Div([
                                    html.Span("时间周期:", className="me-3 fw-bold"),
                                    dbc.ButtonGroup([
                                        dbc.Button("1分", id="timeframe-btn-1m", size="sm", outline=True, color="primary", className="timeframe-btn"),
                                        dbc.Button("5分", id="timeframe-btn-5m", size="sm", outline=True, color="primary", className="timeframe-btn"),
                                        dbc.Button("15分", id="timeframe-btn-15m", size="sm", outline=True, color="primary", className="timeframe-btn"),
                                        dbc.Button("30分", id="timeframe-btn-30m", size="sm", outline=True, color="primary", className="timeframe-btn"),
                                        dbc.Button("1小时", id="timeframe-btn-1h", size="sm", outline=True, color="primary", className="timeframe-btn"),
                                        dbc.Button("4小时", id="timeframe-btn-4h", size="sm", outline=True, color="primary", className="timeframe-btn"),
                                        dbc.Button("8小时", id="timeframe-btn-8h", size="sm", outline=True, color="primary", className="timeframe-btn"),
                                        dbc.Button("1天", id="timeframe-btn-1d", size="sm", outline=True, color="primary", className="timeframe-btn"),
                                        dbc.Button("1周", id="timeframe-btn-1w", size="sm", outline=True, color="primary", className="timeframe-btn"),
                                    ], className="me-3"),
                                ], className="d-flex align-items-center")
                            ], width=12)
                        ])
                    ], className="py-2")
                ], className="mb-2 border-secondary"),

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
                    ], className="p-2")
                ], className="border-secondary chart-card", style={"background-color": "#131722", "border-radius": "8px", "overflow": "hidden"}),
            ], width=10, className="ps-1", style={"padding-left": "12px"}),  # 增加左侧内边距
        ], className="g-0"),  # 去除行间距，这是dbc.Row的结束
                
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
        
    ], fluid=True, className="bg-dark text-light p-3", style={
        "background": "linear-gradient(to bottom, #0a0e17, #131722)",
        "min-height": "100vh",
        "padding": "15px 20px"
    }) # 这是最外层 dbc.Container 的结束
    
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

    # 时间周期选择回调（双向同步：按钮点击和dropdown变化）
    @app.callback(
        [Output("timeframe-dropdown", "value")] +
        [Output(f"timeframe-btn-{tf}", "outline") for tf in ["1m", "5m", "15m", "30m", "1h", "4h", "8h", "1d", "1w"]] +
        [Output(f"timeframe-btn-{tf}", "color") for tf in ["1m", "5m", "15m", "30m", "1h", "4h", "8h", "1d", "1w"]],
        [Input(f"timeframe-btn-{tf}", "n_clicks") for tf in ["1m", "5m", "15m", "30m", "1h", "4h", "8h", "1d", "1w"]] +
        [Input("timeframe-dropdown", "value")],
        prevent_initial_call=False  # 允许初始调用以设置默认状态
    )
    def update_timeframe_selection(*args):
        """处理时间周期按钮点击和dropdown变化的双向同步"""
        ctx = callback_context

        # 时间周期映射
        timeframe_map = {
            "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
            "1h": "1h", "4h": "4h", "8h": "8h", "1d": "1d", "1w": "1w"
        }
        timeframes = ["1m", "5m", "15m", "30m", "1h", "4h", "8h", "1d", "1w"]

        # 默认值
        current_timeframe = "1h"
        dropdown_value = "1h"

        if ctx.triggered:
            trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

            if trigger_id.startswith('timeframe-btn-'):
                # 按钮被点击
                current_timeframe = trigger_id.replace('timeframe-btn-', '')
                dropdown_value = timeframe_map.get(current_timeframe, "1h")
            elif trigger_id == 'timeframe-dropdown':
                # dropdown被改变
                dropdown_value = args[-1]  # 最后一个参数是dropdown的值
                current_timeframe = dropdown_value
        else:
            # 初始调用，使用dropdown的当前值
            dropdown_value = args[-1] if args[-1] else "1h"
            current_timeframe = dropdown_value

        # 更新按钮样式：被选中的按钮不使用outline，其他使用outline
        outline_values = [tf != current_timeframe for tf in timeframes]
        color_values = ["primary" for _ in timeframes]

        return [dropdown_value] + outline_values + color_values

    # 时间周期改变时自动重新加载数据
    @app.callback(
        [Output("chart-data-store", "data", allow_duplicate=True),
         Output("trades-data-store", "data", allow_duplicate=True),
         Output("loading-spinner", "children", allow_duplicate=True),
         Output("status-info", "children", allow_duplicate=True)],
        [Input("timeframe-dropdown", "value")],
        [State("symbol-input", "value"),
         State("start-date-picker", "date"),
         State("end-date-picker", "date"),
         State("data-file-dropdown", "value")],
        prevent_initial_call=True
    )
    def reload_data_on_timeframe_change(timeframe, symbol, start_date, end_date, selected_file_path):
        """当时间周期改变时，自动重新加载数据"""
        if not symbol or not timeframe:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update

        # 显示加载状态
        loading_spinner = dbc.Spinner(
            html.Div("正在切换时间周期，请稍候...", className="text-center p-3"),
            size="sm",
            color="primary"
        )

        try:
            # 获取K线数据
            since, until = calculate_time_range(start_date, end_date)
            df = fetch_ohlcv_data(exchange, symbol, timeframe, since, until)

            if df.empty:
                return [], [], html.Div("未获取到K线数据", className="text-warning p-2"), \
                       html.Div("时间周期切换完成，但未获取到数据", className="text-warning p-2")

            # 从CSV加载仓位数据
            csv_file_path = selected_file_path or get_latest_csv_file()
            positions_data = load_positions_from_csv(csv_file_path, symbol=symbol) if csv_file_path else []

            # 准备图表数据
            chart_data = prepare_data_for_chart(df)

            # 状态信息
            status_info = html.Div([
                html.Span(f"时间周期: {timeframe} | ", className="fw-bold small me-1"),
                html.Span(f"K线数据: {len(df)} 条 | ", className="text-success small me-1"),
                html.Span(f"仓位标记: {len(positions_data)} 个", className="text-info small")
            ], className="p-2 border border-secondary rounded bg-dark")

            return chart_data, positions_data, html.Div(), status_info

        except Exception as e:
            logger.error(f"切换时间周期时出错: {e}")
            return [], [], html.Div(), html.Div(f"切换时间周期失败: {str(e)}", className="text-danger p-2")

    # 文件选择回调 - 当用户选择不同的数据文件时更新币种列表
    @app.callback(
        Output("symbol-grid", "children"),
        Input("data-file-dropdown", "value"),
        prevent_initial_call=True
    )
    def update_symbols_from_file(selected_file_path):
        """当选择不同的数据文件时，更新币种列表"""
        if not selected_file_path:
            return []

        try:
            # 从选择的文件加载币种数据
            symbols_data = load_symbols_from_csv(selected_file_path)

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

            logger.info(f"从文件 {selected_file_path} 加载了 {len(symbol_items)} 个币种")
            return symbol_items

        except Exception as e:
            logger.error(f"更新币种列表时出错: {str(e)}")
            return [html.Div("加载币种数据失败", className="text-danger")]

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
         State("end-date-picker", "date"),
         State("data-file-dropdown", "value")],
        prevent_initial_call=True
    )
    def load_chart_data(load_clicks, reset_clicks, symbol, timeframe, start_date, end_date, selected_file_path):
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
                
                # 从CSV文件加载仓位数据
                positions_data = []
                if selected_file_path and os.path.exists(selected_file_path):
                    # 直接从CSV文件加载仓位数据
                    csv_positions_data = load_positions_from_csv(selected_file_path, symbol)

                    if csv_positions_data:
                        logger.info(f"从CSV文件加载了 {len(csv_positions_data)} 个仓位")
                        positions_data = csv_positions_data
                    else:
                        logger.warning(f"CSV文件中没有找到 {symbol} 的仓位数据")
                else:
                    logger.warning(f"未选择有效的数据文件或文件不存在: {selected_file_path}")

                # 如果CSV中没有数据，尝试从API获取交易记录（备用方案）
                if not positions_data:
                    logger.info("CSV文件中没有数据，尝试从API获取交易记录")
                    df_trades = fetch_trades(exchange, symbol, since, until)

                    # 合并交易记录为仓位信息
                    if not df_trades.empty:
                        positions_df = merge_trades_to_positions(df_trades)

                        # 准备仓位数据用于图表展示 - 新的格式
                        api_positions_data = []

                        if not positions_df.empty:
                            logger.info(f"处理 {len(positions_df)} 个仓位用于图表展示")

                            for _, pos in positions_df.iterrows():
                                # 检查仓位是否有有效的开仓和平仓时间
                                if pd.notna(pos['open_time']) and pd.notna(pos['close_time']):
                                    # 将时间转换为Unix时间戳（秒）以匹配K线数据的 time 格式
                                    # 直接使用时间戳，不做额外的时区处理，避免时间偏移
                                    open_timestamp = int(pd.to_datetime(pos['open_time']).timestamp())
                                    close_timestamp = int(pd.to_datetime(pos['close_time']).timestamp())

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

                                    api_positions_data.append(position_data)
                                elif pd.notna(pos['open_time']) and pos.get('is_open', False):
                                    # 仅有开仓信息的持仓，直接使用时间戳，不做额外的时区处理
                                    open_timestamp = int(pd.to_datetime(pos['open_time']).timestamp())

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

                                    api_positions_data.append(position_data)

                        # 如果API获取到了数据，使用API数据
                        if api_positions_data:
                            positions_data = api_positions_data
                    else:
                        positions_df = pd.DataFrame()
                
                # 确定数据来源
                data_source = "CSV文件" if selected_file_path and os.path.exists(selected_file_path) and positions_data else "API"
                file_name = os.path.basename(selected_file_path) if selected_file_path else "无"

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
                                html.Span("数据来源: ", className="fw-bold small me-1"),
                                html.Span(f"{data_source}", className="text-info small"),
                                html.Span(f" ({file_name})" if data_source == "CSV文件" else "", className="text-muted small")
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
         Output("timeframe-dropdown", "value", allow_duplicate=True)],  # 更新周期选择器
        [Input(f"symbol-{symbol.replace('/', '-').replace(':', '_')}", "n_clicks") for symbol in symbols_data.keys()],
        [State("data-file-dropdown", "value")],  # 添加当前选择的文件作为状态
        prevent_initial_call=True
    )
    def load_data_from_symbol_click(*args):
        """处理币种点击事件，加载数据"""
        ctx = dash.callback_context
        if not ctx.triggered:
            return [dash.no_update] * 8

        # 最后一个参数是选择的文件路径
        selected_file_path = args[-1] if args else None
        
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
            # 检查是否有保存的币种状态
            if clicked_symbol in symbol_load_states:
                # 使用保存的状态，而不是默认值
                saved_state = symbol_load_states[clicked_symbol]
                default_start_date = pd.to_datetime(saved_state.get('start_date', '2024-11-20'))
                default_end_date = pd.to_datetime(saved_state.get('end_date', '2025-5-30'))
                default_timeframe = saved_state.get('timeframe', '15m')
                print(f"使用保存的币种状态: {saved_state}")
            else:
                # 使用前端选择的文件，如果没有选择则使用最新文件
                csv_file_path = selected_file_path or get_latest_csv_file()

                # 尝试加载该币种的交易记录
                positions = load_positions_from_csv(csv_file_path, symbol=clicked_symbol) if csv_file_path else []
                
                # 查找最近一笔交易的时间
                recent_trade_date = None
                if positions and len(positions) > 0:
                    # 查找所有交易中最早的开仓时间
                    open_times = [pos['open_time'] for pos in positions if 'open_time' in pos and pos['open_time']]
                    if open_times:
                        # 将Unix时间戳转换为datetime对象
                        earliest_trade_time = min(open_times)
                        recent_trade_date = datetime.fromtimestamp(earliest_trade_time)
                        # 向前推7天，以便获取交易前的K线数据
                        recent_trade_date = recent_trade_date - timedelta(days=7)
                        logger.info(f"找到{clicked_symbol}最早交易时间: {datetime.fromtimestamp(earliest_trade_time)}，设置开始日期为提前7天: {recent_trade_date}")
                
                # 如果找不到交易记录，则使用默认日期
                if not recent_trade_date:
                    # 默认开始日期设置为6个月前
                    recent_trade_date = datetime.now() - timedelta(days=180)
                    logger.info(f"未找到{clicked_symbol}的交易记录，使用默认开始日期: {recent_trade_date}")

                default_start_date = recent_trade_date
                # 结束日期设置为当前时间，确保不会出现开始时间大于结束时间的问题
                default_end_date = datetime.now()
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
            
            # 获取K线数据
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
            csv_file_path = selected_file_path or get_latest_csv_file()
            positions_data = load_positions_from_csv(csv_file_path, symbol=clicked_symbol) if csv_file_path else []
            
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
            
            # 保存当前币种的加载状态
            symbol_load_states[clicked_symbol] = {
                'start_date': default_start_date.strftime('%Y-%m-%d'),
                'end_date': default_end_date.strftime('%Y-%m-%d'),
                'timeframe': default_timeframe,
                'last_load_time': pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
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
    
    # 添加重置加载更多按钮状态的客户端回调
    app.clientside_callback(
        """
        function(chartData) {
            // 图表数据更新后，重置加载更多按钮
            if (chartData) {
                try {
                    console.log("检测到图表数据更新，准备重置加载更多按钮");
                    const loadMoreBtn = document.querySelector('.load-more-button');
                    if (loadMoreBtn && loadMoreBtn.innerText === '加载中...') {
                        loadMoreBtn.innerText = '加载更多';
                        loadMoreBtn.style.backgroundColor = 'rgba(33, 150, 243, 0.9)';
                        loadMoreBtn.style.cursor = 'pointer';
                        console.log('数据已更新，重置加载更多按钮状态');
                    }
                } catch (e) {
                    console.error('重置加载更多按钮状态时出错:', e);
                }
            }
            return null;
        }
        """,
        Output("load-more-helper-button", "n_clicks", allow_duplicate=True),
        [Input("chart-data-store", "data")],
        prevent_initial_call=True
    )
    
    # 最后添加一个调试按钮的回调
    # 添加调试按钮的客户端回调
    app.clientside_callback(
        """
        function(n_clicks) {
            if (!n_clicks) return "";
            
            try {
                // 检查图表是否已加载
                if (!window.priceChart) {
                    return "图表尚未加载，请先加载数据";
                }
                
                // 查找所有标记元素
                const markerElements = document.querySelectorAll('.tv-lightweight-charts text');
                const markerIds = document.querySelectorAll('[data-marker-id]');
                
                let debugInfo = `找到 ${markerElements.length} 个文本元素, ${markerIds.length} 个带标记ID的元素\\n\\n`;
                
                // 输出带ID的元素信息
                if (markerIds.length > 0) {
                    debugInfo += "带标记ID的元素:\\n";
                    markerIds.forEach((el, index) => {
                        const id = el.getAttribute('data-marker-id');
                        const text = el.textContent || '(无文本)';
                        debugInfo += `${index+1}. ID: ${id}, 文本: ${text.substring(0, 30)}${text.length > 30 ? '...' : ''}\\n`;
                    });
                    debugInfo += "\\n";
                }
                
                // 输出一些文本元素样本
                if (markerElements.length > 0) {
                    const sampleSize = Math.min(5, markerElements.length);
                    debugInfo += `文本元素样本 (前${sampleSize}个):\\n`;
                    for (let i = 0; i < sampleSize; i++) {
                        const text = markerElements[i].textContent || '(无文本)';
                        debugInfo += `${i+1}. "${text.substring(0, 30)}${text.length > 30 ? '...' : ''}"\\n`;
                    }
                }
                
                // 检查事件监听器
                let eventInfo = "\\n事件监听器状态:\\n";
                if (window.priceChart._subscribers && window.priceChart._subscribers.crosshairMove) {
                    eventInfo += `十字线移动监听器: ${window.priceChart._subscribers.crosshairMove.length} 个\\n`;
                } else {
                    eventInfo += "未找到十字线移动监听器\\n";
                }
                
                if (window.priceChart._subscribers && window.priceChart._subscribers.click) {
                    eventInfo += `点击监听器: ${window.priceChart._subscribers.click.length} 个\\n`;
                } else {
                    eventInfo += "未找到点击监听器\\n";
                }
                
                // 添加标记显示诊断信息
                const navigationController = document.getElementById('navigation-controller');
                eventInfo += `\\n导航控制器状态: ${navigationController ? '已找到' : '未找到'}\\n`;
                if (navigationController) {
                    eventInfo += `显示状态: ${window.getComputedStyle(navigationController).display}\\n`;
                    eventInfo += `透明度: ${window.getComputedStyle(navigationController).opacity}\\n`;
                }
                
                // 创建修复按钮
                setTimeout(() => {
                    // 尝试修复可能的问题
                    const positionInfoElement = document.getElementById('position-info');
                    if (positionInfoElement) {
                        positionInfoElement.innerHTML = `
                            <div class="p-2 mb-2" style="background: rgba(38, 166, 154, 0.1); border-radius: 6px;">
                                <div class="d-flex justify-content-between align-items-center mb-1">
                                    <span class="fw-bold">调试信息</span>
                                    <span class="text-warning fw-bold">已激活</span>
                                </div>
                                <div class="small text-info">点击或悬停现在应该能正常工作</div>
                                <div class="text-center small fw-bold mt-1">
                                    自动修复已应用
                                </div>
                            </div>
                        `;
                    }
                    
                    // 确保导航面板可见
                    if (navigationController) {
                        navigationController.style.display = 'block';
                        navigationController.style.opacity = '1';
                    }
                    
                    // 输出到控制台以便进一步调试
                    console.log("调试信息:", debugInfo + eventInfo);
                }, 500);
                
                return debugInfo + eventInfo;
            } catch (error) {
                return `检查标记元素时出错: ${error.message}`;
            }
        }
        """,
        Output("debug-info-output", "children"),
        Input("debug-markers-button", "n_clicks"),
        prevent_initial_call=True
    )
    
    # 添加加载更多K线数据的回调
    @app.callback(
        [Output("chart-data-store", "data", allow_duplicate=True), 
         Output("status-info", "children", allow_duplicate=True)],
        [Input("load-more-trigger", "value")],
        [State("chart-data-store", "data"), 
         State("symbol-input", "value"), 
         State("timeframe-dropdown", "value"),
         State("end-date-picker", "date")],
        prevent_initial_call=True
    )
    def load_more_klines(trigger_value, current_chart_data, symbol, timeframe, end_date):
        # 强制打印调试信息
        print("========== 加载更多K线被触发 ==========")
        print(f"触发值: {trigger_value}")
        print(f"交易对: {symbol}, 周期: {timeframe}")
        
        if not trigger_value or trigger_value == 0 or not current_chart_data:
            print("触发值无效或没有现有数据，取消操作")
            return dash.no_update, dash.no_update
        
        logger.info(f"加载更多K线触发，当前触发值: {trigger_value}")
        
        try:
            # 解析当前图表数据
            chart_data = json.loads(current_chart_data)
            
            if not chart_data or not chart_data.get('candlestick', []):
                print("没有有效的K线数据可以扩展")
                return dash.no_update, html.Div("没有现有数据可以扩展", className="text-warning")
            
            # 获取当前数据的最后一个K线时间
            last_kline = chart_data['candlestick'][-1]
            last_timestamp = last_kline['time']
            
            # 如果是秒级时间戳，转换为毫秒
            if last_timestamp < 10000000000:
                last_timestamp = last_timestamp * 1000
                
            print(f"最后一根K线时间戳: {last_timestamp} ({pd.to_datetime(last_timestamp, unit='ms')})")
            logger.info(f"正在从时间 {last_timestamp} ({pd.to_datetime(last_timestamp, unit='ms')}) 加载更多K线")
            
            # 确保开始时间大于最后一个K线的时间，避免数据重叠
            since = last_timestamp + 1
            
            # 计算结束时间，默认向后加载一定数量的K线
            # 根据时间周期计算时间增量
            time_increment_map = {
                '1m': 1 * 60 * 1000,   # 1分钟，以毫秒计
                '5m': 5 * 60 * 1000,   # 5分钟
                '15m': 15 * 60 * 1000, # 15分钟
                '1h': 60 * 60 * 1000,  # 1小时
                '4h': 4 * 60 * 60 * 1000, # 4小时
                '1d': 24 * 60 * 60 * 1000, # 1天
            }
            
            time_increment = time_increment_map.get(timeframe, 60 * 60 * 1000)  # 默认1小时
            # 加载1000根K线以获取更多数据
            candles_to_load = 1000
            until = since + (time_increment * candles_to_load)
            
            # 如果until超过了当前时间，使用当前时间
            current_time = int(datetime.now().timestamp() * 1000)
            until = min(until, current_time)
            
            print(f"请求时间范围: {pd.to_datetime(since, unit='ms')} 到 {pd.to_datetime(until, unit='ms')}")
            logger.info(f"加载更多K线: 从 {pd.to_datetime(since, unit='ms')} 到 {pd.to_datetime(until, unit='ms')}")
            
            # 获取更多K线数据 - 直接从网络获取，不使用缓存
            try:
                # 确保交易对格式正确
                if ':' not in symbol and symbol.endswith('USDT'):
                    # 如果是U本位合约但没有正确格式，添加:USDT后缀
                    symbol = f"{symbol}:USDT"
                    print(f"调整交易对格式为: {symbol}")
                    logger.info(f"调整交易对格式为: {symbol}")
                
                # 初始化交易所
                print("正在初始化交易所...")
                exchange_instance = initialize_exchange()
                
                # 直接从交易所获取数据，跳过缓存检查
                params = {
                    'startTime': since,
                    'endTime': until
                }
                
                print(f"直接从交易所获取数据，参数: {params}")
                logger.info(f"直接从交易所获取数据，参数: {params}")
                
                # 获取数据
                print(f"正在调用交易所API: fetch_ohlcv({symbol}, {timeframe}, limit=1000, params={params})")
                all_ohlcv = exchange_instance.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=1000,  # 最大限制
                    params=params
                )
                
                print(f"成功从交易所获取了 {len(all_ohlcv)} 条新K线数据")
                logger.info(f"成功从交易所获取了 {len(all_ohlcv)} 条新K线数据")
                
                if not all_ohlcv or len(all_ohlcv) == 0:
                    print("没有找到更多K线数据")
                    return dash.no_update, html.Div("没有找到更多K线数据", className="text-warning p-2 border border-warning rounded")
                
                # 转换为DataFrame
                df_more = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # 转换时间戳为日期时间
                df_more['timestamp'] = pd.to_datetime(df_more['timestamp'], unit='ms')
                
                # 添加计算技术指标
                df_more = add_technical_indicators(df_more)
                
                print(f"已处理 {len(df_more)} 条新K线数据，时间范围: {df_more['timestamp'].min()} - {df_more['timestamp'].max()}")
                logger.info(f"已处理 {len(df_more)} 条新K线数据，时间范围: {df_more['timestamp'].min()} - {df_more['timestamp'].max()}")
                
                # 将新数据追加到现有缓存文件中，而不是创建新的缓存文件
                append_to_cache(symbol, timeframe, df_more)
            
            except Exception as e:
                print(f"直接从交易所获取数据失败: {str(e)}")
                logger.error(f"直接从交易所获取数据失败: {str(e)}")
                import traceback
                error_trace = traceback.format_exc()
                print(error_trace)
                logger.error(error_trace)
                
                # 尝试使用常规方法获取
                print("尝试使用常规方法获取数据...")
                # 这里修复一个问题：使用新初始化的exchange_instance而不是全局exchange
                df_more = fetch_ohlcv_data(exchange_instance, symbol, timeframe, since, until)
                
                # 如果获取成功，同样追加到现有缓存
                if not df_more.empty:
                    append_to_cache(symbol, timeframe, df_more)
            
            if df_more.empty:
                print("没有获取到更多K线数据")
                return dash.no_update, html.Div("没有更多K线数据可用", className="text-warning p-2 border border-warning rounded")
            
            # 准备新的K线数据
            more_chart_data = prepare_data_for_chart(df_more)
            
            # 检查获取的数据是否与现有数据连续
            print(f"现有数据最后一个K线时间戳: {last_timestamp}")
            print(f"新数据第一个K线时间戳: {df_more['timestamp'].iloc[0].timestamp() * 1000}")
            logger.info(f"现有数据最后一个K线时间戳: {last_timestamp}")
            logger.info(f"新数据第一个K线时间戳: {df_more['timestamp'].iloc[0].timestamp() * 1000}")
            
            # 合并数据 - 删除第一个元素以避免与最后一个K线重复
            new_items_added = 0
            for key in more_chart_data:
                if key in chart_data and isinstance(chart_data[key], list) and isinstance(more_chart_data[key], list):
                    # 记录合并前的数量
                    original_count = len(chart_data[key])
                    
                    # 跳过第一个元素以避免重复
                    chart_data[key].extend(more_chart_data[key][1:])
                    
                    # 记录新增的数量
                    new_items_added = len(chart_data[key]) - original_count
                    print(f"合并数据: {key} - 原始: {original_count}, 新增: {new_items_added}, 总计: {len(chart_data[key])}")
                    logger.info(f"合并数据: {key} - 原始: {original_count}, 新增: {new_items_added}, 总计: {len(chart_data[key])}")
            
            # 返回合并后的数据和状态信息
            if new_items_added > 0:
                status_info = html.Div(
                        f"已加载额外的 {new_items_added} 根K线数据，总计 {len(chart_data['candlestick'])} 根",
                    className="text-success p-2 border border-success rounded"
                )
                print(f"成功加载了 {new_items_added} 根新K线数据")
                return json.dumps(chart_data), status_info
            else:
                print("未找到新的K线数据")
                return dash.no_update, html.Div("未找到新的K线数据", className="text-warning p-2 border border-warning rounded")
            
        except Exception as e:
            print(f"加载更多K线数据出错: {str(e)}")
            logger.error(f"加载更多K线数据出错: {str(e)}")
            import traceback
            error_trace = traceback.format_exc()
            print(error_trace)
            logger.error(error_trace)
            return dash.no_update, html.Div(f"加载更多数据出错: {str(e)}", className="text-danger p-2 border border-danger rounded")
    
    # 添加辅助按钮的回调，用于确保"加载更多"功能正常工作
    @app.callback(
        [Output("chart-data-store", "data", allow_duplicate=True), 
         Output("status-info", "children", allow_duplicate=True)],
        [Input("load-more-helper-button", "n_clicks")],
        [State("chart-data-store", "data"), 
         State("symbol-input", "value"), 
         State("timeframe-dropdown", "value"),
         State("end-date-picker", "date")],
        prevent_initial_call=True
    )
    def load_more_klines_helper(n_clicks, current_chart_data, symbol, timeframe, end_date):
        """辅助函数，确保加载更多功能可以正常工作"""
        # 强制打印调试信息
        print("========== 辅助加载更多K线被触发 ==========")
        print(f"按钮点击: {n_clicks}")
        print(f"交易对: {symbol}, 周期: {timeframe}")
        
        if not n_clicks or not current_chart_data:
            print("按钮点击无效或没有现有数据，取消操作")
            return dash.no_update, dash.no_update
        
        logger.info(f"辅助按钮被点击，n_clicks: {n_clicks}")
        
        try:
            # 解析当前图表数据
            chart_data = json.loads(current_chart_data)
            
            if not chart_data or not chart_data.get('candlestick', []):
                print("[辅助] 没有有效的K线数据可以扩展")
                return dash.no_update, html.Div("没有现有数据可以扩展", className="text-warning")
            
            # 获取当前数据的最后一个K线时间
            last_kline = chart_data['candlestick'][-1]
            last_timestamp = last_kline['time']
            
            # 如果是秒级时间戳，转换为毫秒
            if last_timestamp < 10000000000:
                last_timestamp = last_timestamp * 1000
                
            print(f"[辅助] 最后一根K线时间戳: {last_timestamp} ({pd.to_datetime(last_timestamp, unit='ms')})")
            logger.info(f"[辅助] 正在从时间 {last_timestamp} ({pd.to_datetime(last_timestamp, unit='ms')}) 加载更多K线")
            
            # 确保开始时间大于最后一个K线的时间，避免数据重叠
            since = last_timestamp + 1
            
            # 这里我们把获取数据量提高到1000根
            candles_to_load = 1000
            
            # 计算结束时间
            time_increment_map = {
                '1m': 1 * 60 * 1000,   # 1分钟，以毫秒计
                '5m': 5 * 60 * 1000,   # 5分钟
                '15m': 15 * 60 * 1000, # 15分钟
                '1h': 60 * 60 * 1000,  # 1小时
                '4h': 4 * 60 * 60 * 1000, # 4小时
                '1d': 24 * 60 * 60 * 1000, # 1天
            }
            
            time_increment = time_increment_map.get(timeframe, 60 * 60 * 1000)  # 默认1小时
            until = since + (time_increment * candles_to_load)
            
            # 如果until超过了当前时间，使用当前时间
            current_time = int(datetime.now().timestamp() * 1000)
            until = min(until, current_time)
            
            print(f"[辅助] 请求时间范围: {pd.to_datetime(since, unit='ms')} 到 {pd.to_datetime(until, unit='ms')}")
            logger.info(f"[辅助] 加载更多K线: 从 {pd.to_datetime(since, unit='ms')} 到 {pd.to_datetime(until, unit='ms')}")
            
            # 获取更多K线数据 - 直接从网络获取，不使用缓存
            try:
                # 确保交易对格式正确
                if ':' not in symbol and symbol.endswith('USDT'):
                    # 如果是U本位合约但没有正确格式，添加:USDT后缀
                    symbol = f"{symbol}:USDT"
                    print(f"[辅助] 调整交易对格式为: {symbol}")
                    logger.info(f"[辅助] 调整交易对格式为: {symbol}")
                
                # 初始化交易所
                print("[辅助] 正在初始化交易所...")
                exchange_instance = initialize_exchange()
                
                # 直接从交易所获取数据，跳过缓存检查
                params = {
                    'startTime': since,
                    'endTime': until
                }
                
                print(f"[辅助] 直接从交易所获取数据，参数: {params}")
                logger.info(f"[辅助] 直接从交易所获取数据，参数: {params}")
                
                # 获取数据 - 使用更明确的参数
                print(f"[辅助] 正在调用交易所API: fetch_ohlcv({symbol}, {timeframe}, limit=1000, params={params})")
                all_ohlcv = exchange_instance.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=1000,  # 使用最大限制
                    params=params
                )
                
                print(f"[辅助] 成功从交易所获取了 {len(all_ohlcv)} 条新K线数据")
                logger.info(f"[辅助] 成功从交易所获取了 {len(all_ohlcv)} 条新K线数据")
                
                if not all_ohlcv or len(all_ohlcv) == 0:
                    print("[辅助] 没有找到更多K线数据")
                    return dash.no_update, html.Div("[辅助] 没有找到更多K线数据", className="text-warning p-2 border border-warning rounded")
                
                # 转换为DataFrame
                df_more = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # 转换时间戳为日期时间
                df_more['timestamp'] = pd.to_datetime(df_more['timestamp'], unit='ms')
                
                # 添加计算技术指标
                df_more = add_technical_indicators(df_more)
                
                print(f"[辅助] 已处理 {len(df_more)} 条新K线数据，时间范围: {df_more['timestamp'].min()} - {df_more['timestamp'].max()}")
                logger.info(f"[辅助] 已处理 {len(df_more)} 条新K线数据，时间范围: {df_more['timestamp'].min()} - {df_more['timestamp'].max()}")
                
                # 将新数据追加到现有缓存文件中，而不是创建新的缓存文件
                append_to_cache(symbol, timeframe, df_more)
            
            except Exception as e:
                print(f"[辅助] 直接从交易所获取数据失败: {str(e)}")
                logger.error(f"[辅助] 直接从交易所获取数据失败: {str(e)}")
                import traceback
                error_trace = traceback.format_exc()
                print(error_trace)
                logger.error(error_trace)
                
                # 尝试使用常规方法获取
                print("[辅助] 尝试使用常规方法获取数据...")
                # 使用新初始化的exchange_instance而不是全局exchange
                df_more = fetch_ohlcv_data(exchange_instance, symbol, timeframe, since, until)
            
            if df_more.empty:
                print("[辅助] 没有获取到更多K线数据")
                return dash.no_update, html.Div("[辅助] 没有更多K线数据可用", className="text-warning p-2 border border-warning rounded")
            
            # 准备新的K线数据
            more_chart_data = prepare_data_for_chart(df_more)
            
            # 检查获取的数据是否与现有数据连续
            print(f"[辅助] 现有数据最后一个K线时间戳: {last_timestamp}")
            print(f"[辅助] 新数据第一个K线时间戳: {df_more['timestamp'].iloc[0].timestamp() * 1000}")
            logger.info(f"[辅助] 现有数据最后一个K线时间戳: {last_timestamp}")
            logger.info(f"[辅助] 新数据第一个K线时间戳: {df_more['timestamp'].iloc[0].timestamp() * 1000}")
            
            # 合并数据 - 删除第一个元素以避免与最后一个K线重复
            new_items_added = 0
            for key in more_chart_data:
                if key in chart_data and isinstance(chart_data[key], list) and isinstance(more_chart_data[key], list):
                    # 记录合并前的数量
                    original_count = len(chart_data[key])
                    
                    # 跳过第一个元素以避免重复
                    chart_data[key].extend(more_chart_data[key][1:])
                    
                    # 记录新增的数量
                    new_items_added = len(chart_data[key]) - original_count
                    print(f"[辅助] 合并数据: {key} - 原始: {original_count}, 新增: {new_items_added}, 总计: {len(chart_data[key])}")
                    logger.info(f"[辅助] 合并数据: {key} - 原始: {original_count}, 新增: {new_items_added}, 总计: {len(chart_data[key])}")
            
            # 返回合并后的数据和状态信息
            if new_items_added > 0:
                status_info = html.Div(
                    f"已加载额外的 {new_items_added} 根K线数据，总计 {len(chart_data['candlestick'])} 根",
                    className="text-success p-2 border border-success rounded"
                )
                print(f"[辅助] 成功加载了 {new_items_added} 根新K线数据")
                
                # 更新加载更多触发器的值
                try:
                    trigger = html.Div(id="load-more-trigger", children=f"{n_clicks}")
                    print(f"[辅助] 更新了load-more-trigger值为: {n_clicks}")
                except Exception as e:
                    print(f"[辅助] 更新load-more-trigger值失败: {str(e)}")
                    
                return json.dumps(chart_data), status_info
            else:
                print("[辅助] 未找到新的K线数据")
                return dash.no_update, html.Div("[辅助] 未找到新的K线数据", className="text-warning p-2 border border-warning rounded")
            
        except Exception as e:
            print(f"[辅助] 加载更多K线数据出错: {str(e)}")
            logger.error(f"[辅助] 加载更多K线数据出错: {str(e)}")
            import traceback
            error_trace = traceback.format_exc()
            print(error_trace)
            logger.error(error_trace)
            return dash.no_update, html.Div(f"[辅助] 加载更多数据出错: {str(e)}", className="text-danger p-2 border border-danger rounded")
    
    return app

if __name__ == "__main__":
    app = create_app()
    # 允许局域网访问：host='0.0.0.0' 表示监听所有网络接口
    app.run(debug=True, host='0.0.0.0', port=8051)