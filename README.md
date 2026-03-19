# 币安交易复盘工具

这个项目使用 CCXT 拉取交易所数据，生成仓位历史 CSV，并通过 Dash 图表页面进行交易复盘。

## 功能

- 从币安API获取交易历史
- 在价格图表上标注买入和卖出点
- 可视化展示交易盈亏
- 支持不同时间周期的查看
- 为后期与Backtrader量化框架的集成做准备

## 安装

1. 安装依赖：
   ```
   pip install -r requirements.txt
   ```

2. 复制环境变量模板并填写：
   ```
   cp .env.example .env
   ```

3. 按需要配置 `.env`：
   ```
   BINANCE_API_KEY=您的API密钥
   BINANCE_API_SECRET=您的API密钥Secret
   EXCHANGE_PROXY_URL=socks5://127.0.0.1:10808
   APP_PORT=8051
   CHART_DEFAULT_SYMBOL=BTC/USDT:USDT
   ```

## 使用方法

### 1. 抓取仓位历史到 CSV

```
python getPosition.py -e binance -s 2025-07-18 -n 2025-08-02
```

生成的数据会保存在 `data/` 目录。

### 2. 启动图表页面

```
python start_server.py
```

打开浏览器访问：

```
http://127.0.0.1:8051
```

页面会默认读取 `data/` 中最新的 CSV 文件，你也可以在界面中切换数据文件、交易对、时间周期和日期范围。

### 3. 可选配置

以下运行参数已经改为从 `.env` 读取：

- 代理：`EXCHANGE_PROXY_URL`
- 服务端口与调试：`APP_HOST`、`APP_PORT`、`APP_DEBUG`、`APP_USE_RELOADER`
- 图表默认值：`CHART_DEFAULT_SYMBOL`、`CHART_DEFAULT_TIMEFRAME`、`CHART_DEFAULT_START_DATE`、`CHART_DEFAULT_END_DATE`
- 抓取默认值：`POSITION_DEFAULT_EXCHANGE`、`POSITION_DEFAULT_THREADS`、`POSITION_MAX_RETRIES`

## 注意事项

- 请确保 API 密钥仅授予只读权限
- 如果不需要代理，请将 `EXCHANGE_PROXY_URL` 留空
- 该工具仅用于交易复盘和分析，不提供自动交易功能
