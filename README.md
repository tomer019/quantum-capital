# ⚡ Quantum Capital | Quantitative Trading & Research Platform

<div align="center">

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![TradingView](https://img.shields.io/badge/Charts-Lightweight_Charts-2962FF.svg?style=for-the-badge)](https://tradingview.github.io/lightweight-charts/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

**A high-performance algorithmic trading, quantitative screening, and portfolio backtesting workstation powered by FastAPI, Yahoo Finance API, and Lightweight Charts.**

</div>

---

## 🚀 Key Features

### 🤖 1. Multi-Strategy Algorithmic Screener
- **Fundamental Value Strategy:** Screens undervalued, profitable enterprises using inverse P/E, profit margins, and dividend yields.
- **Quantitative Momentum Strategy:** Detects short-to-medium breakouts using Rate of Change (Monthly & Weekly returns), institutional volume spikes (Volume Pulse), and 50-day SMA trend filtering.
- **Multi-Index Support:** Screen S&P 500, Nasdaq 100, and Tel Aviv 125 with dynamic capital allocation calculations.
- **1-Click Portfolio Sync:** Directly import screened stock allocations into the virtual trading dashboard.

### 🧪 2. Historical Backtest Lab & Tear Sheet Generator
- **Full Quantitative Metrics:** Cumulative Return, CAGR, Sharpe Ratio ($R_f=4.5\%$), Sortino Ratio, Max Drawdown, Win Rate, Alpha ($\alpha$), and Beta ($\beta$) relative to benchmark (SPY, QQQ, DIA).
- **Interactive Equity Curve:** Synchronized comparison chart between algo portfolio and benchmark.
- **Monthly Return Heatmap Matrix:** Year-by-month return breakdown with conditional color formatting.
- **Institutional Tear Sheet Report:** One-click PDF/HTML performance report generation.

### 📊 3. Interactive Stock Deep-Dive Panel
- **Candlestick Charting:** Real-time green/red candlestick charts powered by TradingView Lightweight Charts.
- **Technical Overlays:** Toggleable 50-day and 200-day Simple Moving Averages.
- **Institutional Valuation Matrix:** Market Cap, P/E vs. Forward P/E, Profit Margins, 52-Week Range, and Debt-to-Equity.
- **Wall Street Consensus & 12-Month Price Target:** Average analyst consensus rating and calculated upside percentage.

### 💼 4. Virtual Portfolio & Watchlist
- Real-time portfolio valuation with auto-updating live market quotes.
- Asset allocation breakdown.
- LocalStorage persistence for star-marked watchlist items.

---

## 🧠 Mathematical & Quantitative Models

### 1. Fundamental Value Model
$$\text{Value Score} = \left( \frac{1}{\text{P/E}} \times 40\% \right) + (\text{Profit Margin} \times 30\%) + (\text{Dividend Yield} \times 30\%)$$

### 2. Quantitative Momentum Model
$$\text{Momentum Score} = (\text{Return}_{1M} \times 50\%) + (\text{Return}_{1W} \times 30\%) + ((\text{Volume Pulse} - 1) \times 20)$$
$$\text{Volume Pulse} = \frac{\text{Mean Volume}_{5D}}{\text{Mean Volume}_{30D}}$$

---

## 🛠️ Tech Stack & Architecture

- **Backend:** Python 3.11+, FastAPI, Uvicorn, Pandas, NumPy, yfinance.
- **Frontend:** Modern Vanilla ES6+ JavaScript, CSS3 Custom Properties (Dark Fintech Theme), HTML5.
- **Visualizations:** TradingView Lightweight Charts, Chart.js.
- **Data Pipeline:** Asynchronous thread pool downloads with in-memory TTL caching (30-minute auto-expiry).

---

## 💻 Getting Started

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/quantum-capital.git
   cd quantum-capital
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch the platform:**
   ```bash
   python -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload
   ```

5. **Open in browser:**
   Navigate to [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## ☁️ Cloud Deployment (Render / Railway)

1. Push this repository to your GitHub account.
2. Connect to **Render.com** -> New **Web Service**.
3. **Build Command:** `pip install -r requirements.txt`
4. **Start Command:** `uvicorn server:app --host 0.0.0.0 --port $PORT`
5. Click **Deploy**!

---

## 📜 Disclaimer
*This platform is developed strictly for educational, portfolio demonstration, and research purposes. Historical backtesting is no guarantee of future returns. Nothing contained herein constitutes financial or investment advice.*
