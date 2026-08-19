"""
backtester.py - Core simulation engine

Iterates day-by-day over historical data,
runs the strategy, and manages a virtual portfolio.
"""
import pandas as pd
from datetime import datetime
from typing import Optional

from engine.models import (
    Order, OrderSide, OrderStatus,
    Trade, Position, PortfolioSnapshot
)
from strategies.base_strategy import BaseStrategy, Signal


class Backtester:
    """
    The simulation engine.

    Args:
        strategy:       The trading strategy to run
        initial_cash:   Starting capital (default: $10,000)
        commission_pct: Commission per trade as fraction (default: 0.1%)
    """

    def __init__(
        self,
        strategy: BaseStrategy,
        initial_cash: float = 10_000.0,
        commission_pct: float = 0.001,
    ):
        self.strategy = strategy
        self.initial_cash = initial_cash
        self.commission_pct = commission_pct

        # Portfolio state
        self.cash = initial_cash
        self.position: Optional[Position] = None
        self.trades: list[Trade] = []
        self.history: list[PortfolioSnapshot] = []

    def run(self, data: pd.DataFrame) -> dict:
        """
        Runs the simulation over the DataFrame and returns result metrics.
        """
        print(f"\n{'='*52}")
        print(f"  Strategy : {self.strategy.name}")
        print(f"  Symbol   : {self.strategy.symbol}")
        print(f"  Period   : {data.index[0].date()} -> {data.index[-1].date()}")
        print(f"  Capital  : ${self.initial_cash:,.2f}")
        print(f"{'='*52}\n")

        prev_total = self.initial_cash

        for i in range(len(data)):
            current_date = data.index[i]
            current_price = data["Close"].iloc[i]

            signal = self.strategy.generate_signal(data, i)

            if signal == Signal.BUY and self.position is None:
                self._open_position(current_date, current_price)

            elif signal == Signal.SELL and self.position is not None:
                self._close_position(current_date, current_price)

            positions_value = (
                self.position.quantity * current_price
                if self.position else 0.0
            )
            total_value = self.cash + positions_value
            daily_return = (total_value - prev_total) / prev_total * 100 if prev_total > 0 else 0

            self.history.append(PortfolioSnapshot(
                date=current_date,
                cash=self.cash,
                positions_value=positions_value,
                total_value=total_value,
                daily_return=daily_return,
            ))

            prev_total = total_value

        # Close any open position at end of period
        if self.position is not None:
            self._close_position(data.index[-1], data["Close"].iloc[-1])

        return self._compute_metrics()

    def _open_position(self, date, price: float):
        """BUY - invest all available cash"""
        commission = self.cash * self.commission_pct
        investable = self.cash - commission
        quantity = investable / price

        self.position = Position(
            symbol=self.strategy.symbol,
            quantity=quantity,
            avg_entry_price=price,
            entry_date=date,
        )
        self.cash -= (quantity * price + commission)

        print(f"  BUY  [{date.date()}] ${price:.2f} x {quantity:.4f} shares | commission: ${commission:.2f}")

    def _close_position(self, date, price: float):
        """SELL - close the open position"""
        if self.position is None:
            return

        proceeds = self.position.quantity * price
        commission = proceeds * self.commission_pct
        self.cash += proceeds - commission

        trade = Trade(
            date=date,
            symbol=self.position.symbol,
            side=OrderSide.BUY,
            quantity=self.position.quantity,
            entry_price=self.position.avg_entry_price,
            exit_price=price,
            commission=commission * 2,
        )
        self.trades.append(trade)

        pnl_sign = "+" if trade.pnl >= 0 else ""
        print(f"  SELL [{date.date()}] ${price:.2f} | PnL: {pnl_sign}${trade.pnl:.2f} ({pnl_sign}{trade.pnl_pct:.1f}%)")

        self.position = None

    def _compute_metrics(self) -> dict:
        """Compute all performance metrics at the end of the simulation."""
        if not self.history:
            return {}

        portfolio_values = [s.total_value for s in self.history]
        final_value = portfolio_values[-1]

        # Total return
        total_return = (final_value - self.initial_cash) / self.initial_cash * 100

        # Max Drawdown - largest drop from peak
        peak = self.initial_cash
        max_drawdown = 0.0
        for val in portfolio_values:
            if val > peak:
                peak = val
            drawdown = (peak - val) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # Trade statistics
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades  = [t for t in self.trades if t.pnl <= 0]
        win_rate = len(winning_trades) / len(self.trades) * 100 if self.trades else 0

        # Annualized Sharpe Ratio (no risk-free rate)
        returns = pd.Series(portfolio_values).pct_change().dropna()
        sharpe = (returns.mean() / returns.std() * (252 ** 0.5)) if returns.std() > 0 else 0

        return {
            "strategy":          self.strategy.name,
            "symbol":            self.strategy.symbol,
            "initial_cash":      self.initial_cash,
            "final_value":       final_value,
            "total_return_pct":  total_return,
            "max_drawdown_pct":  max_drawdown,
            "sharpe_ratio":      sharpe,
            "total_trades":      len(self.trades),
            "win_rate_pct":      win_rate,
            "winning_trades":    len(winning_trades),
            "losing_trades":     len(losing_trades),
            "portfolio_history": self.history,
        }
