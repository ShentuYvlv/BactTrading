#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
测试修复后的仓位重建逻辑
"""

import os
import sys
import ccxt
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv
import logging
import ssl
import urllib3
import time

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入修复后的函数
from getPosition import rebuild_positions_from_trades, initialize_exchange

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 加载.env文件
load_dotenv()

# 防止Python 3.8中的事件循环关闭警告
if sys.platform.startswith('win'):
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_vine_trades_fixed(exchange, symbol='VINE/USDT:USDT', days=30):
    """获取VINE的交易记录，使用修复后的方法"""
    try:
        # 计算时间范围（毫秒时间戳）
        end_time = datetime.now(timezone.utc)
        start_time = end_time - pd.Timedelta(days=days)
        
        start_timestamp = int(start_time.timestamp() * 1000)
        end_timestamp = int(end_time.timestamp() * 1000)
        
        logger.info(f"📊 获取 {symbol} 最近 {days} 天的交易记录...")
        
        # 按7天分段（币安API限制最大7天）
        time_intervals = []
        current_time = start_timestamp
        seven_days_ms = 7 * 24 * 60 * 60 * 1000
        
        while current_time < end_timestamp:
            interval_end = min(current_time + seven_days_ms, end_timestamp)
            time_intervals.append((current_time, interval_end))
            current_time = interval_end
        
        all_trades = []
        
        # 遍历每个时间段
        for i, (interval_start, interval_end) in enumerate(time_intervals):
            logger.info(f"🔄 处理时间段 {i+1}/{len(time_intervals)}")
            
            interval_trades = []
            limit = 1000
            from_id = None
            
            while True:
                try:
                    params = {
                        'startTime': interval_start,
                        'endTime': interval_end,
                        'limit': limit
                    }
                    
                    if from_id:
                        params['fromId'] = from_id
                    
                    trades = exchange.fetch_my_trades(symbol, params=params)
                    
                    if not trades:
                        break
                    
                    interval_trades.extend(trades)
                    
                    if len(trades) < limit:
                        break
                    
                    from_id = trades[-1]['id']
                    time.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"时间段请求失败: {str(e)}")
                    break
            
            all_trades.extend(interval_trades)
            time.sleep(0.2)
        
        # 按时间排序
        all_trades = sorted(all_trades, key=lambda x: x['timestamp'])
        logger.info(f"📈 总共获取到 {len(all_trades)} 条交易记录")
        return all_trades
        
    except Exception as e:
        logger.error(f"❌ 获取交易记录失败: {str(e)}")
        return []

def test_position_rebuild():
    """测试修复后的仓位重建逻辑"""
    print("🚀 测试修复后的仓位重建逻辑")
    print("=" * 60)
    
    # 初始化交易所
    exchange = initialize_exchange()
    if not exchange:
        print("❌ 无法连接到币安API")
        return
    
    # 获取VINE交易记录
    symbol = 'VINE/USDT:USDT'
    trades = get_vine_trades_fixed(exchange, symbol, days=60)
    
    if not trades:
        print("❌ 没有找到交易记录")
        return
    
    print(f"✅ 获取到 {len(trades)} 条交易记录")
    
    # 使用修复后的逻辑重建仓位
    print("\n🔧 使用修复后的逻辑重建仓位...")
    positions = rebuild_positions_from_trades(trades, symbol)
    
    print(f"📊 重建出 {len(positions)} 个仓位")
    
    # 打印所有仓位
    if positions:
        print(f"\n📋 所有仓位详细信息:")
        print("=" * 120)

        for idx, pos in enumerate(positions, 1):
            print(f"\n仓位 {idx}:")
            print(f"  仓位ID: {pos['position_id']}")
            print(f"  方向: {pos['side']}")
            print(f"  数量: {pos['amount']}")
            print(f"  入场价格: {pos['entry_price']:.8f}")
            print(f"  出场价格: {pos.get('exit_price', 'N/A')}")
            print(f"  开仓时间: {pos['entry_time_formatted']}")
            print(f"  平仓时间: {pos.get('exit_time_formatted', 'N/A')}")
            print(f"  状态: {pos['status']}")
            print(f"  包含交易数: {len(pos['trades'])}")
            print(f"  手续费前PnL: {pos['pnl_before_fees']:.6f} USDT")
            print(f"  总手续费: {pos['total_fees']:.6f} USDT")
            print(f"  净PnL: {pos['pnl']:.6f} USDT")

            # 显示前5笔交易明细
            if len(pos['trades']) > 0:
                print(f"  🔍 交易明细 (前5笔):")
                for i, trade in enumerate(pos['trades'][:5]):
                    trade_time = datetime.fromtimestamp(trade['timestamp'] / 1000)
                    print(f"    交易 {i+1}: {trade_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"      方向: {trade['side']}, 数量: {trade['amount']}, 价格: {trade['price']:.8f}")
                    print(f"      手续费: {trade['fee']['cost'] if trade['fee'] else 0:.6f}")

                if len(pos['trades']) > 5:
                    print(f"    ... 还有 {len(pos['trades']) - 5} 笔交易")

            print("-" * 80)
    
    # 计算总PnL
    total_pnl = sum(pos['pnl'] for pos in positions if pos['status'] == 'closed')
    closed_count = len([pos for pos in positions if pos['status'] == 'closed'])
    open_count = len([pos for pos in positions if pos['status'] == 'open'])
    
    print(f"\n💰 总结:")
    print(f"已平仓位: {closed_count}")
    print(f"持仓中: {open_count}")
    print(f"总净PnL: {total_pnl:.6f} USDT")
    
    # 查找最大持仓量
    max_amount = max(pos['amount'] for pos in positions)
    max_pos = next(pos for pos in positions if pos['amount'] == max_amount)
    print(f"最大持仓量: {max_amount}")
    print(f"最大持仓PnL: {max_pos['pnl']:.6f} USDT")

if __name__ == "__main__":
    test_position_rebuild()
