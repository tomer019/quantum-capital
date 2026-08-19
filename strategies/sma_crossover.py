"""
sma_crossover.py — אסטרטגיית Moving Average Crossover

הלוגיקה:
  - חשב שני ממוצעים נעים: קצר (fast) וארוך (slow)
  - כשה-fast חוצה מעל ה-slow → קנה (BUY)
  - כשה-fast חוצה מתחת ל-slow → מכור (SELL)
  - אחרת → המתן (HOLD)
"""
import pandas as pd
from strategies.base_strategy import BaseStrategy, Signal


class SMACrossover(BaseStrategy):
    """
    אסטרטגיית חיתוך ממוצעים נעים פשוטה.

    Args:
        symbol:     סימול המניה
        fast_window: מספר ימים לממוצע המהיר (ברירת מחדל: 50)
        slow_window: מספר ימים לממוצע האיטי (ברירת מחדל: 200)
    """

    def __init__(self, symbol: str, fast_window: int = 50, slow_window: int = 200):
        super().__init__(symbol)
        self.fast_window = fast_window
        self.slow_window = slow_window
        self._signals_cache: pd.Series | None = None

    def _compute_signals(self, data: pd.DataFrame) -> pd.Series:
        """מחשב את כל האיתותים פעם אחת מראש לכל הנתונים."""
        close = data["Close"]
        fast_ma = close.rolling(window=self.fast_window).mean()
        slow_ma = close.rolling(window=self.slow_window).mean()

        signals = pd.Series(Signal.HOLD, index=data.index)

        # חיתוך: fast עלה מעל slow (Golden Cross)
        crossed_up = (fast_ma > slow_ma) & (fast_ma.shift(1) <= slow_ma.shift(1))
        # חיתוך: fast ירד מתחת ל-slow (Death Cross)
        crossed_down = (fast_ma < slow_ma) & (fast_ma.shift(1) >= slow_ma.shift(1))

        signals[crossed_up] = Signal.BUY
        signals[crossed_down] = Signal.SELL

        return signals

    def generate_signal(self, data: pd.DataFrame, current_index: int) -> str:
        """מחזיר את האיתות ליום הנוכחי."""
        if self._signals_cache is None:
            self._signals_cache = self._compute_signals(data)

        return self._signals_cache.iloc[current_index]

    @property
    def name(self) -> str:
        return f"SMA Crossover ({self.fast_window}/{self.slow_window})"
