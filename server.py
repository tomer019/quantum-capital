import json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path
import uvicorn
from fastapi.responses import FileResponse, HTMLResponse
import yfinance as yf
from backtester import run_portfolio_backtest, generate_tear_sheet_html

app = FastAPI(title="Robot Portfolio API")

DATA_FILE = Path(__file__).parent / "data" / "market_data.json"

# In-memory cache for fast search
ALL_STOCKS_CACHE = []

def get_all_stocks():
    global ALL_STOCKS_CACHE
    if ALL_STOCKS_CACHE:
        return ALL_STOCKS_CACHE
    all_stocks = []
    for index_name in ["SP500", "NASDAQ", "TA125", "DJI30", "EUROSTOXX50", "RUSSELL2000"]:
        all_stocks.extend(load_data_from_file(index_name))
    
    # Deduplicate
    unique = []
    seen = set()
    for s in all_stocks:
        if s["symbol"] not in seen:
            unique.append(s)
            seen.add(s["symbol"])
    ALL_STOCKS_CACHE = unique
    return ALL_STOCKS_CACHE

def load_data_from_file(index_name: str):
    file_path = Path(__file__).parent / "data" / f"market_data_{index_name}.json"
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # Fallback to legacy market_data.json if index file not found yet
    legacy_file = Path(__file__).parent / "data" / "market_data.json"
    if legacy_file.exists():
        with open(legacy_file, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

class ScreenerRequest(BaseModel):
    capital: float
    top_n: int = 10
    max_pe: float = 25.0
    min_margin: float = 0.05
    min_dividend: float = 0.0
    index_name: str = "SP500"
    min_price: float = 0.0
    max_price: float = 1000000.0

class PortfolioRequest(BaseModel):
    symbols: list[str]

@app.post("/api/screen")
def screen_portfolio(req: ScreenerRequest):
    market_data = load_data_from_file(req.index_name)
    if not market_data:
        raise HTTPException(status_code=503, detail="Market data not loaded")
        
    filtered = []
    for stock in market_data:
        # Check criteria
        pe = stock.get("pe_ratio")
        margin = stock.get("profit_margin")
        debt = stock.get("debt_equity")
        
        if pe is None or margin is None:
            continue
            
        if pe <= 0 or pe > req.max_pe:
            continue
            
        if margin < req.min_margin:
            continue
            
        # Price check
        price = stock.get("price") or 0.0
        if price < req.min_price or price > req.max_price:
            continue
            
        # Dividend check
        div = stock.get("dividend_yield") or 0.0
        # yfinance dividend yield is a float like 0.025 for 2.5%, so we compare directly
        if div < req.min_dividend:
            continue
            
        # Optional: you could add debt filtering here too
            
        filtered.append(stock)
        
    if not filtered:
        return {"results": [], "allocation_per_stock": 0}
        
    # Sort by lowest P/E
    filtered.sort(key=lambda x: x["pe_ratio"])
    top_stocks = filtered[:req.top_n]
    
    # Calculate allocation
    allocation_per_stock = req.capital / len(top_stocks)
    
    # Enrich with shares to buy
    for stock in top_stocks:
        stock["shares_to_buy"] = int(allocation_per_stock / stock["price"]) if stock["price"] else 0
        stock["allocation_value"] = stock["shares_to_buy"] * stock["price"]
        
    return {
        "results": top_stocks,
        "allocation_per_stock": allocation_per_stock,
        "total_allocated": sum(s["allocation_value"] for s in top_stocks)
    }

@app.post("/api/watchlist_details")
def get_watchlist_details(req: PortfolioRequest):
    if not req.symbols:
        return {"results": []}
        
    all_stocks = []
    # Load all index files to find the symbols
    for index_name in ["SP500", "NASDAQ", "TA125", "DJI30", "EUROSTOXX50"]:
        all_stocks.extend(load_data_from_file(index_name))
        
    # Filter only requested symbols
    requested_set = set(req.symbols)
    found_stocks = [s for s in all_stocks if s.get("symbol") in requested_set]
    
    # Deduplicate in case a stock is in multiple indices (e.g. AAPL in SP500 and NASDAQ)
    unique_stocks = []
    seen = set()
    for s in found_stocks:
        if s["symbol"] not in seen:
            unique_stocks.append(s)
            seen.add(s["symbol"])
            
    return {"results": unique_stocks}

@app.get("/api/search_ticker")
def search_ticker(q: str = ""):
    if not q or len(q) < 2:
        return {"results": []}
        
    q_lower = q.lower()
    all_stocks = get_all_stocks()
    
    matches = []
    for s in all_stocks:
        symbol = s.get("symbol", "").lower()
        name = s.get("name", "").lower()
        if q_lower in symbol or q_lower in name:
            matches.append({"symbol": s.get("symbol"), "name": s.get("name")})
            if len(matches) >= 10:  # limit to 10 suggestions
                break
                
    return {"results": matches}

@app.post("/api/portfolio_prices")
def get_portfolio_prices(req: PortfolioRequest):
    prices = {}
    if not req.symbols:
        return prices
        
    try:
        # Clean unique symbols
        unique_syms = list(set([s.strip().upper() for s in req.symbols if s.strip()]))
        if not unique_syms:
            return prices

        # Single fast vectorized batch download
        df = yf.download(tickers=unique_syms, period="5d", progress=False)
        if not df.empty and 'Close' in df:
            close_df = df['Close']
            if len(unique_syms) == 1:
                sym = unique_syms[0]
                s_prices = close_df.dropna()
                if not s_prices.empty:
                    prices[sym] = round(float(s_prices.iloc[-1]), 2)
            else:
                for sym in unique_syms:
                    if sym in close_df.columns:
                        s_prices = close_df[sym].dropna()
                        if not s_prices.empty:
                            prices[sym] = round(float(s_prices.iloc[-1]), 2)

        # Fallback for any missing symbols from local index files
        missing = [s for s in unique_syms if s not in prices]
        if missing:
            all_local = get_all_stocks()
            local_map = {s.get("symbol"): s.get("price") for s in all_local if s.get("price")}
            for m in missing:
                if m in local_map and local_map[m]:
                    prices[m] = float(local_map[m])

    except Exception as e:
        print(f"Error fetching portfolio prices: {e}")
        
    return prices

def load_momentum_from_file(index_name: str):
    file_path = Path(__file__).parent / "data" / f"momentum_data_{index_name}.json"
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

class MomentumRequest(BaseModel):
    capital: float = 10000.0
    top_n: int = 10
    index_name: str = "SP500"
    min_price: float = 0.0
    max_price: float = 1000000.0

@app.post("/api/screen_momentum")
def screen_momentum(req: MomentumRequest):
    data = load_momentum_from_file(req.index_name)
    if data:
        # Filter by price
        filtered_data = [s for s in data if s.get("price", 0) >= req.min_price and s.get("price", 0) <= req.max_price]
        
        # Sort by highest momentum score
        filtered_data.sort(key=lambda x: x.get("score", 0), reverse=True)
        top_stocks = filtered_data[:req.top_n]
        
        allocation_per_stock = req.capital / len(top_stocks) if top_stocks else 0
        total_allocated = 0.0
        
        for stock in top_stocks:
            p = stock.get("price", 0)
            if p and p > 0:
                shares = int(allocation_per_stock / p)
                if shares == 0:
                    shares = 1
                stock["shares_to_buy"] = shares
                stock["allocation_value"] = round(shares * p, 2)
                total_allocated += stock["allocation_value"]
            else:
                stock["shares_to_buy"] = 1
                stock["allocation_value"] = 0.0
                
        return {
            "results": top_stocks,
            "allocation_per_stock": allocation_per_stock,
            "total_allocated": round(total_allocated, 2)
        }

    market_data = load_data_from_file(req.index_name)
    if not market_data:
        raise HTTPException(status_code=503, detail="Market data not loaded")

    valid_stocks = {s["symbol"]: s for s in market_data if s.get("price", 0) > 1}
    symbols = list(valid_stocks.keys())
    if not symbols:
        return {"results": [], "allocation_per_stock": 0, "total_allocated": 0}

    try:
        now_ts = time.time()
        cached = MOMENTUM_CACHE.get(req.index_name)

        if cached and (now_ts - cached["timestamp"] < MOMENTUM_CACHE_TTL) and not cached["data"].empty:
            hist = cached["data"]
        else:
            end = datetime.now()
            start = end - timedelta(days=90)
            hist = yf.download(
                symbols,
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                auto_adjust=True,
                progress=False,
                threads=True
            )
            if not hist.empty:
                MOMENTUM_CACHE[req.index_name] = {
                    "data": hist,
                    "timestamp": now_ts
                }

        if hist.empty:
            return {"results": [], "allocation_per_stock": 0, "total_allocated": 0}

        results = []
        single = len(symbols) == 1

        for symbol in symbols:
            try:
                if single:
                    close = hist["Close"].dropna()
                    volume = hist["Volume"].dropna()
                else:
                    if symbol not in hist["Close"].columns:
                        continue
                    close = hist["Close"][symbol].dropna()
                    volume = hist["Volume"][symbol].dropna()

                if len(close) < 10:
                    continue

                current_price = float(close.iloc[-1])
                if math.isnan(current_price) or current_price <= 0:
                    continue

                idx_1m = max(0, len(close) - 22)
                monthly_return = (current_price / float(close.iloc[idx_1m]) - 1) * 100

                idx_1w = max(0, len(close) - 6)
                weekly_return = (current_price / float(close.iloc[idx_1w]) - 1) * 100

                if math.isnan(monthly_return) or math.isnan(weekly_return):
                    continue

                vol_recent = float(volume.iloc[-5:].mean()) if len(volume) >= 5 else float(volume.mean())
                vol_avg = float(volume.iloc[-30:].mean()) if len(volume) >= 30 else float(volume.mean())
                volume_pulse = round(vol_recent / vol_avg, 2) if vol_avg > 0 else 1.0

                ma50 = float(close.iloc[-min(50, len(close)):].mean())
                above_ma = bool(current_price > ma50)

                delta = close.diff()
                gain = delta.clip(lower=0)
                loss = (-delta.clip(upper=0))
                avg_gain = gain.rolling(window=14, min_periods=14).mean().iloc[-1]
                avg_loss = loss.rolling(window=14, min_periods=14).mean().iloc[-1]
                if avg_loss == 0 or math.isnan(avg_loss):
                    rsi = 100.0
                else:
                    rs = avg_gain / avg_loss
                    rsi = round(100 - (100 / (1 + rs)), 1)

                sig_score = 0
                if monthly_return > 5:  sig_score += 2
                elif monthly_return > 0: sig_score += 1
                if weekly_return > 1:   sig_score += 2
                elif weekly_return > 0: sig_score += 1
                if 40 <= rsi <= 65:     sig_score += 2
                elif rsi < 72:          sig_score += 1
                if volume_pulse >= 1.5: sig_score += 2
                elif volume_pulse >= 1.1: sig_score += 1
                if above_ma:            sig_score += 1

                if sig_score >= 7:   signal = "strong"
                elif sig_score >= 4: signal = "moderate"
                else:                signal = "weak"

                score = (0.5 * monthly_return) + (0.3 * weekly_return) + (0.2 * (volume_pulse - 1) * 10)

                stock_info = valid_stocks[symbol]
                results.append({
                    "symbol": symbol,
                    "name": stock_info.get("name", symbol),
                    "sector": stock_info.get("sector", "-"),
                    "price": round(current_price, 2),
                    "monthly_return": round(monthly_return, 2),
                    "weekly_return": round(weekly_return, 2),
                    "volume_pulse": round(volume_pulse, 2),
                    "rsi": rsi,
                    "signal": signal,
                    "above_ma": above_ma,
                    "score": round(score, 2)
                })
            except Exception:
                continue

        results.sort(key=lambda x: x["score"], reverse=True)
        top_stocks = results[:req.top_n]
        
        allocation_per_stock = req.capital / max(1, len(top_stocks))
        total_allocated = 0
        
        for stock in top_stocks:
            stock["shares_to_buy"] = int(allocation_per_stock / stock["price"]) if stock["price"] else 0
            stock["allocation_value"] = stock["shares_to_buy"] * stock["price"]
            total_allocated += stock["allocation_value"]

        return {
            "results": top_stocks,
            "allocation_per_stock": allocation_per_stock,
            "total_allocated": total_allocated
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount static files (HTML, CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def index():
    return FileResponse("static/index.html")

@app.get("/api/stock/{symbol}")
def get_stock_details(symbol: str):
    import math
    import pandas as pd
    try:
        sym = symbol.strip().upper()
        ticker = yf.Ticker(sym)
        hist = ticker.history(period="2y", auto_adjust=True)
        if hist.empty:
            raise HTTPException(status_code=404, detail=f"Stock '{sym}' not found or has no price history")
        
        candlesticks = []
        volumes = []
        sma50_data = []
        sma200_data = []
        
        if not hist.empty:
            hist = hist.sort_index()
            # Calculate Moving Averages over full 2Y period so SMA200 covers all recent days
            hist['SMA50'] = hist['Close'].rolling(window=50).mean()
            hist['SMA200'] = hist['Close'].rolling(window=200).mean()
            
            # Slice the last 1 year (252 trading days)
            recent_hist = hist.iloc[-252:] if len(hist) > 252 else hist
            
            last_date = None
            for date, row in recent_hist.iterrows():
                o = float(row['Open'])
                h = float(row['High'])
                l = float(row['Low'])
                c = float(row['Close'])
                vol = float(row.get('Volume', 0))
                
                if math.isnan(c) or math.isnan(o):
                    continue
                date_str = date.strftime("%Y-%m-%d")
                if date_str == last_date:
                    continue
                last_date = date_str
                
                is_up = c >= o
                candlesticks.append({
                    "time": date_str,
                    "open": round(o, 2),
                    "high": round(h, 2),
                    "low": round(l, 2),
                    "close": round(c, 2)
                })
                volumes.append({
                    "time": date_str,
                    "value": int(vol),
                    "color": "rgba(0, 230, 118, 0.4)" if is_up else "rgba(255, 61, 0, 0.4)"
                })
                if not math.isnan(row['SMA50']):
                    sma50_data.append({"time": date_str, "value": round(float(row['SMA50']), 2)})
                if not math.isnan(row['SMA200']):
                    sma200_data.append({"time": date_str, "value": round(float(row['SMA200']), 2)})

        # Fundamental and Profile data with multi-tier fallback
        try:
            info = ticker.info or {}
        except Exception:
            info = {}

        try:
            finfo = dict(ticker.fast_info) if hasattr(ticker, 'fast_info') else {}
        except Exception:
            finfo = {}

        all_local = get_all_stocks()
        local_s = next((s for s in all_local if s.get("symbol") == sym), {})

        def generate_ai_summary(fund, local_data):
            pe = fund.get("pe_ratio", "-")
            margin = fund.get("profit_margin", "-")
            upside = fund.get("upside_pct")
            rec = fund.get("recommendation", "BUY")
            name = fund.get("name", sym).split()[0].replace(',', '')
            
            rsi = local_data.get("rsi")
            monthly_ret = local_data.get("monthly_return")
            
            summary = f"🧠 ניתוח AI מבוסס נתונים: "
            
            # Valuation
            if pe != "-" and float(pe) < 15:
                summary += f"חברת {name} נסחרת בתמחור ערך אטרקטיבי (מכפיל {pe}), "
            elif pe != "-" and float(pe) > 35:
                summary += f"חברת {name} מתומחרת בצפי צמיחה גבוה (מכפיל {pe}), "
            else:
                summary += f"{name} נסחרת במכפיל סביר לתעשייה, "
            
            # Profitability
            if margin != "-" and float(margin.replace("%", "")) > 20:
                summary += f"ומציגה שולי רווח חזקים מאוד של {margin}. "
            elif margin != "-" and float(margin.replace("%", "")) > 0:
                summary += f"עם רווחיות חיובית של {margin}. "
            else:
                summary += "אך ללא רווחיות נטו כרגע. "
                
            # Technical Momentum
            if rsi:
                if rsi > 70:
                    summary += f"מבחינה טכנית המומנטום חזק אך נמצא בטריטוריית קניית יתר (RSI {rsi}). "
                elif rsi < 35:
                    summary += f"טכנית, המניה עשויה להיות באזור מכירת יתר (הזדמנות איסוף). "
                elif monthly_ret and monthly_ret > 5:
                    summary += "המומנטום בחודש האחרון חיובי במיוחד ומעיד על כניסת כספים. "
                    
            # Analyst Sentiment
            if upside and upside > 5:
                summary += f"הקונצנזוס בוול-סטריט הוא ״{rec}״ עם צפי לעלייה של {upside}% בשנה הקרובה."
            elif upside and upside < 0:
                summary += f"עם זאת, האנליסטים סבורים שהיא מתומחרת במלואה כרגע."
            else:
                summary += f"קונצנזוס האנליסטים הנוכחי הוא ״{rec}״."
                
            return summary

        def fmt_cap(val):
            if not val or math.isnan(val): return "-"
            if val >= 1e12: return f"${val/1e12:.2f}T"
            if val >= 1e9: return f"${val/1e9:.2f}B"
            if val >= 1e6: return f"${val/1e6:.2f}M"
            return f"${val:,.0f}"

        cur_price = float(hist['Close'].iloc[-1]) if not hist.empty else float(info.get('currentPrice') or finfo.get('lastPrice') or local_s.get('price', 0))
        prev_close = float(hist['Close'].iloc[-2]) if len(hist) >= 2 else (float(finfo.get('previousClose', 0)) or cur_price)
        change_pct = round(((cur_price / prev_close) - 1) * 100, 2) if prev_close else 0.0

        raw_target = (
            info.get('targetMeanPrice') or
            info.get('targetMedianPrice') or
            info.get('targetHighPrice')
        )
        if not raw_target:
            try:
                apt = ticker.analyst_price_targets
                if isinstance(apt, dict):
                    raw_target = apt.get('mean') or apt.get('current') or apt.get('median')
            except Exception:
                pass

        if not raw_target and local_s.get('target_price'):
            raw_target = local_s.get('target_price')

        target_price = round(float(raw_target), 2) if (raw_target and not math.isnan(float(raw_target))) else 0.0
        upside_pct = round(((target_price / cur_price) - 1) * 100, 1) if (target_price > 0 and cur_price > 0) else None

        # Resolve stats with fallback
        raw_mcap = info.get("marketCap") or finfo.get("marketCap") or finfo.get("market_cap")
        raw_pe = info.get("trailingPE") or local_s.get("pe_ratio")
        raw_forward_pe = info.get("forwardPE")
        raw_margin = info.get("profitMargins") or local_s.get("profit_margin")
        raw_52high = info.get("fiftyTwoWeekHigh") or finfo.get("yearHigh") or local_s.get("high_52w")
        raw_52low = info.get("fiftyTwoWeekLow") or finfo.get("yearLow") or local_s.get("low_52w")

        # Dividend yield formatting
        dr = info.get('dividendRate')
        if dr and cur_price and cur_price > 0:
            div_str = f"{(float(dr) / cur_price) * 100:.2f}%"
        elif info.get('dividendYield') is not None and not math.isnan(info.get('dividendYield')):
            div_str = f"{float(info.get('dividendYield')):.2f}%"
        elif local_s.get('dividend_yield'):
            div_str = f"{float(local_s.get('dividend_yield')):.2f}%"
        else:
            div_str = "0.00%"

        fundamentals = {
            "name": info.get("longName") or info.get("shortName") or local_s.get("name") or sym,
            "sector": info.get("sector") or local_s.get("sector") or "-",
            "industry": info.get("industry") or "-",
            "price": round(cur_price, 2),
            "change_pct": change_pct,
            "market_cap": fmt_cap(raw_mcap),
            "pe_ratio": round(float(raw_pe), 2) if raw_pe and not math.isnan(float(raw_pe)) else "-",
            "forward_pe": round(float(raw_forward_pe), 2) if raw_forward_pe and not math.isnan(float(raw_forward_pe)) else "-",
            "profit_margin": f"{float(raw_margin)*100:.1f}%" if raw_margin and not math.isnan(float(raw_margin)) else "-",
            "dividend_yield": div_str,
            "high_52w": round(float(raw_52high), 2) if raw_52high and not math.isnan(float(raw_52high)) else "-",
            "low_52w": round(float(raw_52low), 2) if raw_52low and not math.isnan(float(raw_52low)) else "-",
            "target_price": round(target_price, 2) if target_price else "-",
            "upside_pct": upside_pct,
            "recommendation": (info.get("recommendationKey") or local_s.get("recommendation") or "BUY").replace("_", " ").upper(),
            "debt_to_equity": round(float(info.get("debtToEquity")), 1) if info.get("debtToEquity") else (local_s.get("debt_equity") or "-")
        }

        # Safe News Extraction (Never crash on None or unusual structures)
        news_data = []
        try:
            raw_news = ticker.news or []
            for item in raw_news[:4]:
                if not isinstance(item, dict):
                    continue
                title = item.get("title") or ""
                content = item.get("content")
                if not title and isinstance(content, dict):
                    title = content.get("title", "")
                
                publisher = item.get("publisher") or item.get("provider") or ""
                if not publisher and isinstance(content, dict):
                    pub_obj = content.get("provider")
                    if isinstance(pub_obj, dict):
                        publisher = pub_obj.get("displayName", "News")
                    elif pub_obj:
                        publisher = str(pub_obj)
                if not publisher:
                    publisher = "News"
                    
                link = item.get("link") or ""
                if not link and isinstance(content, dict):
                    url_obj = content.get("clickThroughUrl")
                    if isinstance(url_obj, dict):
                        link = url_obj.get("url", "#")
                if not link:
                    link = "#"

                if title:
                    news_data.append({"title": title, "publisher": publisher, "link": link})
        except Exception:
            pass

        return {
            "symbol": sym,
            "fundamentals": fundamentals,
            "ai_summary": generate_ai_summary(fundamentals, local_s),
            "chart": {
                "candlesticks": candlesticks,
                "volumes": volumes,
                "sma50": sma50_data,
                "sma200": sma200_data
            },
            "news": news_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class BacktestRequest(BaseModel):
    symbols: list[str]
    timeframe: str = "1Y"
    initial_capital: float = 10000.0
    benchmark_symbol: str = "SPY"

@app.post("/api/backtest")
def api_backtest(req: BacktestRequest):
    try:
        return run_portfolio_backtest(
            symbols=req.symbols,
            timeframe=req.timeframe,
            initial_capital=req.initial_capital,
            benchmark_symbol=req.benchmark_symbol
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/backtest/report", response_class=HTMLResponse)
def api_backtest_report(req: BacktestRequest):
    try:
        data = run_portfolio_backtest(
            symbols=req.symbols,
            timeframe=req.timeframe,
            initial_capital=req.initial_capital,
            benchmark_symbol=req.benchmark_symbol
        )
        return generate_tear_sheet_html(data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
