from datetime import date

import requests

from app.config import settings


def _is_configured(value: str) -> bool:
    return bool(value and value.strip() and value.strip().lower() != "replace_me")


def validate_oanda_credentials() -> None:
    if not _is_configured(settings.oanda_api_token):
        raise ValueError("OANDA API token is not configured. Set OANDA_API_TOKEN in backend env.")
    if not _is_configured(settings.oanda_account_id):
        raise ValueError("OANDA account ID is not configured. Set OANDA_ACCOUNT_ID in backend env.")


def _base_url() -> str:
    if settings.oanda_env.lower() == "live":
        return "https://api-fxtrade.oanda.com"
    return "https://api-fxpractice.oanda.com"


def _headers() -> dict:
    return {"Authorization": f"Bearer {settings.oanda_api_token}", "Content-Type": "application/json"}


def get_account_summary() -> dict:
    validate_oanda_credentials()
    response = requests.get(
        f"{_base_url()}/v3/accounts/{settings.oanda_account_id}/summary",
        headers=_headers(),
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def get_open_positions() -> dict:
    validate_oanda_credentials()
    response = requests.get(
        f"{_base_url()}/v3/accounts/{settings.oanda_account_id}/openPositions",
        headers=_headers(),
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def get_pricing(instruments: list[str]) -> dict:
    validate_oanda_credentials()
    response = requests.get(
        f"{_base_url()}/v3/accounts/{settings.oanda_account_id}/pricing",
        headers=_headers(),
        params={"instruments": ",".join(instruments)},
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def validate_trade_limits(units: int, trades_today: int) -> None:
    if abs(units) > settings.max_trade_units:
        raise ValueError(f"units exceeds max_trade_units ({settings.max_trade_units})")
    if trades_today >= settings.max_trades_per_day:
        raise ValueError("daily trade limit reached")


def place_market_order(instrument: str, units: int, direction: str, stop_loss_pips: float | None = None) -> dict:
    validate_oanda_credentials()
    signed_units = units if direction == "BUY" else -units
    order: dict = {
        "type": "MARKET",
        "instrument": instrument,
        "units": str(signed_units),
        "timeInForce": "FOK",
        "positionFill": "DEFAULT",
    }
    if stop_loss_pips:
        order["stopLossOnFill"] = {"distance": str(stop_loss_pips / 10000)}
    body = {"order": order}
    response = requests.post(
        f"{_base_url()}/v3/accounts/{settings.oanda_account_id}/orders",
        headers=_headers(),
        json=body,
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def is_auto_trading_enabled() -> bool:
    return settings.auto_trade_enabled and settings.oanda_env.lower() == "practice"


def today_key() -> str:
    return date.today().isoformat()
