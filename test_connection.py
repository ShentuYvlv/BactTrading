#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import ccxt
import time
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 设置代理环境变量
os.environ['HTTP_PROXY'] = 'socks5://127.0.0.1:10808'
os.environ['HTTPS_PROXY'] = 'socks5://127.0.0.1:10808'
os.environ['ALL_PROXY'] = 'socks5://127.0.0.1:10808'

# 获取API密钥
API_KEY = os.getenv('BINANCE_API_KEY')
API_SECRET = os.getenv('BINANCE_API_SECRET')

def test_binance_connection(market_type='future'):
    """测试与币安的连接"""
    print(f"=== 测试币安API连接 (市场类型: {market_type}) ===")
    
    # 打印代理设置
    print(f"HTTP_PROXY: {os.environ.get('HTTP_PROXY')}")
    print(f"HTTPS_PROXY: {os.environ.get('HTTPS_PROXY')}")
    print(f"ALL_PROXY: {os.environ.get('ALL_PROXY')}")
    
    # 创建币安交易所实例
    exchange = ccxt.binance({
        'apiKey': API_KEY,
        'secret': API_SECRET,
        'enableRateLimit': True,
        'timeout': 30000,  # 超时时间设置为30秒
        'proxies': {
            'http': 'socks5://127.0.0.1:10808',
            'https': 'socks5://127.0.0.1:10808'
        },
        'options': {
            'defaultType': market_type,  # 市场类型: 'spot' 或 'future'
            'adjustForTimeDifference': True,
            'recvWindow': 60000,
            'warnOnFetchOHLCVLimitArgument': False,
        },
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    })
    
    try:
        print("\n1. 加载市场数据...")
        markets = exchange.load_markets()
        print(f"成功! 加载了 {len(exchange.symbols)} 个交易对")
        
        print("\n2. 获取BTC/USDT的价格...")
        ticker = exchange.fetch_ticker('BTC/USDT')
        print(f"BTC/USDT 当前价格: {ticker['last']}")
        
        print("\n3. 检查服务器状态...")
        status = exchange.fetch_status()
        print(f"服务器状态: {status}")
        
        if API_KEY and API_SECRET:
            if market_type == 'future':
                print("\n4. 获取合约账户信息 (需要API密钥)...")
                balance = exchange.fetch_balance()
                print("合约账户信息获取成功!")
                
                print("\n5. 获取合约交易历史 (需要API密钥)...")
                try:
                    trades = exchange.fetch_my_trades('BTC/USDT', limit=5, params={'type': 'future'})
                    print(f"获取到 {len(trades)} 条合约交易记录")
                    if trades:
                        print("\n合约交易记录样例:")
                        print(f"ID: {trades[0]['id']}")
                        print(f"时间: {trades[0]['datetime']}")
                        print(f"方向: {trades[0]['side']}")
                        print(f"价格: {trades[0]['price']}")
                        print(f"数量: {trades[0]['amount']}")
                        print(f"成本: {trades[0]['cost']}")
                        if 'info' in trades[0]:
                            print(f"原始信息: {trades[0]['info']}")
                except Exception as e:
                    print(f"获取合约交易历史时出错: {e}")
            else:
                print("\n4. 获取现货账户余额 (需要API密钥)...")
                balance = exchange.fetch_balance()
                print("余额获取成功!")
                
                print("\n5. 获取现货交易历史 (需要API密钥)...")
                trades = exchange.fetch_my_trades('BTC/USDT', limit=5)
                print(f"获取到 {len(trades)} 条交易记录")
        else:
            print("\n4+5. 跳过获取余额和交易历史 (未提供API密钥)")
        
        print("\n=== 连接测试成功! ===")
        return True
        
    except ccxt.NetworkError as e:
        print(f"\n网络错误: {e}")
    except ccxt.ExchangeError as e:
        print(f"\n交易所错误: {e}")
    except Exception as e:
        print(f"\n其他错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== 连接测试失败! ===")
    return False

if __name__ == "__main__":
    # 检查Python版本
    py_version = sys.version.split()[0]
    print(f"Python 版本: {py_version}")
    print(f"CCXT 版本: {ccxt.__version__}")
    
    # 测试现货连接
    print("\n========== 测试现货市场连接 ==========")
    spot_success = test_binance_connection(market_type='spot')
    
    # 测试合约连接
    print("\n========== 测试合约市场连接 ==========")
    future_success = test_binance_connection(market_type='future')
    
    # 总结测试结果
    print("\n========== 测试结果汇总 ==========")
    print(f"现货市场连接: {'成功' if spot_success else '失败'}")
    print(f"合约市场连接: {'成功' if future_success else '失败'}")
    
    # 等待用户按键以防止窗口立即关闭
    if sys.platform.startswith('win'):
        input("\n按Enter键退出...")
        
    # 设置退出代码
    sys.exit(0 if spot_success and future_success else 1) 