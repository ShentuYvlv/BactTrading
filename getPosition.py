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
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from tqdm import tqdm
import signal
import csv
import argparse

from config import get_common_ccxt_config, get_env_int, get_env_str, get_position_defaults

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

# 失败交易对记录
failed_symbols_list = []
failed_symbols_lock = threading.Lock()

# 全局控制变量
shutdown_flag = threading.Event()
csv_filename = None
POSITION_DEFAULTS = get_position_defaults()
current_exchange_name = POSITION_DEFAULTS['exchange']

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
    
    # 确保data目录存在
    data_dir = os.path.dirname(filename)
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        logger.info(f"📁 创建数据目录: {data_dir}")
    
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

def initialize_exchange(exchange_name=None):
    """初始化交易所连接，支持币安和OKX
    
    Args:
        exchange_name (str): 交易所名称，支持 'binance' 或 'okx'
    
    Returns:
        交易所对象
    """
    global current_exchange_name
    exchange_name = exchange_name or POSITION_DEFAULTS['exchange']
    current_exchange_name = exchange_name
    
    logger.info(f"正在初始化交易所: {exchange_name.upper()}")
    
    if exchange_name.lower() == 'binance':
        # 币安配置
        API_KEY = os.getenv('BINANCE_API_KEY')
        API_SECRET = os.getenv('BINANCE_API_SECRET')
        
        if not API_KEY or not API_SECRET:
            raise ValueError("未能从.env文件中读取币安API密钥，请检查BINANCE_API_KEY和BINANCE_API_SECRET")
        
        config = get_common_ccxt_config()
        config.update({
            'options': {
                'defaultType': get_env_str('BINANCE_DEFAULT_TYPE', 'future'),
                'adjustForTimeDifference': True,
                'recvWindow': get_env_int('CCXT_RECV_WINDOW', 60000),
            },
            'apiKey': API_KEY,
            'secret': API_SECRET
        })
        
        try:
            exchange = ccxt.binance(config)
            exchange.load_time_difference()
            server_time = exchange.fetch_time()
            
            # 打印连接信息
            masked_key = API_KEY[:5] + "..." + API_KEY[-5:]
            logger.info(f"✅ 币安连接成功！")
            logger.info(f"API密钥: {masked_key}")
            logger.info(f"服务器时间: {server_time}")
            
            return exchange
        except Exception as e:
            logger.error(f"❌ 币安连接失败: {str(e)}")
            raise
            
    elif exchange_name.lower() == 'okx':
        # OKX配置
        API_KEY = os.getenv('OKX_API_KEY')
        API_SECRET = os.getenv('OKX_API_SECRET')
        API_PASSPHRASE = os.getenv('OKX_API_PASSPHRASE')
        
        if not API_KEY or not API_SECRET or not API_PASSPHRASE:
            raise ValueError("未能从.env文件中读取OKX API密钥，请检查OKX_API_KEY、OKX_API_SECRET和OKX_API_PASSPHRASE")
        
        config = get_common_ccxt_config()
        config.update({
            'options': {
                'defaultType': get_env_str('OKX_DEFAULT_TYPE', 'swap'),
                'adjustForTimeDifference': True,
            },
            'apiKey': API_KEY,
            'secret': API_SECRET,
            'password': API_PASSPHRASE
        })
        
        try:
            exchange = ccxt.okx(config)
            if hasattr(exchange, 'load_time_difference'):
                exchange.load_time_difference()
            server_time = exchange.fetch_time()
            
            # 打印连接信息
            masked_key = API_KEY[:5] + "..." + API_KEY[-5:]
            logger.info(f"✅ OKX连接成功！")
            logger.info(f"API密钥: {masked_key}")
            logger.info(f"服务器时间: {server_time}")
            
            return exchange
        except Exception as e:
            logger.error(f"❌ OKX连接失败: {str(e)}")
            raise
    else:
        raise ValueError(f"不支持的交易所: {exchange_name}，目前支持 'binance' 和 'okx'")

def create_exchange_for_thread():
    """为每个线程创建独立的交易所实例"""
    return initialize_exchange(current_exchange_name)

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
                        # 根据交易所设置不同的参数
                        if current_exchange_name.lower() == 'binance':
                            params = {
                                'startTime': interval_start,
                                'endTime': interval_end,
                                'limit': limit
                            }
                            
                            if from_id:
                                params['fromId'] = from_id
                                
                        elif current_exchange_name.lower() == 'okx':
                            # OKX API参数格式不同
                            # 使用begin和end参数指定时间范围（以毫秒为单位）
                            params = {
                                'begin': str(interval_start),
                                'end': str(interval_end),
                                'limit': limit
                            }
                            
                            # OKX不使用fromId，而是使用after参数进行分页
                            # after参数是交易ID，用于获取该ID之后的交易
                            if from_id:
                                params['after'] = str(from_id)
                        
                        # 获取指定交易对的交易历史
                        trades = exchange.fetch_my_trades(symbol, params=params)
                        
                        if not trades:
                            break
                            
                        interval_trades.extend(trades)
                        
                        # 如果返回的记录少于限制数量，说明已经获取完毕
                        if len(trades) < limit:
                            break
                            
                        # 更新from_id为最后一条记录的ID或时间戳
                        if current_exchange_name.lower() == 'binance':
                            from_id = trades[-1]['id']
                        elif current_exchange_name.lower() == 'okx':
                            from_id = trades[-1]['timestamp']
                        
                        # 添加小延迟避免触发限制
                        time.sleep(0.1 if current_exchange_name.lower() == 'okx' else 0.05)
                        retry_count = 0  # 重置重试计数
                        
                    except Exception as e:
                        error_str = str(e).lower()
                        
                        # 特殊处理"too many requests"错误
                        if 'too many requests' in error_str or '429' in error_str:
                            wait_time = 3.0 if current_exchange_name.lower() == 'okx' else 2.0
                            thread_safe_log('warning', f"[线程{thread_id}] {symbol} 触发频率限制，暂停{wait_time}秒...")
                            time.sleep(wait_time)
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
        # 记录失败的交易对
        with failed_symbols_lock:
            failed_symbols_list.append({
                'symbol': symbol,
                'error': str(e),
                'thread_id': thread_id
            })

        with stats_lock:
            global_stats['completed_symbols'] += 1
            global_stats['failed_symbols'] += 1
        thread_safe_log('error', f"[线程{thread_id}] ❌ 获取 {symbol} 交易历史失败: {str(e)}")
        return symbol, []

def retry_failed_symbols(exchange, time_intervals, max_workers=5, max_retries=3):
    """重试失败的交易对"""
    global failed_symbols_list, global_stats

    retry_count = 0

    while retry_count < max_retries and failed_symbols_list and not shutdown_flag.is_set():
        retry_count += 1

        # 获取当前失败的交易对列表，去重
        with failed_symbols_lock:
            # 去重：只保留每个交易对的最新失败记录
            unique_failed = {}
            for item in failed_symbols_list:
                unique_failed[item['symbol']] = item

            current_failed = list(unique_failed.values())
            failed_symbols_list.clear()  # 清空列表，准备记录新的失败

        if not current_failed:
            break

        logger.info(f"\n🔄 第 {retry_count} 轮重试，处理 {len(current_failed)} 个失败的交易对")

        # 分析失败原因，决定重试策略
        rate_limit_errors = sum(1 for item in current_failed if 'too many requests' in item['error'].lower() or '429' in item['error'])
        network_errors = sum(1 for item in current_failed if any(keyword in item['error'].lower() for keyword in ['timeout', 'connection', 'network']))

        if rate_limit_errors > 0:
            wait_time = min(30, retry_count * 10)  # 最多等待30秒
            logger.info(f"⏳ 检测到 {rate_limit_errors} 个限流错误，等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)
        elif network_errors > 0:
            wait_time = min(15, retry_count * 5)  # 最多等待15秒
            logger.info(f"🌐 检测到 {network_errors} 个网络错误，等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)
        else:
            # 其他错误，短暂等待
            time.sleep(retry_count * 2)

        # 重置统计信息
        retry_symbols = [item['symbol'] for item in current_failed]

        # 使用线程池重试失败的交易对
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_symbol = {
                executor.submit(fetch_symbol_trades, symbol, time_intervals, f"重试{retry_count}-{i}"): symbol
                for i, symbol in enumerate(retry_symbols)
            }

            retry_success = 0
            for future in as_completed(future_to_symbol):
                if shutdown_flag.is_set():
                    logger.info("🛑 收到退出信号，停止重试...")
                    break

                symbol = future_to_symbol[future]
                try:
                    symbol_result, trades = future.result()
                    if trades:  # 如果这次成功获取到数据
                        retry_success += 1
                except Exception as exc:
                    logger.error(f'❌ 重试交易对 {symbol} 仍然失败: {exc}')

        logger.info(f"✅ 第 {retry_count} 轮重试完成，成功: {retry_success}/{len(retry_symbols)}")

        # 如果没有新的失败，退出重试循环
        if not failed_symbols_list:
            logger.info("🎉 所有交易对都已成功获取！")
            break

    # 最终报告
    if failed_symbols_list:
        logger.warning(f"⚠️ 经过 {retry_count} 轮重试后，仍有 {len(failed_symbols_list)} 个交易对失败")
        logger.info("失败的交易对列表:")
        for item in failed_symbols_list[:10]:  # 只显示前10个
            logger.info(f"  - {item['symbol']}: {item['error']}")
        if len(failed_symbols_list) > 10:
            logger.info(f"  ... 还有 {len(failed_symbols_list) - 10} 个")
    else:
        logger.info("🎉 所有交易对都已成功处理！")

def fetch_position_history(exchange, start_date, end_date, max_workers=5, max_retries=3):
    """获取指定时间段的仓位历史数据（多线程版本，支持失败重试）"""
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
        
        # 添加调试信息：显示前10个市场的详细信息
        market_items = list(exchange.markets.items())[:10]
        logger.info(f"市场数据示例 (前10个):")
        for symbol, market in market_items:
            logger.info(f"  {symbol}: type={market.get('type')}, active={market.get('active')}, info={market.get('info', {}).get('instType', 'N/A')}")
        
        for symbol, market in exchange.markets.items():
            # 根据不同交易所过滤交易对
            if current_exchange_name.lower() == 'binance':
                # 币安：过滤期货合约（通常类型为 'future' 或 'swap'，且以 :USDT 结尾）
                if (market.get('type') in ['future', 'swap'] and 
                    symbol.endswith(':USDT') and 
                    market.get('active', True)):
                    all_futures_symbols.append(symbol)
            elif current_exchange_name.lower() == 'okx':
                # OKX：修复过滤条件
                market_type = market.get('type')
                market_info = market.get('info', {})
                inst_type = market_info.get('instType', '')
                
                # OKX的永续合约标识：type='swap' 或 instType='SWAP'
                if ((market_type == 'swap' or inst_type == 'SWAP') and 
                    market.get('active', True) and
                    market.get('settle') == 'USDT'):  # 只获取USDT结算的合约
                    all_futures_symbols.append(symbol)
        
        logger.info(f"找到 {len(all_futures_symbols)} 个{current_exchange_name.upper()}合约交易对")
        
        # 如果还是没有找到交易对，显示更多调试信息
        if len(all_futures_symbols) == 0:
            logger.warning("未找到符合条件的交易对，显示所有市场类型统计:")
            type_count = {}
            inst_type_count = {}
            settle_count = {}
            
            for symbol, market in exchange.markets.items():
                market_type = market.get('type', 'unknown')
                market_info = market.get('info', {})
                inst_type = market_info.get('instType', 'unknown')
                settle = market.get('settle', 'unknown')
                
                type_count[market_type] = type_count.get(market_type, 0) + 1
                inst_type_count[inst_type] = inst_type_count.get(inst_type, 0) + 1
                settle_count[settle] = settle_count.get(settle, 0) + 1
            
            logger.info(f"市场类型统计: {type_count}")
            logger.info(f"合约类型统计: {inst_type_count}")
            logger.info(f"结算币种统计: {settle_count}")
            
            # 尝试更宽松的过滤条件
            logger.info("尝试更宽松的过滤条件...")
            for symbol, market in exchange.markets.items():
                market_type = market.get('type')
                market_info = market.get('info', {})
                inst_type = market_info.get('instType', '')
                
                if (market_type == 'swap' or inst_type == 'SWAP') and market.get('active', True):
                    all_futures_symbols.append(symbol)
                    if len(all_futures_symbols) >= 10:  # 只取前10个作为测试
                        break
            
            logger.info(f"使用宽松条件找到 {len(all_futures_symbols)} 个交易对")
            if all_futures_symbols:
                logger.info(f"示例交易对: {all_futures_symbols[:5]}")
        
        # 更新全局统计
        global_stats['total_symbols'] = len(all_futures_symbols)
        global_stats['completed_symbols'] = 0
        global_stats['successful_symbols'] = 0
        global_stats['failed_symbols'] = 0
        global_stats['total_trades'] = 0
        
        # 计算时间分段（按天分段，避免单次请求时间跨度过大）
        time_intervals = []
        current_time = start_timestamp
        day_ms = 24 * 60 * 60 * 1000  # 一天的毫秒数
        
        while current_time < end_timestamp:
            interval_end = min(current_time + day_ms, end_timestamp)
            time_intervals.append((current_time, interval_end))
            current_time = interval_end
        
        logger.info(f"时间分段: {len(time_intervals)} 个时间段")
        
        # 使用线程池并行获取数据
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_symbol = {
                executor.submit(fetch_symbol_trades, symbol, time_intervals, i % max_workers): symbol 
                for i, symbol in enumerate(all_futures_symbols)
            }
            
            # 等待任务完成
            for future in as_completed(future_to_symbol):
                if shutdown_flag.is_set():
                    logger.info("收到退出信号，取消剩余任务...")
                    break
                
                symbol = future_to_symbol[future]
                try:
                    symbol, trades = future.result()
                except Exception as exc:
                    logger.error(f'交易对 {symbol} 处理异常: {exc}')

        # 重试失败的交易对
        if failed_symbols_list and not shutdown_flag.is_set():
            logger.info(f"\n🔄 开始重试失败的交易对，最大重试次数: {max_retries}")
            retry_failed_symbols(exchange, time_intervals, max_workers, max_retries)

        # 打印最终统计信息
        logger.info("\n" + "="*60)
        logger.info("🎉 最终统计信息:")
        logger.info(f"交易所: {current_exchange_name.upper()}")
        logger.info(f"处理的交易对: {global_stats['completed_symbols']}/{global_stats['total_symbols']}")
        logger.info(f"成功获取数据的交易对: {global_stats['successful_symbols']}")
        logger.info(f"最终失败的交易对: {len(failed_symbols_list)}")
        logger.info(f"总交易记录数: {global_stats['total_trades']}")

        # 计算成功率
        if global_stats['total_symbols'] > 0:
            success_rate = (global_stats['successful_symbols'] / global_stats['total_symbols']) * 100
            logger.info(f"成功率: {success_rate:.1f}%")

        logger.info(f"数据文件: {csv_filename}")

        # 如果还有失败的交易对，显示详细信息
        if failed_symbols_list:
            logger.warning(f"\n⚠️ 仍有 {len(failed_symbols_list)} 个交易对未能成功获取:")
            for i, item in enumerate(failed_symbols_list[:5]):  # 显示前5个
                logger.warning(f"  {i+1}. {item['symbol']}: {item['error']}")
            if len(failed_symbols_list) > 5:
                logger.warning(f"  ... 还有 {len(failed_symbols_list) - 5} 个")
        else:
            logger.info("🎉 所有交易对都已成功处理！")

        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"获取仓位历史时发生错误: {str(e)}")
        raise

def rebuild_positions_from_trades(trades, symbol):
    """从交易记录重建仓位历史（修复逐笔平仓问题）"""
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
                'pnl_before_fees': 0,
                'total_fees': trade['fee']['cost'] if trade['fee'] else 0,
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

                # 累积手续费
                if trade['fee']:
                    current_position['total_fees'] += trade['fee']['cost']

                # 计算这笔平仓的PnL
                close_amount = min(trade['amount'], current_position['amount'])
                if current_position['side'] == 'long':
                    partial_pnl = (trade['price'] - current_position['entry_price']) * close_amount
                else:
                    partial_pnl = (current_position['entry_price'] - trade['price']) * close_amount

                # 累积PnL
                current_position['pnl_before_fees'] += partial_pnl
                current_position['pnl'] = current_position['pnl_before_fees'] - current_position['total_fees']

                if trade['amount'] >= current_position['amount']:
                    # 完全平仓或反向开仓
                    current_position['exit_price'] = trade['price']
                    current_position['exit_time'] = trade['timestamp']
                    current_position['exit_time_formatted'] = datetime.fromtimestamp(trade['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
                    current_position['status'] = 'closed'

                    positions.append(current_position.copy())

                    # 如果有剩余数量，开始新的反向仓位
                    if trade['amount'] > current_position['amount']:
                        remaining_amount = trade['amount'] - current_position['amount']
                        current_position = {
                            'symbol': symbol,
                            'position_id': f"{symbol}_{trade['timestamp']}_reverse",
                            'side': 'long' if trade['side'] == 'buy' else 'short',
                            'amount': remaining_amount,
                            'entry_price': trade['price'],
                            'entry_time': trade['timestamp'],
                            'entry_time_formatted': datetime.fromtimestamp(trade['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                            'trades': [trade],
                            'status': 'open',
                            'exit_price': None,
                            'exit_time': None,
                            'exit_time_formatted': None,
                            'pnl': 0,
                            'pnl_before_fees': 0,
                            'total_fees': trade['fee']['cost'] if trade['fee'] else 0,
                            'pnl_records': []
                        }
                    else:
                        current_position = None
                else:
                    # 部分平仓 - 减少仓位数量，但继续持有
                    current_position['amount'] -= trade['amount']
                    # 更新最后平仓价格和时间（用于显示）
                    current_position['exit_price'] = trade['price']
                    current_position['exit_time'] = trade['timestamp']
                    current_position['exit_time_formatted'] = datetime.fromtimestamp(trade['timestamp'] / 1000).strftime('%Y-%m-%d %H:%M:%S')
            else:
                # 同向交易（加仓）
                current_position['trades'].append(trade)

                # 累积手续费
                if trade['fee']:
                    current_position['total_fees'] += trade['fee']['cost']

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
    # 设置命令行参数
    parser = argparse.ArgumentParser(description='获取交易所仓位历史数据')
    parser.add_argument('--exchange', '-e', choices=['binance', 'okx'], default=POSITION_DEFAULTS['exchange'],
                        help=f"选择交易所 (默认: {POSITION_DEFAULTS['exchange']})")
    parser.add_argument('--start-date', '-s', required=True,
                        help='开始日期 (格式: YYYY-MM-DD)')
    parser.add_argument('--end-date', '-n', required=True,
                        help='结束日期 (格式: YYYY-MM-DD)')
    parser.add_argument('--threads', '-t', type=int, default=POSITION_DEFAULTS['threads'],
                        help=f"线程数量 (默认: {POSITION_DEFAULTS['threads']})")
    parser.add_argument('--max-retries', '-r', type=int, default=POSITION_DEFAULTS['max_retries'],
                        help=f"失败交易对的最大重试次数 (默认: {POSITION_DEFAULTS['max_retries']})")

    args = parser.parse_args()
    
    # 设置信号处理器
    setup_signal_handler()
    
    try:
        # 初始化交易所
        exchange = initialize_exchange(args.exchange)
        
        # 生成CSV文件名 - 保存到data目录
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f"data/{args.exchange}_{args.start_date}_{args.end_date}_{timestamp}.csv"
        
        # 初始化CSV文件
        init_csv_file(csv_filename)
        
        # 获取仓位历史
        fetch_position_history(exchange, args.start_date, args.end_date, args.threads, args.max_retries)
        
        logger.info(f"✅ 任务完成！数据已保存到: {csv_filename}")
        
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序执行出错: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
