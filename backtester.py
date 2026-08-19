import math
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import yfinance as yf

def run_portfolio_backtest(
    symbols: list[str],
    timeframe: str = "1Y",
    initial_capital: float = 10000.0,
    benchmark_symbol: str = "SPY"
) -> dict:
    if not symbols:
        raise ValueError("Symbols list cannot be empty.")

    days_map = {
        "6M": 182,
        "1Y": 365,
        "2Y": 730,
        "3Y": 1095,
        "5Y": 1825
    }
    days = days_map.get(timeframe.upper(), 365)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days + 15)

    all_tickers = list(set(symbols + [benchmark_symbol]))

    try:
        data = yf.download(
            all_tickers,
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            auto_adjust=True,
            progress=False,
            threads=True
        )
    except Exception as e:
        raise RuntimeError(f"Error downloading market data: {str(e)}")

    if data.empty:
        raise ValueError("No historical price data returned for the selected symbols.")

    if "Close" in data.columns:
        df_close = data["Close"]
    else:
        df_close = data

    if isinstance(df_close, pd.Series):
        df_close = df_close.to_frame(name=all_tickers[0])

    valid_symbols = [s for s in symbols if s in df_close.columns]
    if not valid_symbols:
        raise ValueError("None of the specified portfolio symbols have historical data.")

    df_close = df_close.ffill().bfill().dropna()

    if len(df_close) < 10:
        raise ValueError("Insufficient trading days in the requested period.")

    if benchmark_symbol in df_close.columns:
        bench_prices = df_close[benchmark_symbol]
    else:
        bench_prices = df_close[valid_symbols[0]]

    bench_returns = bench_prices.pct_change().fillna(0.0)

    port_prices = df_close[valid_symbols]
    port_returns_daily = port_prices.pct_change().fillna(0.0).mean(axis=1)

    cum_port_growth = (1.0 + port_returns_daily).cumprod()
    cum_bench_growth = (1.0 + bench_returns).cumprod()

    port_equity = cum_port_growth * initial_capital
    bench_equity = cum_bench_growth * initial_capital

    total_return_port = float((cum_port_growth.iloc[-1] - 1.0) * 100)
    total_return_bench = float((cum_bench_growth.iloc[-1] - 1.0) * 100)

    n_days = len(port_returns_daily)
    years = max(n_days / 252.0, 0.1)
    cagr_port = float(((cum_port_growth.iloc[-1]) ** (1.0 / years) - 1.0) * 100)
    cagr_bench = float(((cum_bench_growth.iloc[-1]) ** (1.0 / years) - 1.0) * 100)

    daily_vol = float(port_returns_daily.std())
    ann_vol_port = float(daily_vol * math.sqrt(252) * 100)
    ann_vol_bench = float(bench_returns.std() * math.sqrt(252) * 100)

    rf_daily = (0.035 / 252.0)
    excess_returns = port_returns_daily - rf_daily
    if daily_vol > 1e-8:
        sharpe_ratio = float((excess_returns.mean() / daily_vol) * math.sqrt(252))
    else:
        sharpe_ratio = 0.0

    downside_returns = port_returns_daily[port_returns_daily < 0]
    downside_std = float(downside_returns.std()) if len(downside_returns) > 0 else 0.0
    if downside_std > 1e-8:
        sortino_ratio = float((excess_returns.mean() / downside_std) * math.sqrt(252))
    else:
        sortino_ratio = 0.0

    running_max = port_equity.cummax()
    drawdowns = (port_equity - running_max) / running_max
    max_drawdown = float(drawdowns.min() * 100)

    bench_running_max = bench_equity.cummax()
    bench_drawdowns = (bench_equity - bench_running_max) / bench_running_max
    bench_max_drawdown = float(bench_drawdowns.min() * 100)

    pos_days = int((port_returns_daily > 0).sum())
    total_days = int((port_returns_daily != 0).sum()) or 1
    win_rate = float((pos_days / total_days) * 100)

    cov_matrix = np.cov(port_returns_daily, bench_returns)
    bench_var = float(np.var(bench_returns))
    if bench_var > 1e-8:
        beta = float(cov_matrix[0, 1] / bench_var)
        alpha = float((cagr_port - (3.5 + beta * (cagr_bench - 3.5))))
    else:
        beta = 1.0
        alpha = 0.0

    timeline = []
    drawdown_timeline = []
    for idx, dt in enumerate(port_equity.index):
        t_str = dt.strftime("%Y-%m-%d")
        timeline.append({
            "time": t_str,
            "portfolio": round(float(port_equity.iloc[idx]), 2),
            "benchmark": round(float(bench_equity.iloc[idx]), 2)
        })
        drawdown_timeline.append({
            "time": t_str,
            "value": round(float(drawdowns.iloc[idx] * 100), 2)
        })

    df_monthly = port_returns_daily.to_frame(name="return")
    df_monthly["Year"] = df_monthly.index.year
    df_monthly["Month"] = df_monthly.index.month

    monthly_table = {}
    for (year, month), group in df_monthly.groupby(["Year", "Month"]):
        m_ret = float(((1.0 + group["return"]).prod() - 1.0) * 100)
        if year not in monthly_table:
            monthly_table[year] = {}
        monthly_table[year][month] = round(m_ret, 2)

    monthly_summary = []
    for y in sorted(monthly_table.keys(), reverse=True):
        row = {"year": y, "months": {}, "total_year": 0.0}
        year_cum = 1.0
        for m in range(1, 13):
            val = monthly_table[y].get(m, None)
            row["months"][m] = val
            if val is not None:
                year_cum *= (1.0 + val / 100.0)
        row["total_year"] = round(float((year_cum - 1.0) * 100), 2)
        monthly_summary.append(row)

    return {
        "summary": {
            "initial_capital": initial_capital,
            "final_portfolio_value": round(float(port_equity.iloc[-1]), 2),
            "final_benchmark_value": round(float(bench_equity.iloc[-1]), 2),
            "total_return_pct": round(total_return_port, 2),
            "benchmark_return_pct": round(total_return_bench, 2),
            "cagr_pct": round(cagr_port, 2),
            "benchmark_cagr_pct": round(cagr_bench, 2),
            "annualized_volatility_pct": round(ann_vol_port, 2),
            "benchmark_volatility_pct": round(ann_vol_bench, 2),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "sortino_ratio": round(sortino_ratio, 2),
            "max_drawdown_pct": round(max_drawdown, 2),
            "benchmark_max_drawdown_pct": round(bench_max_drawdown, 2),
            "win_rate_pct": round(win_rate, 2),
            "beta": round(beta, 2),
            "alpha": round(alpha, 2),
            "symbols_count": len(valid_symbols),
            "valid_symbols": valid_symbols,
            "timeframe": timeframe,
            "benchmark_symbol": benchmark_symbol
        },
        "timeline": timeline,
        "drawdown_timeline": drawdown_timeline,
        "monthly_summary": monthly_summary
    }

def generate_tear_sheet_html(backtest_data: dict) -> str:
    s = backtest_data["summary"]
    monthly = backtest_data.get("monthly_summary", [])
    symbols_str = ", ".join(s["valid_symbols"][:15])
    if len(s["valid_symbols"]) > 15:
        symbols_str += f" ועוד {len(s['valid_symbols']) - 15} מניות"

    month_headers = ["ינו", "פבר", "מרץ", "אפר", "מאי", "יונ", "יול", "אוג", "ספט", "אוק", "נוב", "דצמ"]
    
    monthly_rows_html = ""
    for row in monthly:
        cells = f"<td style='font-weight:bold;'>{row['year']}</td>"
        for m in range(1, 13):
            val = row["months"].get(m)
            if val is None:
                cells += "<td style='color:#666;'>-</td>"
            else:
                bg = "rgba(0, 230, 118, 0.15)" if val >= 0 else "rgba(255, 61, 0, 0.15)"
                color = "#00E676" if val >= 0 else "#FF3D00"
                sign = "+" if val > 0 else ""
                cells += f"<td style='background:{bg}; color:{color}; font-weight:500;'>{sign}{val}%</td>"
        
        y_val = row["total_year"]
        y_color = "#00E676" if y_val >= 0 else "#FF3D00"
        y_sign = "+" if y_val > 0 else ""
        cells += f"<td style='font-weight:bold; color:{y_color};'>{y_sign}{y_val}%</td>"
        monthly_rows_html += f"<tr>{cells}</tr>"

    sign_total = "+" if s['total_return_pct'] > 0 else ""
    sign_cagr = "+" if s['cagr_pct'] > 0 else ""
    sign_alpha = "+" if s['alpha'] > 0 else ""

    html = f"""<!DOCTYPE html>
<html dir="rtl" lang="he">
<head>
    <meta charset="UTF-8">
    <title>Quantum Cap — דוח ביצועים כמותי (Tear Sheet)</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Assistant:wght@300;400;600;700;800&display=swap');
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: 'Assistant', sans-serif; }}
        body {{ background: #0D1117; color: #E6EDF3; padding: 30px; line-height: 1.6; }}
        .sheet-container {{ max-width: 1000px; margin: 0 auto; background: #161B22; border: 1px solid #30363D; border-radius: 12px; padding: 30px; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #30363D; padding-bottom: 20px; margin-bottom: 25px; }}
        .title h1 {{ font-size: 26px; color: #00B8FF; font-weight: 800; }}
        .title p {{ font-size: 14px; color: #8B949E; }}
        .btn-print {{ background: #00B8FF; color: #000; font-weight: 700; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 30px; }}
        .metric-card {{ background: #0D1117; border: 1px solid #30363D; border-radius: 8px; padding: 15px; text-align: center; }}
        .metric-title {{ font-size: 13px; color: #8B949E; margin-bottom: 5px; }}
        .metric-val {{ font-size: 22px; font-weight: 700; }}
        .text-good {{ color: #00E676; }}
        .text-bad {{ color: #FF3D00; }}
        .text-neutral {{ color: #00B8FF; }}
        .section-title {{ font-size: 18px; font-weight: 700; color: #F0F6FC; margin: 25px 0 15px 0; border-right: 4px solid #00B8FF; padding-right: 10px; }}
        table {{ width: 100%; border-collapse: collapse; text-align: center; font-size: 13px; margin-bottom: 20px; }}
        th, td {{ padding: 10px 6px; border: 1px solid #30363D; }}
        th {{ background: #21262D; color: #C9D1D9; }}
        .footer {{ text-align: center; color: #8B949E; font-size: 12px; margin-top: 30px; border-top: 1px solid #30363D; padding-top: 15px; }}
        @media print {{
            body {{ background: #fff; color: #000; padding: 0; }}
            .sheet-container {{ border: none; background: #fff; max-width: 100%; }}
            .btn-print {{ display: none; }}
            .metric-card {{ border: 1px solid #ccc; background: #fafafa; }}
            th {{ background: #eee; color: #000; }}
            td, th {{ border: 1px solid #ddd; }}
        }}
    </style>
</head>
<body>
    <div class="sheet-container">
        <div class="header">
            <div class="title">
                <h1>QUANTUM CAP | דוח ביצועים כמותי (TEAR SHEET)</h1>
                <p>תקופת בדיקה: <strong>{s['timeframe']}</strong> | מניות בתיק: <strong>{symbols_str}</strong> | מדד ייחוס: <strong>{s['benchmark_symbol']}</strong></p>
            </div>
            <button class="btn-print" onclick="window.print()">🖨️ הדפס / שמור כ-PDF</button>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-title">תשואה כוללת (תיק)</div>
                <div class="metric-val text-good">{sign_total}{s['total_return_pct']}%</div>
                <div style="font-size:11px; color:#8B949E;">בנצ'מרק: {s['benchmark_return_pct']}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">תשואה שנתית (CAGR)</div>
                <div class="metric-val text-good">{sign_cagr}{s['cagr_pct']}%</div>
                <div style="font-size:11px; color:#8B949E;">בנצ'מרק: {s['benchmark_cagr_pct']}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">יחס שארפ (Sharpe Ratio)</div>
                <div class="metric-val text-neutral">{s['sharpe_ratio']}</div>
                <div style="font-size:11px; color:#8B949E;">Sortino: {s['sortino_ratio']}</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">צלילה מקסימלית (Max DD)</div>
                <div class="metric-val text-bad">{s['max_drawdown_pct']}%</div>
                <div style="font-size:11px; color:#8B949E;">בנצ'מרק: {s['benchmark_max_drawdown_pct']}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">תנודתיות שנתית</div>
                <div class="metric-val">{s['annualized_volatility_pct']}%</div>
                <div style="font-size:11px; color:#8B949E;">בנצ'מרק: {s['benchmark_volatility_pct']}%</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">אחוז ימים מנצחים</div>
                <div class="metric-val text-good">{s['win_rate_pct']}%</div>
                <div style="font-size:11px; color:#8B949E;">Win Rate</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">אלפא למדד (Alpha)</div>
                <div class="metric-val text-good">{sign_alpha}{s['alpha']}%</div>
                <div style="font-size:11px; color:#8B949E;">תשואה עודפת</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">ביתא (Beta)</div>
                <div class="metric-val text-neutral">{s['beta']}</div>
                <div style="font-size:11px; color:#8B949E;">רגישות לשוק</div>
            </div>
        </div>

        <div class="section-title">פירוט תשואות חודשיות (%)</div>
        <table>
            <thead>
                <tr>
                    <th>שנה</th>
                    <th>{"</th><th>".join(month_headers)}</th>
                    <th>שנתי</th>
                </tr>
            </thead>
            <tbody>
                {monthly_rows_html}
            </tbody>
        </table>

        <div class="section-title">פרטי התיק והון</div>
        <div style="display: flex; justify-content: space-between; font-size: 14px; background: #0D1117; padding: 15px; border-radius: 8px; border: 1px solid #30363D;">
            <div>הון התחלתי: <strong>${s['initial_capital']:,.2f}</strong></div>
            <div>שווי תיק סופי: <strong style="color:#00E676;">${s['final_portfolio_value']:,.2f}</strong></div>
            <div>שווי בנצ'מרק סופי: <strong>${s['final_benchmark_value']:,.2f}</strong></div>
            <div>מספר מניות מנותחות: <strong>{s['symbols_count']}</strong></div>
        </div>

        <div class="footer">
            נוצר אוטומטית על ידי מערכת Quantum Cap Algorithmic Trading Platform | {datetime.now().strftime("%d/%m/%Y %H:%M")}
        </div>
    </div>
</body>
</html>"""
    return html
