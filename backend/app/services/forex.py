from datetime import datetime, timezone
import logging

import requests

from app.config import settings

logger = logging.getLogger(__name__)


def _to_instrument(from_symbol: str, to_symbol: str) -> str:
    return f"{from_symbol}_{to_symbol}"


def fetch_alphavantage_candles(from_symbol: str, to_symbol: str, interval: str = "60min") -> list[dict]:
    if not settings.alphavantage_api_key or settings.alphavantage_api_key == "replace_me":
        return []

    url = "https://www.alphavantage.co/query"
    params = {
        "function": "FX_INTRADAY",
        "from_symbol": from_symbol,
        "to_symbol": to_symbol,
        "interval": interval,
        "apikey": settings.alphavantage_api_key,
        "outputsize": "compact",
    }
    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        logger.warning("Alpha Vantage request failed", exc_info=True)
        return []
    key = f"Time Series FX ({interval})"
    rows = payload.get(key, {})
    instrument = _to_instrument(from_symbol, to_symbol)
    normalized = []
    for ts, item in rows.items():
        normalized.append(
            {
                "instrument": instrument,
                "granularity": "H1" if interval == "60min" else interval,
                "time": datetime.fromisoformat(ts).replace(tzinfo=timezone.utc),
                "open": float(item["1. open"]),
                "high": float(item["2. high"]),
                "low": float(item["3. low"]),
                "close": float(item["4. close"]),
                "volume": float(item.get("5. volume", 0)),
            }
        )
    return sorted(normalized, key=lambda x: x["time"])


def fetch_twelvedata_candles(symbol: str = "EUR/USD", interval: str = "1h", outputsize: int = 200) -> list[dict]:
    if not settings.twelvedata_api_key or settings.twelvedata_api_key == "replace_me":
        return []
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": settings.twelvedata_api_key,
    }
    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException:
        logger.warning("TwelveData request failed", exc_info=True)
        return []
    values = payload.get("values", [])
    instrument = symbol.replace("/", "_")
    normalized = []
    for item in values:
        normalized.append(
            {
                "instrument": instrument,
                "granularity": "H1" if interval in {"1h", "60min"} else interval.upper(),
                "time": datetime.fromisoformat(item["datetime"]).replace(tzinfo=timezone.utc),
                "open": float(item["open"]),
                "high": float(item["high"]),
                "low": float(item["low"]),
                "close": float(item["close"]),
                "volume": float(item.get("volume", 0)),
            }
        )
    return sorted(normalized, key=lambda x: x["time"])


def fetch_forex_candles(instrument: str = "EUR_USD", granularity: str = "H1") -> list[dict]:
    if settings.forex_provider == "twelvedata":
        return fetch_twelvedata_candles(symbol=instrument.replace("_", "/"), interval="1h")
    from_symbol, to_symbol = instrument.split("_")
    return fetch_alphavantage_candles(from_symbol=from_symbol, to_symbol=to_symbol, interval="60min")
