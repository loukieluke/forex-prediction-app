import pandas as pd
import ta


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    data = df.copy()
    data["rsi"] = ta.momentum.RSIIndicator(data["close"], window=14).rsi()
    macd = ta.trend.MACD(data["close"], window_fast=12, window_slow=26, window_sign=9)
    data["macd"] = macd.macd()
    data["macd_signal"] = macd.macd_signal()
    bbands = ta.volatility.BollingerBands(data["close"], window=20, window_dev=2)
    data["bb_upper"] = bbands.bollinger_hband()
    data["bb_lower"] = bbands.bollinger_lband()
    data["ema_20"] = ta.trend.EMAIndicator(data["close"], window=20).ema_indicator()
    return data
