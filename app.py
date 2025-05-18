import dash
from dash import dcc, html, callback, Input, Output, State
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta
import pandas as pd
import time
import plotly.graph_objects as go

from binance_api import BinanceAPI
from visualization import create_price_chart, create_trade_summary, calculate_trade_statistics
from config import APP_PORT, APP_HOST, DEBUG_MODE, TIMEFRAMES, SYMBOLS, FUTURES_SYMBOLS, DEFAULT_SYMBOL, CHART_STYLE, PROXY_CONFIG

# 初始化币安API
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
                        ], width=4),
                        dbc.Col([
                            html.Div(id='connection-status')
                        ], width=8)
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
    Input('symbol-dropdown', 'value'),
    prevent_initial_call=True
)
def update_connection_status(symbol):
    if binance_api.test_connection():
        return html.Span('API连接正常', style={'color': 'green'})
    else:
        return html.Span('API连接失败，请检查您的API密钥设置', style={'color': 'red'})

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
        
        # 获取价格历史数据
        price_df = binance_api.get_price_history(
            symbol=symbol,
            timeframe=timeframe,
            since=start_timestamp,
            limit=1000  # 获取足够的数据点
        )
        
        # 获取个人交易记录
        trade_df = binance_api.get_my_trades(
            symbol=symbol, 
            since=start_timestamp,
            limit=1000  # 获取足够的交易记录
        )
        
        # 将数据转换为JSON格式存储
        data = {
            'price_data': price_df.to_json(date_format='iso', orient='split'),
            'trade_data': trade_df.to_json(date_format='iso', orient='split')
        }
        
        # 重新启用按钮
        button_text = '重新加载数据'
        button_disabled = False
        
        return str(data), button_text, button_disabled
    
    except Exception as e:
        print(f"加载数据时出错: {e}")
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
        return go.Figure()
    
    try:
        # 解析JSON数据
        import json
        data = eval(json_data)
        
        price_df = pd.read_json(data['price_data'], orient='split')
        trade_df = pd.read_json(data['trade_data'], orient='split')
        
        # 创建图表
        fig = create_price_chart(price_df, trade_df)
        return fig
    
    except Exception as e:
        print(f"更新价格图表时出错: {e}")
        return go.Figure()

# 回调函数：更新交易摘要
@app.callback(
    Output('trade-summary', 'figure'),
    Input('temp-storage', 'children'),
    prevent_initial_call=True
)
def update_trade_summary(json_data):
    if not json_data or json_data == '{}':
        # 返回空图表
        return go.Figure()
    
    try:
        # 解析JSON数据
        import json
        data = eval(json_data)
        
        trade_df = pd.read_json(data['trade_data'], orient='split')
        
        # 创建交易摘要表格
        fig = create_trade_summary(trade_df)
        return fig
    
    except Exception as e:
        print(f"更新交易摘要时出错: {e}")
        return go.Figure()

# 回调函数：更新交易统计
@app.callback(
    Output('trade-stats', 'children'),
    Input('temp-storage', 'children'),
    State('symbol-dropdown', 'value'),
    prevent_initial_call=True
)
def update_trade_stats(json_data, symbol):
    if not json_data or json_data == '{}':
        return html.Div('无数据')
    
    try:
        # 解析JSON数据
        import json
        data = eval(json_data)
        
        trade_df = pd.read_json(data['trade_data'], orient='split')
        
        # 计算交易统计
        stats = calculate_trade_statistics(trade_df)
        
        # 基本统计信息
        base_stats = [
            html.H5(f"{symbol}交易统计"),
            html.Div([
                html.P(f"总交易次数: {stats['total_trades']}"),
                html.P(f"买入次数: {stats['buy_trades']}"),
                html.P(f"卖出次数: {stats['sell_trades']}"),
                html.Hr(),
                html.P(f"总买入量: {stats['total_buy_volume']:.6f}"),
                html.P(f"总卖出量: {stats['total_sell_volume']:.6f}"),
                html.Hr(),
                html.P(f"总买入金额: {stats['total_buy_cost']:.2f} USDT"),
                html.P(f"总卖出金额: {stats['total_sell_cost']:.2f} USDT"),
                html.Hr(),
                html.P(f"平均买入价: {stats['avg_buy_price']:.4f} USDT"),
                html.P(f"平均卖出价: {stats['avg_sell_price']:.4f} USDT"),
            ])
        ]
        
        # 如果是期货交易，添加额外的盈亏统计
        if stats['is_future']:
            future_stats = html.Div([
                html.Hr(),
                html.H5("合约交易统计"),
                html.P(f"总实现盈亏: {stats['total_pnl']:.4f} USDT", 
                       style={'color': 'green' if stats['total_pnl'] >= 0 else 'red'}),
                html.P(f"盈利交易: {stats['winning_trades']}"),
                html.P(f"亏损交易: {stats['losing_trades']}"),
                html.P(f"胜率: {stats['winning_trades']/stats['total_trades']*100:.2f}%" if stats['total_trades'] > 0 else "胜率: 0%"),
            ])
            return html.Div(base_stats + [future_stats])
        else:
            return html.Div(base_stats)
    
    except Exception as e:
        print(f"更新交易统计时出错: {e}")
        import traceback
        traceback.print_exc()
        return html.Div('统计数据加载失败')

# 启动应用程序
if __name__ == '__main__':
    print("正在初始化币安交易复盘工具...")
    print(f"使用代理配置: {PROXY_CONFIG}")
    
    # 测试API连接
    connection_status = binance_api.test_connection()
    if connection_status:
        print("API连接测试成功，启动Web应用...")
    else:
        print("警告: API连接测试失败，但仍将尝试启动Web应用...")
        print("可能需要检查以下内容:")
        print("1. 币安API密钥是否正确")
        print("2. 代理设置是否正确")
        print("3. 网络连接是否正常")
    
    app.run(host=APP_HOST, port=APP_PORT, debug=DEBUG_MODE) 