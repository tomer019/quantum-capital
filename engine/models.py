"""
models.py — מבני הנתונים הבסיסיים של המנוע
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"


@dataclass
class Order:
    """פקודת קנייה/מכירה"""
    date: datetime
    symbol: str
    side: OrderSide
    quantity: float
    price: float  # מחיר הביצוע
    status: OrderStatus = OrderStatus.PENDING

    @property
    def value(self) -> float:
        return self.quantity * self.price


@dataclass
class Trade:
    """עסקה שבוצעה בפועל"""
    date: datetime
    symbol: str
    side: OrderSide
    quantity: float
    entry_price: float
    exit_price: Optional[float] = None
    commission: float = 0.0

    @property
    def pnl(self) -> float:
        """רווח/הפסד על העסקה"""
        if self.exit_price is None:
            return 0.0
        if self.side == OrderSide.BUY:
            return (self.exit_price - self.entry_price) * self.quantity - self.commission
        else:
            return (self.entry_price - self.exit_price) * self.quantity - self.commission

    @property
    def pnl_pct(self) -> float:
        """אחוז רווח/הפסד"""
        if self.exit_price is None or self.entry_price == 0:
            return 0.0
        if self.side == OrderSide.BUY:
            return (self.exit_price - self.entry_price) / self.entry_price * 100
        else:
            return (self.entry_price - self.exit_price) / self.entry_price * 100


@dataclass
class Position:
    """פוזיציה פתוחה כרגע"""
    symbol: str
    quantity: float
    avg_entry_price: float
    entry_date: datetime

    @property
    def current_value(self, current_price: float = 0) -> float:
        return self.quantity * current_price

    @property
    def cost_basis(self) -> float:
        return self.quantity * self.avg_entry_price


@dataclass
class PortfolioSnapshot:
    """צילום מצב התיק ביום מסוים"""
    date: datetime
    cash: float
    positions_value: float
    total_value: float
    daily_return: float = 0.0
