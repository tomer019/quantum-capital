"""
loader.py — הורדת נתונים היסטוריים מ-Yahoo Finance
"""
import yfinance as yf
import pandas as pd
from pathlib import Path

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)


def load_data(symbol: str, start: str, end: str, use_cache: bool = True) -> pd.DataFrame:
    """
    מוריד נתוני OHLCV היסטוריים עבור מניה מסוימת.

    Args:
        symbol: סימול המניה (למשל: 'AAPL', 'SPY', 'MSFT')
        start:  תאריך התחלה בפורמט 'YYYY-MM-DD'
        end:    תאריך סיום  בפורמט 'YYYY-MM-DD'
        use_cache: אם True, שומר ומשתמש בקובץ מקומי

    Returns:
        DataFrame עם עמודות: Open, High, Low, Close, Volume
    """
    cache_file = CACHE_DIR / f"{symbol}_{start}_{end}.csv"

    if use_cache and cache_file.exists():
        print(f"[Data] טוען מ-cache: {symbol}")
        df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
        return df

    print(f"[Data] מוריד נתונים: {symbol} ({start} → {end})")
    ticker = yf.Ticker(symbol)
    df = ticker.history(start=start, end=end, auto_adjust=True)

    if df.empty:
        raise ValueError(f"לא נמצאו נתונים עבור {symbol} בטווח הנבחר.")

    # ניקוי — רק העמודות שאנחנו צריכים
    df = df[["Open", "High", "Low", "Close", "Volume"]]
    df.index = pd.to_datetime(df.index).tz_localize(None)  # הסרת timezone

    if use_cache:
        df.to_csv(cache_file)
        print(f"[Data] נשמר ל-cache: {cache_file.name}")

    return df


def get_available_symbols() -> list[str]:
    """כמה דוגמאות של סימולים פופולריים"""
    return [
        "AAPL",  # אפל
        "MSFT",  # מיקרוסופט
        "SPY",   # S&P 500 ETF
        "QQQ",   # נאסד"ק ETF
        "TSLA",  # טסלה
        "NVDA",  # נבידיה
        "AMZN",  # אמזון
        "GOOGL", # גוגל
    ]
