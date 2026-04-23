import os
import io
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
from chatbot_engine import (
    get_chat_response,
    build_user_message,
    build_assistant_message,
    get_welcome_message,
)

# =============================================================================
# PAGE CONFIG
# initial_sidebar_state="expanded" is the Streamlit-level lock.
# The CSS below adds a browser-level lock on top of it for desktop.
# =============================================================================
st.set_page_config(
    page_title="AlgoMetrics - Indian Stock Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Defensive API Key Retrieval ---
api_key = None

# Check environment variables first (this avoids the Streamlit file-search crash)
api_key = os.environ.get("NVIDIA_API_KEY")

# Only if environment variable is missing, try st.secrets inside a protective try-block
if not api_key:
    try:
        api_key = st.secrets["NVIDIA_API_KEY"]
    except:
        api_key = None

# Final safety check
if not api_key:
    st.warning("⚠️ API Key not detected. Please configure NVIDIA_API_KEY in Render Environment Variables.")
# -----------------------------------

# Session state controls
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "ticker_input" not in st.session_state:
    st.session_state["ticker_input"] = ""
if "auto_fetch" not in st.session_state:
    st.session_state["auto_fetch"] = False

# =============================================================================
# CSS
# Changes from original:
#   1. Font: JetBrains Mono -> IBM Plex Sans throughout
#   2. Sidebar: desktop lock (transform:none + hide collapse button)
#   3. Mobile: restore sidebar toggle controls
#   4. Chatbot: chat message and container styles
#   5. Movers: gap class for card spacing
# =============================================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap');

/* ── Global typography ────────────────────────────────────────────────── */
html, body, [data-testid="stText"], .stMarkdown {
    font-family: 'IBM Plex Sans', sans-serif !important;
}
h1, h2, h3, h4, h5, h6, .section-title, [data-testid="stMetricLabel"], [data-testid="stMetricValue"] {
    font-family: 'IBM Plex Sans', sans-serif !important;
}

/* ── Sidebar ──────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: #0e1117;
    border-right: 1px solid #1f2937;
    min-width: 280px !important;
    max-width: 320px !important;
}
section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }

/* Desktop: lock sidebar open, hide the collapse arrow entirely */
@media (min-width: 769px) {
    section[data-testid="stSidebar"] { transform: none !important; }
    button[data-testid="baseButton-headerNoPadding"] { display: none !important; }
}

/* Mobile: restore all sidebar controls */
@media (max-width: 768px) {
    section[data-testid="stSidebar"] {
        min-width: 0 !important;
        max-width: 100vw !important;
    }
    .main .block-container {
        padding-top: 24px !important;
        padding-left: 16px !important;
        padding-right: 16px !important;
    }
    header[data-testid="stHeader"] { display: block !important; }
    [data-testid="stToolbar"] { display: block !important; }
    [data-testid="baseButton-headerNoPadding"],
    [data-testid="collapsedControl"] { display: inline-flex !important; }
}

/* ── Metrics ──────────────────────────────────────────────────────────── */
[data-testid="stMetric"] {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 6px;
    padding: 14px 18px;
}
[data-testid="stMetricLabel"] {
    font-size: 10px !important;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #6b7280 !important;
}
[data-testid="stMetricValue"] {
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 1.6rem !important;
    font-weight: 800 !important;
}

/* ── Main canvas ──────────────────────────────────────────────────────── */
.main .block-container {
    background: #0b0f1a;
    padding-top: 24px;
    padding-bottom: 24px !important;
    max-width: 1200px;
}
body { background-color: #0b0f1a; }

.section-title {
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 11px;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #4b5563;
    margin: 28px 0 10px;
    border-bottom: 1px solid #1f2937;
    padding-bottom: 6px;
}

/* ── Strip Streamlit chrome ───────────────────────────────────────────── */
footer                                 { display: none !important; }
#MainMenu                              { display: none !important; }
header[data-testid="stHeader"]         { display: none !important; }
[data-testid="stToolbar"]              { display: none !important; }
[data-testid="stDecoration"]           { display: none !important; }
[data-testid="stStatusWidget"]         { display: none !important; }
[data-testid="stBottom"]               { display: none !important; }
[data-testid="stBottomBlockContainer"] { display: none !important; }
.stDeployButton                        { display: none !important; }
.viewerBadge_container__r5tak         { display: none !important; }
.viewerBadge_link__qRIco              { display: none !important; }
#stDecoration                          { display: none !important; }

/* ── Buttons ──────────────────────────────────────────────────────────── */
.stDownloadButton button {
    background: #00e5a0 !important;
    color: #000 !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 1px !important;
    border: none !important;
    border-radius: 4px !important;
}
.stButton button {
    background: #1a5276 !important;
    color: #fff !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 12px !important;
    letter-spacing: 1px !important;
    border: 1px solid #2471a3 !important;
    border-radius: 4px !important;
    width: 100%;
    padding: 10px !important;
}
.stButton button:hover { background: #2471a3 !important; }

/* ── Market movers gap ────────────────────────────────────────────────── */
.movers-gap { gap: 28px !important; }
.mover-ticker-wrap [data-testid="stButton"] button {
    background: transparent !important;
    border: 1px solid #334155 !important;
    color: #e2e8f0 !important;
    font-size: 0.78rem !important;
    letter-spacing: 1px !important;
    text-transform: uppercase;
    border-radius: 20px !important;
    padding: 6px 12px !important;
    width: auto !important;
}
.mover-ticker-wrap [data-testid="stButton"] button:hover {
    border-color: #00e5a0 !important;
    color: #00e5a0 !important;
}

/* ── Chatbot container ────────────────────────────────────────────────── */
.chat-outer {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 10px;
    padding: 20px 20px 0 20px;
    margin-top: 8px;
}
[data-testid="stChatMessage"] { background: transparent !important; }
[data-testid="stChatMessageContent"] p {
    font-size: 0.88rem !important;
    line-height: 1.75 !important;
    color: #d1d5db !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
}
</style>
""", unsafe_allow_html=True)


# =============================================================================
# DATA FUNCTIONS — unchanged from original
# =============================================================================

@st.cache_data(show_spinner=False, ttl=86400)
def load_nse_stocks():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Referer": "https://www.nseindia.com/",
    }
    try:
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        resp = session.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        from io import StringIO
        df = pd.read_csv(StringIO(resp.text))
        df = df[["SYMBOL", "NAME OF COMPANY"]].dropna()
        df["TICKER"] = df["SYMBOL"].str.strip() + ".NS"
        df["LABEL"] = (
            df["NAME OF COMPANY"].str.strip()
            + " ("
            + df["SYMBOL"].str.strip()
            + " - NSE)"
        )
        return df[["TICKER", "LABEL"]].sort_values("LABEL").reset_index(drop=True)
    except Exception:
        return _nse_fallback()


def _nse_fallback():
    stocks = [
        ("RELIANCE.NS", "Reliance Industries (RELIANCE - NSE)"),
        ("TCS.NS", "Tata Consultancy Services (TCS - NSE)"),
        ("HDFCBANK.NS", "HDFC Bank (HDFCBANK - NSE)"),
        ("INFY.NS", "Infosys (INFY - NSE)"),
        ("ICICIBANK.NS", "ICICI Bank (ICICIBANK - NSE)"),
        ("HINDUNILVR.NS", "Hindustan Unilever (HINDUNILVR - NSE)"),
        ("SBIN.NS", "State Bank of India (SBIN - NSE)"),
        ("BHARTIARTL.NS", "Bharti Airtel (BHARTIARTL - NSE)"),
        ("KOTAKBANK.NS", "Kotak Mahindra Bank (KOTAKBANK - NSE)"),
        ("BAJFINANCE.NS", "Bajaj Finance (BAJFINANCE - NSE)"),
        ("WIPRO.NS", "Wipro (WIPRO - NSE)"),
        ("HCLTECH.NS", "HCL Technologies (HCLTECH - NSE)"),
        ("AXISBANK.NS", "Axis Bank (AXISBANK - NSE)"),
        ("ASIANPAINT.NS", "Asian Paints (ASIANPAINT - NSE)"),
        ("MARUTI.NS", "Maruti Suzuki (MARUTI - NSE)"),
        ("SUNPHARMA.NS", "Sun Pharmaceutical (SUNPHARMA - NSE)"),
        ("TITAN.NS", "Titan Company (TITAN - NSE)"),
        ("ULTRACEMCO.NS", "UltraTech Cement (ULTRACEMCO - NSE)"),
        ("NESTLEIND.NS", "Nestle India (NESTLEIND - NSE)"),
        ("POWERGRID.NS", "Power Grid Corporation (POWERGRID - NSE)"),
        ("NTPC.NS", "NTPC (NTPC - NSE)"),
        ("ONGC.NS", "Oil & Natural Gas Corp (ONGC - NSE)"),
        ("JSWSTEEL.NS", "JSW Steel (JSWSTEEL - NSE)"),
        ("TATAMOTORS.NS", "Tata Motors (TATAMOTORS - NSE)"),
        ("TATASTEEL.NS", "Tata Steel (TATASTEEL - NSE)"),
        ("ADANIENT.NS", "Adani Enterprises (ADANIENT - NSE)"),
        ("ADANIPORTS.NS", "Adani Ports (ADANIPORTS - NSE)"),
        ("ADANIGREEN.NS", "Adani Green Energy (ADANIGREEN - NSE)"),
        ("ADANIPOWER.NS", "Adani Power (ADANIPOWER - NSE)"),
        ("BAJAJFINSV.NS", "Bajaj Finserv (BAJAJFINSV - NSE)"),
        ("BAJAJ-AUTO.NS", "Bajaj Auto (BAJAJ-AUTO - NSE)"),
        ("HEROMOTOCO.NS", "Hero MotoCorp (HEROMOTOCO - NSE)"),
        ("EICHERMOT.NS", "Eicher Motors (EICHERMOT - NSE)"),
        ("CIPLA.NS", "Cipla (CIPLA - NSE)"),
        ("DRREDDY.NS", "Dr. Reddy's Laboratories (DRREDDY - NSE)"),
        ("DIVISLAB.NS", "Divi's Laboratories (DIVISLAB - NSE)"),
        ("APOLLOHOSP.NS", "Apollo Hospitals (APOLLOHOSP - NSE)"),
        ("MAXHEALTH.NS", "Max Healthcare (MAXHEALTH - NSE)"),
        ("TECHM.NS", "Tech Mahindra (TECHM - NSE)"),
        ("LTIM.NS", "LTIMindtree (LTIM - NSE)"),
        ("PERSISTENT.NS", "Persistent Systems (PERSISTENT - NSE)"),
        ("MPHASIS.NS", "Mphasis (MPHASIS - NSE)"),
        ("COFORGE.NS", "Coforge (COFORGE - NSE)"),
        ("LTTS.NS", "L&T Technology Services (LTTS - NSE)"),
        ("LT.NS", "Larsen & Toubro (LT - NSE)"),
        ("SIEMENS.NS", "Siemens India (SIEMENS - NSE)"),
        ("ABB.NS", "ABB India (ABB - NSE)"),
        ("HAVELLS.NS", "Havells India (HAVELLS - NSE)"),
        ("VOLTAS.NS", "Voltas (VOLTAS - NSE)"),
        ("GODREJCP.NS", "Godrej Consumer Products (GODREJCP - NSE)"),
        ("DABUR.NS", "Dabur India (DABUR - NSE)"),
        ("MARICO.NS", "Marico (MARICO - NSE)"),
        ("COLPAL.NS", "Colgate-Palmolive India (COLPAL - NSE)"),
        ("PIDILITIND.NS", "Pidilite Industries (PIDILITIND - NSE)"),
        ("BERGEPAINT.NS", "Berger Paints (BERGEPAINT - NSE)"),
        ("INDIGO.NS", "IndiGo / InterGlobe Aviation (INDIGO - NSE)"),
        ("IRCTC.NS", "IRCTC (IRCTC - NSE)"),
        ("IRFC.NS", "Indian Railway Finance Corp (IRFC - NSE)"),
        ("PFC.NS", "Power Finance Corporation (PFC - NSE)"),
        ("RECLTD.NS", "REC Limited (RECLTD - NSE)"),
        ("CANBK.NS", "Canara Bank (CANBK - NSE)"),
        ("BANKBARODA.NS", "Bank of Baroda (BANKBARODA - NSE)"),
        ("PNB.NS", "Punjab National Bank (PNB - NSE)"),
        ("UNIONBANK.NS", "Union Bank of India (UNIONBANK - NSE)"),
        ("INDUSINDBK.NS", "IndusInd Bank (INDUSINDBK - NSE)"),
        ("FEDERALBNK.NS", "Federal Bank (FEDERALBNK - NSE)"),
        ("IDFCFIRSTB.NS", "IDFC First Bank (IDFCFIRSTB - NSE)"),
        ("BANDHANBNK.NS", "Bandhan Bank (BANDHANBNK - NSE)"),
        ("MUTHOOTFIN.NS", "Muthoot Finance (MUTHOOTFIN - NSE)"),
        ("CHOLAFIN.NS", "Cholamandalam Investment (CHOLAFIN - NSE)"),
        ("SHRIRAMFIN.NS", "Shriram Finance (SHRIRAMFIN - NSE)"),
        ("M&M.NS", "Mahindra & Mahindra (M&M - NSE)"),
        ("TVSMOTOR.NS", "TVS Motor Company (TVSMOTOR - NSE)"),
        ("BOSCHLTD.NS", "Bosch India (BOSCHLTD - NSE)"),
        ("MOTHERSON.NS", "Samvardhana Motherson (MOTHERSON - NSE)"),
        ("BALKRISIND.NS", "Balkrishna Industries (BALKRISIND - NSE)"),
        ("MRF.NS", "MRF (MRF - NSE)"),
        ("APOLLOTYRE.NS", "Apollo Tyres (APOLLOTYRE - NSE)"),
        ("COALINDIA.NS", "Coal India (COALINDIA - NSE)"),
        ("VEDL.NS", "Vedanta (VEDL - NSE)"),
        ("HINDALCO.NS", "Hindalco Industries (HINDALCO - NSE)"),
        ("NATIONALUM.NS", "National Aluminium (NATIONALUM - NSE)"),
        ("SAIL.NS", "Steel Authority of India (SAIL - NSE)"),
        ("NMDC.NS", "NMDC (NMDC - NSE)"),
        ("GAIL.NS", "GAIL India (GAIL - NSE)"),
        ("BPCL.NS", "Bharat Petroleum (BPCL - NSE)"),
        ("IOC.NS", "Indian Oil Corporation (IOC - NSE)"),
        ("HPCL.NS", "Hindustan Petroleum (HPCL - NSE)"),
        ("ZOMATO.NS", "Zomato (ZOMATO - NSE)"),
        ("NYKAA.NS", "Nykaa / FSN E-Commerce (NYKAA - NSE)"),
        ("PAYTM.NS", "Paytm / One97 Communications (PAYTM - NSE)"),
        ("POLICYBZR.NS", "PB Fintech / PolicyBazaar (POLICYBZR - NSE)"),
        ("DELHIVERY.NS", "Delhivery (DELHIVERY - NSE)"),
        ("TATACOMM.NS", "Tata Communications (TATACOMM - NSE)"),
        ("IDEA.NS", "Vodafone Idea (IDEA - NSE)"),
        ("DIXON.NS", "Dixon Technologies (DIXON - NSE)"),
        ("AMBER.NS", "Amber Enterprises (AMBER - NSE)"),
        ("KALYANKJIL.NS", "Kalyan Jewellers (KALYANKJIL - NSE)"),
        ("SENCO.NS", "Senco Gold (SENCO - NSE)"),
        ("TRENT.NS", "Trent (TRENT - NSE)"),
        ("DMART.NS", "Avenue Supermarts / DMart (DMART - NSE)"),
        ("PAGEIND.NS", "Page Industries (PAGEIND - NSE)"),
        ("ABFRL.NS", "Aditya Birla Fashion (ABFRL - NSE)"),
        ("OBEROIRLTY.NS", "Oberoi Realty (OBEROIRLTY - NSE)"),
        ("DLF.NS", "DLF (DLF - NSE)"),
        ("GODREJPROP.NS", "Godrej Properties (GODREJPROP - NSE)"),
        ("PRESTIGE.NS", "Prestige Estates (PRESTIGE - NSE)"),
        ("BRIGADE.NS", "Brigade Enterprises (BRIGADE - NSE)"),
        ("^NSEI", "Nifty 50 Index (^NSEI)"),
        ("^BSESN", "BSE Sensex (^BSESN)"),
        ("^CNXIT", "Nifty IT Index (^CNXIT)"),
        ("^NSEBANK", "Nifty Bank Index (^NSEBANK)"),
    ]
    df = pd.DataFrame(stocks, columns=["TICKER", "LABEL"])
    return df.sort_values("LABEL").reset_index(drop=True)


@st.cache_data(show_spinner=False, ttl=86400)
def load_bse_stocks():
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        url = (
            "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w"
            "?Group=&Scripcode=&industry=&segment=Equity&status=Active"
        )
        resp = requests.get(url, headers=headers, timeout=15)
        rows = resp.json().get("Table", [])
        if not rows:
            return None
        df = pd.DataFrame(rows)[["SCRIP_CD", "Scrip_Name"]].dropna()
        df["TICKER"] = df["SCRIP_CD"].astype(str).str.strip() + ".BO"
        df["LABEL"] = (
            df["Scrip_Name"].str.strip()
            + " ("
            + df["SCRIP_CD"].astype(str).str.strip()
            + " - BSE)"
        )
        return df[["TICKER", "LABEL"]].sort_values("LABEL").reset_index(drop=True)
    except Exception:
        return None


@st.cache_data(show_spinner=False, ttl=300)
def get_data(ticker, start, end, ma_short, ma_long):
    df = yf.download(
        ticker, start=str(start), end=str(end),
        auto_adjust=True, progress=False, threads=True,
    )
    if df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.reset_index(inplace=True)
    df[f"MA_{ma_short}"] = df["Close"].rolling(ma_short).mean().round(2)
    df[f"MA_{ma_long}"] = df["Close"].rolling(ma_long).mean().round(2)
    df["Daily_Return_%"] = (df["Close"].pct_change() * 100).round(4)
    df["Volatility_20d"] = df["Daily_Return_%"].rolling(20).std().round(4)
    df["Cumulative_%"] = ((df["Close"] / df["Close"].iloc[0] - 1) * 100).round(2)
    df.dropna(subset=[f"MA_{ma_long}"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    if len(df) > 500:
        step = len(df) // 500
        df = df.iloc[::step].reset_index(drop=True)
    return df


NIFTY50 = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "HINDUNILVR.NS", "SBIN.NS", "BHARTIARTL.NS", "KOTAKBANK.NS", "BAJFINANCE.NS",
    "WIPRO.NS", "HCLTECH.NS", "AXISBANK.NS", "ASIANPAINT.NS", "MARUTI.NS",
    "SUNPHARMA.NS", "TITAN.NS", "ULTRACEMCO.NS", "NESTLEIND.NS", "POWERGRID.NS",
    "NTPC.NS", "ONGC.NS", "JSWSTEEL.NS", "TATAMOTORS.NS", "TATASTEEL.NS",
    "ADANIENT.NS", "ADANIPORTS.NS", "BAJAJFINSV.NS", "BAJAJ-AUTO.NS", "HEROMOTOCO.NS",
    "EICHERMOT.NS", "CIPLA.NS", "DRREDDY.NS", "DIVISLAB.NS", "APOLLOHOSP.NS",
    "TECHM.NS", "LT.NS", "COALINDIA.NS", "HINDALCO.NS", "GAIL.NS",
    "BPCL.NS", "IOC.NS", "INDUSINDBK.NS", "M&M.NS", "TVSMOTOR.NS",
    "TRENT.NS", "DMART.NS", "DLF.NS", "ZOMATO.NS", "IRCTC.NS",
]


@st.cache_data(show_spinner=False, ttl=900)
def get_movers():
    try:
        records = []
        raw = yf.download(
            NIFTY50, period="5d",
            auto_adjust=True, progress=False,
            threads=True, group_by="ticker",
        )
        for ticker in NIFTY50:
            try:
                closes = raw[ticker]["Close"].dropna()
                if len(closes) == 0:
                    continue
                elif len(closes) == 1:
                    curr_close = float(closes.iloc[-1])
                    pct = 0.0
                else:
                    prev_close = float(closes.iloc[-2])
                    curr_close = float(closes.iloc[-1])
                    pct = (curr_close - prev_close) / prev_close * 100
                records.append({
                    "ticker": ticker,
                    "name": ticker.replace(".NS", ""),
                    "close": curr_close,
                    "pct": pct,
                })
            except Exception:
                continue
        if not records:
            return None, None
        df = pd.DataFrame(records)
        gainer = df.loc[df["pct"].idxmax()].to_dict()
        loser = df.loc[df["pct"].idxmin()].to_dict()
        return gainer, loser
    except Exception:
        return None, None


@st.cache_data(show_spinner=False, ttl=3600)
def get_nim_context(ticker, pct, direction):
    """NIM call for market movers widget. Uses Render env var."""
    # Check environment variables first (this avoids the Streamlit file-search crash)
    nim_api_key = os.environ.get("NVIDIA_API_KEY")

    # Only if environment variable is missing, try st.secrets inside a protective try-block
    if not nim_api_key:
        try:
            nim_api_key = st.secrets["NVIDIA_API_KEY"]
        except:
            nim_api_key = None

    if not nim_api_key:
        return "NIM key not configured."
    prompt = (
        f"You are a concise Indian stock market analyst. "
        f"{ticker.replace('.NS', '')} stock moved {pct:+.2f}% today on the NSE. "
        f"In 2-3 sentences, give the most likely fundamental or market reason "
        f"for this {'gain' if direction == 'up' else 'decline'}. "
        f"Be specific to Indian markets. No disclaimers."
    )
    for attempt in range(3):
        try:
            resp = requests.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {nim_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "meta/llama-3.1-70b-instruct",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 120,
                    "temperature": 0.4,
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            if attempt == 2:
                return "AI analysis temporarily unavailable. Please try again shortly."
            continue


# =============================================================================
# PLOT LAYOUT — font updated to IBM Plex Sans
# =============================================================================
PLOT_LAYOUT = dict(
    paper_bgcolor="#0b0f1a",
    plot_bgcolor="#0b0f1a",
    font=dict(family="IBM Plex Sans, sans-serif", color="#9ca3af", size=11),
    xaxis=dict(gridcolor="#1f2937", showgrid=True, zeroline=False),
    yaxis=dict(gridcolor="#1f2937", showgrid=True, zeroline=False),
    margin=dict(l=12, r=12, t=40, b=12),
    legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", yanchor="bottom", y=1.02),
    hovermode="x unified",
    uirevision="constant",
)


# =============================================================================
# CHART FUNCTIONS — unchanged from original
# =============================================================================

def chart_candlestick(df, ma1, ma2, ticker):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df["Date"], open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"], name="OHLC",
        increasing=dict(line=dict(color="#00e5a0", width=1), fillcolor="rgba(0,229,160,0.75)"),
        decreasing=dict(line=dict(color="#f87171", width=1), fillcolor="rgba(248,113,113,0.75)"),
    ))
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df[f"MA_{ma1}"],
        name=f"MA {ma1}d", line=dict(color="#00e5a0", width=1.5, dash="dot"),
    ))
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df[f"MA_{ma2}"],
        name=f"MA {ma2}d", line=dict(color="#3b82f6", width=1.5, dash="dot"),
    ))
    layout = {k: v for k, v in PLOT_LAYOUT.items() if k != "xaxis"}
    layout["title"] = dict(
        text=f"Candlestick & Moving Averages - {ticker}",
        font=dict(size=13, color="#e2e8f0"),
    )
    layout["xaxis"] = dict(
        gridcolor="#1f2937", showgrid=True, zeroline=False,
        rangeslider=dict(
            visible=True, thickness=0.06,
            bgcolor="#111827", bordercolor="#1f2937", borderwidth=1,
        ),
        rangeselector=dict(
            buttons=[
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=3, label="3M", step="month", stepmode="backward"),
                dict(count=6, label="6M", step="month", stepmode="backward"),
                dict(count=1, label="1Y", step="year", stepmode="backward"),
                dict(step="all", label="All"),
            ],
            bgcolor="#111827", activecolor="#00e5a0",
            bordercolor="#1f2937", borderwidth=1,
            font=dict(color="#9ca3af", size=11), x=0, y=1.02,
        ),
    )
    fig.update_layout(**layout)
    return fig


def chart_volatility(df, ticker):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Volatility_20d"], name="20d Volatility",
        fill="tozeroy", line=dict(color="#f59e0b", width=1.5),
        fillcolor="rgba(245,158,11,0.1)",
    ))
    fig.update_layout(
        **PLOT_LAYOUT,
        title=dict(text=f"20-Day Rolling Volatility - {ticker}", font=dict(size=13, color="#e2e8f0")),
    )
    return fig


def chart_returns(df, ticker):
    colors = ["#00e5a0" if v >= 0 else "#f87171" for v in df["Daily_Return_%"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["Date"], y=df["Daily_Return_%"],
        name="Daily Return %", marker_color=colors,
    ))
    fig.add_hline(y=0, line_color="#4b5563", line_width=1)
    fig.update_layout(
        **PLOT_LAYOUT,
        title=dict(text=f"Daily Returns (%) - {ticker}", font=dict(size=13, color="#e2e8f0")),
    )
    return fig


def chart_cumulative(df, ticker):
    final_val = float(df["Cumulative_%"].iloc[-1])
    color = "#00e5a0" if final_val >= 0 else "#f87171"
    fill_rgb = "0,229,160" if final_val >= 0 else "248,113,113"
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Cumulative_%"], name="Cumulative Return",
        fill="tozeroy", line=dict(color=color, width=2),
        fillcolor=f"rgba({fill_rgb},0.08)",
    ))
    fig.add_hline(y=0, line_color="#4b5563", line_width=1)
    fig.update_layout(
        **PLOT_LAYOUT,
        title=dict(text=f"Cumulative Return (%) - {ticker}", font=dict(size=13, color="#e2e8f0")),
    )
    return fig


# =============================================================================
# ANALYST INSIGHT — unchanged from original
# =============================================================================

def render_insight(df, chart_type, ma1, ma2, ticker):
    latest = df.iloc[-1]
    prev = df.iloc[-2]
    close = float(latest["Close"])
    ma_short = float(latest[f"MA_{ma1}"])
    ma_long = float(latest[f"MA_{ma2}"])
    vol = float(latest["Volatility_20d"])
    avg_vol = float(df["Volatility_20d"].mean())
    cum = float(latest["Cumulative_%"])
    ret = float(latest["Daily_Return_%"])
    prev_ma_s = float(prev[f"MA_{ma1}"])
    prev_ma_l = float(prev[f"MA_{ma2}"])
    price_above_short = close > ma_short
    price_above_long = close > ma_long
    golden_cross = (ma_short > ma_long) and (prev_ma_s <= prev_ma_l)
    death_cross = (ma_short < ma_long) and (prev_ma_s >= prev_ma_l)
    high_vol = vol > avg_vol * 1.5
    low_vol = vol < avg_vol * 0.5

    if chart_type == "ma":
        title = "Reading the Moving Average Chart"
        what = (
            f"This chart overlays the raw closing price of <strong>{ticker}</strong> with its "
            f"{ma1}-day and {ma2}-day Simple Moving Averages (SMA). A moving average smooths out "
            f"daily noise by averaging the price over a rolling window - the longer the window, "
            f"the smoother and slower the line."
        )
        if price_above_short and price_above_long:
            signal = (
                f"Bullish signal: The price (Rs.{close:.2f}) is <strong>above</strong> both the "
                f"{ma1}d (Rs.{ma_short:.2f}) and {ma2}d (Rs.{ma_long:.2f}) moving averages - "
                f"the stock is in an uptrend and buyers are in control."
            )
        elif not price_above_short and not price_above_long:
            signal = (
                f"Bearish signal: The price (Rs.{close:.2f}) is <strong>below</strong> both the "
                f"{ma1}d (Rs.{ma_short:.2f}) and {ma2}d (Rs.{ma_long:.2f}) moving averages - "
                f"selling pressure or a downtrend may be forming."
            )
        else:
            signal = (
                f"Mixed signal: The price (Rs.{close:.2f}) sits between the "
                f"{ma1}d (Rs.{ma_short:.2f}) and {ma2}d (Rs.{ma_long:.2f}) moving averages - "
                f"the market is in a transitional phase. Watch for a decisive break in either direction."
            )
        if golden_cross:
            extra = (
                f"Golden Cross detected: The {ma1}d MA just crossed <em>above</em> the {ma2}d MA - "
                f"historically one of the strongest bullish signals in technical analysis."
            )
        elif death_cross:
            extra = (
                f"Death Cross detected: The {ma1}d MA just crossed <em>below</em> the {ma2}d MA - "
                f"historically a bearish signal that can indicate the start of a sustained downtrend."
            )
        else:
            direction = "above" if ma_short > ma_long else "below"
            bias = "short-term bullish" if ma_short > ma_long else "short-term bearish"
            extra = (
                f"The {ma1}d MA is currently <strong>{direction}</strong> the {ma2}d MA - "
                f"indicating a {bias} bias relative to the longer-term average."
            )

    elif chart_type == "volatility":
        title = "Reading the Volatility Chart"
        what = (
            f"This chart shows the <strong>20-day rolling volatility</strong> of {ticker} - "
            f"calculated as the standard deviation of daily returns over the past 20 trading days. "
            f"Think of it as a fear gauge: high peaks mean uncertainty or reaction to major news; "
            f"flat low periods mean calm, steady price action."
        )
        if high_vol:
            signal = (
                f"Elevated volatility: Current volatility ({vol:.2f}%) is significantly above "
                f"the average ({avg_vol:.2f}%) - the stock is experiencing unusually large price "
                f"swings. Higher risk, potentially higher reward. Exercise caution with sizing."
            )
        elif low_vol:
            signal = (
                f"Calm market: At {vol:.2f}% versus an average of {avg_vol:.2f}%, the stock is "
                f"in a low-turbulence phase. Low volatility periods often precede breakouts."
            )
        else:
            signal = (
                f"Normal volatility: At {vol:.2f}% versus an average of {avg_vol:.2f}%, this stock "
                f"is behaving within its typical range - no unusual fear or euphoria right now."
            )
        extra = (
            "Volatility is not the same as direction - a highly volatile stock can move sharply "
            "up <em>or</em> down. Always pair this with the price trend in the MA chart above."
        )

    elif chart_type == "cumulative":
        title = "Reading the Cumulative Return Chart"
        what = (
            f"This chart answers a powerful question: <em>if you had invested on the first day "
            f"of the selected period, what would your total return be today?</em> It compounds "
            f"all daily gains and losses into a single running total, removing the noise of individual days."
        )
        if cum >= 0:
            signal = (
                f"Positive journey: {ticker} has returned <strong>+{cum:.2f}%</strong> over the "
                f"selected period. A steep upward angle means rapid growth; a gradual climb means "
                f"slow and steady compounding."
            )
        else:
            signal = (
                f"Negative journey: {ticker} has returned <strong>{cum:.2f}%</strong> - the stock "
                f"is worth less today than at the start of this window. Check the MA chart to "
                f"determine whether this is a long-term trend or a recent dip."
            )
        extra = (
            "Use this chart to <strong>compare stocks</strong> - fetching two different tickers "
            "with the same date range and comparing their cumulative curves gives an instant, "
            "apples-to-apples performance comparison."
        )

    else:
        title = "Reading the Daily Returns Chart"
        what = (
            f"Each bar represents the percentage change in {ticker}'s closing price from the "
            f"previous trading day. <strong>Green bars</strong> are up days; <strong>red bars</strong> "
            f"are down days. The height of the bar reflects the magnitude of the move."
        )
        move = "gained" if ret >= 0 else "lost"
        context = (
            "A move of this magnitude typically corresponds to a major event - earnings, RBI policy, "
            "or global news. Check the news on this date for context."
            if abs(ret) > 2
            else "Normal day-to-day fluctuation - no extreme move in the latest session."
        )
        signal = (
            f"Latest session: {ticker} {move} <strong>{ret:+.3f}%</strong> in the most recent "
            f"trading day. {context}"
        )
        extra = (
            "Look for <strong>outlier bars</strong> - unusually tall spikes almost always correspond "
            "to earnings announcements, RBI decisions, or major global events. Cross-referencing "
            "these dates with news adds real analytical depth."
        )

    st.markdown(f"""
    <div style="background:#111827;border:1px solid #1f2937;border-radius:8px;
    padding:22px 26px;margin-top:-8px;margin-bottom:28px">
        <div style="font-family:'IBM Plex Sans',sans-serif;font-size:11px;letter-spacing:2.5px;
        text-transform:uppercase;color:#4b5563;margin-bottom:10px">analyst note</div>
        <div style="font-family:'IBM Plex Sans',sans-serif;font-size:1rem;font-weight:700;
        color:#e2e8f0;margin-bottom:12px">{title}</div>
        <div style="font-size:0.87rem;color:#6b7280;line-height:1.9;
        margin-bottom:12px">{what}</div>
        <div style="background:#0b0f1a;border-radius:6px;padding:14px 18px;
        margin-bottom:10px;font-size:0.87rem;color:#9ca3af;line-height:1.8">{signal}</div>
        <div style="font-size:0.83rem;color:#4b5563;line-height:1.8;
        border-top:1px solid #1f2937;padding-top:10px">Tip: {extra}</div>
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# CHATBOT — moved from sidebar to main page
# Key changes:
#   - No longer inside st.sidebar or st.expander
#   - Uses st.secrets["NVIDIA_API_KEY"] as requested
#   - Only activates after fetch_btn (df is passed in, not None)
#   - Full-width st.container with fixed height scroll area
#   - chatbot_engine.py handles all AI logic
# =============================================================================

def render_chatbot_main(df, ticker_input):
    """
    Renders ArthBot on the main page below the analysis charts.

    Flow control:
        df=None  -> welcome state, no API calls made
        df!=None -> full chat with silent stock context injected on first message

    Separation of Concerns:
        This function: Streamlit UI, session_state, layout
        chatbot_engine.py: system prompt, API call, error handling
    """

    st.markdown("---")
    st.markdown(
        '<p class="section-title">ArthBot - AI Markets Analyst</p>',
        unsafe_allow_html=True,
    )

    # Session state init
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "arth_stock_ctx" not in st.session_state:
        st.session_state.arth_stock_ctx = None

    # Reset history when user switches to a new stock
    if df is not None and st.session_state.arth_stock_ctx != ticker_input:
        st.session_state.arth_stock_ctx = ticker_input
        st.session_state.messages = []

    # Header row with clear button
    h_col, btn_col = st.columns([6, 1])
    with h_col:
        if df is not None:
            st.markdown(
                f"<span style='font-size:0.85rem;color:#6b7280;'>"
                f"Discussing <strong style='color:#e2e8f0'>{ticker_input}</strong> "
                f"- ask about technicals, fundamentals, sector outlook, or any Indian markets topic."
                f"</span>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                "<span style='font-size:0.85rem;color:#4b5563;'>"
                "Fetch a stock above to start a context-aware analysis, or ask any general markets question."
                "</span>",
                unsafe_allow_html=True,
            )
    with btn_col:
        if st.session_state.messages:
            if st.button("Clear", key="arth_clear", use_container_width=True):
                st.session_state.messages = []
                st.session_state.arth_stock_ctx = None
                st.rerun()

    # Scrollable chat area
    chat_area = st.container(height=420)

    with chat_area:
        # Welcome message when history is empty
        if not st.session_state.messages:
            with st.chat_message("assistant", avatar="🤖"):
                if df is not None:
                    close_price = float(df.iloc[-1]["Close"])
                    cum = float(df.iloc[-1]["Cumulative_%"])
                    st.markdown(
                        f"Namaste! I can see you are analysing **{ticker_input}** "
                        f"(last close: Rs.{close_price:.2f}, cumulative return: {cum:+.2f}%). "
                        f"Ask me anything about this stock, its sector, F&O outlook, or the broader market."
                    )
                else:
                    st.markdown(get_welcome_message())

        # Replay history
        for msg in st.session_state.messages:
            avatar = "👤" if msg["role"] == "user" else "🤖"
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])

    # Chat input - placeholder changes based on context
    placeholder = (
        f"Ask about {ticker_input}, its sector, technicals, F&O..."
        if df is not None
        else "Ask any Indian markets question..."
    )
    user_input = st.chat_input(placeholder, key="arth_main_input")

    if user_input:
        if not api_key:
            st.session_state.messages.append(build_user_message(user_input))
            st.session_state.messages.append(build_assistant_message(
                "NVIDIA API key is missing. Please configure NVIDIA_API_KEY in Render secrets or environment variables to enable ArthBot."
            ))
            st.rerun()
        user_msg = build_user_message(user_input)
        st.session_state.messages.append(user_msg)

        # Build API history - silently inject stock context on first message
        api_history = st.session_state.messages.copy()
        if df is not None and len(st.session_state.messages) == 1:
            close_price = float(df.iloc[-1]["Close"])
            cum = float(df.iloc[-1]["Cumulative_%"])
            vol = float(df.iloc[-1]["Volatility_20d"])
            ctx = (
                f"[Dashboard context - do not repeat unless asked: "
                f"User is viewing {ticker_input}. "
                f"Last close Rs.{close_price:.2f}, "
                f"cumulative return {cum:+.2f}%, "
                f"20-day volatility {vol:.2f}%.]"
            )
            api_history = [build_user_message(ctx)] + api_history

        with chat_area:
            with st.chat_message("user", avatar="👤"):
                st.markdown(user_input)

        with chat_area:
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Analysing..."):
                    # chatbot_engine reads NVIDIA_API_KEY from os.environ (Render)
                    reply = get_chat_response(api_history)
                st.markdown(reply)

        st.session_state.messages.append(build_assistant_message(reply))


# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown("## Indian Stock Dashboard")
    st.markdown("---")
    nse_stocks = load_nse_stocks()
    bse_stocks = load_bse_stocks()
    _parts = [s for s in [nse_stocks, bse_stocks] if s is not None]
    all_stocks = (
        pd.concat(_parts, ignore_index=True)
        .sort_values("LABEL")
        .reset_index(drop=True)
        if _parts else None
    )

    if all_stocks is not None:
        st.markdown('<p class="section-title">Search NSE &amp; BSE</p>', unsafe_allow_html=True)
        labels = ["-- Type or select a company --"] + all_stocks["LABEL"].tolist()
        selected = st.selectbox("Stock", labels, label_visibility="collapsed")
        auto_ticker = (
            all_stocks.loc[all_stocks["LABEL"] == selected, "TICKER"].values[0]
            if selected != "-- Type or select a company --"
            else ""
        )
    else:
        auto_ticker = ""

    recommended_ticker = ""
    with st.expander("Custom ticker or company name", expanded=(auto_ticker == "")):
        st.markdown(
            '<p class="section-title" style="margin-top:4px">Type a name or ticker</p>',
            unsafe_allow_html=True,
        )
        manual = st.text_input(
            "Search",
            value="",
            placeholder="e.g. Infosys / 500325.BO / ^NSEI",
            label_visibility="collapsed",
        )
        manual_clean = manual.strip()
        if manual_clean:
            looks_like_ticker = "." in manual_clean or manual_clean.startswith("^")
            if not looks_like_ticker and all_stocks is not None:
                query = manual_clean.lower()
                mask = all_stocks["LABEL"].str.lower().str.contains(query, regex=False)
                matches = all_stocks[mask].head(8)
                if not matches.empty:
                    st.markdown(
                        '<p class="section-title" style="margin-top:10px">Recommendations</p>',
                        unsafe_allow_html=True,
                    )
                    rec_options = ["-- Select a match --"] + matches["LABEL"].tolist()
                    rec_choice = st.selectbox("Matches", rec_options, label_visibility="collapsed")
                    if rec_choice != "-- Select a match --":
                        recommended_ticker = all_stocks.loc[
                            all_stocks["LABEL"] == rec_choice, "TICKER"
                        ].values[0]
                else:
                    st.caption("No companies matched - try a direct ticker like INFY.NS or 500325.BO")

    manual_upper = manual.strip().upper()
    looks_like_ticker = "." in manual_upper or manual_upper.startswith("^")
    sidebar_ticker_input = (
        manual_upper if looks_like_ticker
        else (recommended_ticker if recommended_ticker else auto_ticker)
    )
    if sidebar_ticker_input and not st.session_state.get("auto_fetch", False):
        st.session_state["ticker_input"] = sidebar_ticker_input

    st.markdown('<p class="section-title">Date Range</p>', unsafe_allow_html=True)
    range_opt = st.radio(
        "Range", ["1 Year", "2 Years", "5 Years", "Custom"],
        label_visibility="collapsed",
    )
    today = datetime.today()
    if range_opt == "1 Year":
        start_default = today - timedelta(days=365)
    elif range_opt == "2 Years":
        start_default = today - timedelta(days=730)
    elif range_opt == "5 Years":
        start_default = today - timedelta(days=1825)
    else:
        start_default = today - timedelta(days=365)

    if range_opt == "Custom":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("From", value=start_default)
        with col2:
            end_date = st.date_input("To", value=today)
    else:
        start_date = start_default.date()
        end_date = today.date()

    st.markdown('<p class="section-title">Moving Averages</p>', unsafe_allow_html=True)
    ma1 = st.slider("Short MA (days)", 5, 50, 20)
    ma2 = st.slider("Long MA (days)", 20, 200, 50)
    fetch_btn = st.button("Fetch & Analyse")


# =============================================================================
# HEADER
# =============================================================================
st.markdown("""
<div style="margin-bottom:8px">
  <span style="font-family:'IBM Plex Sans',sans-serif;font-size:2rem;font-weight:800;
  color:#e2e8f0;letter-spacing:-1px;">
    Stock Market <span style="color:#00e5a0;">Analyser</span>
  </span><br>
  <span style="font-size:11px;color:#4b5563;letter-spacing:2px;text-transform:uppercase;">
    NSE - BSE - Real-time via Yahoo Finance
  </span>
</div>
""", unsafe_allow_html=True)
st.markdown("---")

# =============================================================================
# MARKET MOVERS
# Gap between cards increased via column gap CSS + spacer column
# =============================================================================
st.markdown(
    "<p class=\"section-title\">Today's Market Movers - Nifty 50</p>",
    unsafe_allow_html=True,
)

with st.spinner("Scanning Nifty 50 for latest movers..."):
    gainer, loser = get_movers()

if gainer and loser:
    mg, ml = st.columns(2, gap="large")

    with mg:
        nim_up = get_nim_context(gainer["ticker"], gainer["pct"], "up")
        st.markdown(f"""
        <div style="background:#0d1f12;border:1px solid #1a3a20;border-left:4px solid #00e5a0;
        border-radius:10px;padding:24px 26px;">
            <div style="font-family:'IBM Plex Sans',sans-serif;font-size:10px;letter-spacing:2px;
            text-transform:uppercase;color:#4b5563;margin-bottom:10px">Top Gainer</div>
            <div style="font-family:'IBM Plex Sans',sans-serif;font-size:1.5rem;font-weight:800;
            color:#00e5a0;line-height:1;margin-bottom:6px">{gainer['name']}</div>
            <div style="font-size:1.1rem;font-weight:600;color:#e2e8f0;margin-bottom:16px">
                Rs.{gainer['close']:.2f}
                <span style="color:#00e5a0;font-size:0.95rem;margin-left:8px">{gainer['pct']:+.2f}%</span>
            </div>
            <div style="margin-bottom:12px"></div>
            <div style="border-top:1px solid #1a3a20;padding-top:14px;
            font-size:0.83rem;color:#6b7280;line-height:1.75;">
                <span style="font-family:'IBM Plex Sans',sans-serif;font-size:9px;letter-spacing:1.5px;
                text-transform:uppercase;color:#4b5563;display:block;margin-bottom:6px;">
                NIM Analysis</span>
                {nim_up}
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<div class="mover-ticker-wrap">', unsafe_allow_html=True)
        if st.button(gainer["ticker"], key="mover_gainer_btn"):
            st.session_state["ticker_input"] = gainer["ticker"]
            st.session_state["auto_fetch"] = True
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with ml:
        nim_dn = get_nim_context(loser["ticker"], loser["pct"], "down")
        st.markdown(f"""
        <div style="background:#1f0d0d;border:1px solid #3a1a1a;border-left:4px solid #f87171;
        border-radius:10px;padding:24px 26px;">
            <div style="font-family:'IBM Plex Sans',sans-serif;font-size:10px;letter-spacing:2px;
            text-transform:uppercase;color:#4b5563;margin-bottom:10px">Top Loser</div>
            <div style="font-family:'IBM Plex Sans',sans-serif;font-size:1.5rem;font-weight:800;
            color:#f87171;line-height:1;margin-bottom:6px">{loser['name']}</div>
            <div style="font-size:1.1rem;font-weight:600;color:#e2e8f0;margin-bottom:16px">
                Rs.{loser['close']:.2f}
                <span style="color:#f87171;font-size:0.95rem;margin-left:8px">{loser['pct']:+.2f}%</span>
            </div>
            <div style="margin-bottom:12px"></div>
            <div style="border-top:1px solid #3a1a1a;padding-top:14px;
            font-size:0.83rem;color:#6b7280;line-height:1.75;">
                <span style="font-family:'IBM Plex Sans',sans-serif;font-size:9px;letter-spacing:1.5px;
                text-transform:uppercase;color:#4b5563;display:block;margin-bottom:6px;">
                NIM Analysis</span>
                {nim_dn}
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('<div class="mover-ticker-wrap">', unsafe_allow_html=True)
        if st.button(loser["ticker"], key="mover_loser_btn"):
            st.session_state["ticker_input"] = loser["ticker"]
            st.session_state["auto_fetch"] = True
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
else:
    st.caption("Could not load mover data. Please refresh the page.")

st.markdown("---")

df = None
ticker_input = st.session_state.get("ticker_input", "")
analysis_ready = (fetch_btn or st.session_state.get("auto_fetch", False)) and bool(ticker_input)

if analysis_ready:
    # =============================================================================
    # DATA FETCH
    # =============================================================================
    with st.spinner(f"Fetching {ticker_input} from Yahoo Finance..."):
        df = get_data(ticker_input, start_date, end_date, ma1, ma2)
    st.session_state["auto_fetch"] = False

if analysis_ready and (df is None or df.empty):
    st.markdown(f"""
    <div style="background:#111827;border:1px solid #1f2937;border-left:3px solid #f59e0b;
    border-radius:6px;padding:24px 28px;margin-top:20px">
        <div style="font-family:'IBM Plex Sans',sans-serif;font-weight:700;font-size:1.1rem;
        color:#e2e8f0;margin-bottom:8px">We could not find data for
        <span style="color:#f59e0b">{ticker_input}</span></div>
        <div style="font-size:0.88rem;color:#6b7280;line-height:1.8">
            This could be due to an incorrect ticker symbol or a temporary issue
            with the data source.<br><br>
            <span style="color:#9ca3af">Things to check:</span><br>
            &nbsp;&nbsp;- NSE stocks:
            <code style="background:#1a2236;padding:1px 6px;border-radius:3px;
            color:#00e5a0">RELIANCE.NS</code><br>
            &nbsp;&nbsp;- BSE stocks:
            <code style="background:#1a2236;padding:1px 6px;border-radius:3px;
            color:#00e5a0">RELIANCE.BO</code><br>
            &nbsp;&nbsp;- Indices:
            <code style="background:#1a2236;padding:1px 6px;border-radius:3px;
            color:#00e5a0">^NSEI</code>
        </div>
    </div>
    """, unsafe_allow_html=True)
elif analysis_ready:
    # =============================================================================
    # METRICS
    # =============================================================================
    latest = df.iloc[-1]
    first = df.iloc[0]
    total_ret = float((latest["Close"] - first["Close"]) / first["Close"] * 100)
    avg_vol = float(df["Volatility_20d"].mean())

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Latest Close", f"Rs.{float(latest['Close']):.2f}")
    c2.metric("Total Return", f"{total_ret:+.2f}%", delta=f"{total_ret:+.2f}%")
    c3.metric(f"MA {ma1}d", f"Rs.{float(latest[f'MA_{ma1}']):.2f}")
    c4.metric(f"MA {ma2}d", f"Rs.{float(latest[f'MA_{ma2}']):.2f}")
    c5.metric("Avg Volatility", f"{avg_vol:.2f}%")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    _price_now = float(latest["Close"])
    _price_delta = float(latest["Daily_Return_%"])
    _week52_high = float(df["High"].iloc[-min(252, len(df)):].max())
    _avg_volume = float(df["Volume"].mean())

    st.markdown('<p class="section-title">Market Snapshot</p>', unsafe_allow_html=True)
    _m1, _m2, _m3 = st.columns(3)
    _m1.metric(
        "Current Price",
        f"Rs.{_price_now:.2f}",
        delta=f"{_price_delta:+.2f}% today",
        delta_color="normal",
    )
    _m2.metric("52-Week High", f"Rs.{_week52_high:.2f}")
    _m3.metric("Avg Daily Volume", f"{_avg_volume:,.0f}")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # =============================================================================
    # CHARTS + INSIGHTS
    # =============================================================================
    st.plotly_chart(chart_candlestick(df, ma1, ma2, ticker_input), use_container_width=True)
    render_insight(df, "ma", ma1, ma2, ticker_input)

    col_l, col_r = st.columns(2)
    with col_l:
        st.plotly_chart(chart_volatility(df, ticker_input), use_container_width=True)
        render_insight(df, "volatility", ma1, ma2, ticker_input)
        st.plotly_chart(chart_returns(df, ticker_input), use_container_width=True)
        render_insight(df, "returns", ma1, ma2, ticker_input)
    with col_r:
        st.plotly_chart(chart_cumulative(df, ticker_input), use_container_width=True)
        render_insight(df, "cumulative", ma1, ma2, ticker_input)

    # =============================================================================
    # RAW DATA TABLE
    # =============================================================================
    with st.expander("View Raw Data Table"):
        st.dataframe(
            df.style.format({
                "Close": "Rs.{:.2f}",
                f"MA_{ma1}": "Rs.{:.2f}",
                f"MA_{ma2}": "Rs.{:.2f}",
                "Daily_Return_%": "{:.3f}%",
                "Volatility_20d": "{:.3f}",
                "Cumulative_%": "{:.2f}%",
            }),
            use_container_width=True,
        )
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine="openpyxl")
        st.download_button(
            label="Download as Excel",
            data=buffer.getvalue(),
            file_name=f"{ticker_input.replace('.', '_')}_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
else:
    st.markdown("""
    <div style="background:#111827;border:1px solid #1f2937;border-radius:10px;
    text-align:center;padding:70px 20px;margin-top:12px;margin-bottom:8px">
        <div style="font-size:40px;margin-bottom:14px">📈</div>
        <div style="font-family:'IBM Plex Sans',sans-serif;font-size:1.05rem;font-weight:700;
        color:#cbd5e1;letter-spacing:0.5px">Select a stock to view detailed analysis</div>
        <div style="font-size:0.86rem;color:#6b7280;margin-top:10px;line-height:1.8">
        Choose a stock in the sidebar and click <strong>Fetch &amp; Analyse</strong> to unlock candlesticks,
        volatility insights, and stock-specific metrics.
        </div>
    </div>
    """, unsafe_allow_html=True)

# =============================================================================
# CHATBOT — dedicated bottom container on main page
# =============================================================================
chatbot_container = st.container()
with chatbot_container:
    render_chatbot_main(df, ticker_input if ticker_input else "")

st.markdown("---")

# =============================================================================
# PROFESSIONAL FOOTER
# =============================================================================
link_col_1, link_col_2, link_col_3, link_col_4 = st.columns(4)
with link_col_1:
    st.markdown(
        "<div style='text-align:center;font-family:\"IBM Plex Sans\",sans-serif;'>"
        "<a href='https://www.linkedin.com/in/ritam-biswas-71a036374/' target='_blank' rel='noopener noreferrer' "
        "style='color:#9ca3af;text-decoration:none;font-size:0.86rem;'>LinkedIn</a></div>",
        unsafe_allow_html=True,
    )
with link_col_2:
    st.markdown(
        "<div style='text-align:center;font-family:\"IBM Plex Sans\",sans-serif;'>"
        "<a href='https://github.com/gitritam06' target='_blank' rel='noopener noreferrer' "
        "style='color:#9ca3af;text-decoration:none;font-size:0.86rem;'>GitHub</a></div>",
        unsafe_allow_html=True,
    )
with link_col_3:
    st.markdown(
        "<div style='text-align:center;font-family:\"IBM Plex Sans\",sans-serif;'>"
        "<span style='color:#6b7280;font-size:0.86rem;'>Twitter / X (coming soon)</span></div>",
        unsafe_allow_html=True,
    )
with link_col_4:
    st.markdown(
        "<div style='text-align:center;font-family:\"IBM Plex Sans\",sans-serif;'>"
        "<span style='color:#6b7280;font-size:0.86rem;'>Portfolio (coming soon)</span></div>",
        unsafe_allow_html=True,
    )

with st.expander("Terms of Use & Disclaimer"):
    st.markdown(
        "<div style='font-family:\"IBM Plex Sans\",sans-serif;color:#9ca3af;font-size:0.84rem;line-height:1.8;'>"
        "This dashboard is for educational purposes only. Data is provided by yfinance and may be delayed. "
        "I am not a SEBI registered advisor; please consult a professional before investing."
        "</div>",
        unsafe_allow_html=True,
    )

st.markdown(
    "<div style='font-family:\"IBM Plex Sans\",sans-serif;font-size:10px;color:#4b5563;text-align:center;"
    "letter-spacing:1px;margin-top:10px'>"
    "© 2024 | Built by Ritam Biswas | Powered by NVIDIA NIM"
    "</div>",
    unsafe_allow_html=True,
)
