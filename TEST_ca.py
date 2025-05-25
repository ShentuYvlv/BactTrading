#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import ccxt
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

# 设置代理环境变量
os.environ['HTTP_PROXY'] = 'socks5://127.0.0.1:10808'
os.environ['HTTPS_PROXY'] = 'socks5://127.0.0.1:10808'
os.environ['ALL_PROXY'] = 'socks5://127.0.0.1:10808'

# 防止Python 3.8中的事件循环关闭警告
if sys.platform.startswith('win'):
    # Windows系统特定修复
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger(__name__)

def main():
    """主函数 - 最简化版本，只进行连接测试和获取当前仓位"""
    print("======== 币安CCXT连接测试 ========")
    
    # 从环境变量中获取API密钥
    API_KEY = os.getenv('BINANCE_API_KEY')
    API_SECRET = os.getenv('BINANCE_API_SECRET')
    
    if API_KEY and API_SECRET:
        print(f"已从.env文件中读取API密钥")
        # 打印部分密钥用于确认（只显示前5位和后5位）
        masked_key = API_KEY[:5] + "..." + API_KEY[-5:]
        masked_secret = API_SECRET[:5] + "..." + API_SECRET[-5:]
        print(f"API密钥: {masked_key}")
        print(f"API密钥密钥: {masked_secret}")
    else:
        print("未能从.env文件中读取API密钥，将以只读模式运行")
    
    # 创建交易所实例
    config = {
        'enableRateLimit': True,
        'timeout': 60000,
        'proxies': {
            'http': 'socks5://127.0.0.1:10808',
            'https': 'socks5://127.0.0.1:10808'
        },
        'options': {
            'defaultType': 'future',  # 默认使用合约市场
            'adjustForTimeDifference': True,  # 自动调整时间差
            'recvWindow': 60000,
        },
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
    }
    
    # 如果提供了API密钥，添加到配置中
    if API_KEY and API_SECRET:
        config['apiKey'] = API_KEY
        config['secret'] = API_SECRET
    
    try:
        # 创建交易所实例
        exchange = ccxt.binance(config)
        
        # 同步服务器时间（重要！）
        print("正在同步服务器时间...")
        exchange.load_time_difference()
        server_time = exchange.fetch_time()
        local_time = int(time.time() * 1000)
        time_diff = server_time - local_time
        print(f"服务器时间: {server_time} ms")
        print(f"本地时间: {local_time} ms")
        print(f"时间差: {time_diff} ms")
        
        # 测试连接 - 获取服务器时间
        print("\n===== 测试连接 =====")
        print(f"连接测试成功！服务器时间: {server_time}")
        
        # 如果提供了API密钥，尝试获取当前仓位
        if API_KEY and API_SECRET:
            print("\n===== 获取当前仓位 =====")
            
            # 加载市场数据
            exchange.load_markets()
            
            # 获取当前仓位
            # positions = exchange.fetch_positions()
            
            # if positions:
            #     print(f"找到 {len(positions)} 个持仓:")
            #     for pos in positions:
            #         if float(pos['contracts']) > 0:  # 只显示有持仓的
            #             symbol = pos['symbol']
            #             side = "多" if pos['side'] == 'long' else "空"
            #             size = pos['contracts']
            #             entry_price = pos['entryPrice']
            #             leverage = pos['leverage']
            #             unrealized_pnl = pos['unrealizedPnl']
            #             print(f"{symbol}: {side}仓 {size}张 入场价:{entry_price} 杠杆:{leverage}x 未实现盈亏:{unrealized_pnl}")
            # else:
            #     print("当前没有持仓")
                
            # 获取账户余额
            print("\n===== 获取账户余额 =====")
            balance = exchange.fetch_balance()
            
            # 提取USDT余额
            if 'USDT' in balance:
                usdt_free = balance['USDT']['free']
                usdt_used = balance['USDT']['used']
                usdt_total = balance['USDT']['total']
                print(f"USDT余额: 可用={usdt_free}, 已用={usdt_used}, 总计={usdt_total}")
            else:
                print("未找到USDT余额")
            
            # 显示可用方法
            # print("\n===== 交易所支持的方法 =====")
            # print("支持的方法:")
            # for method_name, supported in exchange.has.items():
            #     if supported and ('trade' in method_name.lower() or 'position' in method_name.lower()):
            #         print(f"- {method_name}: {supported}")
        
    except Exception as e:
        print(f"错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
