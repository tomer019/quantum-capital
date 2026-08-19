document.addEventListener('DOMContentLoaded', () => {
    // Elegant Toast Notification System
    const showToast = (message, type = 'error') => {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            document.body.appendChild(container);
        }
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        const icon = type === 'success' ? '✅' : (type === 'info' ? 'ℹ️' : '⚠️');
        toast.innerHTML = `<span style="font-size:18px;">${icon}</span><span>${message}</span>`;
        
        container.appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('toast-hiding');
            setTimeout(() => toast.remove(), 350);
        }, 3500);
    };

    // Elements
    const capitalSlider = document.getElementById('capital-slider');
    const capitalInput = document.getElementById('capital-input');
    const topNSlider = document.getElementById('top-n-slider');
    const topNValue = document.getElementById('top-n-value');
    const peSlider = document.getElementById('pe-slider');
    const peValue = document.getElementById('pe-value');
    const indexSelect = document.getElementById('index-select');
    const btnScan = document.getElementById('btn-scan');
    
    const resultsBody = document.getElementById('results-body');
    const resultsCount = document.getElementById('results-count');

    // Update slider values
    capitalSlider.addEventListener('input', (e) => {
        capitalInput.value = e.target.value;
    });

    capitalInput.addEventListener('input', (e) => {
        capitalSlider.value = e.target.value;
    });

    topNSlider.addEventListener('input', (e) => {
        topNValue.textContent = e.target.value;
    });

    peSlider.addEventListener('input', (e) => {
        peValue.textContent = e.target.value + '.0';
    });



    // Deep-Dive Modal Logic
    const modal = document.getElementById('stock-modal');
    const closeModal = document.getElementById('close-modal');
    const modalSymbol = document.getElementById('modal-symbol');
    const modalCompanyName = document.getElementById('modal-company-name');
    const modalSectorBadge = document.getElementById('modal-sector-badge');
    const modalPrice = document.getElementById('modal-price');
    const modalChange = document.getElementById('modal-change');
    const btnModalBacktest = document.getElementById('btn-modal-backtest');
    const btnModalWatchlist = document.getElementById('btn-modal-watchlist');
    const newsList = document.getElementById('news-list');
    const toggleSma50 = document.getElementById('toggle-sma50');
    const toggleSma200 = document.getElementById('toggle-sma200');

    let modalChart = null;
    let candleSeries = null;
    let volumeSeries = null;
    let sma50Series = null;
    let sma200Series = null;
    let currentModalSymbol = null;

    closeModal.onclick = () => {
        modal.style.display = "none";
    };

    window.onclick = (event) => {
        if (event.target == modal) {
            modal.style.display = "none";
        }
    };

    if (btnModalBacktest) {
        btnModalBacktest.addEventListener('click', () => {
            if (!currentModalSymbol) return;
            modal.style.display = "none";
            const btInput = document.getElementById('bt-symbols-input');
            if (btInput) btInput.value = currentModalSymbol;
            switchView('backtest');
            runBacktest();
        });
    }

    const btnModalAddPortfolio = document.getElementById('btn-modal-add-portfolio');
    if (btnModalAddPortfolio) {
        btnModalAddPortfolio.addEventListener('click', () => {
            if (!currentModalSymbol) return;
            let port = JSON.parse(localStorage.getItem('quantum_portfolio')) || [];
            const existing = port.find(p => p.symbol === currentModalSymbol);
            if (existing) {
                existing.qty += 10;
            } else {
                port.push({ symbol: currentModalSymbol, qty: 10 });
            }
            localStorage.setItem('quantum_portfolio', JSON.stringify(port));
            showToast(`נוספו 10 מניות ${currentModalSymbol} לתיק האישי!`, 'success');
            refreshDashboard();
        });
    }

    const btnSyncPortfolio = document.getElementById('btn-sync-portfolio');
    if (btnSyncPortfolio) {
        btnSyncPortfolio.addEventListener('click', () => {
            if (!currentResults || currentResults.length === 0) {
                showToast('אנא הרץ סריקה תחילה כדי שיהיו מניות לייבוא.', 'info');
                return;
            }
            let port = JSON.parse(localStorage.getItem('quantum_portfolio')) || [];
            let addedCount = 0;
            currentResults.forEach(s => {
                const shares = s.shares_to_buy > 0 ? s.shares_to_buy : 10;
                const buyPrice = s.price || 0;
                const existing = port.find(p => p.symbol === s.symbol);
                if (existing) {
                    const oldTotal = existing.qty * (existing.avgPrice || buyPrice);
                    const newTotal = shares * buyPrice;
                    existing.qty += shares;
                    existing.avgPrice = (oldTotal + newTotal) / existing.qty;
                } else {
                    port.push({ symbol: s.symbol, qty: shares, avgPrice: buyPrice });
                }
                addedCount++;
            });
            localStorage.setItem('quantum_portfolio', JSON.stringify(port));
            showToast(`נוספו ${addedCount} מניות לתיק האישי! 💼`, 'success');
            refreshDashboard();
            switchView('dashboard');
        });
    }

    if (btnModalWatchlist) {
        btnModalWatchlist.addEventListener('click', () => {
            if (!currentModalSymbol) return;
            toggleWatchlist(currentModalSymbol);
            const wl = JSON.parse(localStorage.getItem('quantum_watchlist')) || [];
            const isStarred = wl.includes(currentModalSymbol);
            btnModalWatchlist.textContent = isStarred ? '★ במועדפים' : '☆ שמור למעקב';
            showToast(isStarred ? `נוספה ${currentModalSymbol} לרשימת המעקב` : `הוסרה ${currentModalSymbol} מרשימת המעקב`, 'info');
        });
    }

    if (toggleSma50) {
        toggleSma50.addEventListener('change', (e) => {
            if (sma50Series) sma50Series.applyOptions({ visible: e.target.checked });
        });
    }

    if (toggleSma200) {
        toggleSma200.addEventListener('change', (e) => {
            if (sma200Series) sma200Series.applyOptions({ visible: e.target.checked });
        });
    }

    const openStockDetails = async (symbol) => {
        currentModalSymbol = symbol;
        modal.style.display = "block";
        modalSymbol.textContent = symbol;
        modalCompanyName.textContent = "טוען נתונים חיים...";
        modalSectorBadge.textContent = "-";
        modalPrice.textContent = "$0.00";
        modalChange.textContent = "0.00%";
        modalChange.className = "text-good";
        newsList.innerHTML = '<p style="color:var(--text-secondary); font-size:12px;">טוען חדשות...</p>';

        const wl = JSON.parse(localStorage.getItem('quantum_watchlist')) || [];
        btnModalWatchlist.textContent = wl.includes(symbol) ? '★ במועדפים' : '⭐ שמור למעקב';

        try {
            const response = await fetch(`/api/stock/${symbol}`);
            if (!response.ok) throw new Error('API Error');
            const data = await response.json();
            const f = data.fundamentals || {};

            // Header info
            modalCompanyName.textContent = f.name || symbol;
            modalSectorBadge.textContent = f.sector || "-";
            modalPrice.textContent = `$${f.price.toFixed(2)}`;
            const isUp = f.change_pct >= 0;
            modalChange.textContent = `${isUp ? '+' : ''}${f.change_pct}%`;
            modalChange.className = isUp ? 'text-good' : 'text-bad';

            const aiContainer = document.getElementById('modal-ai-summary-container');
            const aiText = document.getElementById('modal-ai-text');
            if (data.ai_summary) {
                aiText.textContent = data.ai_summary;
                aiContainer.style.display = 'block';
            } else {
                aiContainer.style.display = 'none';
            }

            // Fundamental Stats Matrix
            document.getElementById('stat-mcap').textContent = f.market_cap || "-";
            document.getElementById('stat-pe').textContent = f.pe_ratio || "-";
            document.getElementById('stat-margin').textContent = f.profit_margin || "-";
            document.getElementById('stat-div').textContent = f.dividend_yield || "-";
            document.getElementById('stat-52w').textContent = (f.low_52w !== '-' && f.high_52w !== '-') ? `$${f.low_52w} - $${f.high_52w}` : "-";
            document.getElementById('stat-rec').textContent = f.recommendation || "-";

            // Target Price & Upside
            const targetEl = document.getElementById('stat-target-price');
            const upsideEl = document.getElementById('stat-upside-badge');
            const hasTarget = f.target_price && f.target_price !== '-' && parseFloat(f.target_price) > 0;
            if (hasTarget) {
                targetEl.textContent = `$${parseFloat(f.target_price).toFixed(2)}`;
                targetEl.style.fontSize = '20px';
                targetEl.style.color = '#00B8FF';
                if (f.upside_pct !== null && f.upside_pct !== undefined) {
                    const upPos = f.upside_pct >= 0;
                    upsideEl.textContent = `${upPos ? '+' : ''}${f.upside_pct}% פוטנציאל`;
                    upsideEl.style.background = upPos ? 'rgba(0, 230, 118, 0.15)' : 'rgba(255, 61, 0, 0.15)';
                    upsideEl.style.color = upPos ? '#00E676' : '#FF3D00';
                    upsideEl.style.display = 'block';
                } else {
                    upsideEl.style.display = 'none';
                }
            } else {
                targetEl.textContent = "אין כיסוי בוול-סטריט";
                targetEl.style.fontSize = '14px';
                targetEl.style.color = 'var(--text-secondary)';
                upsideEl.style.display = 'none';
            }

            // Candlestick Chart Rendering
            const chartContainer = document.getElementById('modal-candlestick-chart');
            chartContainer.innerHTML = '';
            
            modalChart = LightweightCharts.createChart(chartContainer, {
                width: chartContainer.clientWidth,
                height: 380,
                layout: {
                    background: { type: 'solid', color: 'transparent' },
                    textColor: '#8B949E',
                    fontFamily: 'Assistant, sans-serif'
                },
                grid: {
                    vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                    horzLines: { color: 'rgba(255, 255, 255, 0.05)' }
                },
                rightPriceScale: {
                    borderColor: '#30363D',
                    scaleMargins: { top: 0.1, bottom: 0.25 }
                },
                timeScale: {
                    borderColor: '#30363D',
                    timeVisible: true
                },
                crosshair: {
                    vertLine: { color: 'rgba(255, 255, 255, 0.2)', width: 1 },
                    horzLine: { color: 'rgba(255, 255, 255, 0.2)', width: 1 }
                }
            });

            // 1. Candlestick Series
            candleSeries = modalChart.addCandlestickSeries({
                upColor: '#00E676',
                downColor: '#FF3D00',
                borderUpColor: '#00E676',
                borderDownColor: '#FF3D00',
                wickUpColor: '#00E676',
                wickDownColor: '#FF3D00',
            });
            candleSeries.setData(data.chart.candlesticks || []);

            // 2. Volume Series
            volumeSeries = modalChart.addHistogramSeries({
                priceFormat: { type: 'volume' },
                priceScaleId: '',
                scaleMargins: { top: 0.8, bottom: 0 }
            });
            volumeSeries.setData(data.chart.volumes || []);

            // 3. SMA 50 Line (Neon Cyan)
            sma50Series = modalChart.addLineSeries({
                color: '#00B8FF',
                lineWidth: 2,
                title: 'SMA 50',
                priceLineVisible: false
            });
            sma50Series.setData(data.chart.sma50 || []);
            if (toggleSma50) sma50Series.applyOptions({ visible: toggleSma50.checked });

            // 4. SMA 200 Line (Amber)
            sma200Series = modalChart.addLineSeries({
                color: '#F59E0B',
                lineWidth: 2,
                title: 'SMA 200',
                priceLineVisible: false
            });
            sma200Series.setData(data.chart.sma200 || []);
            if (toggleSma200) sma200Series.applyOptions({ visible: toggleSma200.checked });

            modalChart.timeScale().fitContent();

            // Populate News
            newsList.innerHTML = '';
            if (data.news && data.news.length > 0) {
                data.news.forEach(item => {
                    newsList.innerHTML += `
                        <div style="background: rgba(255,255,255,0.03); padding: 8px 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,0.05);">
                            <a href="${item.link}" target="_blank" style="color: #fff; text-decoration: none; font-size: 12px; font-weight: 500; display: block; line-height: 1.4;">${item.title}</a>
                            <span style="font-size: 10px; color: var(--accent-blue); margin-top: 4px; display: inline-block;">${item.publisher}</span>
                        </div>
                    `;
                });
            } else {
                newsList.innerHTML = '<p style="color:var(--text-secondary); font-size: 12px;">אין חדשות אחרונות.</p>';
            }

        } catch (error) {
            console.error('Error fetching deep-dive:', error);
            showToast(`שגיאה בטעינת נתוני ${symbol}: ${error.message}`, 'error');
            modalCompanyName.textContent = 'שגיאה בטעינה';
        }
    };

    // Sorting state
    let currentResults = [];
    let currentResultsValue = [];
    let currentResultsMomentum = [];
    let currentSort = { column: 'pe_ratio', asc: true };

    let valueAllocation = 0;
    let valueTotal = 0;
    let momentumAllocation = 0;
    let momentumTotal = 0;

    // Format money helper
    const formatMoney = (amount) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            maximumFractionDigits: 0
        }).format(amount);
    };

    const dividendSlider = document.getElementById('dividend-slider');
    const dividendValue = document.getElementById('dividend-value');

    if (dividendSlider) {
        dividendSlider.addEventListener('input', (e) => {
            dividendValue.textContent = `${e.target.value}%`;
        });
    }

    // ─── MODE MANAGEMENT ─────────────────────────────────────────────────────
    let currentMode = localStorage.getItem('quantum_mode') || 'value';

    const btnModeValue      = document.getElementById('btn-mode-value');
    const btnModeMomentum   = document.getElementById('btn-mode-momentum');
    const valueControls     = document.querySelector('.card.strategy-card');
    const momentumControls  = document.getElementById('momentum-controls');
    const screenerTitle     = document.getElementById('screener-title');
    const thead             = document.querySelector('#results-table thead tr');

    const VALUE_HEADERS = `
        <th data-sort="symbol" class="sortable" title="סימול המניה">מניה ↕</th>
        <th data-sort="name" class="sortable" title="שם החברה">חברה ↕</th>
        <th data-sort="sector" class="sortable" title="סקטור פיננסי">סקטור ↕</th>
        <th data-sort="price" class="sortable" title="מחיר אחרון בדולרים">מחיר ($) ↕</th>
        <th data-sort="pe_ratio" class="sortable" title="מכפיל רווח: מחיר חלקי רווח למניה. ככל שנמוך יותר, המניה זולה יותר">P/E ↕</th>
        <th data-sort="profit_margin" class="sortable" title="שולי רווח נקי: אחוז הרווח הנקי מתוך סך ההכנסות">שולי רווח ↕</th>
        <th data-sort="dividend_yield" class="sortable" title="תשואת דיבידנד שנתית באחוזים">דיבידנד ↕</th>
        <th data-sort="shares_to_buy" class="sortable" title="כמות מניות מומלצת לקנייה לחלוקת הון שווה">הקצאה ↕</th>
        <th>מעקב</th>`;

    const MOMENTUM_HEADERS = `
        <th data-sort="symbol" class="sortable" title="סימול המניה">מניה ↕</th>
        <th data-sort="name" class="sortable" title="שם החברה">חברה ↕</th>
        <th data-sort="sector" class="sortable" title="סקטור פיננסי">סקטור ↕</th>
        <th data-sort="price" class="sortable" title="מחיר אחרון בדולרים">מחיר ($) ↕</th>
        <th data-sort="monthly_return" class="sortable" title="תשואת מחיר ב-30 הימים האחרונים">שינוי חודשי ↕</th>
        <th data-sort="weekly_return" class="sortable" title="תשואת מחיר ב-7 הימים האחרונים">שינוי שבועי ↕</th>
        <th data-sort="volume_pulse" class="sortable" title="פאלס נפח: יחס מחזור המסחר האחרון מול ממוצע 30 יום">נפח ↕</th>
        <th data-sort="rsi" class="sortable" title="מדד עוצמה יחסית (14 יום). מעל 70 = קניית יתר, מתחת 30 = מכירת יתר">RSI ↕</th>
        <th data-sort="above_ma" class="sortable" title="האם המחיר מעל ממוצע נע 50 יום (טרנד חיובי)">טרנד ↕</th>
        <th data-sort="score" class="sortable" title="ציון עוצמת המומנטום המשוקלל">סיגנל ↕</th>
        <th data-sort="shares_to_buy" class="sortable" title="כמות מניות מומלצת לקנייה לחלוקת הון שווה">הקצאה ↕</th>
        <th>מעקב</th>`;

    const applyMode = (mode) => {
        currentMode = mode;
        localStorage.setItem('quantum_mode', mode);
        document.getElementById('results-count').textContent = '';

        if (mode === 'momentum') {
            btnModeValue.classList.remove('active');
            btnModeMomentum.classList.add('active');
            if (valueControls) valueControls.style.display = 'none';
            if (momentumControls) momentumControls.style.display = 'block';
            if (thead) thead.innerHTML = MOMENTUM_HEADERS;
            
            currentSort = { column: 'score', asc: false };
            currentResults = currentResultsMomentum;
            if (currentResults.length > 0) {
                if (screenerTitle) screenerTitle.textContent = `סריקת מומנטום — נמצאו ${currentResults.length} מניות`;
                renderMomentumTable(currentResults);
            } else {
                if (screenerTitle) screenerTitle.textContent = 'סריקת מומנטום (טווח קצר)';
                resultsBody.innerHTML = '<tr><td colspan="11"><div class="empty-state"><div class="empty-state-icon">⚡</div><p>לחץ "סרוק מומנטום" כדי להתחיל</p></div></td></tr>';
            }
        } else {
            btnModeMomentum.classList.remove('active');
            btnModeValue.classList.add('active');
            if (valueControls) valueControls.style.display = 'block';
            if (momentumControls) momentumControls.style.display = 'none';
            if (thead) thead.innerHTML = VALUE_HEADERS;

            currentSort = { column: 'pe_ratio', asc: true };
            currentResults = currentResultsValue;
            if (currentResults.length > 0) {
                if (screenerTitle) screenerTitle.textContent = `תוצאות הסריקה — נמצאו ${currentResults.length} מניות`;
                renderTable();
            } else {
                if (screenerTitle) screenerTitle.textContent = `תוצאות הסריקה (S&P 500)`;
                resultsBody.innerHTML = '<tr><td colspan="8"><div class="empty-state"><div class="empty-state-icon">🔍</div><p>לחץ "הרץ סריקת רובוט" כדי להתחיל</p></div></td></tr>';
            }
        }
        
        renderAllocationSummary();
    };

    if (btnModeValue)     btnModeValue.addEventListener('click',     () => applyMode('value'));
    if (btnModeMomentum)  btnModeMomentum.addEventListener('click',  () => applyMode('momentum'));

    // Momentum capital slider
    const momentumCapitalSlider = document.getElementById('momentum-capital-slider');
    const momentumCapitalInput = document.getElementById('momentum-capital-input');
    if (momentumCapitalSlider && momentumCapitalInput) {
        momentumCapitalSlider.addEventListener('input', (e) => {
            momentumCapitalInput.value = e.target.value;
        });
        momentumCapitalInput.addEventListener('input', (e) => {
            momentumCapitalSlider.value = e.target.value;
        });
    }

    // Momentum top-n slider
    const momentumTopN = document.getElementById('momentum-top-n');
    const momentumTopNValue = document.getElementById('momentum-top-n-value');
    if (momentumTopN) {
        momentumTopN.addEventListener('input', (e) => {
            momentumTopNValue.textContent = e.target.value;
        });
    }

    // ─── MOMENTUM SCAN ───────────────────────────────────────────────────────
    const runMomentumScan = async () => {
        const btnM = document.getElementById('btn-momentum-scan');
        const indexSel = document.getElementById('momentum-index-select');
        if (!btnM) return;

        btnM.textContent = '⚡ סורק...';
        btnM.disabled = true;
        resultsBody.innerHTML = Array(5).fill('<tr><td colspan="9"><div class="skeleton-row"></div></td></tr>').join('');
        if (screenerTitle) screenerTitle.textContent = `סריקת מומנטום (${indexSel?.value || 'SP500'}) — שואב נתוני מחירים...`;

        try {
            const res = await fetch('/api/screen_momentum', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    capital: parseFloat(momentumCapitalInput?.value || 10000),
                    top_n: parseInt(momentumTopN?.value || 10),
                    index_name: indexSel?.value || 'SP500',
                    min_price: parseFloat(document.getElementById('momentum-min-price')?.value || 0.0),
                    max_price: parseFloat(document.getElementById('momentum-max-price')?.value || 1000000.0)
                })
            });
            const data = await res.json();
            const stocks = data.results || [];
            currentResultsMomentum = stocks;
            currentResults = stocks;
            momentumAllocation = data.allocation_per_stock || 0;
            momentumTotal = data.total_allocated || 0;

            if (screenerTitle) screenerTitle.textContent = `סריקת מומנטום — נמצאו ${stocks.length} מניות`;
            document.getElementById('results-count').textContent = `${stocks.length} מניות עם מומנטום חזק`;

            renderMomentumTable();
            renderAllocationSummary();
        } catch (err) {
            console.error('Momentum scan error:', err);
            resultsBody.innerHTML = '<tr><td colspan="11"><div class="empty-state"><div class="empty-state-icon">⏳</div><p>השרת בענן מתעורר או שואב נתונים היסטוריים...<br><button onclick="runMomentumScan()" class="btn-primary" style="margin-top:10px; padding:6px 14px; width:auto; font-size:13px; background:#F59E0B; color:#000;">נסה שוב 🔄</button></p></div></td></tr>';
            showToast('השרת שואב נתונים היסטוריים, נסה שוב בעוד מספר שניות', 'info');
        } finally {
            btnM.textContent = '⚡ סרוק מומנטום';
            btnM.disabled = false;
        }
    };

    const renderMomentumTable = () => {
        const stocks = currentResults;
        resultsBody.innerHTML = '';
        if (stocks.length === 0) {
            resultsBody.innerHTML = '<tr><td colspan="11"><div class="empty-state"><div class="empty-state-icon">🔍</div><p>לא נמצאו מניות</p></div></td></tr>';
            return;
        }

        const { column, asc } = currentSort;
        stocks.sort((a, b) => {
            let valA = a[column];
            let valB = b[column];
            
            // Special handling for signal column ranking
            if (column === 'score' || column === 'signal') {
                const sigRank = { 'strong': 3, 'moderate': 2, 'weak': 1 };
                valA = a.score !== undefined ? a.score : (sigRank[a.signal] || 0);
                valB = b.score !== undefined ? b.score : (sigRank[b.signal] || 0);
                return asc ? (valA - valB) : (valB - valA);
            }
            if (column === 'price' || column === 'monthly_return' || column === 'weekly_return' || column === 'volume_pulse' || column === 'rsi') {
                valA = parseFloat(valA) || 0;
                valB = parseFloat(valB) || 0;
                return asc ? (valA - valB) : (valB - valA);
            }
            if (column === 'above_ma') {
                valA = a.above_ma ? 1 : 0;
                valB = b.above_ma ? 1 : 0;
                return asc ? (valA - valB) : (valB - valA);
            }
            if (typeof valA === 'string') valA = valA.toLowerCase();
            if (typeof valB === 'string') valB = (typeof valB === 'string') ? valB.toLowerCase() : '';
            if (valA < valB) return asc ? -1 : 1;
            if (valA > valB) return asc ? 1 : -1;
            return 0;
        });

        stocks.forEach(stock => {
            const wl = JSON.parse(localStorage.getItem('quantum_watchlist')) || [];
            const isStarred = wl.includes(stock.symbol);
            const starColor = isStarred ? '#FFD700' : '#4B5563';

            const mRet = stock.monthly_return;
            const wRet = stock.weekly_return;
            const mClass = mRet >= 0 ? 'text-good' : 'text-bad';
            const wClass = wRet >= 0 ? 'text-good' : 'text-bad';
            const mSign = mRet >= 0 ? '+' : '';
            const wSign = wRet >= 0 ? '+' : '';
            const trend = stock.above_ma ? '<span class="text-good">▲</span>' : '<span class="text-bad">▼</span>';
            const volClass = stock.volume_pulse >= 1.5 ? 'text-good' : (stock.volume_pulse < 0.8 ? 'text-bad' : 'text-neutral');

            // RSI color: green = normal zone, orange = overbought, blue = oversold
            const rsi = stock.rsi || 50;
            const rsiClass = rsi > 70 ? 'text-bad' : (rsi < 30 ? '' : 'text-neutral');
            const rsiStyle = rsi > 70 ? 'color:#F59E0B' : (rsi < 30 ? 'color:#60A5FA' : '');

            // Signal badge
            const signalMap = {
                strong:   { emoji: '🟢', label: 'חזק',   color: '#00E676' },
                moderate: { emoji: '🟡', label: 'מעורב', color: '#F59E0B' },
                weak:     { emoji: '🔴', label: 'חלש',   color: '#FF3D00' }
            };
            const sig = signalMap[stock.signal] || signalMap.moderate;

            // Calculate allocation
            const capital = parseFloat(capitalSlider.value) || 0;
            const perStock = capital / (currentResults.length || 1);
            const sharesToBuy = Math.floor(perStock / (stock.price || 1));
            const allocVal = (sharesToBuy * (stock.price || 0)).toLocaleString('en-US', {minimumFractionDigits:0, maximumFractionDigits:0});

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="font-weight:500; color:var(--accent-blue);" dir="ltr">${stock.symbol}</td>
                <td>${stock.name}</td>
                <td><span class="sector-badge">${stock.sector}</span></td>
                <td dir="ltr">$${stock.price.toFixed(2)}</td>
                <td dir="ltr" class="${mClass}">${mSign}${mRet.toFixed(2)}%</td>
                <td dir="ltr" class="${wClass}">${wSign}${wRet.toFixed(2)}%</td>
                <td dir="ltr" class="${volClass}">${stock.volume_pulse}x</td>
                <td dir="ltr" style="${rsiStyle}; font-weight:500;">${rsi}</td>
                <td>${trend}</td>
                <td style="font-weight:600; color:${sig.color}; font-size:13px;">${sig.emoji} ${sig.label}</td>
                <td dir="ltr" style="line-height: 1.4; vertical-align: middle;">
                    <span class="shares-badge" style="display: block; background: rgba(0, 184, 255, 0.12); border: 1px solid rgba(0, 184, 255, 0.25); color: #00B8FF; font-weight: 700; padding: 2px 6px; border-radius: 4px; font-size: 12px; margin-bottom: 2px; text-align: center;">${sharesToBuy} יח'</span>
                    <span style="display: block; font-size: 11px; color: var(--text-secondary); text-align: center;">($${allocVal})</span>
                </td>
                <td>
                    <button onclick="event.stopPropagation(); toggleWatchlist('${stock.symbol}')"
                        style="background:none;border:none;cursor:pointer;color:${starColor};font-size:18px;"
                        title="הוסף למעקב">${isStarred ? '★' : '☆'}</button>
                </td>
            `;
            tr.addEventListener('click', () => openStockDetails(stock.symbol));
            tr.style.cursor = 'pointer';
            resultsBody.appendChild(tr);
        });
    };

    const btnMomentumScan = document.getElementById('btn-momentum-scan');
    if (btnMomentumScan) btnMomentumScan.addEventListener('click', runMomentumScan);

    // Apply saved mode on load
    applyMode(currentMode);

    // ─── END MODE MANAGEMENT ─────────────────────────────────────────────────

    // Run Scan
    const runScan = async () => {
        btnScan.textContent = 'סורק נתונים...';
        btnScan.disabled = true;
        
        // Skeleton loading
        resultsBody.innerHTML = Array(5).fill('<tr><td colspan="8"><div class="skeleton-row"></div></td></tr>').join('');
        
        try {
            const reqData = {
                capital: parseFloat(capitalSlider.value),
                top_n: parseInt(topNSlider.value),
                max_pe: parseFloat(peSlider.value),
                min_margin: 0.05,
                min_dividend: dividendSlider ? parseFloat(dividendSlider.value) : 0.0,
                index_name: indexSelect.value,
                min_price: parseFloat(document.getElementById('min-price-value')?.value || 0.0),
                max_price: parseFloat(document.getElementById('max-price-value')?.value || 1000000.0)
            };

            const response = await fetch('/api/screen', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(reqData)
            });

            if (!response.ok) throw new Error('API Error');
            const data = await response.json();
            currentResults = data.results || [];
            currentResultsValue = currentResults;
            valueAllocation = data.allocation_per_stock || 0;
            valueTotal = data.total_allocated || 0;

            // Update title
            const indexNames = {
                'SP500': 'S&P 500',
                'NASDAQ': 'Nasdaq 100',
                'DJI30': 'Dow Jones 30',
                'EUROSTOXX50': 'Euro Stoxx 50',
                'TA125': 'TA-125'
            };
            const titleEl = document.getElementById('screener-title');
            if (titleEl) {
                titleEl.textContent = `תוצאות הסריקה (${indexNames[reqData.index_name]})`;
            }

            // Update count
            resultsCount.textContent = `נמצאו ${currentResults.length} מניות מנצחות`;

            renderTable();
            renderAllocationSummary();

            if (data.results.length === 0) {
                resultsBody.innerHTML = '<tr><td colspan="6" style="text-align: center;">לא נמצאו מניות שעומדות בקריטריונים</td></tr>';
            }

        } catch (error) {
            console.error('Error:', error);
            resultsBody.innerHTML = '<tr><td colspan="8"><div class="empty-state"><div class="empty-state-icon">⏳</div><p>השרת בענן מתעורר משינה (Cold Start) או שחלה השהיה קלה ברשת.<br><button onclick="runScan()" class="btn-primary" style="margin-top:10px; padding:6px 14px; width:auto; font-size:13px; background:var(--accent-blue); color:#000;">נסה שוב 🔄</button></p></div></td></tr>';
            showToast('השרת בענן מתעורר (Cold Start), נסה שוב בעוד מספר שניות', 'info');
        } finally {
            btnScan.textContent = 'הרץ סריקת רובוט 🚀';
            btnScan.disabled = false;
        }
    };

    btnScan.addEventListener('click', runScan);
    
    const renderTable = () => {
        resultsBody.innerHTML = '';
        if (currentResults.length === 0) {
            resultsBody.innerHTML = '<tr><td colspan="8"><div class="empty-state"><div class="empty-state-icon">🔍</div><p>לא נמצאו מניות שעומדות בקריטריונים</p></div></td></tr>';
            return;
        }

        // Perform sort
        const { column, asc } = currentSort;
        currentResults.sort((a, b) => {
            let valA = a[column];
            let valB = b[column];
            if (column === 'price' || column === 'pe_ratio' || column === 'profit_margin' || column === 'dividend_yield' || column === 'score') {
                valA = parseFloat(valA) || 0;
                valB = parseFloat(valB) || 0;
                return asc ? (valA - valB) : (valB - valA);
            }
            if (typeof valA === 'string') valA = valA.toLowerCase();
            if (typeof valB === 'string') valB = (typeof valB === 'string') ? valB.toLowerCase() : '';
            if (valA < valB) return asc ? -1 : 1;
            if (valA > valB) return asc ? 1 : -1;
            return 0;
        });

        resultsBody.innerHTML = '';
        currentResults.forEach(stock => {
            const divYield = stock.dividend_yield ? (stock.dividend_yield).toFixed(2) + '%' : '0.00%';
            
            // Color coding
            const peClass = stock.pe_ratio < 15 ? 'text-good' : (stock.pe_ratio > 25 ? 'text-bad' : 'text-neutral');
            const marginClass = stock.profit_margin > 0.20 ? 'text-good' : 'text-neutral';

            // Check if in watchlist
            const wl = JSON.parse(localStorage.getItem('quantum_watchlist')) || [];
            const isStarred = wl.includes(stock.symbol);
            const starColor = isStarred ? '#FFD700' : '#4B5563';

            // Calculate allocation
            const capital = parseFloat(capitalSlider.value) || 0;
            const perStock = capital / (currentResults.length || 1);
            const sharesToBuy = Math.floor(perStock / (stock.price || 1));
            const allocVal = (sharesToBuy * (stock.price || 0)).toLocaleString('en-US', {minimumFractionDigits:0, maximumFractionDigits:0});

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="font-weight: 500; color: var(--accent-blue);" class="clickable-symbol" dir="ltr">${stock.symbol}</td>
                <td>${stock.name}</td>
                <td><span class="sector-badge">${stock.sector}</span></td>
                <td dir="ltr">$${stock.price.toFixed(2)}</td>
                <td dir="ltr" class="${peClass}">${stock.pe_ratio.toFixed(1)}</td>
                <td dir="ltr" class="${marginClass}">${(stock.profit_margin * 100).toFixed(1)}%</td>
                <td dir="ltr">${divYield}</td>
                <td dir="ltr" style="line-height: 1.4; vertical-align: middle;">
                    <span class="shares-badge" style="display: block; background: rgba(0, 184, 255, 0.12); border: 1px solid rgba(0, 184, 255, 0.25); color: #00B8FF; font-weight: 700; padding: 2px 6px; border-radius: 4px; font-size: 12px; margin-bottom: 2px; text-align: center;">${sharesToBuy} יח'</span>
                    <span style="display: block; font-size: 11px; color: var(--text-secondary); text-align: center;">($${allocVal})</span>
                </td>
                <td>
                    <button onclick="event.stopPropagation(); toggleWatchlist('${stock.symbol}')" style="background:none; border:none; cursor:pointer; color:${starColor}; font-size:18px;" title="הוסף למעקב">${isStarred ? '★' : '☆'}</button>
                </td>
            `;
            
            tr.addEventListener('click', () => openStockDetails(stock.symbol));
            tr.style.cursor = 'pointer';
            
            resultsBody.appendChild(tr);
        });    };

    // ─── ALLOCATION SUMMARY RENDERER ─────────────────────────────────────────
    const renderAllocationSummary = () => {
        const panel = document.getElementById('allocation-summary');
        const grid = document.getElementById('alloc-grid');
        const statsDiv = document.getElementById('alloc-stats');
        if (!panel || !grid) return;

        let capital = 0;
        if (currentMode === 'momentum' && momentumCapitalSlider) {
            capital = parseFloat(momentumCapitalSlider.value) || 0;
        } else if (capitalSlider) {
            capital = parseFloat(capitalSlider.value) || 0;
        }
        if (!currentResults || currentResults.length === 0 || capital <= 0) {
            panel.style.display = 'none';
            return;
        }

        const perStock = capital / currentResults.length;
        let totalInvested = 0;
        const cards = [];

        currentResults.forEach(stock => {
            const price = stock.price || 0;
            if (price <= 0) return;
            const shares = Math.floor(perStock / price);
            const invested = shares * price;
            totalInvested += invested;
            const pctOfCapital = ((invested / capital) * 100).toFixed(1);
            cards.push(`
                <div style="display:flex; align-items:center; gap:10px; padding:8px 12px; background:var(--bg-card); border:1px solid var(--border-color); border-radius:8px; font-size:13px;">
                    <span style="font-weight:700; color:var(--accent-blue); min-width:60px;" dir="ltr">${stock.symbol}</span>
                    <span style="color:var(--text-primary); font-weight:600;" dir="ltr">${shares} מניות</span>
                    <span style="color:var(--text-secondary); margin-right:auto;" dir="ltr">$${invested.toLocaleString('en-US', {minimumFractionDigits:0, maximumFractionDigits:0})}</span>
                    <span style="color:var(--text-secondary); font-size:11px;" dir="ltr">${pctOfCapital}%</span>
                </div>
            `);
        });

        const remaining = capital - totalInvested;
        statsDiv.innerHTML = `
            <span title="הון כולל להשקעה">💵 הון: <b style="color:var(--text-primary);">$${capital.toLocaleString()}</b></span>
            <span title="סה\"כ מושקע בפועל">📊 מושקע: <b style="color:#00E676;">$${totalInvested.toLocaleString('en-US', {minimumFractionDigits:0, maximumFractionDigits:0})}</b></span>
            <span title="עודף לא מושקע (שארית חלוקה)">🏦 עודף: <b style="color:#F59E0B;">$${remaining.toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2})}</b></span>
        `;
        grid.innerHTML = cards.join('');
        panel.style.display = 'block';
    };

    // Export to CSV
    const btnExportCsv = document.getElementById('btn-export-csv');
    if (btnExportCsv) {
        btnExportCsv.addEventListener('click', () => {
            if (!currentResults || currentResults.length === 0) {
                showToast('אין נתונים לייצוא', 'info');
                return;
            }
            let csvContent = "data:text/csv;charset=utf-8,\uFEFF"; // BOM for Hebrew
            
            if (currentMode === 'momentum') {
                csvContent += "Symbol,Name,Sector,Price,Monthly Return %,Weekly Return %,Volume Pulse,RSI,Trend,Signal,Score\n";
                currentResults.forEach(s => {
                    const sym = s.symbol || '';
                    const name = (s.name || '').replace(/"/g, '""');
                    const sector = s.sector || '-';
                    const price = s.price || 0;
                    const mRet = s.monthly_return !== undefined ? s.monthly_return : '';
                    const wRet = s.weekly_return !== undefined ? s.weekly_return : '';
                    const vol = s.volume_pulse || '';
                    const rsi = s.rsi || '';
                    const trend = s.above_ma ? 'Above MA50' : 'Below MA50';
                    const sig = s.signal || '';
                    const score = s.score !== undefined ? s.score : '';
                    csvContent += `${sym},"${name}",${sector},${price},${mRet},${wRet},${vol},${rsi},${trend},${sig},${score}\n`;
                });
            } else {
                csvContent += "Symbol,Name,Sector,Price,P/E,Profit Margin,Dividend Yield\n";
                currentResults.forEach(s => {
                    const sym = s.symbol || '';
                    const name = (s.name || '').replace(/"/g, '""');
                    const sector = s.sector || '-';
                    const price = s.price || 0;
                    const pe = s.pe_ratio !== undefined ? s.pe_ratio.toFixed(2) : '-';
                    const margin = s.profit_margin !== undefined ? (s.profit_margin * 100).toFixed(2) + '%' : '-';
                    const div = s.dividend_yield !== undefined ? (s.dividend_yield).toFixed(2) + '%' : '0.00%';
                    csvContent += `${sym},"${name}",${sector},${price},${pe},${margin},${div}\n`;
                });
            }
            
            const encodedUri = encodeURI(csvContent);
            const link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", `quantum_${currentMode}_results.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            showToast('הקובץ יוצא בהצלחה לאקסל! 📥', 'success');
        });
    }

    // Sorting Headers (Event Delegation)
    if (thead && thead.parentElement) {
        thead.parentElement.addEventListener('click', (e) => {
            const th = e.target.closest('th.sortable');
            if (!th) return;
            const column = th.dataset.sort;
            if (currentSort.column === column) {
                currentSort.asc = !currentSort.asc;
            } else {
                currentSort.column = column;
                // High-first default for scores, returns, dividends, margins
                if (column === 'score' || column === 'monthly_return' || column === 'weekly_return' || column === 'volume_pulse' || column === 'profit_margin' || column === 'dividend_yield') {
                    currentSort.asc = false;
                } else {
                    currentSort.asc = true;
                }
            }
            if (currentMode === 'momentum') renderMomentumTable();
            else renderTable();
        });
    }

    // Event Listeners for running scan
    capitalSlider.addEventListener('change', runScan);
    capitalInput.addEventListener('change', runScan);
    topNSlider.addEventListener('change', runScan);
    peSlider.addEventListener('change', runScan);
    indexSelect.addEventListener('change', runScan);
    if (dividendSlider) dividendSlider.addEventListener('change', runScan);

    if (momentumCapitalSlider) momentumCapitalSlider.addEventListener('change', runMomentumScan);
    if (momentumCapitalInput) momentumCapitalInput.addEventListener('change', runMomentumScan);
    if (momentumTopN) momentumTopN.addEventListener('change', runMomentumScan);
    const momentumIndexSelect = document.getElementById('momentum-index-select');
    if (momentumIndexSelect) momentumIndexSelect.addEventListener('change', runMomentumScan);

    // Run initial scan based on current mode
    if (currentMode === 'momentum') {
        runMomentumScan();
    } else {
        runScan();
    }

    // ==========================================
    // WATCHLIST LOGIC
    // ==========================================
    const navWatchlist = document.getElementById('nav-watchlist');
    const viewWatchlist = document.getElementById('view-watchlist');
    const watchlistBody = document.getElementById('watchlist-body');

    window.toggleWatchlist = (symbol) => {
        let wl = JSON.parse(localStorage.getItem('quantum_watchlist')) || [];
        if (wl.includes(symbol)) {
            wl = wl.filter(s => s !== symbol);
        } else {
            wl.push(symbol);
        }
        localStorage.setItem('quantum_watchlist', JSON.stringify(wl));
        renderTable(); // Re-render screener to update stars
        if (navWatchlist.classList.contains('active')) {
            refreshWatchlist();
        }
    };

    window.removeFromWatchlist = (symbol) => {
        let wl = JSON.parse(localStorage.getItem('quantum_watchlist')) || [];
        wl = wl.filter(s => s !== symbol);
        localStorage.setItem('quantum_watchlist', JSON.stringify(wl));
        refreshWatchlist();
        renderTable(); // Re-render screener to update stars
    };

    const refreshWatchlist = async () => {
        let wl = JSON.parse(localStorage.getItem('quantum_watchlist')) || [];
        if (wl.length === 0) {
            watchlistBody.innerHTML = '<tr><td colspan="8"><div class="empty-state"><div class="empty-state-icon">⭐</div><p>אין מניות ברשימת המעקב. סמן כוכב בסורק!</p></div></td></tr>';
            return;
        }

        // Skeleton loading
        watchlistBody.innerHTML = Array(wl.length).fill('<tr><td colspan="8"><div class="skeleton-row"></div></td></tr>').join('');
        
        try {
            const res = await fetch('/api/watchlist_details', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbols: wl })
            });
            const data = await res.json();
            const watchlistResults = data.results || [];
            
            watchlistBody.innerHTML = '';
            
            if (watchlistResults.length === 0) {
                 watchlistBody.innerHTML = '<tr><td colspan="8" style="text-align: center;">שגיאה: לא נמצאו הנתונים למניות אלו.</td></tr>';
                 return;
            }

            watchlistResults.forEach(stock => {
                const divYield = stock.dividend_yield ? (stock.dividend_yield).toFixed(2) + '%' : '0.00%';
                const peClass = stock.pe_ratio < 15 ? 'text-good' : (stock.pe_ratio > 25 ? 'text-bad' : 'text-neutral');
                const marginClass = stock.profit_margin > 0.20 ? 'text-good' : 'text-neutral';
                
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td style="font-weight: 500; color: var(--accent-blue);" class="clickable-symbol" dir="ltr">${stock.symbol}</td>
                    <td>${stock.name}</td>
                    <td><span class="sector-badge">${stock.sector}</span></td>
                    <td dir="ltr">$${stock.price.toFixed(2)}</td>
                    <td dir="ltr" class="${peClass}">${stock.pe_ratio.toFixed(1)}</td>
                    <td dir="ltr" class="${marginClass}">${(stock.profit_margin * 100).toFixed(1)}%</td>
                    <td dir="ltr">${divYield}</td>
                    <td>
                        <button onclick="event.stopPropagation(); removeFromWatchlist('${stock.symbol}')" style="background:none; border:none; color:#FF3366; cursor:pointer;" title="הסר מרשימת מעקב">❌</button>
                    </td>
                `;
                
                tr.addEventListener('click', () => openStockDetails(stock.symbol));
                tr.style.cursor = 'pointer';
                
                watchlistBody.appendChild(tr);
            });
        } catch (e) {
            console.error("Watchlist fetch error", e);
            watchlistBody.innerHTML = '<tr><td colspan="8" style="text-align: center; color:red;">שגיאה בטעינת הנתונים</td></tr>';
        }
    };

    if (navWatchlist) navWatchlist.addEventListener('click', (e) => { if (e) e.preventDefault(); switchView('watchlist'); });

    // ==========================================
    // DASHBOARD & PORTFOLIO LOGIC
    // ==========================================
    const navDashboard = document.getElementById('nav-dashboard');
    const navScreener = document.getElementById('nav-screener');
    const viewDashboard = document.getElementById('view-dashboard');
    const viewScreener = document.getElementById('view-screener');
    const btnAddStock = document.getElementById('btn-add-stock');
    const inputSymbol = document.getElementById('add-symbol');
    const inputQty = document.getElementById('add-qty');
    const portfolioBody = document.getElementById('portfolio-body');
    const dashTotalValue = document.getElementById('dash-total-value');
    
    let portfolio = JSON.parse(localStorage.getItem('quantum_portfolio')) || [];
    let portfolioPrices = {};
    let portfolioChart = null;

    if (navDashboard) navDashboard.addEventListener('click', (e) => { if (e) e.preventDefault(); switchView('dashboard'); });
    if (navScreener) navScreener.addEventListener('click', (e) => { if (e) e.preventDefault(); switchView('screener'); });

    // Autocomplete Logic
    const autocompleteInput = document.getElementById('add-symbol');
    const autocompleteList = document.getElementById('autocomplete-list');
    let autocompleteTimeout = null;

    if (autocompleteInput && autocompleteList) {
        autocompleteInput.addEventListener('input', (e) => {
            clearTimeout(autocompleteTimeout);
            const val = e.target.value.trim();
            if (val.length < 2) {
                autocompleteList.style.display = 'none';
                return;
            }
            autocompleteTimeout = setTimeout(async () => {
                try {
                    const res = await fetch(`/api/search_ticker?q=${encodeURIComponent(val)}`);
                    const data = await res.json();
                    autocompleteList.innerHTML = '';
                    if (data.results && data.results.length > 0) {
                        data.results.forEach(item => {
                            const div = document.createElement('div');
                            div.className = 'autocomplete-suggestion';
                            div.innerHTML = `<strong>${item.symbol}</strong> - ${item.name}`;
                            div.addEventListener('click', () => {
                                autocompleteInput.value = item.symbol;
                                autocompleteList.style.display = 'none';
                            });
                            autocompleteList.appendChild(div);
                        });
                        autocompleteList.style.display = 'block';
                    } else {
                        autocompleteList.style.display = 'none';
                    }
                } catch (err) {
                    console.error("Autocomplete error", err);
                }
            }, 300); // 300ms debounce
        });

        // Hide list when clicking outside
        document.addEventListener('click', (e) => {
            if (e.target !== autocompleteInput && e.target !== autocompleteList) {
                autocompleteList.style.display = 'none';
            }
        });
    }

    // Restore active tab on load
    const activeTab = localStorage.getItem('quantum_active_tab') || 'screener';
    if (activeTab === 'watchlist') {
        navWatchlist.click();
    } else if (activeTab === 'dashboard') {
        navDashboard.click();
    } else {
        navScreener.click();
    }

    // Add Stock
    btnAddStock.addEventListener('click', async () => {
        const symbol = inputSymbol.value.trim().toUpperCase();
        const qty = parseFloat(inputQty.value);
        if (!symbol || isNaN(qty) || qty <= 0) return;

        btnAddStock.textContent = 'בודק...';
        btnAddStock.disabled = true;

        try {
            // Validate symbol by fetching price
            const res = await fetch('/api/portfolio_prices', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbols: [symbol] })
            });
            const prices = await res.json();
            
            if (!prices[symbol]) {
                showToast('מניה לא קיימת או שאין נתונים עבורה.', 'error');
                btnAddStock.textContent = 'הוסף';
                btnAddStock.disabled = false;
                return;
            }

            const buyPrice = prices[symbol].price || 0;
            const existing = portfolio.find(p => p.symbol === symbol);
            if (existing) {
                const oldTotal = existing.qty * (existing.avgPrice || buyPrice);
                const newTotal = qty * buyPrice;
                existing.qty += qty;
                existing.avgPrice = (oldTotal + newTotal) / existing.qty;
            } else {
                portfolio.push({ symbol, qty, avgPrice: buyPrice });
            }

            localStorage.setItem('quantum_portfolio', JSON.stringify(portfolio));
            inputSymbol.value = '';
            inputQty.value = '';
            showToast(`נוספה מניית ${symbol} לתיק בהצלחה!`, 'success');
            refreshDashboard();
        } catch (e) {
            showToast('שגיאה בחיבור לשרת.', 'error');
        } finally {
            btnAddStock.textContent = 'הוסף';
            btnAddStock.disabled = false;
        }
    });

    // Remove Stock
    window.removeStock = (symbol) => {
        portfolio = portfolio.filter(p => p.symbol !== symbol);
        localStorage.setItem('quantum_portfolio', JSON.stringify(portfolio));
        refreshDashboard();
    };

    const fetchPortfolioPrices = async () => {
        if (portfolio.length === 0) return;
        const symbols = portfolio.map(p => p.symbol);
        try {
            const res = await fetch('/api/portfolio_prices', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ symbols })
            });
            if (res.ok) {
                portfolioPrices = await res.json();
            }
        } catch (e) {
            console.error("Failed to fetch live prices", e);
        }
    };

    const updateChart = (labels, dataValues) => {
        const ctx = document.getElementById('portfolioChart').getContext('2d');
        if (portfolioChart) {
            portfolioChart.destroy();
        }
        
        if (labels.length === 0) {
            // Draw an empty grey chart if no valid values
            portfolioChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: ['אין נתונים'],
                    datasets: [{ data: [1], backgroundColor: ['#2A2F45'], borderWidth: 0 }]
                },
                options: { responsive: true, maintainAspectRatio: false, cutout: '70%', plugins: { legend: { display: false } } }
            });
            return;
        }

        portfolioChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: dataValues,
                    backgroundColor: [
                        '#00B8FF', '#00FF88', '#FF3366', '#FFD700', '#9D00FF',
                        '#FF8C00', '#00FFFF', '#FF1493', '#32CD32', '#8A2BE2'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: '#8F9BB3', font: { family: 'Heebo' } }
                    }
                }
            }
        });
    };

    window.updateStockQty = (symbol, newQty) => {
        const q = parseFloat(newQty);
        if (isNaN(q) || q <= 0) return;
        const item = portfolio.find(p => p.symbol === symbol);
        if (item) {
            item.qty = q;
            localStorage.setItem('quantum_portfolio', JSON.stringify(portfolio));
            refreshDashboard();
            showToast(`עודכנה כמות ${symbol} ל-${q} יחידות`, 'info');
        }
    };

    const refreshDashboard = async () => {
        portfolio = JSON.parse(localStorage.getItem('quantum_portfolio')) || [];
        if (portfolio.length === 0) {
            portfolioBody.innerHTML = '<tr><td colspan="8"><div class="empty-state"><div class="empty-state-icon">📂</div><p>התיק שלך ריק. הוסף מניות או ייבא מתוצאות הסורק!</p></div></td></tr>';
            document.getElementById('dash-total-value').textContent = '$0.00';
            if (portfolioChart) portfolioChart.destroy();
            return;
        }

        portfolioBody.innerHTML = '<tr><td colspan="8" style="text-align: center;">טוען מחירים חיים במקביל...</td></tr>';
        await fetchPortfolioPrices();

        let totalValue = 0;
        let labels = [];
        let values = [];
        
        // First pass: calculate total value
        portfolio.forEach(p => {
            const price = portfolioPrices[p.symbol] || 0;
            totalValue += price * p.qty;
        });

        portfolioBody.innerHTML = '';

        // Second pass: render rows with percentages and inline quantity editor
        let totalCost = 0;
        portfolio.forEach(p => {
            const price = portfolioPrices[p.symbol] || 0;
            const value = price * p.qty;
            const avgPrice = p.avgPrice || price; // Fallback to current if missing
            const cost = avgPrice * p.qty;
            totalCost += cost;
            
            if (value > 0) {
                labels.push(p.symbol);
                values.push(value);
            }

            const percentage = totalValue > 0 ? ((value / totalValue) * 100).toFixed(1) + '%' : '0%';
            
            const pnl = value - cost;
            const pnlPct = cost > 0 ? (pnl / cost) * 100 : 0;
            const pnlClass = pnl >= 0 ? 'text-good' : 'text-bad';
            const pnlSign = pnl >= 0 ? '+' : '';
            
            const pnlStr = `<span class="${pnlClass}">${pnlSign}$${Math.abs(pnl).toFixed(2)} (${pnlSign}${pnlPct.toFixed(1)}%)</span>`;

            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td style="font-weight: 600; color: #00B8FF;" dir="ltr">${p.symbol}</td>
                <td dir="ltr">
                    <input type="number" class="manual-input" style="width: 75px; text-align: center; padding: 4px 6px; font-weight: 700; background: rgba(0,0,0,0.3);" value="${p.qty}" min="1" step="1" onchange="updateStockQty('${p.symbol}', this.value)" title="שנה כמות מניות להקצאה מותאמת אישית">
                </td>
                <td dir="ltr">$${avgPrice.toFixed(2)}</td>
                <td dir="ltr">${price > 0 ? '$' + price.toFixed(2) : 'N/A'}</td>
                <td dir="ltr">${value > 0 ? '$' + value.toFixed(2) : 'N/A'}</td>
                <td dir="ltr" style="font-weight: bold;">${pnlStr}</td>
                <td dir="ltr" style="font-weight: bold; color: var(--accent-green);">${percentage}</td>
                <td><button onclick="removeStock('${p.symbol}')" style="background:none; border:none; color:#FF3366; cursor:pointer;" title="הסר מהתיק">❌</button></td>
            `;
            portfolioBody.appendChild(tr);
        });
        
        // Update top-level dashboard values
        const totalPnl = totalValue - totalCost;
        const totalPnlPct = totalCost > 0 ? (totalPnl / totalCost) * 100 : 0;
        const totalPnlClass = totalPnl >= 0 ? 'text-good' : 'text-bad';
        const totalPnlSign = totalPnl >= 0 ? '+' : '';
        
        dashTotalValue.innerHTML = `${formatMoney(totalValue)} <span class="${totalPnlClass}" style="font-size: 16px; margin-left: 12px; display: inline-block;">${totalPnlSign}${formatMoney(Math.abs(totalPnl))} (${totalPnlSign}${totalPnlPct.toFixed(2)}%)</span>`;
        
        updateChart(labels, values);
    };

    // ==========================================
    // BACKTESTING & QUANT LAB LOGIC
    // ==========================================
    const navBacktest = document.getElementById('nav-backtest');
    const viewBacktest = document.getElementById('view-backtest');
    const btnQuickBacktest = document.getElementById('btn-quick-backtest');
    const btnRunBacktest = document.getElementById('btn-run-backtest');
    const btnExportTearsheet = document.getElementById('btn-export-tearsheet');
    const btSymbolsInput = document.getElementById('bt-symbols-input');
    const btTimeframe = document.getElementById('bt-timeframe');
    const btCapital = document.getElementById('bt-capital');
    const btBenchmark = document.getElementById('bt-benchmark');
    const btChartContainer = document.getElementById('bt-equity-chart');

    let btChart = null;
    let btPortSeries = null;
    let btBenchSeries = null;
    let lastBacktestData = null;

    const switchView = (tabName) => {
        navScreener.classList.remove('active');
        navDashboard.classList.remove('active');
        navWatchlist.classList.remove('active');
        if (navBacktest) navBacktest.classList.remove('active');

        viewScreener.style.display = 'none';
        viewDashboard.style.display = 'none';
        viewWatchlist.style.display = 'none';
        if (viewBacktest) viewBacktest.style.display = 'none';

        if (tabName === 'dashboard') {
            navDashboard.classList.add('active');
            viewDashboard.style.display = 'block';
            refreshDashboard();
        } else if (tabName === 'watchlist') {
            navWatchlist.classList.add('active');
            viewWatchlist.style.display = 'block';
            refreshWatchlist();
        } else if (tabName === 'backtest') {
            if (navBacktest) navBacktest.classList.add('active');
            if (viewBacktest) viewBacktest.style.display = 'block';
            setTimeout(() => {
                if (btChart && btChartContainer) {
                    btChart.applyOptions({ width: btChartContainer.clientWidth });
                }
            }, 100);
            if (!lastBacktestData) runBacktest();
        } else {
            navScreener.classList.add('active');
            viewScreener.style.display = 'block';
        }
        localStorage.setItem('quantum_active_tab', tabName);
    };

    if (navBacktest) {
        navBacktest.addEventListener('click', (e) => {
            if (e) e.preventDefault();
            switchView('backtest');
            if (!lastBacktestData) runBacktest();
        });
    }

    // Quick backtest from screener results
    if (btnQuickBacktest) {
        btnQuickBacktest.addEventListener('click', () => {
            const currentList = currentResults.map(s => s.symbol);
            if (currentList.length === 0) {
                showToast('אנא הרץ סריקה תחילה כדי שיהיו מניות לבקטסטינג.', 'info');
                return;
            }
            if (btSymbolsInput) {
                btSymbolsInput.value = currentList.join(', ');
            }
            switchView('backtest');
            runBacktest();
        });
    }

    const initBtChart = () => {
        if (!btChartContainer) return;
        btChartContainer.innerHTML = '';

        btChart = LightweightCharts.createChart(btChartContainer, {
            width: btChartContainer.clientWidth,
            height: 380,
            layout: {
                background: { type: 'solid', color: 'transparent' },
                textColor: '#8B949E',
                fontFamily: 'Assistant, sans-serif'
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.05)' }
            },
            rightPriceScale: {
                borderColor: '#30363D',
                scaleMargins: { top: 0.1, bottom: 0.1 }
            },
            timeScale: {
                borderColor: '#30363D',
                timeVisible: true
            },
            crosshair: {
                vertLine: { color: 'rgba(255, 255, 255, 0.2)', width: 1 },
                horzLine: { color: 'rgba(255, 255, 255, 0.2)', width: 1 }
            }
        });

        // Portfolio Line (Neon Green)
        btPortSeries = btChart.addLineSeries({
            color: '#00E676',
            lineWidth: 3,
            title: 'תיק אלגו ($)',
            priceLineVisible: false
        });

        // Benchmark Line (Amber)
        btBenchSeries = btChart.addLineSeries({
            color: '#F59E0B',
            lineWidth: 2,
            lineStyle: LightweightCharts.LineStyle.Dotted,
            title: 'בנצ׳מרק ($)',
            priceLineVisible: false
        });

        window.addEventListener('resize', () => {
            if (btChart && btChartContainer) {
                btChart.applyOptions({ width: btChartContainer.clientWidth });
            }
        });
    };

    const runBacktest = async () => {
        if (!btSymbolsInput) return;
        const rawSymbols = btSymbolsInput.value
            .split(/[\s,]+/)
            .map(s => s.trim().toUpperCase())
            .filter(s => s.length > 0);

        if (rawSymbols.length === 0) {
            showToast('אנא הזן לפחות סימול מניה אחד לבדיקה.', 'error');
            return;
        }

        if (btnRunBacktest) {
            btnRunBacktest.textContent = '⏳ מריץ סימולציה...';
            btnRunBacktest.disabled = true;
        }

        try {
            const reqData = {
                symbols: rawSymbols,
                timeframe: btTimeframe ? btTimeframe.value : '1Y',
                initial_capital: btCapital ? parseFloat(btCapital.value) || 10000 : 10000,
                benchmark_symbol: btBenchmark ? btBenchmark.value : 'SPY'
            };

            const res = await fetch('/api/backtest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(reqData)
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || 'Failed to execute backtest');
            }

            const data = await res.json();
            lastBacktestData = data;
            const s = data.summary;

            // Update KPI Cards
            const setKpi = (id, text, isGood = true) => {
                const el = document.getElementById(id);
                if (!el) return;
                el.textContent = text;
            };

            const signTot = s.total_return_pct >= 0 ? '+' : '';
            const signCagr = s.cagr_pct >= 0 ? '+' : '';
            const signAlpha = s.alpha >= 0 ? '+' : '';

            setKpi('bt-total-return', `${signTot}${s.total_return_pct}%`);
            setKpi('bt-bench-total', `בנצ'מרק: ${s.benchmark_return_pct >= 0 ? '+' : ''}${s.benchmark_return_pct}%`);
            
            setKpi('bt-cagr', `${signCagr}${s.cagr_pct}%`);
            setKpi('bt-bench-cagr', `בנצ'מרק: ${s.benchmark_cagr_pct >= 0 ? '+' : ''}${s.benchmark_cagr_pct}%`);

            setKpi('bt-sharpe', s.sharpe_ratio.toFixed(2));
            setKpi('bt-sortino', `Sortino: ${s.sortino_ratio.toFixed(2)}`);

            setKpi('bt-max-dd', `${s.max_drawdown_pct}%`);
            setKpi('bt-bench-max-dd', `בנצ'מרק: ${s.benchmark_max_drawdown_pct}%`);

            setKpi('bt-win-rate', `${s.win_rate_pct}%`);
            setKpi('bt-alpha-beta', `α: ${signAlpha}${s.alpha}% | β: ${s.beta}`);

            // Draw Equity Chart
            if (!btChart) initBtChart();
            if (btPortSeries && btBenchSeries) {
                const portData = data.timeline.map(d => ({ time: d.time, value: d.portfolio }));
                const benchData = data.timeline.map(d => ({ time: d.time, value: d.benchmark }));
                
                // Sort ascending by time
                portData.sort((a, b) => a.time.localeCompare(b.time));
                benchData.sort((a, b) => a.time.localeCompare(b.time));

                btPortSeries.setData(portData);
                btBenchSeries.setData(benchData);
                btChart.timeScale().fitContent();
            }

            // Render Monthly Heatmap
            const mBody = document.getElementById('bt-monthly-body');
            if (mBody && data.monthly_summary) {
                mBody.innerHTML = '';
                data.monthly_summary.forEach(row => {
                    const tr = document.createElement('tr');
                    let cells = `<td style="font-weight: 700; color: var(--text-primary);">${row.year}</td>`;
                    
                    for (let m = 1; m <= 12; m++) {
                        const val = row.months[m];
                        if (val === null || val === undefined) {
                            cells += `<td style="color: var(--text-secondary);">-</td>`;
                        } else {
                            const isPos = val >= 0;
                            const bg = isPos ? 'rgba(0, 230, 118, 0.12)' : 'rgba(255, 61, 0, 0.12)';
                            const col = isPos ? '#00E676' : '#FF3D00';
                            const sign = val > 0 ? '+' : '';
                            cells += `<td dir="ltr" style="background:${bg}; color:${col}; font-weight:600;">${sign}${val}%</td>`;
                        }
                    }

                    const yVal = row.total_year;
                    const yPos = yVal >= 0;
                    const yCol = yPos ? '#00E676' : '#FF3D00';
                    cells += `<td dir="ltr" style="font-weight: 800; color:${yCol};">${yVal > 0 ? '+' : ''}${yVal}%</td>`;
                    tr.innerHTML = cells;
                    mBody.appendChild(tr);
                });
            }

        } catch (err) {
            console.error('Backtest error:', err);
            showToast(`שגיאה בהרצת הבקטסטינג: ${err.message}`, 'error');
        } finally {
            if (btnRunBacktest) {
                btnRunBacktest.textContent = '⚡ הרץ סימולציה';
                btnRunBacktest.disabled = false;
            }
        }
    };

    if (btnRunBacktest) {
        btnRunBacktest.addEventListener('click', runBacktest);
    }

    // Tear Sheet HTML Export
    if (btnExportTearsheet) {
        btnExportTearsheet.addEventListener('click', async () => {
            if (!btSymbolsInput) return;
            const rawSymbols = btSymbolsInput.value
                .split(/[\s,]+/)
                .map(s => s.trim().toUpperCase())
                .filter(s => s.length > 0);

            if (rawSymbols.length === 0) {
                showToast('אנא הזן מניות תחילה.', 'error');
                return;
            }

            btnExportTearsheet.textContent = '⏳ מפיק דוח...';
            btnExportTearsheet.disabled = true;

            try {
                const reqData = {
                    symbols: rawSymbols,
                    timeframe: btTimeframe ? btTimeframe.value : '1Y',
                    initial_capital: btCapital ? parseFloat(btCapital.value) || 10000 : 10000,
                    benchmark_symbol: btBenchmark ? btBenchmark.value : 'SPY'
                };

                const res = await fetch('/api/backtest/report', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(reqData)
                });

                if (!res.ok) throw new Error('Failed to generate report');
                const htmlText = await res.text();

                // Open tear sheet in a new tab
                const reportWindow = window.open('', '_blank');
                if (reportWindow) {
                    reportWindow.document.write(htmlText);
                    reportWindow.document.close();
                } else {
                    showToast('נא לאפשר פתיחת חלונות קופצים (Popups) כדי לצפות בדוח.', 'info');
                }
            } catch (err) {
                console.error('Tear sheet generation error:', err);
                showToast(`שגיאה בהפקת הדוח: ${err.message}`, 'error');
            } finally {
                btnExportTearsheet.textContent = '📄 הפק דוח ביצועים מלא (Tear Sheet)';
                btnExportTearsheet.disabled = false;
            }
        });
    }

    // Update existing navigation links to use switchView
    navDashboard.addEventListener('click', (e) => {
        if (e) e.preventDefault();
        switchView('dashboard');
    });

    navScreener.addEventListener('click', (e) => {
        if (e) e.preventDefault();
        switchView('screener');
    });

    navWatchlist.addEventListener('click', (e) => {
        if (e) e.preventDefault();
        switchView('watchlist');
    });

    // Check active tab on load
    const savedTab = localStorage.getItem('quantum_active_tab') || 'screener';
    if (savedTab === 'backtest' || savedTab === 'dashboard' || savedTab === 'watchlist') {
        switchView(savedTab);
    }

    // ==========================================
    // METHODOLOGY MODAL & ONBOARDING GUIDE
    // ==========================================
    const methodologyModal = document.getElementById('methodology-modal');
    const btnOpenMethodology = document.getElementById('btn-open-methodology');
    const btnSidebarMethodology = document.getElementById('btn-sidebar-methodology');
    const closeMethodology = document.getElementById('close-methodology');

    const openMethodology = () => {
        if (methodologyModal) methodologyModal.style.display = 'block';
    };

    if (btnOpenMethodology) btnOpenMethodology.addEventListener('click', openMethodology);
    if (btnSidebarMethodology) btnSidebarMethodology.addEventListener('click', (e) => {
        if (e) e.preventDefault();
        openMethodology();
    });
    if (closeMethodology) {
        closeMethodology.addEventListener('click', () => {
            if (methodologyModal) methodologyModal.style.display = 'none';
        });
    }

    window.addEventListener('click', (e) => {
        if (e.target === methodologyModal) {
            methodologyModal.style.display = 'none';
        }
    });

    // Dismissable Onboarding Banner
    const onboardingBanner = document.getElementById('onboarding-banner');
    const btnDismissBanner = document.getElementById('btn-dismiss-banner');
    if (localStorage.getItem('quantum_guide_dismissed') === 'true') {
        if (onboardingBanner) onboardingBanner.style.display = 'none';
    }
    if (btnDismissBanner && onboardingBanner) {
        btnDismissBanner.addEventListener('click', () => {
            onboardingBanner.style.display = 'none';
            localStorage.setItem('quantum_guide_dismissed', 'true');
        });
    }

    // Quick Search Input in Screener Table
    const tableSearch = document.getElementById('table-search');
    if (tableSearch) {
        tableSearch.addEventListener('input', (e) => {
            const query = e.target.value.trim().toLowerCase();
            const rows = resultsBody.querySelectorAll('tr');
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                if (text.includes(query)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }
});
