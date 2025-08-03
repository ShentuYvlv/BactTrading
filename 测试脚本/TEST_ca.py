#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import ccxt
import time
import logging
import ssl
import urllib3
from datetime import datetime
from dotenv import load_dotenv

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 加载.env文件中的环境变量
load_dotenv()

# 设置代理环境变量（先注释掉，测试直连）
# os.environ['HTTP_PROXY'] = 'socks5://127.0.0.1:10808'
# os.environ['HTTPS_PROXY'] = 'socks5://127.0.0.1:10808'
# os.environ['ALL_PROXY'] = 'socks5://127.0.0.1:10808'

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

def test_connection_with_proxy():
    """使用代理的连接测试"""
    print("\n===== 测试代理连接 =====")
    
    # 从环境变量中获取API密钥
    API_KEY = os.getenv('BINANCE_API_KEY')
    API_SECRET = os.getenv('BINANCE_API_SECRET')
    
    config = {
        'enableRateLimit': True,
        'timeout': 60000,
        'proxies': {
            'http': 'socks5://127.0.0.1:10808',
            'https': 'socks5://127.0.0.1:10808'
        },
        'options': {
            'defaultType': 'future',
            'adjustForTimeDifference': True,
            'recvWindow': 60000,
        },
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        },
        'verify': False,  # 禁用SSL证书验证
    }
    
    if API_KEY and API_SECRET:
        config['apiKey'] = API_KEY
        config['secret'] = API_SECRET
    
    try:
        exchange = ccxt.binance(config)
        exchange.load_time_difference()
        server_time = exchange.fetch_time()
        print(f"代理连接成功！服务器时间: {server_time}")
        return exchange
    except Exception as e:
        print(f"代理连接失败: {str(e)}")
        return None

def test_connection_direct():
    """直连测试"""
    print("\n===== 测试直连 =====")
    
    # 从环境变量中获取API密钥
    API_KEY = os.getenv('BINANCE_API_KEY')
    API_SECRET = os.getenv('BINANCE_API_SECRET')
    
    config = {
        'enableRateLimit': True,
        'timeout': 60000,
        'options': {
            'defaultType': 'future',
            'adjustForTimeDifference': True,
            'recvWindow': 60000,
        },
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        },
        'verify': False,  # 禁用SSL证书验证
    }
    
    if API_KEY and API_SECRET:
        config['apiKey'] = API_KEY
        config['secret'] = API_SECRET
    
    try:
        exchange = ccxt.binance(config)
        exchange.load_time_difference()
        server_time = exchange.fetch_time()
        print(f"直连成功！服务器时间: {server_time}")
        return exchange
    except Exception as e:
        print(f"直连失败: {str(e)}")
        return None

def main():
    """主函数 - 增强版本，尝试多种连接方式"""
    print("======== 币安CCXT连接测试（增强版） ========")
    
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
    
    # 尝试不同的连接方式
    exchange = None
    
    # 1. 先尝试直连
    exchange = test_connection_direct()
    
    # 2. 如果直连失败，再尝试代理连接
    if exchange is None:
        exchange = test_connection_with_proxy()
    
    # 3. 如果都失败了，给出诊断建议
    if exchange is None:
        print("\n===== 连接诊断建议 =====")
        print("所有连接方式都失败了，可能的原因：")
        print("1. 网络连接问题")
        print("2. 代理服务器(127.0.0.1:10808)未运行")
        print("3. 防火墙阻止连接")
        print("4. 币安API服务器暂时不可用")
        print("\n建议操作：")
        print("1. 检查网络连接")
        print("2. 确认代理软件是否正常运行")
        print("3. 尝试重启代理软件")
        print("4. 稍后再试")
        return
    
    # 连接成功，继续执行其他操作
    try:
        print(f"\n===== 连接成功，服务器时间同步 =====")
        server_time = exchange.fetch_time()
        local_time = int(time.time() * 1000)
        time_diff = server_time - local_time
        print(f"服务器时间: {server_time} ms")
        print(f"本地时间: {local_time} ms")
        print(f"时间差: {time_diff} ms")
        
        # 如果提供了API密钥，尝试获取账户信息
        if API_KEY and API_SECRET:
            print("\n===== 获取账户余额 =====")
            
            # 加载市场数据
            exchange.load_markets()
            
            # 获取账户余额
            balance = exchange.fetch_balance()
            
            # 提取USDT余额
            if 'USDT' in balance:
                usdt_free = balance['USDT']['free']
                usdt_used = balance['USDT']['used']
                usdt_total = balance['USDT']['total']
                print(f"USDT余额: 可用={usdt_free}, 已用={usdt_used}, 总计={usdt_total}")
            else:
                print("未找到USDT余额")
        
        print("\n===== 测试完成 =====")
        print("连接测试成功！")
        
    except Exception as e:
        print(f"获取账户信息时发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
