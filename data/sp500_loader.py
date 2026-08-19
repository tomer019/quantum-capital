"""
sp500_loader.py - Load the S&P 500 stock list
Uses multiple fallback methods to get the ticker list reliably.
"""
import pandas as pd
import requests
from pathlib import Path

CACHE_FILE = Path(__file__).parent / "cache" / "sp500_tickers.csv"


def get_sp500_tickers(use_cache: bool = True) -> list[str]:
    """
    Returns the current list of S&P 500 ticker symbols.
    Tries multiple sources with fallbacks.
    """
    if use_cache and CACHE_FILE.exists():
        print("[SP500] Loading ticker list from cache...")
        df = pd.read_csv(CACHE_FILE)
        return df["Symbol"].tolist()

    # Method 1: GitHub hosted CSV (very reliable)
    print("[SP500] Fetching S&P 500 ticker list...")
    try:
        url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        from io import StringIO
        df = pd.read_csv(StringIO(response.text))
        tickers = df["Symbol"].str.replace(".", "-", regex=False).tolist()
        print(f"[SP500] Fetched {len(tickers)} tickers from GitHub dataset.")

    except Exception as e:
        print(f"[SP500] GitHub source failed ({e}), using built-in list...")
        tickers = _get_fallback_tickers()

    CACHE_FILE.parent.mkdir(exist_ok=True)
    pd.DataFrame({"Symbol": tickers}).to_csv(CACHE_FILE, index=False)
    print(f"[SP500] Saved {len(tickers)} tickers to cache.")
    return tickers


def _get_fallback_tickers() -> list[str]:
    """A curated list of major S&P 500 stocks for when network fails."""
    return [
        # Technology
        "AAPL", "MSFT", "NVDA", "AVGO", "META", "GOOGL", "GOOG", "AMZN",
        "TSLA", "ORCL", "AMD", "QCOM", "TXN", "AMAT", "MU", "KLAC",
        "LRCX", "SNPS", "CDNS", "ADI", "MCHP", "NXPI", "ON", "STX",
        # Healthcare
        "LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "ABT", "DHR",
        "PFE", "AMGN", "MDT", "ELV", "CI", "HCA", "CVS", "ISRG",
        # Financials
        "BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS",
        "BLK", "SPGI", "CB", "MMC", "AXP", "USB", "PNC", "TFC",
        # Consumer
        "AMZN", "HD", "MCD", "NKE", "SBUX", "TGT", "LOW", "COST",
        "WMT", "PG", "KO", "PEP", "CL", "EL", "MDLZ", "GIS",
        # Energy
        "XOM", "CVX", "COP", "EOG", "SLB", "MPC", "PSX", "VLO",
        "OXY", "DVN", "HAL", "BKR", "FANG", "HES", "APA", "MRO",
        # Industrials
        "GE", "HON", "CAT", "DE", "RTX", "LMT", "BA", "NOC",
        "UPS", "FDX", "CSX", "NSC", "EMR", "ETN", "ITW", "PH",
        # Communication
        "META", "GOOGL", "NFLX", "DIS", "CMCSA", "T", "VZ", "TMUS",
        # Utilities & REITs
        "NEE", "DUK", "SO", "D", "AEP", "SRE", "EXC", "XEL",
        # Materials
        "LIN", "APD", "SHW", "FCX", "NEM", "DOW", "DD", "PPG",
    ]

def get_nasdaq100_tickers() -> list[str]:
    """Returns a curated list of Nasdaq 100 tickers."""
    return [
        "AAPL", "MSFT", "AMZN", "NVDA", "META", "AVGO", "GOOGL", "GOOG", "TSLA",
        "COST", "ADBE", "AMD", "PEP", "CSCO", "TMUS", "CMCSA", "INTC", "TXN",
        "QCOM", "AMGN", "INTU", "HON", "AMAT", "ISRG", "SBUX", "BKNG", "MDLZ",
        "GILD", "ADP", "LRCX", "VRTX", "ADI", "REGN", "MU", "PANW", "SNPS",
        "KLAC", "MELI", "CDNS", "PYPL", "CSX", "MAR", "ASML", "CTAS", "ORLY",
        "NXPI", "MNST", "WDAY", "FTNT", "KDP", "ABNB", "CHTR", "PCAR", "MCHP",
        "KHC", "AEP", "PAYX", "DXCM", "ROST", "LULU", "EXC", "BIIB", "AZN",
        "ODFL", "FAST", "XEL", "VRSK", "CPRT", "CTSH", "EA", "SIRI", "WBA"
    ]

def get_ta125_tickers() -> list[str]:
    """Returns a curated list of top TA-125 tickers (Tel Aviv) formatted for yfinance."""
    return [
        "LEUMI.TA", "POLI.TA", "NICE.TA", "TEVA.TA", "ICL.TA",
        "ELBIT.TA", "DISI.TA", "FIBI.TA", "MZT.TA", "ESLT.TA",
        "DANE.TA", "ENOG.TA", "AZRG.TA", "PHOE.TA", "BEZQ.TA",
        "OPK.TA", "TSEM.TA", "HREL.TA", "AMOT.TA", "ALHE.TA",
        "PTNR.TA", "CEL.TA", "ARPT.TA", "NVMI.TA", "SPEN.TA",
        "MVNE.TA", "MLSR.TA", "DIFI.TA", "HLAN.TA", "ONE.TA",
        "MTRX.TA", "ILCO.TA", "GMF.TA", "BLSR.TA", "SKBN.TA",
        "KMP.TA", "ALRA.TA", "FIBI.TA", "POLI.TA", "VTS.TA"
    ]

def get_dji30_tickers() -> list[str]:
    """Returns the 30 Dow Jones Industrial Average (DJIA) tickers."""
    return [
        "AAPL", "AMGN", "AXP", "BA", "CAT",
        "CRM", "CSCO", "CVX", "DIS", "DOW",
        "GS", "HD", "HON", "IBM", "INTC",
        "JNJ", "JPM", "KO", "MCD", "MMM",
        "MRK", "MSFT", "NKE", "PG", "TRV",
        "UNH", "V", "VZ", "WMT", "AMZN"
    ]

def get_eurostoxx50_tickers() -> list[str]:
    """Returns major Euro Stoxx 50 tickers formatted for yfinance."""
    return [
        # France
        "OR.PA", "MC.PA", "SAN.PA", "AIR.PA", "BNP.PA",
        "SU.PA", "DG.PA", "AI.PA", "RI.PA", "SGO.PA",
        # Germany
        "SAP.DE", "SIE.DE", "ALV.DE", "MBG.DE", "BMW.DE",
        "BAYN.DE", "DTE.DE", "MUV2.DE", "BAS.DE", "ADS.DE",
        # Netherlands
        "ASML.AS", "RDSA.AS", "ING.AS", "PHIA.AS", "UNA.AS",
        # Spain
        "ITX.MC", "SAN.MC", "BBVA.MC", "IBE.MC", "REP.MC",
        # Italy
        "ENI.MI", "ENEL.MI", "ISP.MI", "UCG.MI", "STLAM.MI",
        # Belgium / Finland / Others
        "INGA.AS", "NOKIA.HE", "ABI.BR", "KER.PA", "EL.PA",
        "CS.PA", "ORA.PA", "ENGI.PA", "VIV.PA", "SGO.PA",
        "TTE.PA", "AXA.PA", "EDF.PA", "SG.PA", "CAP.PA"
    ]

def get_russell2000_tickers() -> list[str]:
    """Returns a curated list of top Russell 2000 (Small/Mid Cap) tickers."""
    return [
        "SMCI", "CELH", "RXRX", "MSTR", "ELF", "SOFI", "PLTR", "IONQ", "LCID", 
        "RIVN", "UPST", "AFRM", "HOOD", "AI", "CVNA", "CHWY", "DKNG", "RBLX", 
        "PATH", "TOST", "COIN", "U", "SQSP", "DUOL", "MNDY", "GLBE", "FVRR", 
        "WIX", "PINS", "SNAP", "BYND", "PTON", "ZILL", "OPEN", "RDFN", "PACW", 
        "WAL", "ZION", "CMA", "KEY", "FHN", "EWBC", "WBS", "BOKF", "CFR",
        "CROX", "SKX", "YETI", "SHAK", "WING", "TXRH", "PLAY", "CAVA", "SG",
        "OSCR", "ALGN", "EXAS", "TDOC", "SDGR", "GH", "NTLA", "CRSP", "EDIT",
        "RUN", "FSLR", "ENPH", "SEDG", "PLUG", "BLDP", "FCEL", "SPWR", "NOVA",
        "MARA", "RIOT", "CLSK", "HUT", "BITF", "ARGO", "ANY", "MIGI", "WULF"
    ]
