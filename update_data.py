"""
update_data.py - Fetch and cache market fundamentals.
Run this script once a day to keep the Web App fast.
"""
import json
import sys
from pathlib import Path

# Add project root to path
import sys
from pathlib import Path
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from data.sp500_loader import get_sp500_tickers, get_nasdaq100_tickers, get_ta125_tickers, get_dji30_tickers, get_eurostoxx50_tickers, get_russell2000_tickers
from strategies.value_screener import fetch_fundamentals

DATA_DIR = Path(__file__).parent / "data"

def main():
    indices = {
        "SP500":       get_sp500_tickers(),
        "NASDAQ":      get_nasdaq100_tickers(),
        "TA125":       get_ta125_tickers(),
        "DJI30":       get_dji30_tickers(),
        "EUROSTOXX50": get_eurostoxx50_tickers(),
        "RUSSELL2000": get_russell2000_tickers(),
    }
    
    DATA_DIR.mkdir(exist_ok=True)
    
    for index_name, tickers in indices.items():
        print(f"\n=== Fetching {index_name} ({len(tickers)} stocks) ===")
        results = []
        
        for i, symbol in enumerate(tickers, 1):
            print(f"\rScanning {i}/{len(tickers)} - {symbol:<10}", end="", flush=True)
            stock = fetch_fundamentals(symbol)
            if stock and stock.pe_ratio and stock.profit_margin:
                results.append({
                    "symbol": stock.symbol,
                    "name": stock.name,
                    "price": stock.price,
                    "pe_ratio": stock.pe_ratio,
                    "debt_equity": stock.debt_equity,
                    "profit_margin": stock.profit_margin,
                    "sector": stock.sector,
                    "dividend_yield": stock.dividend_yield
                })
            time.sleep(0.2)
                
        print(f"\nSaving data for {index_name}...")
        outfile = DATA_DIR / f"market_data_{index_name}.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
            
        print(f"Successfully saved {len(results)} valid stocks to {outfile.name}.")

if __name__ == "__main__":
    main()
