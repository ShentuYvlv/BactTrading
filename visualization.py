import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from config import CHART_STYLE
import logging

def create_price_chart(price_df, trade_df=None):
    """
    创建价格图表，可选择性地添加交易标记
    
    参数:
        price_df (pandas.DataFrame): 包含价格数据的DataFrame
        trade_df (pandas.DataFrame, optional): 包含交易数据的DataFrame
        
    返回:
        plotly.graph_objects.Figure: 创建的图表对象
    """
    logger = logging.getLogger(__name__)
    
    try:
        # 检查输入数据
        if price_df.empty:
            logger.warning("价格数据为空，返回空图表")
            fig = go.Figure()
            fig.add_annotation(
                text="无价格数据可显示",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=20)
            )
            return fig
        
        # 检查必要的列是否存在
        required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        for col in required_columns:
            if col not in price_df.columns:
                logger.error(f"价格数据缺少必要的列: {col}")
                raise ValueError(f"价格数据缺少必要的列: {col}")
        
        # 确保时间戳是datetime类型
        if not pd.api.types.is_datetime64_any_dtype(price_df['timestamp']):
            logger.warning("价格数据时间戳不是datetime类型，正在转换...")
            price_df['timestamp'] = pd.to_datetime(price_df['timestamp'])
        
        # 创建包含价格和交易量子图的图表
        logger.info("创建子图...")
        fig = make_subplots(
            rows=2, 
            cols=1, 
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.7, 0.3]
        )
        
        # 添加K线图
        logger.info("添加K线图...")
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
            ),
            row=1, col=1
        )
        
        # 添加交易量柱状图
        logger.info("添加交易量柱状图...")
        colors = np.where(price_df['close'] >= price_df['open'], CHART_STYLE['buy_color'], CHART_STYLE['sell_color'])
        fig.add_trace(
            go.Bar(
                x=price_df['timestamp'],
                y=price_df['volume'],
                name='交易量',
                marker_color=colors,
                opacity=0.5
            ),
            row=2, col=1
        )
        
        # 如果有交易数据，添加交易标记
        if trade_df is not None and not trade_df.empty:
            logger.info("添加交易标记...")
            
            # 检查交易数据是否包含必要的列
            trade_required_columns = ['timestamp', 'side', 'price', 'amount']
            for col in trade_required_columns:
                if col not in trade_df.columns:
                    logger.warning(f"交易数据缺少列: {col}，跳过交易标记")
                    break
            else:  # 如果所有必要的列都存在
                # 确保交易数据的时间戳是datetime类型
                if not pd.api.types.is_datetime64_any_dtype(trade_df['timestamp']):
                    logger.warning("交易数据时间戳不是datetime类型，正在转换...")
                    trade_df['timestamp'] = pd.to_datetime(trade_df['timestamp'])
                
                # 买入标记
                buy_trades = trade_df[trade_df['side'] == 'buy']
                if not buy_trades.empty:
                    logger.info(f"添加 {len(buy_trades)} 个买入标记")
                    try:
                        fig.add_trace(
                            go.Scatter(
                                x=buy_trades['timestamp'],
                                y=buy_trades['price'],
                                mode='markers',
                                name='买入',
                                marker=dict(
                                    symbol='triangle-up',
                                    size=12,
                                    color=CHART_STYLE['buy_color'],
                                    line=dict(width=2, color='white')
                                ),
                                text=[
                                    f"买入: {row['price']}<br>数量: {row['amount']}<br>时间: {row['timestamp']}"
                                    for _, row in buy_trades.iterrows()
                                ],
                                hoverinfo='text'
                            ),
                            row=1, col=1
                        )
                    except Exception as e:
                        logger.error(f"添加买入标记时出错: {e}")
                
                # 卖出标记
                sell_trades = trade_df[trade_df['side'] == 'sell']
                if not sell_trades.empty:
                    logger.info(f"添加 {len(sell_trades)} 个卖出标记")
                    try:
                        fig.add_trace(
                            go.Scatter(
                                x=sell_trades['timestamp'],
                                y=sell_trades['price'],
                                mode='markers',
                                name='卖出',
                                marker=dict(
                                    symbol='triangle-down',
                                    size=12,
                                    color=CHART_STYLE['sell_color'],
                                    line=dict(width=2, color='white')
                                ),
                                text=[
                                    f"卖出: {row['price']}<br>数量: {row['amount']}<br>时间: {row['timestamp']}"
                                    for _, row in sell_trades.iterrows()
                                ],
                                hoverinfo='text'
                            ),
                            row=1, col=1
                        )
                    except Exception as e:
                        logger.error(f"添加卖出标记时出错: {e}")
        
        # 设置图表布局和样式
        logger.info("设置图表布局...")
        fig.update_layout(
            title='价格图表与交易记录',
            xaxis_title='时间',
            yaxis_title='价格',
            xaxis_rangeslider_visible=False,
            plot_bgcolor=CHART_STYLE['plot_bgcolor'],
            paper_bgcolor=CHART_STYLE['paper_bgcolor'],
            font=dict(color=CHART_STYLE['font_color']),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            height=800,
            margin=dict(l=50, r=20, t=50, b=50),
        )
        
        # 设置Y轴网格
        fig.update_yaxes(
            showgrid=True, 
            gridwidth=1, 
            gridcolor=CHART_STYLE['grid_color'],
            zeroline=False
        )
        
        # 设置X轴网格
        fig.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor=CHART_STYLE['grid_color'],
            zeroline=False
        )
        
        logger.info("价格图表创建完成")
        return fig
    
    except Exception as e:
        logger.error(f"创建价格图表时出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # 返回带有错误信息的空图表
        fig = go.Figure()
        fig.add_annotation(
            text=f"创建图表时出错: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="red")
        )
        return fig

def create_trade_summary(trade_df):
    """
    创建交易摘要表格
    
    参数:
        trade_df (pandas.DataFrame): 包含交易数据的DataFrame
        
    返回:
        plotly.graph_objects.Figure: 创建的表格对象
    """
    logger = logging.getLogger(__name__)
    
    try:
        if trade_df.empty:
            logger.warning("交易数据为空，返回空表格")
            fig = go.Figure()
            fig.add_annotation(
                text="无交易数据可显示",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=20)
            )
            return fig
        
        # 检查必要的列是否存在
        required_columns = ['timestamp', 'side', 'price', 'amount', 'cost']
        for col in required_columns:
            if col not in trade_df.columns:
                logger.error(f"交易数据缺少必要的列: {col}")
                raise ValueError(f"交易数据缺少必要的列: {col}")
        
        # 计算每笔交易的盈亏（简化版，实际应考虑手续费等）
        df_summary = trade_df.copy()
        
        # 确保时间戳是datetime类型并格式化
        if not pd.api.types.is_datetime64_any_dtype(df_summary['timestamp']):
            logger.warning("交易摘要时间戳不是datetime类型，正在转换...")
            df_summary['timestamp'] = pd.to_datetime(df_summary['timestamp'])
        
        # 检查是否包含期货特有字段
        is_future = 'position_side' in df_summary.columns and 'realized_pnl' in df_summary.columns
        logger.info(f"是否为期货交易数据: {is_future}")
        
        # 设置表头和单元格值
        header_values = ['时间', '交易方向', '价格', '数量', '成交额']
        cell_values = [
            df_summary['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S'),
            df_summary['side'],
            df_summary['price'].round(4),
            df_summary['amount'].round(6),
            df_summary['cost'].round(2)
        ]
        
        # 如果是期货交易，添加额外字段
        if is_future:
            logger.info("添加期货特有字段到表格")
            header_values.extend(['仓位方向', '已实现盈亏'])
            cell_values.extend([
                df_summary['position_side'],
                df_summary['realized_pnl'].round(4)
            ])
        
        # 设置单元格颜色
        cell_colors = [
            ['white']*len(df_summary),  # 时间列
            [CHART_STYLE['buy_color'] if s == 'buy' else CHART_STYLE['sell_color'] for s in df_summary['side']],  # 交易方向列
            ['white']*len(df_summary),  # 价格列
            ['white']*len(df_summary),  # 数量列
            ['white']*len(df_summary),  # 成交额列
        ]
        
        # 如果是期货交易，为额外字段添加颜色
        if is_future:
            cell_colors.extend([
                ['white']*len(df_summary),  # 仓位方向列
                ['#27ae60' if pnl >= 0 else '#e74c3c' for pnl in df_summary['realized_pnl']]  # 已实现盈亏列
            ])
        
        # 创建表格
        logger.info("创建交易摘要表格...")
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
                    fill_color=cell_colors,
                    align='left',
                    font=dict(color='black'),
                    line=dict(color='#f2f2f2')
                )
            )
        ])
        
        fig.update_layout(
            title='交易记录摘要',
            margin=dict(l=0, r=0, t=30, b=0),
            height=400
        )
        
        logger.info("交易摘要表格创建完成")
        return fig
    
    except Exception as e:
        logger.error(f"创建交易摘要表格时出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # 返回带有错误信息的空图表
        fig = go.Figure()
        fig.add_annotation(
            text=f"创建交易摘要表格时出错: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="red")
        )
        return fig

def calculate_trade_statistics(trade_df):
    """
    计算交易统计数据
    
    参数:
        trade_df (pandas.DataFrame): 包含交易数据的DataFrame
        
    返回:
        dict: 包含统计数据的字典
    """
    if trade_df.empty:
        return {
            'total_trades': 0,
            'buy_trades': 0,
            'sell_trades': 0,
            'total_buy_volume': 0,
            'total_sell_volume': 0,
            'total_buy_cost': 0,
            'total_sell_cost': 0,
            'avg_buy_price': 0,
            'avg_sell_price': 0,
            'is_future': False,
            'total_pnl': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0,
            'total_fee': 0
        }
    
    # 计算基本统计数据
    buy_df = trade_df[trade_df['side'] == 'buy']
    sell_df = trade_df[trade_df['side'] == 'sell']
    
    total_trades = len(trade_df)
    buy_trades = len(buy_df)
    sell_trades = len(sell_df)
    
    total_buy_volume = buy_df['amount'].sum() if not buy_df.empty else 0
    total_sell_volume = sell_df['amount'].sum() if not sell_df.empty else 0
    
    total_buy_cost = buy_df['cost'].sum() if not buy_df.empty else 0
    total_sell_cost = sell_df['cost'].sum() if not sell_df.empty else 0
    
    avg_buy_price = total_buy_cost / total_buy_volume if total_buy_volume > 0 else 0
    avg_sell_price = total_sell_cost / total_sell_volume if total_sell_volume > 0 else 0
    
    # 计算总手续费
    total_fee = trade_df['fee'].sum() if 'fee' in trade_df.columns else 0
    
    # 检查是否包含期货交易的特定字段
    is_future = 'realized_pnl' in trade_df.columns
    
    # 期货交易特有的统计
    total_pnl = 0
    winning_trades = 0
    losing_trades = 0
    win_rate = 0
    
    if is_future:
        total_pnl = trade_df['realized_pnl'].sum()
        winning_trades = len(trade_df[trade_df['realized_pnl'] > 0])
        losing_trades = len(trade_df[trade_df['realized_pnl'] < 0])
        # 计算胜率
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
    
    # 返回统计数据
    return {
        'total_trades': total_trades,
        'buy_trades': buy_trades,
        'sell_trades': sell_trades,
        'total_buy_volume': total_buy_volume,
        'total_sell_volume': total_sell_volume,
        'total_buy_cost': total_buy_cost,
        'total_sell_cost': total_sell_cost,
        'avg_buy_price': avg_buy_price,
        'avg_sell_price': avg_sell_price,
        'is_future': is_future,
        'total_pnl': total_pnl,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'total_fee': total_fee
    } 