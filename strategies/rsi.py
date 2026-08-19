"""
rsi.py - RSI (Relative Strength Index) Strategy

Logic:
  - Calculate RSI over a rolling window (default: 14 days)
  - RSI below 30 = stock is "oversold" (too cheap) -> BUY
  - RSI above 70 = stock is "overbought" (too expensive) -> SELL
  - Otherwise -> HOLD
"""
import pandas as pd
from strategies.base_strategy import BaseStrategy, Signal


class RSIStrategy(BaseStrategy):
    """
    RSI-based mean reversion strategy.

    Args:
        symbol:      Stock symbol
        period:      RSI calculation window in days (default: 14)
        oversold:    RSI threshold to BUY below (default: 30)
        overbought:  RSI threshold to SELL above (default: 70)
    """

    def __init__(
        self,
        symbol: str,
        period: int = 14,
        oversold: float = 30.0,
        overbought: float = 70.0,
    ):
        super().__init__(symbol)
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
        self._signals_cache: pd.Series | None = None

    def _compute_rsi(self, close: pd.Series) -> pd.Series:
        """Compute RSI using Wilder's smoothing method."""
        delta = close.diff()

        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        avg_gain = gain.ewm(alpha=1 / self.period, min_periods=self.period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / self.period, min_periods=self.period, adjust=False).mean()

        rs = avg_gain / avg_loss.replace(0, 1e-10)  # avoid division by zero
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def _compute_signals(self, data: pd.DataFrame) -> pd.Series:
        """Pre-compute all signals for the full dataset."""
        close = data["Close"]
        rsi = self._compute_rsi(close)

        signals = pd.Series(Signal.HOLD, index=data.index)

        # Only signal on crossings (not every day RSI is in zone)
        crossed_oversold   = (rsi < self.oversold)  & (rsi.shift(1) >= self.oversold)
        crossed_overbought = (rsi > self.overbought) & (rsi.shift(1) <= self.overbought)

        signals[crossed_oversold]   = Signal.BUY
        signals[crossed_overbought] = Signal.SELL

        return signals

    def generate_signal(self, data: pd.DataFrame, current_index: int) -> str:
        if self._signals_cache is None:
            self._signals_cache = self._compute_signals(data)
        return self._signals_cache.iloc[current_index]

    @property
    def name(self) -> str:
        return f"RSI ({self.period}) [{self.oversold}/{self.overbought}]"
