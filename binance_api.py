import ccxt
import pandas as pd
from datetime import datetime
import time
from config import BINANCE_API_KEY, BINANCE_API_SECRET, PROXY_CONFIG

class BinanceAPI:
    """处理与币安API的交互"""
    
    def __init__(self, market_type='future'):
        """
        初始化币安交易所连接
        
        参数:
            market_type (str): 市场类型，'spot'为现货，'future'为合约/期货
        """
        # 创建交易所实例
        self.exchange = ccxt.binance({
            'apiKey': BINANCE_API_KEY,
            'secret': BINANCE_API_SECRET,
            'enableRateLimit': True,
            'timeout': 30000,  # 超时时间设置为30秒
            'proxies': PROXY_CONFIG,
            'options': {
                'defaultType': market_type,  # 设置为future可用于期货/合约交易
                'adjustForTimeDifference': True,
                'recvWindow': 60000,
                'warnOnFetchOHLCVLimitArgument': False,
            },
            'headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        })
        
        self.market_type = market_type
        # 测试网络连接
        self._init_connection()
    
    def _init_connection(self):
        """初始化连接并测试"""
        try:
            print("正在初始化币安API连接...")
            # 加载市场数据
            self.exchange.load_markets()
            print(f"成功加载市场数据，支持的交易对数量: {len(self.exchange.symbols)}")
        except Exception as e:
            print(f"初始化连接时出错: {e}")
    
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
            # 获取OHLCV数据
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
            print(f"获取价格历史时出错: {e}")
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
            print(f"正在获取{self.market_type}交易记录，交易对: {symbol}")
            
            # 确保使用正确的市场类型
            if self.market_type == 'future':
                # 对于期货市场，需要特殊处理
                params = {'type': 'future'}
                # 获取期货交易记录
                trades = self.exchange.fetch_my_trades(symbol=symbol, since=since, limit=limit, params=params)
            else:
                # 获取现货交易记录
                trades = self.exchange.fetch_my_trades(symbol=symbol, since=since, limit=limit)
            
            if not trades:
                print(f"未找到交易记录")
                return pd.DataFrame()
            
            print(f"找到 {len(trades)} 条交易记录")
            
            # 提取需要的字段并转换为DataFrame
            trades_data = []
            for trade in trades:
                # 打印原始交易数据进行调试
                print(f"处理交易记录: {trade['id']}")
                
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
                if self.market_type == 'future':
                    # 可能需要根据实际API返回调整
                    trade_data['position_side'] = trade.get('info', {}).get('positionSide', 'BOTH')
                    trade_data['realized_pnl'] = float(trade.get('info', {}).get('realizedPnl', 0))
                
                trades_data.append(trade_data)
            
            df = pd.DataFrame(trades_data)
            
            # 将时间戳转换为日期时间
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                
            return df
            
        except Exception as e:
            print(f"获取交易记录时出错: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()
    
    def get_account_balance(self):
        """
        获取账户余额
        
        返回:
            pandas.DataFrame: 包含账户余额的数据框
        """
        try:
            # 获取余额
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
            print(f"获取账户余额时出错: {e}")
            return pd.DataFrame()
    
    def get_available_symbols(self):
        """
        获取可用的交易对列表
        
        返回:
            list: 可用的交易对列表
        """
        try:
            markets = self.exchange.load_markets()
            symbols = [market for market in markets.keys() if '/USDT' in market]
            return sorted(symbols)
        except Exception as e:
            print(f"获取可用交易对时出错: {e}")
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
                print(f"尝试连接币安API... (尝试 {attempt+1}/{max_retries})")
                # 使用fetch_status来测试连接
                status = self.exchange.fetch_status()
                if status.get('status') == 0 or status.get('status') == 'ok':
                    print("币安API连接成功!")
                    print(f"状态: {status}")
                    return True
                else:
                    print(f"币安系统状态: {status}")
            except ccxt.NetworkError as e:
                print(f"网络错误: {str(e)}")
            except ccxt.ExchangeError as e:
                print(f"交易所错误: {str(e)}")
            except Exception as e:
                print(f"连接测试失败: {str(e)}")
                
            if attempt < max_retries - 1:
                print(f"等待 {retry_delay} 秒后重试...")
                time.sleep(retry_delay)
                retry_delay *= 2  # 指数级增加重试延迟
                
        print("所有连接尝试均失败")
        return False 