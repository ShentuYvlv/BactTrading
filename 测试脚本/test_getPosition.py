#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import ccxt
import time
import logging
import ssl
import urllib3
import pandas as pd
from datetime import datetime, timezone
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from tqdm import tqdm
import signal
import csv

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 加载.env文件中的环境变量
load_dotenv()

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

# 线程锁，用于保护日志输出和统计信息
log_lock = threading.Lock()
stats_lock = threading.Lock()
csv_lock = threading.Lock()

# 全局统计信息
global_stats = {
    'total_symbols': 0,
    'completed_symbols': 0,
    'total_trades': 0,
    'successful_symbols': 0,
    'failed_symbols': 0
}

# 全局控制变量
shutdown_flag = threading.Event()
csv_filename = None

def signal_handler(sig, frame):
    """处理CTRL+C信号"""
    print('\n\n🛑 收到中断信号，正在安全退出...')
    print('等待当前线程完成并保存数据...')
    shutdown_flag.set()

def setup_signal_handler():
    """设置信号处理器"""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def init_csv_file(filename):
    """初始化CSV文件"""
    global csv_filename
    csv_filename = filename
    
    # 写入CSV文件头
    headers = [
        '仓位ID', '交易对', '方向', '数量', '开仓价格', '开仓时间', 
        '平仓价格', '平仓时间', '状态', 'PnL', '交易次数', 
        '原始开仓时间戳', '原始平仓时间戳'
    ]
    
    with open(csv_filename, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(headers)
    
    logger.info(f"📁 CSV文件已初始化: {csv_filename}")

def save_positions_to_csv(positions):
    """增量保存仓位数据到CSV文件"""
    if not positions or not csv_filename:
        return
    
    with csv_lock:
        try:
            with open(csv_filename, 'a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                
                for position in positions:
                    row = [
                        position['position_id'],
                        position['symbol'],
                        '多头' if position['side'] == 'long' else '空头',
                        position['amount'],
                        position['entry_price'],
                        position['entry_time_formatted'],
                        position.get('exit_price', '持仓中'),
                        position.get('exit_time_formatted', '持仓中'),
                        '已平仓' if position['status'] == 'closed' else '持仓中',
                        position.get('pnl', 0),
                        len(position['trades']),
                        position['entry_time'],
                        position.get('exit_time', '')
                    ]
                    writer.writerow(row)
            
            logger.info(f"💾 已保存 {len(positions)} 个仓位到CSV文件")
            
        except Exception as e:
            logger.error(f"❌ 保存CSV文件失败: {str(e)}")

def thread_safe_log(level, message):
    """线程安全的日志输出"""
    with log_lock:
        if level == 'info':
            logger.info(message)
        elif level == 'warning':
            logger.warning(message)
        elif level == 'error':
            logger.error(message)

def initialize_exchange():
    """初始化币安期货交易所连接，使用和TEST_ca.py相同的配置"""
    # 从环境变量中获取API密钥
    API_KEY = os.getenv('BINANCE_API_KEY')
    API_SECRET = os.getenv('BINANCE_API_SECRET')
    
    if not API_KEY or not API_SECRET:
        raise ValueError("未能从.env文件中读取API密钥，请检查BINANCE_API_KEY和BINANCE_API_SECRET")
    
    # 使用和TEST_ca.py相同的成功连接配置
    config = {
        'enableRateLimit': True,
        'timeout': 60000,
        'proxies': {
            'http': 'socks5://127.0.0.1:10808',
            'https': 'socks5://127.0.0.1:10808'
        },
        'options': {
            'defaultType': 'future',  # 期货交易
            'adjustForTimeDifference': True,
            'recvWindow': 60000,
        },
        'headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        },
        'verify': False,  # 禁用SSL证书验证
        'apiKey': API_KEY,
        'secret': API_SECRET
    }
    
    try:
        exchange = ccxt.binance(config)
        exchange.load_time_difference()
        server_time = exchange.fetch_time()
        
        # 打印连接信息
        masked_key = API_KEY[:5] + "..." + API_KEY[-5:]
        logger.info(f"✅ 连接成功！")
        logger.info(f"API密钥: {masked_key}")
        logger.info(f"服务器时间: {server_time}")
        
        return exchange
    except Exception as e:
        logger.error(f"❌ 连接失败: {str(e)}")
        raise

def create_exchange_for_thread():
    """为每个线程创建独立的交易所实例"""
    return initialize_exchange()

def fetch_symbol_trades(symbol, time_intervals, thread_id):
    """获取单个交易对的所有交易数据（在独立线程中运行）"""
    global global_stats
    
    # 检查是否需要退出
    if shutdown_flag.is_set():
        return symbol, []
    
    try:
        # 为每个线程创建独立的exchange实例
        exchange = create_exchange_for_thread()
        
        thread_safe_log('info', f"[线程{thread_id}] 开始获取 {symbol} 的交易历史...")
        
        symbol_trades = []
        
        for i, (interval_start, interval_end) in enumerate(time_intervals):
            # 检查是否需要退出
            if shutdown_flag.is_set():
                thread_safe_log('info', f"[线程{thread_id}] 收到退出信号，停止处理 {symbol}")
                break
                
            try:
                limit = 1000
                from_id = None
                interval_trades = []
                retry_count = 0
                max_retries = 3
                
                while True:
                    # 检查是否需要退出
                    if shutdown_flag.is_set():
                        break
                        
                    try:
                        params = {
                            'startTime': interval_start,
                            'endTime': interval_end,
                            'limit': limit
                        }
                        
                        if from_id:
                            params['fromId'] = from_id
                        
                        # 获取指定交易对的交易历史
                        trades = exchange.fetch_my_trades(symbol, params=params)
                        
                        if not trades:
                            break
                            
                        interval_trades.extend(trades)
                        
                        # 如果返回的记录少于限制数量，说明已经获取完毕
                        if len(trades) < limit:
                            break
                            
                        # 更新from_id为最后一条记录的ID
                        from_id = trades[-1]['id']
                        
                        # 添加小延迟避免触发限制
                        time.sleep(0.05)  # 减少延迟提高速度
                        retry_count = 0  # 重置重试计数
                        
                    except Exception as e:
                        error_str = str(e).lower()
                        
                        # 特殊处理"too many requests"错误
                        if 'too many requests' in error_str or '429' in error_str:
                            thread_safe_log('warning', f"[线程{thread_id}] {symbol} 触发频率限制，暂停2秒...")
                            time.sleep(2.0)  # 暂停2秒
                            continue
                        
                        retry_count += 1
                        if retry_count <= max_retries:
                            thread_safe_log('warning', f"[线程{thread_id}] {symbol} 时间段数据获取出错，重试 {retry_count}/{max_retries}: {str(e)}")
                            time.sleep(retry_count * 0.5)  # 递增延迟
                            continue
                        else:
                            thread_safe_log('warning', f"[线程{thread_id}] {symbol} 时间段数据获取失败，跳过: {str(e)}")
                            break
                
                if interval_trades:
                    symbol_trades.extend(interval_trades)
                
            except Exception as e:
                thread_safe_log('warning', f"[线程{thread_id}] 处理 {symbol} 时间段 {i+1} 时出错: {str(e)}")
                continue
        
        # 如果获取到交易数据，立即处理并保存
        if symbol_trades and not shutdown_flag.is_set():
            # 按时间排序
            symbol_trades.sort(key=lambda x: x['timestamp'])
            
            # 重建仓位历史
            positions = rebuild_positions_from_trades(symbol_trades, symbol)
            
            if positions:
                # 立即保存到CSV
                save_positions_to_csv(positions)
        
        # 更新统计信息
        with stats_lock:
            global_stats['completed_symbols'] += 1
            if symbol_trades:
                global_stats['successful_symbols'] += 1
                global_stats['total_trades'] += len(symbol_trades)
                thread_safe_log('info', f"[线程{thread_id}] ✅ {symbol}: {len(symbol_trades)} 条记录 (进度: {global_stats['completed_symbols']}/{global_stats['total_symbols']})")
            else:
                thread_safe_log('info', f"[线程{thread_id}] ⚪ {symbol}: 无记录 (进度: {global_stats['completed_symbols']}/{global_stats['total_symbols']})")
        
        return symbol, symbol_trades
        
    except Exception as e:
        with stats_lock:
            global_stats['completed_symbols'] += 1
            global_stats['failed_symbols'] += 1
        thread_safe_log('error', f"[线程{thread_id}] ❌ 获取 {symbol} 交易历史失败: {str(e)}")
        return symbol, []

def fetch_position_history(exchange, start_date, end_date, max_workers=5):
    """获取指定时间段的仓位历史数据（多线程版本）"""
    global global_stats
    
    logger.info(f"正在获取 {start_date} 到 {end_date} 的仓位历史... (使用 {max_workers} 个线程)")
    logger.info("💡 提示: 按 Ctrl+C 可以安全退出并保存已获取的数据")
    
    # 转换日期为时间戳（毫秒）
    start_timestamp = int(datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp() * 1000)
    end_timestamp = int(datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp() * 1000)
    
    try:
        # 加载市场数据
        exchange.load_markets()
        
        # 首先尝试获取当前仓位
        logger.info("获取当前仓位...")
        current_positions = exchange.fetch_positions()
        logger.info(f"当前活跃仓位数量: {len([p for p in current_positions if p['contracts'] > 0])}")
        
        # 获取所有支持的合约交易对
        logger.info("获取所有支持的合约交易对...")
        all_futures_symbols = []
        
        for symbol, market in exchange.markets.items():
            # 过滤期货合约（通常类型为 'future' 或 'swap'，且以 :USDT 结尾）
            if (market.get('type') in ['future', 'swap'] and 
                symbol.endswith(':USDT') and 
                market.get('active', True)):
                all_futures_symbols.append(symbol)
        
        logger.info(f"找到 {len(all_futures_symbols)} 个活跃的合约交易对")
        
        # 显示前10个交易对作为示例
        if all_futures_symbols:
            logger.info(f"交易对示例: {all_futures_symbols[:10]}")
        
        # 如果没有找到合约交易对，使用备用方案
        if not all_futures_symbols:
            logger.warning("未找到合约交易对，使用备用交易对列表...")
            all_futures_symbols = [
                'BTC/USDT:USDT', 'ETH/USDT:USDT', 'BNB/USDT:USDT', 
                'SOL/USDT:USDT', 'ADA/USDT:USDT', 'DOT/USDT:USDT',
                'MATIC/USDT:USDT', 'AVAX/USDT:USDT', 'LINK/USDT:USDT'
            ]
        
        # 初始化CSV文件
        csv_filename = f"positions_realtime_{start_date.replace('-', '')}_{end_date.replace('-', '')}.csv"
        init_csv_file(csv_filename)
        
        # 初始化统计信息
        with stats_lock:
            global_stats['total_symbols'] = len(all_futures_symbols)
            global_stats['completed_symbols'] = 0
            global_stats['total_trades'] = 0
            global_stats['successful_symbols'] = 0
            global_stats['failed_symbols'] = 0
        
        # 计算时间分割点（7天间隔）
        time_intervals = []
        current_start = start_timestamp
        seven_days_ms = 7 * 24 * 60 * 60 * 1000  # 7天的毫秒数
        
        while current_start < end_timestamp:
            current_end = min(current_start + seven_days_ms, end_timestamp)
            time_intervals.append((current_start, current_end))
            current_start = current_end
        
        logger.info(f"将分 {len(time_intervals)} 个时间段查询数据（每段最多7天）")
        
        # 使用线程池并行获取交易数据
        logger.info(f"🚀 开始并行获取交易数据（最大并发：{max_workers} 个线程）...")
        
        all_trades = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_symbol = {}
            for i, symbol in enumerate(all_futures_symbols):
                if shutdown_flag.is_set():
                    break
                future = executor.submit(fetch_symbol_trades, symbol, time_intervals, i+1)
                future_to_symbol[future] = symbol
            
            # 收集结果
            for future in as_completed(future_to_symbol):
                if shutdown_flag.is_set():
                    logger.info("🛑 收到退出信号，取消剩余任务...")
                    break
                    
                symbol = future_to_symbol[future]
                
                try:
                    returned_symbol, trades = future.result()
                    if trades:
                        all_trades.extend(trades)
                except Exception as e:
                    logger.error(f"❌ 处理 {symbol} 时出错: {str(e)}")
        
        # 显示最终统计
        with stats_lock:
            if shutdown_flag.is_set():
                logger.info(f"🛑 程序被用户中断")
            else:
                logger.info(f"🎉 并行获取完成！")
            
            logger.info(f"📊 最终统计信息:")
            logger.info(f"   - 总交易对: {global_stats['total_symbols']}")
            logger.info(f"   - 已处理: {global_stats['completed_symbols']}")
            logger.info(f"   - 成功获取: {global_stats['successful_symbols']}")
            logger.info(f"   - 失败: {global_stats['failed_symbols']}")
            logger.info(f"   - 总交易记录: {global_stats['total_trades']}")
            logger.info(f"📁 数据已实时保存到: {csv_filename}")
        
        return []  # 返回空列表，因为数据已经实时保存到CSV
        
    except Exception as e:
        logger.error(f"❌ 获取仓位历史失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

def rebuild_positions_from_trades(trades, symbol):
    """从交易记录重建仓位历史"""
    positions = []
    current_position = None
    
    for trade in trades:
        if current_position is None:
            # 开始新仓位
            current_position = {
                'symbol': symbol,
                'position_id': f"{symbol}_{trade['timestamp']}",
                'side': 'long' if trade['side'] == 'buy' else 'short',
                'amount': trade['amount'],
                'entry_price': trade['price'],
                'entry_time': trade['timestamp'],
                'entry_time_formatted': datetime.fromtimestamp(trade['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                'trades': [trade],
                'status': 'open',
                'exit_price': None,
                'exit_time': None,
                'exit_time_formatted': None,
                'pnl': 0,
                'pnl_records': []
            }
        else:
            # 检查是否为反向交易（平仓或反向开仓）
            is_opposite_side = (
                (current_position['side'] == 'long' and trade['side'] == 'sell') or
                (current_position['side'] == 'short' and trade['side'] == 'buy')
            )
            
            if is_opposite_side:
                # 平仓交易
                current_position['trades'].append(trade)
                
                if trade['amount'] >= current_position['amount']:
                    # 完全平仓或反向开仓
                    current_position['exit_price'] = trade['price']
                    current_position['exit_time'] = trade['timestamp']
                    current_position['exit_time_formatted'] = datetime.fromtimestamp(trade['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
                    current_position['status'] = 'closed'
                    
                    # 计算PnL
                    if current_position['side'] == 'long':
                        current_position['pnl'] = (trade['price'] - current_position['entry_price']) * current_position['amount']
                    else:
                        current_position['pnl'] = (current_position['entry_price'] - trade['price']) * current_position['amount']
                    
                    positions.append(current_position.copy())
                    
                    # 如果有剩余数量，开始新的反向仓位
                    if trade['amount'] > current_position['amount']:
                        current_position = {
                            'symbol': symbol,
                            'position_id': f"{symbol}_{trade['timestamp']}_reverse",
                            'side': 'long' if trade['side'] == 'buy' else 'short',
                            'amount': trade['amount'] - current_position['amount'],
                            'entry_price': trade['price'],
                            'entry_time': trade['timestamp'],
                            'entry_time_formatted': datetime.fromtimestamp(trade['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                            'trades': [trade],
                            'status': 'open',
                            'exit_price': None,
                            'exit_time': None,
                            'exit_time_formatted': None,
                            'pnl': 0,
                            'pnl_records': []
                        }
                    else:
                        current_position = None
                else:
                    # 部分平仓
                    current_position['amount'] -= trade['amount']
            else:
                # 同向交易（加仓）
                current_position['trades'].append(trade)
                # 计算平均入场价格
                total_value = current_position['entry_price'] * current_position['amount'] + trade['price'] * trade['amount']
                total_amount = current_position['amount'] + trade['amount']
                current_position['entry_price'] = total_value / total_amount
                current_position['amount'] = total_amount
    
    # 如果有未关闭的仓位，也添加到结果中
    if current_position is not None:
        positions.append(current_position)
    
    return positions

def main():
    """主函数"""
    logger.info("========== 币安合约仓位历史获取工具（多线程版本） ==========")
    logger.info("💡 按 Ctrl+C 可以安全退出并保存已获取的数据")
    
    # 设置信号处理器
    setup_signal_handler()
    
    try:
        # 初始化交易所连接
        exchange = initialize_exchange()
        
        # 设置时间范围
        start_date = '2024-04-01'
        end_date = '2024-05-30'
        
        # 设置线程数（可根据需要调整，建议5-10个）
        max_workers = 6  # 减少线程数避免触发频率限制
        
        logger.info(f"获取时间范围: {start_date} 到 {end_date}")
        logger.info(f"并发线程数: {max_workers}")
        
        # 记录开始时间
        start_time = time.time()
        
        # 获取仓位历史
        positions = fetch_position_history(exchange, start_date, end_date, max_workers)
        
        # 记录结束时间
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        if shutdown_flag.is_set():
            logger.info(f"⏱️ 运行时间: {elapsed_time:.2f} 秒 (用户中断)")
            logger.info("✅ 程序已安全退出，数据已保存")
        else:
            logger.info(f"⏱️ 总耗时: {elapsed_time:.2f} 秒")
            logger.info("✅ 所有数据已实时保存到CSV文件")
        
        logger.info("========== 处理完成 ==========")
        
    except KeyboardInterrupt:
        logger.info("🛑 收到键盘中断信号")
        logger.info("✅ 程序已安全退出，数据已保存")
    except Exception as e:
        logger.error(f"❌ 程序执行失败: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
