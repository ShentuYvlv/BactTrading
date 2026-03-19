# BactTrading

本项目已经完成从单文件 Dash 页到前后端分离架构的重构：

- 后端：FastAPI
- 前端：React + Vite + Tailwind CSS
- 图表：Lightweight Charts 5.x

当前定位是本机单机复盘工作台，后续可以直接部署到服务器。

## 目录结构

```text
backend/     FastAPI API、图表服务、CSV/缓存/交易所逻辑
frontend/    React 前端工作台
data/        仓位历史 CSV
cache/       OHLCV 缓存
getPosition.py  仓位重建 CLI
start_server.py 后端启动入口
```

## 功能

- 列出 `data/` 目录下的 CSV，并按最新文件优先加载
- 从 CSV 读取交易对、交易次数和仓位记录
- 从交易所获取 K 线并缓存到 `cache/`
- 指标支持：`EMA20`、`布林带`、`RSI`、`MACD`、`成交量`
- 图表支持：多 pane、十字线 legend、工具条、快捷键、右键菜单、仓位聚焦
- 仓位导航支持：上一笔、下一笔、序号跳转、仓位信息卡
- 保留仓位重建 CLI：支持 `binance` / `okx`

## 安装

### 1. Python 依赖

```bash
pip install -r requirements.txt
```

### 2. 前端依赖

```bash
cd frontend
npm install
cd ..
```

### 3. 环境变量

```bash
cp .env.example .env
```

常用项：

```env
EXCHANGE_PROXY_URL=
APP_HOST=0.0.0.0
APP_PORT=8051
APP_USE_RELOADER=false

BINANCE_API_KEY=
BINANCE_API_SECRET=
OKX_API_KEY=
OKX_API_SECRET=
OKX_API_PASSPHRASE=

CHART_DEFAULT_SYMBOL=NXPC/USDT:USDT
CHART_DEFAULT_TIMEFRAME=1h
CHART_DEFAULT_START_DATE=2025-07-18
CHART_DEFAULT_END_DATE=2025-08-02

POSITION_DEFAULT_EXCHANGE=binance
POSITION_DEFAULT_THREADS=5
POSITION_MAX_RETRIES=3
```

如果你只想看本地 CSV，API Key 可以先留空。

## 启动

### 1. 构建前端

首次启动或前端代码有变动后，先执行：

```bash
cd frontend
npm run build
cd ..
```

### 2. 启动服务

```bash
python start_server.py
```

打开：

```text
http://127.0.0.1:8051
```

FastAPI 会直接托管 `frontend/dist`，不再依赖旧的 Dash 页面。

## 开发模式

前端开发：

```bash
cd frontend
npm run dev
```

后端开发：

```bash
python start_server.py
```

Vite 已代理 `/api` 到 `http://127.0.0.1:8051`。

## 仓位重建

CLI 入口仍保留：

```bash
python getPosition.py -e binance -s 2025-07-18 -n 2025-08-02
```

也可以在新页面左侧“重建仓位”面板直接触发。

生成的数据会写入 `data/`，随后可以直接在页面里切换新 CSV。

## 常用命令

```bash
python start_server.py
python getPosition.py -e binance -s 2025-07-18 -n 2025-08-02
cd frontend && npm run build
cd frontend && npm run dev
```

## 说明

- 旧的 `lightweight_charts.py` 不再是主入口。
- 当前主入口是 `start_server.py -> backend.app.main:app`。
- 如果代理留空，会直接直连交易所。
