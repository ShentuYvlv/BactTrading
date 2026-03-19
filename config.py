import os
from datetime import datetime, timedelta

from dotenv import load_dotenv


load_dotenv()


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


def get_env_str(key, default=None):
    value = os.getenv(key)
    if value is None:
        return default
    value = value.strip()
    return value if value else default


def get_env_int(key, default):
    value = get_env_str(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_env_bool(key, default=False):
    value = get_env_str(key)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def get_env_date(key, default):
    value = get_env_str(key)
    if value is None:
        return default
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return default


def get_proxy_config():
    proxy_url = get_env_str("EXCHANGE_PROXY_URL")
    if not proxy_url:
        return None
    return {
        "http": proxy_url,
        "https": proxy_url,
    }


def get_common_ccxt_config():
    config = {
        "enableRateLimit": get_env_bool("CCXT_ENABLE_RATE_LIMIT", True),
        "timeout": get_env_int("CCXT_TIMEOUT_MS", 60000),
        "headers": {
            "User-Agent": get_env_str("CCXT_USER_AGENT", DEFAULT_USER_AGENT),
        },
        "verify": get_env_bool("CCXT_VERIFY_SSL", False),
    }
    proxies = get_proxy_config()
    if proxies:
        config["proxies"] = proxies
    return config


def get_chart_defaults():
    today = datetime.now().date()
    default_start_date = today - timedelta(days=1)

    return {
        "symbol": get_env_str("CHART_DEFAULT_SYMBOL", "NXPC/USDT:USDT"),
        "fallback_symbol": get_env_str("CHART_FALLBACK_SYMBOL", "NXPC/USDT:USDT"),
        "timeframe": get_env_str("CHART_DEFAULT_TIMEFRAME", "1h"),
        "start_date": get_env_date("CHART_DEFAULT_START_DATE", default_start_date),
        "end_date": get_env_date("CHART_DEFAULT_END_DATE", today),
        "min_trades": get_env_int("CHART_MIN_TRADES", 5),
    }


def get_server_config():
    return {
        "host": get_env_str("APP_HOST", "0.0.0.0"),
        "port": get_env_int("APP_PORT", 8051),
        "debug": get_env_bool("APP_DEBUG", True),
        "use_reloader": get_env_bool("APP_USE_RELOADER", False),
        "port_fallback_end": get_env_int("APP_PORT_FALLBACK_END", 8060),
    }


def get_position_defaults():
    return {
        "exchange": get_env_str("POSITION_DEFAULT_EXCHANGE", "binance"),
        "threads": get_env_int("POSITION_DEFAULT_THREADS", 5),
        "max_retries": get_env_int("POSITION_MAX_RETRIES", 3),
    }
