from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/api/system", tags=["system"])


def _is_configured(value: str) -> bool:
    return bool(value and value.strip() and value.strip().lower() != "replace_me")


@router.get("/readiness")
def readiness():
    alphavantage_ready = _is_configured(settings.alphavantage_api_key)
    twelvedata_ready = _is_configured(settings.twelvedata_api_key)
    newsapi_ready = _is_configured(settings.news_api_key)
    oanda_token_ready = _is_configured(settings.oanda_api_token)
    oanda_account_ready = _is_configured(settings.oanda_account_id)
    oanda_ready = oanda_token_ready and oanda_account_ready
    model_ready = settings.model_path != "" and settings.model_path is not None

    return {
        "overall_ready": alphavantage_ready or twelvedata_ready,
        "app_env": settings.app_env,
        "providers": {
            "forex": {
                "selected_provider": settings.forex_provider,
                "alphavantage_ready": alphavantage_ready,
                "twelvedata_ready": twelvedata_ready,
                "any_forex_source_ready": alphavantage_ready or twelvedata_ready,
            },
            "news": {
                "rss_enabled": settings.use_rss_news,
                "newsapi_ready": newsapi_ready,
                "any_news_source_ready": settings.use_rss_news or newsapi_ready,
            },
            "broker": {
                "oanda_env": settings.oanda_env,
                "oanda_token_ready": oanda_token_ready,
                "oanda_account_ready": oanda_account_ready,
                "oanda_ready": oanda_ready,
                "auto_trade_enabled": settings.auto_trade_enabled,
            },
        },
        "model": {
            "model_path": settings.model_path,
            "configured": model_ready,
        },
        "notes": [
            "A source is considered not ready if empty or set to 'replace_me'.",
            "RSS can keep news ingestion functional even when NewsAPI is not configured.",
            "Auto trade should remain disabled until OANDA practice credentials are verified.",
        ],
    }
