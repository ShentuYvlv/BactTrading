#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
币安交易数据可视化示例 - TradingView风格
使用CCXT获取数据，Plotly绘制图表，Dash创建Web界面
增强版: 添加技术指标、绘图工具和更多交互功能
"""

import os
import sys
import ccxt
import time
import logging
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
from dash import Dash, dcc, html, callback, Input, Output, State, ALL, MATCH, ctx
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import dash_daq as daq
from datetime import datetime, timedelta
import json
import traceback
import dotenv
# 导入技术分析库
import pandas_ta as ta

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

def initialize_exchange():
    """初始化并返回配置好的交易所对象"""
    # 从环境变量中获取API密钥
    API_KEY = os.getenv('BINANCE_API_KEY')
    API_SECRET = os.getenv('BINANCE_API_SECRET')
    
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
    if API_KEY and API_SECRET:
        config['apiKey'] = API_KEY
        config['secret'] = API_SECRET
        logger.info("使用API密钥认证")
    else:
        logger.warning("未提供API密钥，将以只读模式运行")
    
    # 创建交易所实例
    exchange = ccxt.binance(config)
    
    return exchange, API_KEY, API_SECRET

def fetch_ohlcv_data(exchange, symbol='NXPC/USDT:USDT', timeframe='1h', limit=100):
    """获取K线历史数据"""
    try:
        logger.info(f"获取 {symbol} 的 {timeframe} K线数据, 数量: {limit}...")
        
        # 获取OHLCV数据
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        
        # 转换为DataFrame
        df_ohlc = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # 转换时间戳为日期时间
        df_ohlc['timestamp'] = pd.to_datetime(df_ohlc['timestamp'], unit='ms')
        
        logger.info(f"成功获取 {len(df_ohlc)} 条K线数据")
        return df_ohlc
    
    except Exception as e:
        logger.error(f"获取K线数据失败: {str(e)}")
        logger.error(traceback.format_exc())
        # 返回空DataFrame
        return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

def fetch_trades(exchange, symbol='NXPC/USDT:USDT', limit=100):
    """获取个人交易记录"""
    try:
        # 检查是否有API密钥
        if not exchange.apiKey or not exchange.secret:
            logger.warning("未提供API密钥，无法获取交易记录")
            return pd.DataFrame()
        
        logger.info(f"获取 {symbol} 的交易记录, 数量: {limit}...")
        
        # 获取交易记录
        trades = exchange.fetch_my_trades(symbol, limit=limit)
        
        # 如果没有交易记录，返回空DataFrame
        if not trades:
            logger.info("没有找到交易记录")
            return pd.DataFrame()
        
        # 转换为DataFrame
        df_trades = pd.DataFrame(trades)
        
        # 转换时间戳为日期时间
        if 'timestamp' in df_trades.columns:
            df_trades['timestamp'] = pd.to_datetime(df_trades['timestamp'], unit='ms')
        
        logger.info(f"成功获取 {len(df_trades)} 条交易记录")
        return df_trades
    
    except Exception as e:
        logger.error(f"获取交易记录失败: {str(e)}")
        logger.error(traceback.format_exc())
        # 返回空DataFrame
        return pd.DataFrame()

def create_chart(df_ohlc, df_trades=None, symbol='NXPC/USDT:USDT'):
    """创建价格图表和交易标记"""
    try:
        logger.info("创建价格图表...")
        
        # 创建蜡烛图
        fig = go.Figure()
        
        # 添加K线图
        fig.add_trace(
            go.Candlestick(
                x=df_ohlc['timestamp'],
                open=df_ohlc['open'],
                high=df_ohlc['high'],
                low=df_ohlc['low'],
                close=df_ohlc['close'],
                name='价格',
                increasing_line_color='#26a69a',  # 上涨蜡烛颜色
                decreasing_line_color='#ef5350',  # 下跌蜡烛颜色
            )
        )
        
        # 如果有交易记录，添加交易标记
        if df_trades is not None and not df_trades.empty and 'timestamp' in df_trades.columns:
            logger.info("添加交易标记...")
            
            # 遍历每条交易记录
            for idx, trade in df_trades.iterrows():
                # 确定买卖方向
                side = trade.get('side', '')
                
                # 设置标记颜色和符号
                marker_color = 'green' if side.lower() == 'buy' else 'red'
                marker_symbol = 'triangle-up' if side.lower() == 'buy' else 'triangle-down'
                
                # 获取价格和数量
                price = trade.get('price', 0)
                amount = trade.get('amount', 0)
                cost = price * amount
                
                # 添加散点图标记交易
                fig.add_trace(
                    go.Scatter(
                        x=[trade['timestamp']],
                        y=[price],
                        mode='markers+text',
                        marker=dict(
                            color=marker_color,
                            size=12,
                            symbol=marker_symbol
                        ),
                        text=[f"{side.capitalize()} {amount:.4f}"],
                        textposition="top center",
                        name=f"{side.capitalize()} {amount:.4f}",
                        hoverinfo='text',
                        hovertext=f"时间: {trade['timestamp']}<br>方向: {side}<br>价格: {price}<br>数量: {amount}<br>金额: {cost:.2f}"
                    )
                )
        
        # 设置图表布局
        fig.update_layout(
            title=f'{symbol} 价格图表与交易记录',
            xaxis_title='时间',
            yaxis_title='价格',
            xaxis_rangeslider_visible=False,  # 隐藏下方的滑块
            template='plotly_white',  # 使用白色主题
            legend_orientation="h",  # 水平图例
            legend=dict(x=0, y=1.1),  # 图例位置
            hovermode='closest',  # 鼠标悬停模式
            margin=dict(l=10, r=10, t=60, b=10)  # 边距设置
        )
        
        logger.info("价格图表创建成功")
        return fig
    
    except Exception as e:
        logger.error(f"创建图表失败: {str(e)}")
        logger.error(traceback.format_exc())
        
        # 返回一个带错误信息的简单图表
        fig = go.Figure()
        fig.add_annotation(
            text=f"创建图表时出错: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(color="red", size=14)
        )
        return fig

def main():
    """主函数 - 创建Dash应用"""
    # 初始化交易所
    exchange, api_key, api_secret = initialize_exchange()
    
    # 设置交易对和时间周期
    symbol = 'NXPC/USDT:USDT'
    timeframe = '1h'
    
    # 获取数据
    df_ohlc = fetch_ohlcv_data(exchange, symbol, timeframe, limit=100)
    
    # 如果有API密钥，尝试获取交易记录
    df_trades = None
    if api_key and api_secret:
        df_trades = fetch_trades(exchange, symbol, limit=50)
    
    # 创建图表
    fig = create_chart(df_ohlc, df_trades, symbol)
    
    # 创建Dash应用
    app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.title = '币安交易数据可视化'
    
    # 定义应用布局
    app.layout = dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H1('币安交易数据可视化示例', className='text-center mt-4 mb-4')
            ])
        ]),
        
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader('价格图表与交易记录'),
                    dbc.CardBody([
                        dcc.Graph(id='trade-chart', figure=fig)
                    ])
                ])
            ])
        ]),
        
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.P('这是一个简单的示例，展示如何使用CCXT获取币安数据并使用Plotly绘制图表。', className='mt-3'),
                    html.P([
                        '交易对: ', 
                        html.Strong(symbol), 
                        ', 时间周期: ', 
                        html.Strong(timeframe)
                    ]),
                    html.P([
                        'K线数据: ', 
                        html.Strong(f"{len(df_ohlc)} 条"), 
                        ', 交易记录: ', 
                        html.Strong(f"{len(df_trades) if df_trades is not None else 0} 条")
                    ]),
                ], className='mt-4 mb-4 text-center')
            ])
        ]),
        
    ], fluid=True)
    
    # 启动应用
    app.run(host='127.0.0.1', port=8050, debug=True, dev_tools_props_check=False)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("用户中断，程序已停止")
    except Exception as e:
        logger.error(f"程序发生错误: {str(e)}")
        logger.error(traceback.format_exc())
