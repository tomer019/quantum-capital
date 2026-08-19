"""
base_strategy.py — מחלקת בסיס לכל אסטרטגיה
"""
from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd

from engine.models import OrderSide


class Signal:
    """איתות מסחר שהאסטרטגיה מייצרת"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"  # אל תעשה כלום


class BaseStrategy(ABC):
    """
    כל אסטרטגיה חדשה יורשת ממחלקה זו ומממשת את generate_signal.
    """

    def __init__(self, symbol: str):
        self.symbol = symbol

    @abstractmethod
    def generate_signal(self, data: pd.DataFrame, current_index: int) -> str:
        """
        מקבל את כל הנתונים ואת האינדקס הנוכחי,
        ומחזיר BUY / SELL / HOLD.

        Args:
            data: DataFrame עם כל הנתונים ההיסטוריים
            current_index: האינדקס של היום הנוכחי בסימולציה
        """
        pass

    @property
    def name(self) -> str:
        return self.__class__.__name__
