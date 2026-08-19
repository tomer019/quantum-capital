"""
screener.py - Robot Portfolio entry point

Usage:
    py screener.py                              # scan full S&P 500, top 10
    py screener.py --top 15                    # top 15 stocks
    py screener.py --max-pe 15                 # stricter PE filter
    py screener.py --cash 27000                # show how many shares to buy
    py screener.py --no-cache                  # re-fetch ticker list
"""
import argparse
import sys
import io
from pathlib import Path
from datetime import date

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

from data.sp500_loader import get_sp500_tickers
from strategies.value_screener import screen_stocks


def parse_args():
    parser = argparse.ArgumentParser(
        description="Robot Portfolio Screener - Value stock screener for S&P 500",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  py screener.py                    # full scan, top 10
  py screener.py --top 15          # top 15 stocks
  py screener.py --max-pe 15       # only stocks with P/E under 15
  py screener.py --cash 50000      # show buy quantities for $50,000
  py screener.py --no-cache        # re-download S&P 500 list
        """
    )
    parser.add_argument("--top",      default=10,   type=int,   help="Number of stocks to select (default: 10)")
    parser.add_argument("--max-pe",   default=20.0, type=float, help="Max P/E ratio to include (default: 20)")
    parser.add_argument("--max-debt", default=1.0,  type=float, help="Max Debt/Equity to include (default: 1.0)")
    parser.add_argument("--min-margin",default=0.05,type=float, help="Min profit margin to include (default: 0.05 = 5%%)")
    parser.add_argument("--cash",     default=0,    type=float, help="Your investment capital in USD (shows share quantities)")
    parser.add_argument("--no-cache", action="store_true",      help="Re-download S&P 500 ticker list")
    parser.add_argument("--save",     action="store_true",      help="Save results to CSV file in results/")
    return parser.parse_args()


def print_portfolio(df, cash: float, top_n: int):
    """Print a clean, formatted portfolio table."""
    print(f"\n{'='*72}")
    print(f"  ROBOT PORTFOLIO  |  {date.today().strftime('%B %d, %Y')}")
    print(f"{'='*72}")

    if cash > 0:
        per_stock = cash / top_n
        print(f"  Capital: ${cash:,.0f}  |  Per stock: ${per_stock:,.0f}  |  {top_n} equal positions")
    else:
        print(f"  Top {top_n} value stocks by P/E  |  Equal weight allocation")

    print(f"{'='*72}")
    print(f"  {'#':<3} {'Symbol':<7} {'Name':<28} {'P/E':>5} {'Debt/Eq':>8} {'Margin':>8} {'Sector':<18}", end="")
    if cash > 0:
        print(f"  {'Shares':>7}", end="")
    print()
    print(f"  {'-'*68}")

    for i, row in enumerate(df.itertuples(), 1):
        shares_str = ""
        if cash > 0:
            per_stock = cash / top_n
            shares = int(per_stock / row._3)  # _3 = Price ($)
            shares_str = f"  {shares:>7}"

        debt_str = f"{row._5:>8.2f}" if isinstance(row._5, float) else f"{'N/A':>8}"
        print(
            f"  {i:<3} {row.Symbol:<7} {row.Name[:27]:<28} "
            f"{row._4:>5.1f} {debt_str} {row._6:>8} "
            f"{row.Sector[:17]:<18}{shares_str}"
        )

    print(f"{'='*72}")
    print(f"\n  Strategy: Buy equal amounts, hold 1 year, then re-run this screener.")
    print(f"  Next review date: {date.today().replace(year=date.today().year + 1).strftime('%B %d, %Y')}\n")


def main():
    args = parse_args()

    print(f"\n=== Robot Portfolio Screener ===")
    print(f"    Filters: P/E < {args.max_pe} | Debt/Equity < {args.max_debt} | Margin > {args.min_margin*100:.0f}%")
    print(f"    Target : Top {args.top} stocks\n")

    # 1. Load S&P 500 tickers
    try:
        tickers = get_sp500_tickers(use_cache=not args.no_cache)
        print(f"[SP500] Loaded {len(tickers)} tickers.\n")
    except Exception as e:
        print(f"ERROR loading ticker list: {e}")
        sys.exit(1)

    # 2. Screen stocks
    print(f"[Screener] Scanning all {len(tickers)} stocks... (this takes 3-5 minutes)\n")
    df = screen_stocks(
        tickers=tickers,
        top_n=args.top,
        max_pe=args.max_pe,
        max_debt_equity=args.max_debt,
        min_margin=args.min_margin,
    )

    if df.empty:
        print("No stocks passed the filters. Try relaxing the criteria.")
        sys.exit(0)

    # 3. Print results
    print_portfolio(df, cash=args.cash, top_n=args.top)

    # 4. Optionally save
    if args.save:
        save_dir = Path(__file__).parent / "results"
        save_dir.mkdir(exist_ok=True)
        filename = save_dir / f"robot_portfolio_{date.today()}.csv"
        df.to_csv(filename, index=False)
        print(f"[Saved] Portfolio saved to: {filename}")


if __name__ == "__main__":
    main()
