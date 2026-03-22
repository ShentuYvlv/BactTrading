from __future__ import annotations

import logging
import time

import ccxt
import urllib3

from backend.app.core.config import settings


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)


def _common_config(*, use_proxy: bool = True) -> dict:
    config = {
        "enableRateLimit": settings.ccxt_enable_rate_limit,
        "timeout": settings.ccxt_timeout_ms,
        "headers": {"User-Agent": settings.ccxt_user_agent},
        "verify": settings.ccxt_verify_ssl,
    }
    if use_proxy and settings.exchange_proxy_url:
        config["proxies"] = {
            "http": settings.exchange_proxy_url,
            "https": settings.exchange_proxy_url,
        }
    return config


def create_exchange(exchange_name: str = "binance", require_auth: bool = False, *, use_proxy: bool = True):
    exchange_name = exchange_name.lower()
    config = _common_config(use_proxy=use_proxy)

    if exchange_name == "binance":
        config["options"] = {
            "defaultType": settings.binance_default_type,
            "adjustForTimeDifference": True,
            "recvWindow": settings.ccxt_recv_window,
            "warnOnFetchOHLCVLimitArgument": False,
            "createMarketBuyOrderRequiresPrice": False,
            "fetchOHLCVWarning": False,
        }
        if require_auth:
            if not settings.binance_api_key or not settings.binance_api_secret:
                raise ValueError("缺少币安API密钥")
            config["apiKey"] = settings.binance_api_key
            config["secret"] = settings.binance_api_secret
        exchange = ccxt.binance(config)
    elif exchange_name == "okx":
        config["options"] = {
            "defaultType": settings.okx_default_type,
            "adjustForTimeDifference": True,
        }
        if require_auth:
            if not settings.okx_api_key or not settings.okx_api_secret or not settings.okx_api_passphrase:
                raise ValueError("缺少OKX API密钥")
            config["apiKey"] = settings.okx_api_key
            config["secret"] = settings.okx_api_secret
            config["password"] = settings.okx_api_passphrase
        exchange = ccxt.okx(config)
    else:
        raise ValueError(f"不支持的交易所: {exchange_name}")

    try:
        if hasattr(exchange, "load_time_difference"):
            exchange.load_time_difference()
        server_time = exchange.fetch_time()
        local_time = int(time.time() * 1000)
        logger.info("%s 连接成功，服务器时间差: %s", exchange_name.upper(), abs(server_time - local_time))
    except Exception as exc:
        logger.warning("同步交易所时间失败: %s", exc)

    return exchange
