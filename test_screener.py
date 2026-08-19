import sys, io
sys.path.insert(0, '.')
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from data.sp500_loader import get_sp500_tickers
from strategies.value_screener import screen_stocks

# Test with first 50 tickers, relaxed filters
tickers = get_sp500_tickers()[:50]
print(f"Testing with first {len(tickers)} tickers...\n")

df = screen_stocks(tickers, top_n=5, max_pe=25.0, max_debt_equity=100.0, min_margin=0.05)
print()

if df.empty:
    print("No stocks passed filters in this sample.")
else:
    print(f"Found {len(df)} stocks:\n")
    print(df.to_string(index=False))
