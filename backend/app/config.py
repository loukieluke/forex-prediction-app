from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Forex Prediction API"
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_allow_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/forex_app"
    redis_url: str = "redis://localhost:6379/0"

    forex_provider: str = "alphavantage"
    alphavantage_api_key: str = ""
    twelvedata_api_key: str = ""
    news_api_key: str = ""
    use_rss_news: bool = True

    oanda_env: str = "practice"
    oanda_api_token: str = ""
    oanda_account_id: str = ""
    auto_trade_enabled: bool = False
    max_trade_units: int = 1000
    max_trades_per_day: int = 10
    risk_per_trade: float = 0.01
    signal_confidence_threshold: float = 0.65
    prediction_hold_threshold: float = 0.60
    ml_blend_weight: float = 0.45
    strategy_blend_weight: float = 0.55
    blend_hold_band: float = 0.15

    model_path: str = "/app/model_artifacts/latest.joblib"
    sentiment_backend: str = "keyword"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
