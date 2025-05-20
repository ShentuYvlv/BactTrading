#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import ccxt
import time
import logging
import traceback
import dotenv

# 加载.env文件中的环境变量
dotenv.load_dotenv()

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
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def test_connection(api_key=None, api_secret=None):
    """测试与币安的连接"""
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
                'defaultType': 'future',  # 使用U本位永续合约
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
        
        # 如果提供了API密钥，添加到配置中
        if api_key and api_secret:
            config['apiKey'] = api_key
            config['secret'] = api_secret
            logger.info("使用API密钥认证")
        else:
            logger.warning("未提供API密钥，将以只读模式运行")
        
        # 创建交易所实例
        exchange = ccxt.binance(config)
        
        # 先获取服务器时间进行测试 - 公开API调用
        logger.info("获取服务器时间...")
        server_time = exchange.fetch_time()
        local_time = int(time.time() * 1000)
        time_diff = abs(server_time - local_time)
        
        logger.info(f"连接测试成功！")
        logger.info(f"服务器时间: {server_time} ms")
        logger.info(f"本地时间: {local_time} ms")
        logger.info(f"时间差: {time_diff} ms")
        
        # 获取单个交易对的价格 - 公开API调用，不加载全部市场数据
        logger.info("获取BTC/USDT价格信息...")
        ticker = exchange.fetch_ticker('BTC/USDT:USDT')
        logger.info(f"BTC/USDT 最新价格: {ticker['last']} USDT")
        
        # 如果提供了API密钥，进行私有API调用测试
        if api_key and api_secret:
            try:
                logger.info("\n===== 使用API密钥，开始测试私有API调用 =====")
                
                # 使用CCXT的标准方法获取账户余额
                logger.info("获取账户余额...")
                balance = exchange.fetch_balance()
                
                # 提取USDT余额
                usdt_free = balance['USDT']['free'] if 'USDT' in balance else 0
                usdt_used = balance['USDT']['used'] if 'USDT' in balance else 0
                usdt_total = balance['USDT']['total'] if 'USDT' in balance else 0
                
                logger.info(f"USDT余额: 可用={usdt_free}, 已用={usdt_used}, 总计={usdt_total}")
                
                # 使用CCXT的标准方法获取持仓信息
                logger.info("获取合约持仓信息...")
                positions = exchange.fetch_positions()
                
                # 获取交易所状态
                logger.info("获取交易所状态...")
                system_status = exchange.fetch_status()
                logger.info(f"交易所状态: {system_status.get('status', '')}, 消息: {system_status.get('message', '')}")
                
                logger.info("私有API调用测试成功!")
                return True
                
            except Exception as e:
                logger.error(f"私有API调用失败: {str(e)}")
                logger.error(traceback.format_exc())
                return False
        
        return True
    except Exception as e:
        logger.error(f"连接测试失败: {str(e)}")
        logger.error(traceback.format_exc())
        return False

def main():
    """主函数"""
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
    
    # 测试连接
    success = test_connection(API_KEY, API_SECRET)
    
    if success:
        print("\n✅ 连接测试成功！可以正常访问币安API")
        if API_KEY and API_SECRET:
            print("✅ 并且成功进行了API密钥认证")
    else:
        print("\n❌ 连接测试失败，请检查网络和代理设置")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断，程序已停止")
    except Exception as e:
        print(f"程序发生错误: {str(e)}")
        traceback.print_exc()
