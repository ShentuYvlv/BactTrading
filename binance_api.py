import ccxt
import pandas as pd
from datetime import datetime
import time
import logging
import traceback
from config import BINANCE_API_KEY, BINANCE_API_SECRET, PROXY_CONFIG

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BinanceAPI:
    """处理与币安API的交互"""
    
    def __init__(self, market_type='future'):
        """
        初始化币安交易所连接
        
        参数:
            market_type (str): 市场类型，'spot'为现货，'future'为合约/期货
        """
        self.market_type = market_type
        self.exchange = None
        self.initialized = False
        
        # 初始化交易所连接
        self.initialize()
    
    def initialize(self):
        """初始化交易所连接，使用TEST_ca.py中的方式"""
        try:
            # 设置币安交易所配置
            config = {
                'enableRateLimit': True,
                'timeout': 60000,  # 超时时间设置为60秒
                'proxies': {
                    'http': 'socks5://127.0.0.1:10808',
                    'https': 'socks5://127.0.0.1:10808'
                },
                'options': {
                    'defaultType': self.market_type,  # 市场类型: 'spot' 或 'future'
                    'adjustForTimeDifference': True,
                    'recvWindow': 60000,  # 增加接收窗口
                    'warnOnFetchOHLCVLimitArgument': False,
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
            
            # 添加API密钥（如果有）
            if BINANCE_API_KEY and BINANCE_API_SECRET:
                config['apiKey'] = BINANCE_API_KEY
                config['secret'] = BINANCE_API_SECRET
                logger.info("已连接到币安交易所，并使用API密钥进行认证")
            else:
                logger.warning("未提供API密钥，将以只读模式运行")
            
            # 创建交易所实例
            self.exchange = ccxt.binance(config)
            
            # 先获取服务器时间进行测试
            server_time = self.exchange.fetch_time()
            local_time = int(time.time() * 1000)
            time_diff = abs(server_time - local_time)
            
            logger.info(f"连接测试成功！")
            logger.info(f"服务器时间: {server_time} ms")
            logger.info(f"本地时间: {local_time} ms")
            logger.info(f"时间差: {time_diff} ms")
            
            # 加载市场数据
            self.exchange.load_markets()
            logger.info(f"成功加载市场数据，支持的交易对数量: {len(self.exchange.symbols)}")
            
            self.initialized = True
            return True
        except Exception as e:
            logger.error(f"初始化币安API失败: {str(e)}")
            logger.error(traceback.format_exc())
            return False
    
    def get_price_history(self, symbol, timeframe, since=None, limit=500):
        """
        获取价格历史数据
        
        参数:
            symbol (str): 交易对，如'BTC/USDT'
            timeframe (str): 时间周期，如'1m', '1h', '1d'
            since (int): 开始时间的时间戳（毫秒）
            limit (int): 返回数据点的最大数量
            
        返回:
            pandas.DataFrame: 包含价格历史的数据框
        """
        try:
            # 获取OHLCV数据 - 使用标准CCXT方法
            ohlcv = self.exchange.fetch_ohlcv(
                symbol=symbol, 
                timeframe=timeframe,
                since=since,
                limit=limit
            )
            
            # 转换为DataFrame
            df = pd.DataFrame(
                ohlcv, 
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            
            # 将时间戳转换为日期时间
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
            
        except Exception as e:
            logger.error(f"获取价格历史时出错: {e}")
            logger.error(traceback.format_exc())
            return pd.DataFrame()
    
    def get_my_trades(self, symbol, since=None, limit=100):
        """
        获取用户的交易记录
        
        参数:
            symbol (str): 交易对，如'BTC/USDT'
            since (int): 开始时间的时间戳（毫秒）
            limit (int): 返回交易记录的最大数量
            
        返回:
            pandas.DataFrame: 包含用户交易记录的数据框
        """
        try:
            logger.info(f"正在获取{self.market_type}交易记录，交易对: {symbol}")
            
            # 使用标准CCXT方法获取交易记录
            trades = self.exchange.fetch_my_trades(symbol=symbol, since=since, limit=limit)
            
            if not trades:
                logger.info(f"未找到{symbol}的交易记录")
                return pd.DataFrame()
            
            logger.info(f"找到 {len(trades)} 条交易记录")
            
            # 提取需要的字段并转换为DataFrame
            trades_data = []
            for trade in trades:
                # 打印调试信息
                logger.debug(f"处理交易记录: {trade['id']}")
                
                trade_data = {
                    'id': trade['id'],
                    'timestamp': trade['timestamp'],
                    'datetime': trade['datetime'],
                    'symbol': trade['symbol'],
                    'side': trade['side'],  # 'buy' 或 'sell'
                    'price': trade['price'],
                    'amount': trade['amount'],
                    'cost': trade['cost'],
                }
                
                # 处理手续费
                if 'fee' in trade and trade['fee']:
                    trade_data['fee'] = trade['fee']['cost'] if 'cost' in trade['fee'] else 0
                    trade_data['fee_currency'] = trade['fee']['currency'] if 'currency' in trade['fee'] else ''
                else:
                    trade_data['fee'] = 0
                    trade_data['fee_currency'] = ''
                
                # 添加其他期货特有字段
                if self.market_type == 'future' and 'info' in trade:
                    info = trade['info']
                    # 添加仓位方向
                    trade_data['position_side'] = info.get('positionSide', 'BOTH') if info else 'BOTH'
                    # 添加实现盈亏
                    trade_data['realized_pnl'] = float(info.get('realizedPnl', 0)) if info else 0
                    # 记录原始信息用于调试
                    logger.debug(f"期货交易原始信息: {info}")
                
                trades_data.append(trade_data)
            
            df = pd.DataFrame(trades_data)
            
            # 将时间戳转换为日期时间
            if 'timestamp' in df.columns and not df.empty:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                
            return df
            
        except Exception as e:
            logger.error(f"获取交易记录时出错: {e}")
            logger.error(traceback.format_exc())
            return pd.DataFrame()
    
    def get_account_balance(self):
        """
        获取账户余额
        
        返回:
            pandas.DataFrame: 包含账户余额的数据框
        """
        try:
            # 使用标准CCXT方法获取余额
            balance = self.exchange.fetch_balance()
            
            # 提取非零余额
            non_zero = {
                currency: data for currency, data in balance['total'].items() 
                if data > 0
            }
            
            # 转换为DataFrame
            df = pd.DataFrame([
                {'currency': currency, 'total': amount} 
                for currency, amount in non_zero.items()
            ])
            
            return df.sort_values(by='total', ascending=False).reset_index(drop=True)
            
        except Exception as e:
            logger.error(f"获取账户余额时出错: {e}")
            logger.error(traceback.format_exc())
            return pd.DataFrame()
    
    def get_positions(self):
        """
        获取当前持仓信息
        
        返回:
            pandas.DataFrame: 包含持仓信息的数据框
        """
        try:
            # 使用标准CCXT方法获取持仓
            positions = self.exchange.fetch_positions()
            
            # 将持仓信息转换为DataFrame
            pos_data = []
            for pos in positions:
                # 只包含有仓位的数据
                contracts = float(pos.get('contracts', 0))
                if abs(contracts) > 0:
                    pos_data.append({
                        'symbol': pos.get('symbol', ''),
                        'side': pos.get('side', ''),
                        'contracts': contracts,
                        'entry_price': float(pos.get('entryPrice', 0)),
                        'mark_price': float(pos.get('markPrice', 0)),
                        'unrealized_pnl': float(pos.get('unrealizedPnl', 0)),
                        'leverage': float(pos.get('leverage', 1))
                    })
            
            if pos_data:
                return pd.DataFrame(pos_data)
            else:
                logger.info("当前没有活跃持仓")
                return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"获取持仓信息时出错: {e}")
            logger.error(traceback.format_exc())
            return pd.DataFrame()
    
    def get_funding_rates(self, symbols=None):
        """
        获取资金费率
        
        参数:
            symbols (list): 交易对列表，如果为None则获取所有支持的交易对
            
        返回:
            pandas.DataFrame: 包含资金费率的数据框
        """
        try:
            # 如果没有指定交易对，则使用加载的合约交易对
            if symbols is None:
                markets = self.exchange.load_markets()
                # 筛选出合约交易对
                symbols = [symbol for symbol in markets.keys() if '/USDT:USDT' in symbol]
                symbols = symbols[:10]  # 为避免请求过多，仅获取前10个
            
            # 使用标准CCXT方法获取资金费率
            funding_rates = self.exchange.fetch_funding_rates(symbols)
            
            # 转换为DataFrame
            rates_data = []
            for symbol, rate_info in funding_rates.items():
                # 获取下次资金费率结算时间
                next_funding_time = rate_info.get('nextFundingTime', 0)
                next_funding_time_str = datetime.fromtimestamp(next_funding_time/1000).strftime('%Y-%m-%d %H:%M:%S') if next_funding_time else 'N/A'
                
                rates_data.append({
                    'symbol': symbol,
                    'funding_rate': rate_info.get('fundingRate', 0) * 100,  # 转为百分比
                    'next_funding_time': next_funding_time,
                    'next_funding_time_str': next_funding_time_str
                })
            
            return pd.DataFrame(rates_data)
        
        except Exception as e:
            logger.error(f"获取资金费率时出错: {e}")
            logger.error(traceback.format_exc())
            return pd.DataFrame()
    
    def get_available_symbols(self):
        """
        获取可用的交易对列表
        
        返回:
            list: 可用的交易对列表
        """
        try:
            markets = self.exchange.load_markets()
            
            # 根据市场类型筛选交易对
            if self.market_type == 'future':
                # 获取期货交易对，在币安中通常以/USDT结尾
                symbols = [market for market in markets.keys() if '/USDT:USDT' in market]
            else:
                # 获取现货交易对
                symbols = [market for market in markets.keys() if '/USDT' in market and ':' not in market]
                
            return sorted(symbols)
        except Exception as e:
            logger.error(f"获取可用交易对时出错: {e}")
            logger.error(traceback.format_exc())
            return []
            
    def test_connection(self):
        """
        测试API连接是否正常
        
        返回:
            bool: 连接成功返回True，否则返回False
        """
        max_retries = 3
        retry_delay = 2  # 秒
        
        for attempt in range(max_retries):
            try:
                logger.info(f"尝试连接币安API... (尝试 {attempt+1}/{max_retries})")
                
                # 使用标准CCXT方法测试连接
                server_time = self.exchange.fetch_time()
                local_time = int(time.time() * 1000)
                time_diff = abs(server_time - local_time)
                
                # 获取BTC/USDT的价格作为API连接测试
                if self.market_type == 'future':
                    ticker = self.exchange.fetch_ticker('BTC/USDT:USDT')
                else:
                    ticker = self.exchange.fetch_ticker('BTC/USDT')
                    
                logger.info(f"BTC/USDT 当前价格: {ticker['last']} USDT")
                logger.info(f"币安API连接成功! 服务器时间: {datetime.fromtimestamp(server_time/1000).strftime('%Y-%m-%d %H:%M:%S')}")
                logger.info(f"时间差: {time_diff} ms")
                
                # 获取交易所状态
                status = self.exchange.fetch_status()
                logger.info(f"交易所状态: {status.get('status', '')}")
                
                return True
            except ccxt.NetworkError as e:
                logger.error(f"网络错误: {str(e)}")
            except ccxt.ExchangeError as e:
                logger.error(f"交易所错误: {str(e)}")
            except Exception as e:
                logger.error(f"连接测试失败: {str(e)}")
                
            if attempt < max_retries - 1:
                logger.info(f"等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
                retry_delay *= 2  # 指数级增加重试延迟
                
        logger.error("所有连接尝试均失败")
        return False 