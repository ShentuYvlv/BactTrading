import dash
from dash import dcc, html, callback, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta
import pandas as pd
import time
import plotly.graph_objects as go
import logging
import os
from dash.dash_table.Format import Format

from binance_api import BinanceAPI
from visualization import create_price_chart, create_trade_summary, calculate_trade_statistics
from config import APP_PORT, APP_HOST, DEBUG_MODE, TIMEFRAMES, SYMBOLS, FUTURES_SYMBOLS, DEFAULT_SYMBOL, CHART_STYLE, PROXY_CONFIG

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化币安API
logger.info("正在初始化币安API...")
binance_api = BinanceAPI(market_type='future')  # 使用合约/期货模式

# 初始化Dash应用
app = dash.Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title='币安交易复盘工具'
)

# 定义应用布局
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1('币安交易复盘工具', className='text-center mt-4 mb-4')
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader('API连接状态'),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            dbc.Button('测试API连接', id='test-connection-button', color='primary', className='w-100')
                        ], width=4),
                        dbc.Col([
                            html.Div(id='connection-status', className='d-flex align-items-center h-100')
                        ], width=8)
                    ])
                ])
            ], className='mb-4')
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader('设置'),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label('交易对'),
                            dcc.Dropdown(
                                id='symbol-dropdown',
                                options=[{'label': s, 'value': s} for s in FUTURES_SYMBOLS],
                                value=DEFAULT_SYMBOL,
                                clearable=False
                            )
                        ], width=4),
                        dbc.Col([
                            html.Label('时间周期'),
                            dcc.Dropdown(
                                id='timeframe-dropdown',
                                options=[{'label': k, 'value': v} for k, v in TIMEFRAMES.items()],
                                value='4h',
                                clearable=False
                            )
                        ], width=3),
                        dbc.Col([
                            html.Label('日期范围'),
                            dcc.DatePickerRange(
                                id='date-range-picker',
                                start_date=(datetime.now() - timedelta(days=30)).date(),
                                end_date=datetime.now().date(),
                                display_format='YYYY-MM-DD'
                            )
                        ], width=5)
                    ], className='mb-3'),
                    dbc.Row([
                        dbc.Col([
                            dbc.Button('加载数据', id='load-data-button', color='primary', className='w-100')
                        ], width=4)
                    ])
                ])
            ], className='mb-4')
        ])
    ]),
    
    dbc.Row([
        dbc.Col([
            dbc.Spinner(
                dcc.Graph(id='price-chart', style={'height': '70vh'})
            )
        ])
    ], className='mb-4'),
    
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader('交易统计'),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Div(id='trade-stats')
                        ])
                    ])
                ])
            ])
        ], width=4),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader('交易记录'),
                dbc.CardBody([
                    dbc.Spinner(
                        dcc.Graph(id='trade-summary', style={'height': '40vh'})
                    )
                ])
            ])
        ], width=8)
    ], className='mb-4'),
    
    dbc.Row([
        dbc.Col([
            html.Div(id='temp-storage', style={'display': 'none'})
        ])
    ]),
    
], fluid=True)

# 回调函数：测试API连接
@app.callback(
    Output('connection-status', 'children'),
    Input('test-connection-button', 'n_clicks'),
    prevent_initial_call=True
)
def update_connection_status(n_clicks):
    """测试币安API连接并更新状态"""
    if n_clicks:
        logging.info("开始测试币安API连接...")
        
        # 测试连接
        success = binance_api.test_connection()
        
        if success:
            return html.Div([
                html.I(className="bi bi-check-circle-fill me-2", style={"color": "green"}),
                "连接成功!"
            ])
    else:
            return html.Div([
                html.I(className="bi bi-x-circle-fill me-2", style={"color": "red"}),
                "连接失败!"
            ])
    
    return "未测试"

# 回调函数：加载数据
@app.callback(
    [
        Output('temp-storage', 'children'),
        Output('load-data-button', 'children'),
        Output('load-data-button', 'disabled')
    ],
    Input('load-data-button', 'n_clicks'),
    [
        State('symbol-dropdown', 'value'),
        State('timeframe-dropdown', 'value'),
        State('date-range-picker', 'start_date'),
        State('date-range-picker', 'end_date'),
    ],
    prevent_initial_call=True
)
def load_data(n_clicks, symbol, timeframe, start_date, end_date):
    if n_clicks is None:
        return dash.no_update, dash.no_update, dash.no_update
    
    # 禁用按钮并显示加载中
    button_text = '数据加载中...'
    button_disabled = True
    
    try:
        # 将日期转换为时间戳
        start_timestamp = int(time.mktime(datetime.strptime(start_date, '%Y-%m-%d').timetuple()) * 1000)
        end_timestamp = int(time.mktime(datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59).timetuple()) * 1000)
        
        logger.info(f"加载交易对 {symbol} 的数据，时间范围: {start_date} 至 {end_date}, 时间周期: {timeframe}")
        
        # 获取价格历史数据
        price_df = binance_api.get_price_history(
            symbol=symbol,
            timeframe=timeframe,
            since=start_timestamp,
            limit=1000  # 获取足够的数据点
        )
        
        logger.info(f"获取到 {len(price_df)} 条价格历史数据")
        
        # 获取个人交易记录
        trade_df = binance_api.get_my_trades(
            symbol=symbol, 
            since=start_timestamp,
            limit=1000  # 获取足够的交易记录
        )
        
        logger.info(f"获取到 {len(trade_df)} 条交易记录")
        
        # 确保时间戳列是日期时间格式
        if 'timestamp' in price_df.columns and not pd.api.types.is_datetime64_any_dtype(price_df['timestamp']):
            price_df['timestamp'] = pd.to_datetime(price_df['timestamp'])
            
        if not trade_df.empty and 'timestamp' in trade_df.columns and not pd.api.types.is_datetime64_any_dtype(trade_df['timestamp']):
            trade_df['timestamp'] = pd.to_datetime(trade_df['timestamp'])
        
        # 将数据转换为JSON格式存储，使用简单字符串格式
        try:
            # 使用json模块替代pd.to_json，可能更稳定
            import json
            
            # 将DataFrame转换为可序列化的字典
            price_data = price_df.to_dict('records')
            trade_data = trade_df.to_dict('records')
            
            # 转换日期时间为字符串
            for record in price_data:
                if 'timestamp' in record and pd.api.types.is_datetime64_any_dtype(pd.Series([record['timestamp']])):
                    record['timestamp'] = record['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                    
            for record in trade_data:
                if 'timestamp' in record and pd.api.types.is_datetime64_any_dtype(pd.Series([record['timestamp']])):
                    record['timestamp'] = record['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
            
        data = {
                'price_data': price_data,
                'trade_data': trade_data,
                'symbol': symbol,
                'timeframe': timeframe
            }
            
            json_data = json.dumps(data)
            logger.info(f"数据JSON序列化成功，数据大小: {len(json_data)} 字节")
        
        # 重新启用按钮
        button_text = '重新加载数据'
        button_disabled = False
        
            return json_data, button_text, button_disabled
        
        except Exception as e:
            logger.error(f"数据JSON序列化失败: {e}")
            raise
    
    except Exception as e:
        logger.error(f"加载数据时出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        # 重新启用按钮
        button_text = '加载失败，请重试'
        button_disabled = False
        return '{}', button_text, button_disabled

# 回调函数：更新价格图表
@app.callback(
    Output('price-chart', 'figure'),
    Input('temp-storage', 'children'),
    prevent_initial_call=True
)
def update_price_chart(json_data):
    if not json_data or json_data == '{}':
        # 返回空图表
        logger.warning("未找到有效数据，返回空图表")
        # 创建一个简单的空图表，避免复杂结构
        fig = go.Figure()
        fig.update_layout(
            title='无可用数据',
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            annotations=[
                dict(
                    text="无可用价格数据",
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                    font=dict(size=20)
                )
            ],
            template='plotly_white'
        )
        return fig
    
    try:
        # 解析JSON数据
        import json
        logger.info("正在解析JSON数据...")
        
        try:
            data = json.loads(json_data)
        except Exception as e:
            logger.error(f"JSON数据解析失败: {e}")
            logger.error(f"数据内容: {json_data[:100]}...")  # 只记录前100个字符
            raise
        
        logger.info("正在读取价格和交易数据...")
        try:
            # 转换列表数据为DataFrame
            price_data = data['price_data']
            logger.info(f"价格数据读取成功，共 {len(price_data)} 条记录")
            
            # 创建DataFrame并转换时间戳
            price_df = pd.DataFrame(price_data)
            if 'timestamp' in price_df.columns:
                price_df['timestamp'] = pd.to_datetime(price_df['timestamp'])
                logger.info("价格数据时间戳转换成功")
    except Exception as e:
            logger.error(f"价格数据读取失败: {e}")
            raise
            
        try:
            # 转换列表数据为DataFrame
            trade_data = data['trade_data']
            logger.info(f"交易数据读取成功，共 {len(trade_data)} 条记录")
            
            # 创建DataFrame并转换时间戳
            trade_df = pd.DataFrame(trade_data)
            if not trade_df.empty and 'timestamp' in trade_df.columns:
                trade_df['timestamp'] = pd.to_datetime(trade_df['timestamp'])
                logger.info("交易数据时间戳转换成功")
        except Exception as e:
            logger.error(f"交易数据读取失败: {e}")
            raise
        
        logger.info("开始创建价格图表...")
        # 尝试先创建一个简单的图表，确认基本渲染功能正常
        try:
            # 创建简单的图表
            fig = go.Figure()
            
            # 添加K线图
            fig.add_trace(
                go.Candlestick(
                    x=price_df['timestamp'],
                    open=price_df['open'],
                    high=price_df['high'],
                    low=price_df['low'],
                    close=price_df['close'],
                    name='价格',
                    increasing_line_color=CHART_STYLE['buy_color'],
                    decreasing_line_color=CHART_STYLE['sell_color'],
                )
            )
            
            # 设置图表布局和样式
            fig.update_layout(
                title='价格图表',
                xaxis_title='时间',
                yaxis_title='价格',
                template='plotly_white'
            )
            
            logger.info("简化价格图表创建成功！")
            return fig
            
        except Exception as e:
            logger.error(f"简化图表创建失败: {e}")
            # 如果简化图表失败，尝试原始创建方法
            fig = create_price_chart(price_df, trade_df)
            logger.info("原始价格图表创建成功！")
        return fig
    
    except Exception as e:
        logger.error(f"更新价格图表时出错: {e}")
        import traceback
        trace = traceback.format_exc()
        logger.error(f"详细错误信息: {trace}")
        
        # 返回带有错误信息的简单图表
        fig = go.Figure()
        fig.update_layout(
            title='图表创建错误',
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            annotations=[
                dict(
                    text=f"创建图表时出错: {str(e)}",
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                    font=dict(size=14, color="red")
                )
            ],
            template='plotly_white'
        )
        return fig

# 回调函数：更新交易统计
@app.callback(
    Output('trade-stats', 'children'),
    Input('temp-storage', 'children'),
    State('symbol-dropdown', 'value'),
    prevent_initial_call=True
)
def update_trade_stats(json_data, symbol):
    if not json_data or json_data == '{}':
        # 返回空内容
        return html.Div("无可用数据")
    
    try:
        # 解析JSON数据
        import json
        logger.info("正在解析交易统计JSON数据...")
        
        try:
            data = json.loads(json_data)
            symbol = data.get('symbol', symbol)  # 使用JSON中的symbol如果有的话
        except Exception as e:
            logger.error(f"交易统计JSON数据解析失败: {e}")
            raise
        
        logger.info("正在读取交易统计数据...")
        try:
            # 转换列表数据为DataFrame
            trade_data = data['trade_data']
            logger.info(f"交易统计数据读取成功，共 {len(trade_data)} 条记录")
            
            # 创建DataFrame并转换时间戳
            trade_df = pd.DataFrame(trade_data)
            if not trade_df.empty and 'timestamp' in trade_df.columns:
                trade_df['timestamp'] = pd.to_datetime(trade_df['timestamp'])
                logger.info("交易统计数据时间戳转换成功")
        except Exception as e:
            logger.error(f"交易统计数据读取失败: {e}")
            raise
        
        if trade_df.empty:
            return html.Div(f"未找到{symbol}的交易记录")
        
        # 计算交易统计
        logger.info("开始计算交易统计...")
        stats = calculate_trade_statistics(trade_df)
        logger.info("交易统计计算完成")
        
        # 判断是否有实现盈亏数据
        has_pnl = 'realized_pnl' in trade_df.columns
        
        # 创建统计卡片
        cards = []
        
        # 添加交易次数卡片
        cards.append(
            dbc.Card([
                dbc.CardBody([
                    html.H5("总交易次数", className="card-title"),
                    html.P(f"{stats['total_trades']}", className="card-text fs-4 text-center")
                ])
            ], className="mb-3")
        )
        
        # 添加盈利交易卡片
        win_pct = stats['win_rate'] * 100 if 'win_rate' in stats else 0
        cards.append(
            dbc.Card([
                dbc.CardBody([
                    html.H5("胜率", className="card-title"),
                    html.P(f"{win_pct:.1f}%", className="card-text fs-4 text-center text-success")
                ])
            ], className="mb-3")
        )
        
        # 如果有实现盈亏数据，添加盈亏卡片
        if has_pnl:
            pnl_color = "text-success" if stats.get('total_pnl', 0) >= 0 else "text-danger"
            cards.append(
                dbc.Card([
                    dbc.CardBody([
                        html.H5("总实现盈亏", className="card-title"),
                        html.P(f"{stats.get('total_pnl', 0):.2f} USDT", className=f"card-text fs-4 text-center {pnl_color}")
                    ])
                ], className="mb-3")
            )
        
        # 添加总手续费卡片
        cards.append(
            dbc.Card([
                dbc.CardBody([
                    html.H5("总手续费", className="card-title"),
                    html.P(f"{stats.get('total_fee', 0):.4f}", className="card-text fs-4 text-center text-warning")
                ])
            ], className="mb-3")
        )
        
        # 添加平均持仓时间卡片（如果有）
        if 'avg_holding_time' in stats:
            cards.append(
                dbc.Card([
                    dbc.CardBody([
                        html.H5("平均持仓时间", className="card-title"),
                        html.P(f"{stats['avg_holding_time']}", className="card-text fs-4 text-center")
                    ])
                ], className="mb-3")
            )
        
        # 布局卡片
        card_rows = []
        for i in range(0, len(cards), 2):
            row_cards = cards[i:i+2]
            row = dbc.Row([
                dbc.Col(card, width=6)
                for card in row_cards
            ])
            card_rows.append(row)
        
        logger.info("交易统计卡片创建完成")
        return html.Div(card_rows)
    
    except Exception as e:
        logger.error(f"更新交易统计时出错: {e}")
        import traceback
        trace = traceback.format_exc()
        logger.error(f"详细错误信息: {trace}")
        return html.Div(f"计算交易统计时出错: {str(e)}")

# 回调函数：更新交易摘要
@app.callback(
    Output('trade-summary', 'figure'),
    Input('temp-storage', 'children'),
    prevent_initial_call=True
)
def update_trade_summary(json_data):
    if not json_data or json_data == '{}':
        # 返回空图表
        logger.warning("未找到有效数据，返回空交易摘要图表")
        fig = go.Figure()
        fig.update_layout(
            title='无可用数据',
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            annotations=[
                dict(
                    text="无可用交易数据",
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                    font=dict(size=20)
                )
            ],
            template='plotly_white'
        )
        return fig
    
    try:
        # 解析JSON数据
        import json
        logger.info("正在解析交易摘要JSON数据...")
        
        try:
            data = json.loads(json_data)
        except Exception as e:
            logger.error(f"交易摘要JSON数据解析失败: {e}")
            raise
        
        logger.info("正在读取交易数据...")
        try:
            # 转换列表数据为DataFrame
            trade_data = data['trade_data']
            logger.info(f"交易数据读取成功，共 {len(trade_data)} 条记录")
            
            # 创建DataFrame并转换时间戳
            trade_df = pd.DataFrame(trade_data)
            if not trade_df.empty and 'timestamp' in trade_df.columns:
                trade_df['timestamp'] = pd.to_datetime(trade_df['timestamp'])
                logger.info("交易数据时间戳转换成功")
        except Exception as e:
            logger.error(f"交易数据读取失败: {e}")
            raise
        
        if trade_df.empty:
            # 返回一个带有提示的空图表
            logger.warning("交易数据为空，返回空图表")
            fig = go.Figure()
            fig.update_layout(
                title='无可用数据',
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                annotations=[
                    dict(
                        text="无可用交易数据",
                        xref="paper",
                        yref="paper",
                        x=0.5,
                        y=0.5,
                        showarrow=False,
                        font=dict(size=20)
                    )
                ],
                template='plotly_white'
            )
            return fig
        
        # 创建交易摘要图表
        logger.info("开始创建交易摘要图表...")
        
        # 尝试创建简单的交易摘要表格
        try:
            # 简化版交易摘要表格
            header_values = ['时间', '交易方向', '价格', '数量', '成交额']
            
            # 获取前10条数据用于显示
            display_df = trade_df.head(10)
            
            cell_values = [
                display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S'),
                display_df['side'],
                display_df['price'].round(4),
                display_df['amount'].round(6),
                display_df['cost'].round(2)
            ]
            
            fig = go.Figure(data=[
                go.Table(
                    header=dict(
                        values=header_values,
                        fill_color='#f2f2f2',
                        align='left',
                        font=dict(color='black', size=12)
                    ),
                    cells=dict(
                        values=cell_values,
                        align='left',
                        font=dict(color='black'),
                        line=dict(color='#f2f2f2')
                    )
                )
            ])
            
            fig.update_layout(
                title=f'交易记录摘要 (显示前{len(display_df)}条，共{len(trade_df)}条)',
                margin=dict(l=0, r=0, t=30, b=0),
                height=400
            )
            
            logger.info("简化交易摘要表格创建成功！")
            return fig
            
        except Exception as e:
            logger.error(f"简化交易摘要表格创建失败: {e}")
            # 如果简化表格失败，尝试原始创建方法
            fig = create_trade_summary(trade_df)
            logger.info("原始交易摘要表格创建成功！")
            return fig
    
    except Exception as e:
        logger.error(f"更新交易摘要时出错: {e}")
        import traceback
        trace = traceback.format_exc()
        logger.error(f"详细错误信息: {trace}")
        
        fig = go.Figure()
        fig.update_layout(
            title='交易摘要创建错误',
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            annotations=[
                dict(
                    text=f"更新交易摘要时出错: {str(e)}",
                    xref="paper",
                    yref="paper",
                    x=0.5,
                    y=0.5,
                    showarrow=False,
                    font=dict(size=14, color="red")
                )
            ],
            template='plotly_white'
        )
        return fig

# 启动应用程序
if __name__ == '__main__':
    logger.info("正在初始化币安交易复盘工具...")
    logger.info(f"使用代理配置: {PROXY_CONFIG}")
    logger.info(f"环境变量代理: HTTP_PROXY={os.environ.get('HTTP_PROXY')}, HTTPS_PROXY={os.environ.get('HTTPS_PROXY')}")
    
    # 测试API连接
    connection_status = binance_api.test_connection()
    if connection_status:
        logger.info("API连接测试成功，启动Web应用...")
    else:
        logger.warning("警告: API连接测试失败，但仍将尝试启动Web应用...")
        logger.warning("可能需要检查以下内容:")
        logger.warning("1. 币安API密钥是否正确")
        logger.warning("2. 代理设置是否正确")
        logger.warning("3. 网络连接是否正常")
    
    # 将启动信息打印到控制台
    print("\n" + "="*80)
    print(f"币安交易复盘工具已启动，请访问: http://{APP_HOST}:{APP_PORT}")
    print("如果使用本地主机，也可以访问: http://localhost:8050")
    print("="*80 + "\n")
    
    # 配置Dash应用程序
    app.title = '币安交易复盘工具'
    
    # 防止浏览器缓存资源
    app.config.suppress_callback_exceptions = True
    
    # 启动应用程序
    app.run(host=APP_HOST, 
            port=APP_PORT, 
            debug=DEBUG_MODE,
            dev_tools_ui=DEBUG_MODE,
            dev_tools_props_check=False,
            dev_tools_hot_reload=DEBUG_MODE) 