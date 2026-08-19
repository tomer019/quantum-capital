"""
value_screener.py - The Robot Portfolio stock screener

Screens stocks by fundamental criteria:
  - Profitable (positive earnings)
  - Low debt (Debt/Equity < threshold)
  - Cheap (low P/E ratio)
  - Decent profit margin

Then ranks by P/E and picks the top N stocks.
"""
import yfinance as yf
import pandas as pd
from dataclasses import dataclass
from typing import Optional


@dataclass
class StockFundamentals:
    """Financial data for a single stock."""
    symbol:        str
    name:          str
    price:         float
    pe_ratio:      Optional[float]
    debt_equity:   Optional[float]
    profit_margin: Optional[float]
    sector:        str
    dividend_yield:Optional[float]

    def passes_filter(
        self,
        max_pe:          float = 20.0,
        max_debt_equity: float = 100.0,  # yfinance gives debt/equity as percentage (e.g. 53 = 53%)
        min_margin:      float = 0.05,
    ) -> bool:
        """Returns True if the stock passes all filters."""
        if self.pe_ratio is None or self.profit_margin is None:
            return False
        if self.pe_ratio <= 0:
            return False  # Losing money
        if self.pe_ratio > max_pe:
            return False  # Too expensive
        # Debt check: only filter out if we have data AND it's too high
        if self.debt_equity is not None and self.debt_equity > max_debt_equity:
            return False  # Too much debt
        if self.profit_margin < min_margin:
            return False  # Margins too thin
        return True


def fetch_fundamentals(symbol: str) -> Optional[StockFundamentals]:
    """
    Fetch key financial metrics for a single stock via yfinance.
    Returns None if data is unavailable or invalid.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if not price:
            return None

        return StockFundamentals(
            symbol=symbol,
            name=info.get("shortName", symbol),
            price=price,
            pe_ratio=info.get("trailingPE"),
            debt_equity=info.get("debtToEquity", None),
            profit_margin=info.get("profitMargins", None),
            sector=info.get("sector", "Unknown"),
            dividend_yield=info.get("dividendYield", 0.0),
        )
    except Exception:
        return None


def screen_stocks(
    tickers: list[str],
    top_n:          int   = 10,
    max_pe:         float = 25.0,
    max_debt_equity:float = 100.0,  # as percentage: 100 = 100% debt/equity
    min_margin:     float = 0.05,
) -> pd.DataFrame:
    """
    Screens a list of tickers, filters by criteria, and returns
    the top N ranked by lowest P/E ratio.

    Args:
        tickers:         List of stock symbols to screen
        top_n:           Number of stocks to select
        max_pe:          Maximum acceptable P/E ratio
        max_debt_equity: Maximum Debt/Equity ratio
        min_margin:      Minimum profit margin (e.g. 0.05 = 5%)

    Returns:
        DataFrame with the selected portfolio stocks, ranked by P/E
    """
    results = []
    total = len(tickers)

    for i, symbol in enumerate(tickers, 1):
        print(f"\r[Screener] Scanning {i}/{total} — {symbol:<6}", end="", flush=True)
        stock = fetch_fundamentals(symbol)
        if stock and stock.passes_filter(max_pe, max_debt_equity, min_margin):
            results.append(stock)

    print()  # newline after progress

    if not results:
        print("[Screener] No stocks passed the filters.")
        return pd.DataFrame()

    # Sort by P/E ascending (cheapest first) and take top N
    results.sort(key=lambda s: s.pe_ratio)
    selected = results[:top_n]

    df = pd.DataFrame([{
        "Symbol":        s.symbol,
        "Name":          s.name,
        "Price ($)":     round(s.price, 2),
        "P/E Ratio":     round(s.pe_ratio, 1),
        "Debt/Equity":   round(s.debt_equity, 2) if s.debt_equity is not None else "N/A",
        "Profit Margin": f"{s.profit_margin * 100:.1f}%",
        "Sector":        s.sector,
    } for s in selected])

    return df
