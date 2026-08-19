"""
main.py - Algo-Trading Backtester entry point

Usage:
    py main.py                                         # default: AAPL, SMA strategy
    py main.py --strategy rsi                          # RSI strategy
    py main.py --strategy both                         # compare both side by side
    py main.py --symbol NVDA --start 2014-01-01        # different stock
    py main.py --symbol SPY --cash 50000 --no-plot     # no chart
"""
import argparse
import sys
import io
from pathlib import Path

# Force UTF-8 output on Windows Hebrew systems
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from data.loader import load_data
from strategies.sma_crossover import SMACrossover
from strategies.rsi import RSIStrategy
from engine.backtester import Backtester
from engine.reporter import print_results, plot_comparison, plot_results


def parse_args():
    parser = argparse.ArgumentParser(
        description="Algo-Trading Backtester",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  py main.py                                      # AAPL with SMA strategy
  py main.py --strategy rsi                       # AAPL with RSI strategy
  py main.py --strategy both                      # compare both strategies
  py main.py --symbol NVDA --start 2014-01-01    # NVDA from 2014
  py main.py --symbol SPY --cash 50000 --no-plot # no chart
        """
    )
    parser.add_argument("--symbol",     default="AAPL",       help="Stock symbol (default: AAPL)")
    parser.add_argument("--start",      default="2019-01-01", help="Start date YYYY-MM-DD (default: 2019-01-01)")
    parser.add_argument("--end",        default="2024-12-31", help="End date YYYY-MM-DD (default: 2024-12-31)")
    parser.add_argument("--cash",       default=10000, type=float, help="Initial capital in USD (default: 10000)")
    parser.add_argument("--strategy",   default="sma", choices=["sma", "rsi", "both"], help="Strategy to run: sma, rsi, or both (default: sma)")
    parser.add_argument("--fast",       default=50,   type=int,   help="[SMA] Fast MA window days (default: 50)")
    parser.add_argument("--slow",       default=200,  type=int,   help="[SMA] Slow MA window days (default: 200)")
    parser.add_argument("--rsi-period", default=14,   type=int,   help="[RSI] RSI period days (default: 14)")
    parser.add_argument("--oversold",   default=30,   type=float, help="[RSI] Buy threshold (default: 30)")
    parser.add_argument("--overbought", default=70,   type=float, help="[RSI] Sell threshold (default: 70)")
    parser.add_argument("--commission", default=0.001, type=float, help="Commission per trade (default: 0.001 = 0.1%%)")
    parser.add_argument("--no-plot",    action="store_true",       help="Skip chart generation")
    parser.add_argument("--no-cache",   action="store_true",       help="Re-download data ignoring cache")
    return parser.parse_args()


def run_strategy(strategy, data, cash, commission):
    """Run a single strategy and return metrics."""
    bt = Backtester(strategy=strategy, initial_cash=cash, commission_pct=commission)
    return bt.run(data)


def main():
    args = parse_args()

    print(f"\n=== Algo-Trading Backtester ===")
    print(f"    Symbol   : {args.symbol}")
    print(f"    Period   : {args.start} -> {args.end}")
    print(f"    Capital  : ${args.cash:,.0f}")
    print(f"    Strategy : {args.strategy.upper()}\n")

    # 1. Load data
    try:
        data = load_data(
            symbol=args.symbol,
            start=args.start,
            end=args.end,
            use_cache=not args.no_cache,
        )
    except Exception as e:
        print(f"\nERROR loading data: {e}")
        sys.exit(1)

    # 2. Build strategies
    sma_strategy = SMACrossover(args.symbol, fast_window=args.fast, slow_window=args.slow)
    rsi_strategy = RSIStrategy(args.symbol, period=args.rsi_period, oversold=args.oversold, overbought=args.overbought)

    # 3. Run selected strategy/strategies
    if args.strategy == "sma":
        metrics = run_strategy(sma_strategy, data, args.cash, args.commission)
        print_results(metrics)
        if not args.no_plot:
            plot_results(metrics, data)

    elif args.strategy == "rsi":
        metrics = run_strategy(rsi_strategy, data, args.cash, args.commission)
        print_results(metrics)
        if not args.no_plot:
            plot_results(metrics, data)

    elif args.strategy == "both":
        print("--- Running SMA Crossover ---")
        sma_metrics = run_strategy(sma_strategy, data, args.cash, args.commission)

        print("\n--- Running RSI ---")
        rsi_metrics = run_strategy(rsi_strategy, data, args.cash, args.commission)

        # Print both results
        print_results(sma_metrics)
        print_results(rsi_metrics)

        # Print comparison table
        print_comparison(sma_metrics, rsi_metrics)

        if not args.no_plot:
            plot_comparison(sma_metrics, rsi_metrics, data)


def print_comparison(m1: dict, m2: dict):
    """Print a side-by-side comparison table."""
    print(f"\n{'='*60}")
    print(f"  HEAD-TO-HEAD COMPARISON")
    print(f"{'='*60}")
    print(f"  {'Metric':<20} {'SMA Crossover':>18} {'RSI':>18}")
    print(f"  {'-'*56}")

    def row(label, key, fmt=".2f", suffix=""):
        v1 = m1.get(key, 0)
        v2 = m2.get(key, 0)
        winner1 = " <--" if v1 > v2 else ""
        winner2 = " <--" if v2 > v1 else ""
        print(f"  {label:<20} {f'{v1:{fmt}}{suffix}':>18}{winner1:<4} {f'{v2:{fmt}}{suffix}':>18}{winner2}")

    row("Total Return %",   "total_return_pct",  ".2f", "%")
    row("Final Value $",    "final_value",        ",.0f", "")
    row("Max Drawdown %",   "max_drawdown_pct",   ".2f", "%")
    row("Sharpe Ratio",     "sharpe_ratio",       ".3f", "")
    row("Total Trades",     "total_trades",       ".0f", "")
    row("Win Rate %",       "win_rate_pct",       ".1f", "%")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
