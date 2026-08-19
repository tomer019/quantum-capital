"""
reporter.py - Results printing and chart generation
"""
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend - saves to file instead of displaying
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from pathlib import Path

RESULTS_DIR = Path(__file__).parent.parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

# Dark theme settings
plt.rcParams["figure.facecolor"] = "#0d1117"
plt.rcParams["axes.facecolor"]   = "#161b22"
plt.rcParams["text.color"]       = "#e6edf3"
plt.rcParams["axes.labelcolor"]  = "#8b949e"
plt.rcParams["xtick.color"]      = "#8b949e"
plt.rcParams["ytick.color"]      = "#8b949e"
plt.rcParams["axes.edgecolor"]   = "#30363d"
plt.rcParams["grid.color"]       = "#21262d"
plt.rcParams["grid.linestyle"]   = "--"
plt.rcParams["grid.alpha"]       = 0.5


def print_results(metrics: dict):
    """Print the results summary to terminal."""
    r    = metrics["total_return_pct"]
    sign = "+" if r >= 0 else ""

    print(f"\n{'='*52}")
    print(f"  RESULTS: {metrics['strategy']}")
    print(f"{'='*52}")
    print(f"  Symbol        : {metrics['symbol']}")
    print(f"  Initial cash  : ${metrics['initial_cash']:>12,.2f}")
    print(f"  Final value   : ${metrics['final_value']:>12,.2f}")
    print(f"  Total return  : {sign}{r:.2f}%")
    print(f"  Max Drawdown  : -{metrics['max_drawdown_pct']:.2f}%")
    print(f"  Sharpe Ratio  : {metrics['sharpe_ratio']:.3f}")
    print(f"  Total trades  : {metrics['total_trades']}")
    if metrics['total_trades'] > 0:
        print(f"  Win Rate      : {metrics['win_rate_pct']:.1f}%")
        print(f"  Winners       : {metrics['winning_trades']}")
        print(f"  Losers        : {metrics['losing_trades']}")
    print(f"{'='*52}\n")


def plot_results(metrics: dict, data: pd.DataFrame):
    """Generate and save a performance chart vs Buy & Hold."""
    history   = metrics["portfolio_history"]
    dates     = [s.date for s in history]
    port_vals = [s.total_value for s in history]

    initial     = metrics["initial_cash"]
    start_price = data["Close"].iloc[0]
    bh_values   = [initial * (p / start_price) for p in data["Close"]]

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={"height_ratios": [3, 1]})
    fig.suptitle(
        f"{metrics['strategy']}  |  {metrics['symbol']}",
        fontsize=14, color="#e6edf3", fontweight="bold", y=0.98
    )

    ax1 = axes[0]
    ax1.plot(dates, port_vals, color="#3fb950", linewidth=2, label="Strategy", zorder=3)
    ax1.plot(data.index[:len(bh_values)], bh_values,
             color="#58a6ff", linewidth=1.5, linestyle="--", label="Buy & Hold", alpha=0.7)
    ax1.fill_between(dates, port_vals, alpha=0.1, color="#3fb950")
    ax1.set_ylabel("Portfolio Value ($)", fontsize=10)
    ax1.legend(loc="upper left", framealpha=0.3, facecolor="#161b22")
    ax1.grid(True)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    final_r = metrics["total_return_pct"]
    bh_r    = (bh_values[-1] - initial) / initial * 100
    s1 = "+" if final_r >= 0 else ""
    s2 = "+" if bh_r    >= 0 else ""
    ax1.text(0.02, 0.92, f"Strategy: {s1}{final_r:.1f}%", transform=ax1.transAxes, color="#3fb950", fontsize=11, fontweight="bold")
    ax1.text(0.02, 0.82, f"Buy&Hold: {s2}{bh_r:.1f}%",   transform=ax1.transAxes, color="#58a6ff", fontsize=11)

    ax2 = axes[1]
    ax2.plot(data.index, data["Close"], color="#e3b341", linewidth=1.2)
    ax2.set_ylabel("Price ($)", fontsize=9)
    ax2.set_xlabel("Date", fontsize=9)
    ax2.grid(True)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    plt.tight_layout()
    save_path = RESULTS_DIR / f"{metrics['symbol']}_results.png"
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[Chart] Saved to: {save_path}")
    return save_path


def plot_comparison(m1: dict, m2: dict, data: pd.DataFrame):
    """
    Generate a side-by-side comparison chart:
    Strategy 1 vs Strategy 2 vs Buy & Hold.
    """
    initial     = m1["initial_cash"]
    start_price = data["Close"].iloc[0]
    bh_values   = [initial * (p / start_price) for p in data["Close"]]

    dates1 = [s.date for s in m1["portfolio_history"]]
    vals1  = [s.total_value for s in m1["portfolio_history"]]

    dates2 = [s.date for s in m2["portfolio_history"]]
    vals2  = [s.total_value for s in m2["portfolio_history"]]

    symbol = m1["symbol"]

    fig, axes = plt.subplots(2, 1, figsize=(14, 9), gridspec_kw={"height_ratios": [3, 1]})
    fig.suptitle(
        f"Strategy Comparison  |  {symbol}",
        fontsize=14, color="#e6edf3", fontweight="bold", y=0.98
    )

    # Top: portfolio values
    ax1 = axes[0]
    ax1.plot(dates1, vals1, color="#3fb950", linewidth=2, label=m1["strategy"], zorder=3)
    ax1.plot(dates2, vals2, color="#f78166", linewidth=2, label=m2["strategy"], zorder=3)
    ax1.plot(data.index[:len(bh_values)], bh_values,
             color="#58a6ff", linewidth=1.5, linestyle="--", label="Buy & Hold", alpha=0.7)

    ax1.fill_between(dates1, vals1, alpha=0.07, color="#3fb950")
    ax1.fill_between(dates2, vals2, alpha=0.07, color="#f78166")

    ax1.set_ylabel("Portfolio Value ($)", fontsize=10)
    ax1.legend(loc="upper left", framealpha=0.3, facecolor="#161b22")
    ax1.grid(True)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    # Annotate returns
    r1   = m1["total_return_pct"]
    r2   = m2["total_return_pct"]
    bh_r = (bh_values[-1] - initial) / initial * 100

    ax1.text(0.02, 0.95, f"{m1['strategy']}: {'+' if r1>=0 else ''}{r1:.1f}%",
             transform=ax1.transAxes, color="#3fb950", fontsize=10, fontweight="bold")
    ax1.text(0.02, 0.87, f"{m2['strategy']}: {'+' if r2>=0 else ''}{r2:.1f}%",
             transform=ax1.transAxes, color="#f78166", fontsize=10, fontweight="bold")
    ax1.text(0.02, 0.79, f"Buy & Hold: {'+' if bh_r>=0 else ''}{bh_r:.1f}%",
             transform=ax1.transAxes, color="#58a6ff", fontsize=10)

    # Bottom: stock price
    ax2 = axes[1]
    ax2.plot(data.index, data["Close"], color="#e3b341", linewidth=1.2)
    ax2.set_ylabel("Price ($)", fontsize=9)
    ax2.set_xlabel("Date", fontsize=9)
    ax2.grid(True)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

    plt.tight_layout()
    save_path = RESULTS_DIR / f"{symbol}_comparison.png"
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"[Chart] Comparison saved to: {save_path}")
    return save_path
