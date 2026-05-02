import os
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import io
import requests
from datetime import datetime, timedelta
from market_indices import display_market_indices
from chatbot_engine import (
    get_chat_response,
    build_user_message,
    build_assistant_message,
    get_welcome_message,
)
from src.legal import render_legal_section
from src.faq import render_faq
from src.utils import get_data_with_fallback

# Session state controls (must initialize early)
if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "ticker_input" not in st.session_state:
    st.session_state["ticker_input"] = ""
if "auto_fetch" not in st.session_state:
    st.session_state["auto_fetch"] = False

st.set_page_config(
    page_title="AlgoMetrics — Indian Stock Dashboard",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" rel="stylesheet" />
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;1,100;1,200;1,300;1,400;1,500;1,600;1,700&display=swap');
html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"], .main, .stMarkdown, p, div, label {
  font-family: 'IBM Plex Sans', sans-serif !important;
}
/* Apply to spans EXCEPT Streamlit's internal icon elements */
span:not(.material-symbols-rounded):not([data-testid]):not([class*="icon"]) {
  font-family: 'IBM Plex Sans', sans-serif !important;
}
/* Force Material Symbols font on all Streamlit icon elements */
.material-symbols-rounded,
[data-testid="stExpanderToggleIcon"],
[data-testid="collapsedControl"] span,
button[kind="headerNoPadding"] span,
.stExpander span[data-testid],
[data-baseweb] span[aria-hidden="true"] {
  font-family: 'Material Symbols Rounded' !important;
  font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24 !important;
  -webkit-font-feature-settings: 'liga' 1;
  font-feature-settings: 'liga' 1;
}
/* ── Hide sidebar entirely ──────────────────────────────── */
section[data-testid="stSidebar"] { display: none !important; }
[data-testid="stSidebarCollapsedControl"] { display: none !important; }
[data-testid="collapsedControl"] { display: none !important; }
button[data-testid="baseButton-headerNoPadding"] { display: none !important; }
[data-testid="stMetric"] { background: #111827; border: 1px solid #1f2937; border-radius: 6px; padding: 14px 18px; }
[data-testid="stMetricLabel"] { font-size: 10px !important; letter-spacing: 1.5px; text-transform: uppercase; color: #6b7280 !important; }
[data-testid="stMetricValue"] { font-family: 'Syne', sans-serif !important; font-size: 1.6rem !important; font-weight: 800 !important; }
.main .block-container { background: #0b0f1a; padding-top: 24px; max-width: 1200px; }
body { background-color: #0b0f1a; }
.section-title { font-family: 'Syne', sans-serif; font-size: 11px; letter-spacing: 3px; text-transform: uppercase; color: #4b5563; margin: 28px 0 10px; border-bottom: 1px solid #1f2937; padding-bottom: 6px; }
/* ── Strip every Streamlit chrome element ───────────────── */
footer                                    { display: none !important; }
#MainMenu                                 { display: none !important; }
header[data-testid="stHeader"]            { display: none !important; }
[data-testid="stToolbar"]                 { display: none !important; }
[data-testid="stDecoration"]              { display: none !important; }
[data-testid="stStatusWidget"]            { display: none !important; }
[data-testid="stBottom"]                  { display: none !important; }
[data-testid="stBottomBlockContainer"]    { display: none !important; }
.stDeployButton                           { display: none !important; }
.viewerBadge_container__r5tak            { display: none !important; }
.viewerBadge_link__qRIco                 { display: none !important; }
#stDecoration                             { display: none !important; }
/* Remove dead space the hidden footer/header left behind */
.main .block-container                    { padding-bottom: 24px !important; }
/* Normalise top padding so mobile === desktop */
@media (max-width: 768px) {
  .main .block-container { padding-top: 24px !important; padding-left: 16px !important; padding-right: 16px !important; }
}
/* ── Popover styling ───────────────────────────────────── */
[data-testid="stPopover"] > div { min-width: 340px; }
.stDownloadButton button { background: #00e5a0 !important; color: #000 !important; font-family: 'JetBrains Mono', monospace !important; font-size: 11px !important; font-weight: 600 !important; letter-spacing: 1px !important; border: none !important; border-radius: 4px !important; }
.stButton button { background: #1a5276 !important; color: #fff !important; font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important; letter-spacing: 1px !important; border: 1px solid #2471a3 !important; border-radius: 4px !important; width: 100%; padding: 10px !important; }
.stButton button:hover { background: #2471a3 !important; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="section-title">Major Indices</p>', unsafe_allow_html=True)
@st.cache_data(ttl=3600) 
st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
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
        # Warm up the session with a cookie first
        session.get("https://www.nseindia.com", headers=headers, timeout=10)
        url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
        resp = session.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        from io import StringIO
        df = pd.read_csv(StringIO(resp.text))
        df = df[["SYMBOL", "NAME OF COMPANY"]].dropna()
        df["TICKER"] = df["SYMBOL"].str.strip() + ".NS"
        df["LABEL"] = df["NAME OF COMPANY"].str.strip() + " (" + df["SYMBOL"].str.strip() + " · NSE)"
        return df[["TICKER", "LABEL"]].sort_values("LABEL").reset_index(drop=True)
    except Exception:
        return _nse_fallback()
def _nse_fallback():
    """Comprehensive fallback list of NSE stocks when live fetch fails."""
    stocks = [
        ("RELIANCE.NS","Reliance Industries (RELIANCE · NSE)"),
        ("TCS.NS","Tata Consultancy Services (TCS · NSE)"),
        ("HDFCBANK.NS","HDFC Bank (HDFCBANK · NSE)"),
        ("INFY.NS","Infosys (INFY · NSE)"),
        ("ICICIBANK.NS","ICICI Bank (ICICIBANK · NSE)"),
        ("HINDUNILVR.NS","Hindustan Unilever (HINDUNILVR · NSE)"),
        ("SBIN.NS","State Bank of India (SBIN · NSE)"),
        ("BHARTIARTL.NS","Bharti Airtel (BHARTIARTL · NSE)"),
        ("KOTAKBANK.NS","Kotak Mahindra Bank (KOTAKBANK · NSE)"),
        ("BAJFINANCE.NS","Bajaj Finance (BAJFINANCE · NSE)"),
        ("WIPRO.NS","Wipro (WIPRO · NSE)"),
        ("HCLTECH.NS","HCL Technologies (HCLTECH · NSE)"),
        ("AXISBANK.NS","Axis Bank (AXISBANK · NSE)"),
        ("ASIANPAINT.NS","Asian Paints (ASIANPAINT · NSE)"),
        ("MARUTI.NS","Maruti Suzuki (MARUTI · NSE)"),
        ("SUNPHARMA.NS","Sun Pharmaceutical (SUNPHARMA · NSE)"),
        ("TITAN.NS","Titan Company (TITAN · NSE)"),
        ("ULTRACEMCO.NS","UltraTech Cement (ULTRACEMCO · NSE)"),
        ("NESTLEIND.NS","Nestle India (NESTLEIND · NSE)"),
        ("POWERGRID.NS","Power Grid Corporation (POWERGRID · NSE)"),
        ("NTPC.NS","NTPC (NTPC · NSE)"),
        ("ONGC.NS","Oil & Natural Gas Corp (ONGC · NSE)"),
        ("JSWSTEEL.NS","JSW Steel (JSWSTEEL · NSE)"),
        ("TATAMOTORS.NS","Tata Motors (TATAMOTORS · NSE)"),
        ("TATASTEEL.NS","Tata Steel (TATASTEEL · NSE)"),
        ("ADANIENT.NS","Adani Enterprises (ADANIENT · NSE)"),
        ("ADANIPORTS.NS","Adani Ports (ADANIPORTS · NSE)"),
        ("ADANIGREEN.NS","Adani Green Energy (ADANIGREEN · NSE)"),
        ("ADANIPOWER.NS","Adani Power (ADANIPOWER · NSE)"),
        ("BAJAJFINSV.NS","Bajaj Finserv (BAJAJFINSV · NSE)"),
        ("BAJAJ-AUTO.NS","Bajaj Auto (BAJAJ-AUTO · NSE)"),
        ("HEROMOTOCO.NS","Hero MotoCorp (HEROMOTOCO · NSE)"),
        ("EICHERMOT.NS","Eicher Motors (EICHERMOT · NSE)"),
        ("CIPLA.NS","Cipla (CIPLA · NSE)"),
        ("DRREDDY.NS","Dr. Reddy's Laboratories (DRREDDY · NSE)"),
        ("DIVISLAB.NS","Divi's Laboratories (DIVISLAB · NSE)"),
        ("APOLLOHOSP.NS","Apollo Hospitals (APOLLOHOSP · NSE)"),
        ("MAXHEALTH.NS","Max Healthcare (MAXHEALTH · NSE)"),
        ("TECHM.NS","Tech Mahindra (TECHM · NSE)"),
        ("LTIM.NS","LTIMindtree (LTIM · NSE)"),
        ("PERSISTENT.NS","Persistent Systems (PERSISTENT · NSE)"),
        ("MPHASIS.NS","Mphasis (MPHASIS · NSE)"),
        ("COFORGE.NS","Coforge (COFORGE · NSE)"),
        ("LTTS.NS","L&T Technology Services (LTTS · NSE)"),
        ("LT.NS","Larsen & Toubro (LT · NSE)"),
        ("SIEMENS.NS","Siemens India (SIEMENS · NSE)"),
        ("ABB.NS","ABB India (ABB · NSE)"),
        ("HAVELLS.NS","Havells India (HAVELLS · NSE)"),
        ("VOLTAS.NS","Voltas (VOLTAS · NSE)"),
        ("GODREJCP.NS","Godrej Consumer Products (GODREJCP · NSE)"),
        ("DABUR.NS","Dabur India (DABUR · NSE)"),
        ("MARICO.NS","Marico (MARICO · NSE)"),
        ("COLPAL.NS","Colgate-Palmolive India (COLPAL · NSE)"),
        ("PIDILITIND.NS","Pidilite Industries (PIDILITIND · NSE)"),
        ("BERGEPAINT.NS","Berger Paints (BERGEPAINT · NSE)"),
        ("INDIGO.NS","IndiGo / InterGlobe Aviation (INDIGO · NSE)"),
        ("IRCTC.NS","IRCTC (IRCTC · NSE)"),
        ("IRFC.NS","Indian Railway Finance Corp (IRFC · NSE)"),
        ("PFC.NS","Power Finance Corporation (PFC · NSE)"),
        ("RECLTD.NS","REC Limited (RECLTD · NSE)"),
        ("CANBK.NS","Canara Bank (CANBK · NSE)"),
        ("BANKBARODA.NS","Bank of Baroda (BANKBARODA · NSE)"),
        ("PNB.NS","Punjab National Bank (PNB · NSE)"),
        ("UNIONBANK.NS","Union Bank of India (UNIONBANK · NSE)"),
        ("INDUSINDBK.NS","IndusInd Bank (INDUSINDBK · NSE)"),
        ("FEDERALBNK.NS","Federal Bank (FEDERALBNK · NSE)"),
        ("IDFCFIRSTB.NS","IDFC First Bank (IDFCFIRSTB · NSE)"),
        ("BANDHANBNK.NS","Bandhan Bank (BANDHANBNK · NSE)"),
        ("MUTHOOTFIN.NS","Muthoot Finance (MUTHOOTFIN · NSE)"),
        ("CHOLAFIN.NS","Cholamandalam Investment (CHOLAFIN · NSE)"),
        ("SHRIRAMFIN.NS","Shriram Finance (SHRIRAMFIN · NSE)"),
        ("M&M.NS","Mahindra & Mahindra (M&M · NSE)"),
        ("TVSMOTOR.NS","TVS Motor Company (TVSMOTOR · NSE)"),
        ("BOSCHLTD.NS","Bosch India (BOSCHLTD · NSE)"),
        ("MOTHERSON.NS","Samvardhana Motherson (MOTHERSON · NSE)"),
        ("BALKRISIND.NS","Balkrishna Industries (BALKRISIND · NSE)"),
        ("MRF.NS","MRF (MRF · NSE)"),
        ("APOLLOTYRE.NS","Apollo Tyres (APOLLOTYRE · NSE)"),
        ("COALINDIA.NS","Coal India (COALINDIA · NSE)"),
        ("VEDL.NS","Vedanta (VEDL · NSE)"),
        ("HINDALCO.NS","Hindalco Industries (HINDALCO · NSE)"),
        ("NATIONALUM.NS","National Aluminium (NATIONALUM · NSE)"),
        ("SAIL.NS","Steel Authority of India (SAIL · NSE)"),
        ("NMDC.NS","NMDC (NMDC · NSE)"),
        ("GAIL.NS","GAIL India (GAIL · NSE)"),
        ("BPCL.NS","Bharat Petroleum (BPCL · NSE)"),
        ("IOC.NS","Indian Oil Corporation (IOC · NSE)"),
        ("HPCL.NS","Hindustan Petroleum (HPCL · NSE)"),
        ("ZOMATO.NS","Zomato (ZOMATO · NSE)"),
        ("NYKAA.NS","Nykaa / FSN E-Commerce (NYKAA · NSE)"),
        ("PAYTM.NS","Paytm / One97 Communications (PAYTM · NSE)"),
        ("POLICYBZR.NS","PB Fintech / PolicyBazaar (POLICYBZR · NSE)"),
        ("DELHIVERY.NS","Delhivery (DELHIVERY · NSE)"),
        ("TATACOMM.NS","Tata Communications (TATACOMM · NSE)"),
        ("IDEA.NS","Vodafone Idea (IDEA · NSE)"),
        ("DIXON.NS","Dixon Technologies (DIXON · NSE)"),
        ("AMBER.NS","Amber Enterprises (AMBER · NSE)"),
        ("KALYANKJIL.NS","Kalyan Jewellers (KALYANKJIL · NSE)"),
        ("SENCO.NS","Senco Gold (SENCO · NSE)"),
        ("TRENT.NS","Trent (TRENT · NSE)"),
        ("DMART.NS","Avenue Supermarts / DMart (DMART · NSE)"),
        ("PAGEIND.NS","Page Industries (PAGEIND · NSE)"),
        ("ABFRL.NS","Aditya Birla Fashion (ABFRL · NSE)"),
        ("OBEROIRLTY.NS","Oberoi Realty (OBEROIRLTY · NSE)"),
        ("DLF.NS","DLF (DLF · NSE)"),
        ("GODREJPROP.NS","Godrej Properties (GODREJPROP · NSE)"),
        ("PRESTIGE.NS","Prestige Estates (PRESTIGE · NSE)"),
        ("BRIGADE.NS","Brigade Enterprises (BRIGADE · NSE)"),
        ("^NSEI","Nifty 50 Index (^NSEI)"),
        ("^BSESN","BSE Sensex (^BSESN)"),
        ("^CNXIT","Nifty IT Index (^CNXIT)"),
        ("^NSEBANK","Nifty Bank Index (^NSEBANK)"),
    ]
    df = pd.DataFrame(stocks, columns=["TICKER", "LABEL"])
    return df.sort_values("LABEL").reset_index(drop=True)


@st.cache_data(show_spinner=False, ttl=86400)
def load_bse_stocks():
    """Fetch live BSE equity list. Tickers use numeric BSE scrip code + .BO (yfinance format)."""
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
            + " · BSE)"
        )
        return df[["TICKER", "LABEL"]].sort_values("LABEL").reset_index(drop=True)
    except Exception:
        return None


@st.cache_data(show_spinner=False, ttl=300)
def get_data(ticker, start, end, ma_short, ma_long):
    df = get_data_with_fallback(ticker, start=str(start), end=str(end))
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
    "RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS",
    "HINDUNILVR.NS","SBIN.NS","BHARTIARTL.NS","KOTAKBANK.NS","BAJFINANCE.NS",
    "WIPRO.NS","HCLTECH.NS","AXISBANK.NS","ASIANPAINT.NS","MARUTI.NS",
    "SUNPHARMA.NS","TITAN.NS","ULTRACEMCO.NS","NESTLEIND.NS","POWERGRID.NS",
    "NTPC.NS","ONGC.NS","JSWSTEEL.NS","TATAMOTORS.NS","TATASTEEL.NS",
    "ADANIENT.NS","ADANIPORTS.NS","BAJAJFINSV.NS","BAJAJ-AUTO.NS","HEROMOTOCO.NS",
    "EICHERMOT.NS","CIPLA.NS","DRREDDY.NS","DIVISLAB.NS","APOLLOHOSP.NS",
    "TECHM.NS","LT.NS","COALINDIA.NS","HINDALCO.NS","GAIL.NS",
    "BPCL.NS","IOC.NS","INDUSINDBK.NS","M&M.NS","TVSMOTOR.NS",
    "TRENT.NS","DMART.NS","DLF.NS","ZOMATO.NS","IRCTC.NS",
]

@st.cache_data(show_spinner=False, ttl=900)   # refresh every 15 min
def get_movers():
    """Return top gainer and loser from Nifty 50 for today."""
    try:
        records = []
        raw = get_data_with_fallback(
            NIFTY50,
            period="5d",
            group_by="ticker",
        )
        for ticker in NIFTY50:
            try:
                closes = raw[ticker]["Close"].dropna()
                if len(closes) < 2:
                    continue
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
        loser  = df.loc[df["pct"].idxmin()].to_dict()
        return gainer, loser
    except Exception:
        return None, None


@st.cache_data(show_spinner=False, ttl=3600)   # cache AI answer 1 hour
def get_nim_context(ticker, pct, direction):
    """Ask NVIDIA NIM why stock moved today."""
    try:
        api_key = os.environ.get("NVIDIA_API_KEY", "")
    except Exception:
        return "NVIDIA NIM key not found in Streamlit secrets."

    prompt = (
        f"You are a concise Indian stock market analyst. "
        f"{ticker.replace('.NS','')} stock moved {pct:+.2f}% today on the NSE. "
        f"In 2-3 sentences, give the most likely fundamental or market reason "
        f"for this {'gain' if direction == 'up' else 'decline'}. "
        f"Be specific to Indian markets. No disclaimers."
    )

    try:
        resp = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "meta/llama-3.1-70b-instruct",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 120,
                "temperature": 0.4,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"Could not fetch AI context: {str(e)}"

PLOT_LAYOUT = dict(
    paper_bgcolor="#0b0f1a", plot_bgcolor="#0b0f1a",
    font=dict(family="JetBrains Mono, monospace", color="#9ca3af", size=11),
    xaxis=dict(gridcolor="#1f2937", showgrid=True, zeroline=False),
    yaxis=dict(gridcolor="#1f2937", showgrid=True, zeroline=False),
    margin=dict(l=12, r=12, t=40, b=12),
    legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", yanchor="bottom", y=1.02),
    hovermode="x unified", uirevision="constant",
)


def chart_candlestick(df, ma1, ma2, ticker):
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df["Date"],
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="OHLC",
        increasing=dict(line=dict(color="#00e5a0", width=1), fillcolor="rgba(0,229,160,0.75)"),
        decreasing=dict(line=dict(color="#f87171", width=1), fillcolor="rgba(248,113,113,0.75)"),
    ))
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df[f"MA_{ma1}"],
        name=f"MA {ma1}d",
        line=dict(color="#00e5a0", width=1.5, dash="dot"),
    ))
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df[f"MA_{ma2}"],
        name=f"MA {ma2}d",
        line=dict(color="#3b82f6", width=1.5, dash="dot"),
    ))

    # Build layout without duplicate xaxis key — merge base settings into one dict
    candlestick_layout = {k: v for k, v in PLOT_LAYOUT.items() if k != "xaxis"}
    candlestick_layout["title"] = dict(
        text=f"Candlestick & Moving Averages — {ticker}",
        font=dict(size=13, color="#e2e8f0"),
    )
    candlestick_layout["xaxis"] = dict(
        gridcolor="#1f2937",
        showgrid=True,
        zeroline=False,
        rangeslider=dict(
            visible=True,
            thickness=0.06,
            bgcolor="#111827",
            bordercolor="#1f2937",
            borderwidth=1,
        ),
        rangeselector=dict(
            buttons=[
                dict(count=1,  label="1M",  step="month", stepmode="backward"),
                dict(count=3,  label="3M",  step="month", stepmode="backward"),
                dict(count=6,  label="6M",  step="month", stepmode="backward"),
                dict(count=1,  label="1Y",  step="year",  stepmode="backward"),
                dict(step="all", label="All"),
            ],
            bgcolor="#111827",
            activecolor="#00e5a0",
            bordercolor="#1f2937",
            borderwidth=1,
            font=dict(color="#9ca3af", size=11),
            x=0, y=1.02,
        ),
    )
    fig.update_layout(**candlestick_layout)
    return fig


def chart_volatility(df, ticker):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Volatility_20d"], name="20d Volatility", fill="tozeroy", line=dict(color="#f59e0b", width=1.5), fillcolor="rgba(245,158,11,0.1)"))
    fig.update_layout(**PLOT_LAYOUT, title=dict(text=f"20-Day Rolling Volatility — {ticker}", font=dict(size=13, color="#e2e8f0")))
    return fig


def chart_returns(df, ticker):
    colors = ["#00e5a0" if v >= 0 else "#f87171" for v in df["Daily_Return_%"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["Date"], y=df["Daily_Return_%"], name="Daily Return %", marker_color=colors))
    fig.add_hline(y=0, line_color="#4b5563", line_width=1)
    fig.update_layout(**PLOT_LAYOUT, title=dict(text=f"Daily Returns (%) — {ticker}", font=dict(size=13, color="#e2e8f0")))
    return fig


def chart_cumulative(df, ticker):
    final_val = float(df["Cumulative_%"].iloc[-1])
    color = "#00e5a0" if final_val >= 0 else "#f87171"
    fill_rgb = "0,229,160" if final_val >= 0 else "248,113,113"
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Cumulative_%"], name="Cumulative Return", fill="tozeroy", line=dict(color=color, width=2), fillcolor=f"rgba({fill_rgb},0.08)"))
    fig.add_hline(y=0, line_color="#4b5563", line_width=1)
    fig.update_layout(**PLOT_LAYOUT, title=dict(text=f"Cumulative Return (%) — {ticker}", font=dict(size=13, color="#e2e8f0")))
    return fig


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
        what = (f"This chart overlays the raw closing price of <strong>{ticker}</strong> with its {ma1}-day and {ma2}-day Simple Moving Averages (SMA). A moving average smooths out daily noise by averaging the price over a rolling window — the longer the window, the smoother and slower the line.")
        if price_above_short and price_above_long:
            signal = (f"🟢 <strong>Bullish signal:</strong> The price (₹{close:.2f}) is <strong>above</strong> both the {ma1}d (₹{ma_short:.2f}) and {ma2}d (₹{ma_long:.2f}) moving averages — the stock is in an uptrend and buyers are in control.")
        elif not price_above_short and not price_above_long:
            signal = (f"🔴 <strong>Bearish signal:</strong> The price (₹{close:.2f}) is <strong>below</strong> both the {ma1}d (₹{ma_short:.2f}) and {ma2}d (₹{ma_long:.2f}) moving averages — selling pressure or a downtrend may be forming.")
        else:
            signal = (f"🟡 <strong>Mixed signal:</strong> The price (₹{close:.2f}) sits between the {ma1}d (₹{ma_short:.2f}) and {ma2}d (₹{ma_long:.2f}) moving averages — the market is in a transitional phase. Watch for a decisive break in either direction.")
        if golden_cross:
            extra = (f"⚡ <strong>Golden Cross detected:</strong> The {ma1}d MA just crossed <em>above</em> the {ma2}d MA — historically one of the strongest bullish signals in technical analysis.")
        elif death_cross:
            extra = (f"⚠️ <strong>Death Cross detected:</strong> The {ma1}d MA just crossed <em>below</em> the {ma2}d MA — historically a bearish signal that can indicate the start of a sustained downtrend.")
        else:
            direction = "above" if ma_short > ma_long else "below"
            bias = "short-term bullish" if ma_short > ma_long else "short-term bearish"
            extra = (f"The {ma1}d MA is currently <strong>{direction}</strong> the {ma2}d MA — indicating a {bias} bias relative to the longer-term average.")

    elif chart_type == "volatility":
        title = "Reading the Volatility Chart"
        what = (f"This chart shows the <strong>20-day rolling volatility</strong> of {ticker} — calculated as the standard deviation of daily returns over the past 20 trading days. Think of it as a fear gauge: high peaks mean uncertainty or reaction to major news; flat low periods mean calm, steady price action.")
        if high_vol:
            signal = (f"🔴 <strong>Elevated volatility:</strong> Current volatility ({vol:.2f}%) is significantly above the average ({avg_vol:.2f}%) — the stock is experiencing unusually large price swings. Higher risk, potentially higher reward. Exercise caution with sizing.")
        elif low_vol:
            signal = (f"🟢 <strong>Calm market:</strong> At {vol:.2f}% versus an average of {avg_vol:.2f}%, the stock is in a low-turbulence phase. Low volatility periods often precede breakouts in either direction.")
        else:
            signal = (f"🟡 <strong>Normal volatility:</strong> At {vol:.2f}% versus an average of {avg_vol:.2f}%, this stock is behaving within its typical range — no unusual fear or euphoria right now.")
        extra = "Volatility is not the same as direction — a highly volatile stock can move sharply up <em>or</em> down. Always pair this with the price trend in the MA chart above."

    elif chart_type == "cumulative":
        title = "Reading the Cumulative Return Chart"
        what = (f"This chart answers a powerful question: <em>if you had invested on the first day of the selected period, what would your total return be today?</em> It compounds all daily gains and losses into a single running total, removing the noise of individual days.")
        if cum >= 0:
            signal = (f"🟢 <strong>Positive journey:</strong> {ticker} has returned <strong>+{cum:.2f}%</strong> over the selected period. A steep upward angle means rapid growth; a gradual climb means slow and steady compounding.")
        else:
            signal = (f"🔴 <strong>Negative journey:</strong> {ticker} has returned <strong>{cum:.2f}%</strong> — the stock is worth less today than at the start of this window. Check the MA chart to determine whether this is a long-term trend or a recent dip.")
        extra = "Use this chart to <strong>compare stocks</strong> — fetching two different tickers with the same date range and comparing their cumulative curves gives an instant, apples-to-apples performance comparison."

    else:
        title = "Reading the Daily Returns Chart"
        what = (f"Each bar represents the percentage change in {ticker}'s closing price from the previous trading day. <strong>Green bars</strong> are up days; <strong>red bars</strong> are down days. The height of the bar reflects the magnitude of the move.")
        move = "gained" if ret >= 0 else "lost"
        context = ("A move of this magnitude typically corresponds to a major event — earnings, RBI policy, or global news. Check the news on this date for context." if abs(ret) > 2 else "Normal day-to-day fluctuation — no extreme move in the latest session.")
        signal = (f"🟢 <strong>Latest session:</strong> {ticker} {move} <strong>{ret:+.3f}%</strong> in the most recent trading day. {context}")
        extra = "Look for <strong>outlier bars</strong> — unusually tall spikes almost always correspond to earnings announcements, RBI decisions, or major global events. Cross-referencing these dates with news adds real analytical depth."

    st.markdown(f"""
    <div style="background:#111827;border:1px solid #1f2937;border-radius:8px;padding:22px 26px;margin-top:-8px;margin-bottom:28px">
        <div style="font-family:'Syne',sans-serif;font-size:11px;letter-spacing:2.5px;text-transform:uppercase;color:#4b5563;margin-bottom:10px">analyst's note</div>
        <div style="font-family:'Syne',sans-serif;font-size:1rem;font-weight:700;color:#e2e8f0;margin-bottom:12px">{title}</div>
        <div style="font-size:0.87rem;color:#6b7280;line-height:1.9;margin-bottom:12px">{what}</div>
        <div style="background:#0b0f1a;border-radius:6px;padding:14px 18px;margin-bottom:10px;font-size:0.87rem;color:#9ca3af;line-height:1.8">{signal}</div>
        <div style="font-size:0.83rem;color:#4b5563;line-height:1.8;border-top:1px solid #1f2937;padding-top:10px">💡 {extra}</div>
    </div>
    """, unsafe_allow_html=True)


def render_chatbot_main(df, ticker_input):
    """Render ArthBot on the main page with optional stock context."""
    st.markdown("---")
    st.markdown(
        '<p class="section-title">ArthBot - AI Markets Analyst</p>',
        unsafe_allow_html=True,
    )

    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "arth_stock_ctx" not in st.session_state:
        st.session_state.arth_stock_ctx = None

    if df is not None and st.session_state.arth_stock_ctx != ticker_input:
        st.session_state.arth_stock_ctx = ticker_input
        st.session_state.messages = []

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

    chat_area = st.container(height=420)
    with chat_area:
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

        for msg in st.session_state.messages:
            avatar = "👤" if msg["role"] == "user" else "🤖"
            with st.chat_message(msg["role"], avatar=avatar):
                st.markdown(msg["content"])

    placeholder = (
        f"Ask about {ticker_input}, its sector, technicals, F&O..."
        if df is not None
        else "Ask any Indian markets question..."
    )
    user_input = st.chat_input(placeholder, key="arth_main_input")

    if user_input:
        nim_key = os.environ.get("NVIDIA_API_KEY")
        if not nim_key:
            try:
                nim_key = st.secrets["NVIDIA_API_KEY"]
            except Exception:
                nim_key = None

        if not nim_key:
            st.session_state.messages.append(build_user_message(user_input))
            st.session_state.messages.append(build_assistant_message(
                "NVIDIA API key is missing. Please configure NVIDIA_API_KEY in Render secrets or environment variables to enable ArthBot."
            ))
            st.rerun()

        user_msg = build_user_message(user_input)
        st.session_state.messages.append(user_msg)

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
                    reply = get_chat_response(api_history)
                st.markdown(reply)

        st.session_state.messages.append(build_assistant_message(reply))


# ── Load stock lists (needed before popover) ──────────────
nse_stocks = load_nse_stocks()
bse_stocks = load_bse_stocks()
_parts = [s for s in [nse_stocks, bse_stocks] if s is not None]
all_stocks = (
    pd.concat(_parts, ignore_index=True)
    .sort_values("LABEL")
    .reset_index(drop=True)
    if _parts else None
)


# ── Header ─────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:8px">
  <div>
    <span style="font-family:'Syne',sans-serif;font-size:2rem;font-weight:800;color:#e2e8f0;letter-spacing:-1px;">
      Stock Market <span style="color:#00e5a0;">Analyser</span>
    </span><br>
    <span style="font-size:11px;color:#4b5563;letter-spacing:2px;text-transform:uppercase;">NSE · BSE · Real-time via Yahoo Finance</span>
  </div>
</div>
""", unsafe_allow_html=True)
st.markdown("---")
# ── Daily Movers ───────────────────────────────────────────
st.markdown('<p class="section-title">Today\'s Market Movers — Nifty 50</p>', unsafe_allow_html=True)

with st.spinner("Scanning Nifty 50 for today's movers..."):
    gainer, loser = get_movers()

if gainer and loser:
    mg, ml = st.columns(2)

    with mg:
        nim_up = get_nim_context(gainer["ticker"], gainer["pct"], "up")
        st.markdown(f"""
        <div style="background:#0d1f12;border:1px solid #1a3a20;border-left:4px solid #00e5a0;
        border-radius:8px;padding:20px 22px;height:100%">
            <div style="font-family:'Syne',sans-serif;font-size:10px;letter-spacing:2px;
            text-transform:uppercase;color:#4b5563;margin-bottom:8px">🟢 Top Gainer</div>
            <div style="font-family:'Syne',sans-serif;font-size:1.4rem;font-weight:800;
            color:#00e5a0;line-height:1">{gainer['name']}</div>
            <div style="font-size:1.1rem;font-weight:700;color:#e2e8f0;margin:4px 0 2px">
            ₹{gainer['close']:.2f}
            <span style="color:#00e5a0;font-size:0.95rem">&nbsp;{gainer['pct']:+.2f}%</span>
            </div>
            <div style="margin-top:12px;padding-top:12px;border-top:1px solid #1a3a20;
            font-size:0.83rem;color:#6b7280;line-height:1.7">
            <span style="color:#4b5563;font-size:10px;letter-spacing:1px;
            text-transform:uppercase">🤖 NIM Analysis</span><br>{nim_up}
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(gainer["ticker"], key="mover_gainer_btn"):
            st.session_state["ticker_input"] = gainer["ticker"]
            st.session_state["auto_fetch"] = True
            st.rerun()

    with ml:
        nim_dn = get_nim_context(loser["ticker"], loser["pct"], "down")
        st.markdown(f"""
        <div style="background:#1f0d0d;border:1px solid #3a1a1a;border-left:4px solid #f87171;
        border-radius:8px;padding:20px 22px;height:100%">
            <div style="font-family:'Syne',sans-serif;font-size:10px;letter-spacing:2px;
            text-transform:uppercase;color:#4b5563;margin-bottom:8px">🔴 Top Loser</div>
            <div style="font-family:'Syne',sans-serif;font-size:1.4rem;font-weight:800;
            color:#f87171;line-height:1">{loser['name']}</div>
            <div style="font-size:1.1rem;font-weight:700;color:#e2e8f0;margin:4px 0 2px">
            ₹{loser['close']:.2f}
            <span style="color:#f87171;font-size:0.95rem">&nbsp;{loser['pct']:+.2f}%</span>
            </div>
            <div style="margin-top:12px;padding-top:12px;border-top:1px solid #3a1a1a;
            font-size:0.83rem;color:#6b7280;line-height:1.7">
            <span style="color:#4b5563;font-size:10px;letter-spacing:1px;
            text-transform:uppercase">🤖 NIM Analysis</span><br>{nim_dn}
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button(loser["ticker"], key="mover_loser_btn"):
            st.session_state["ticker_input"] = loser["ticker"]
            st.session_state["auto_fetch"] = True
            st.rerun()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
else:
    st.caption("Market data unavailable right now — movers will appear during trading hours.")

st.markdown("---")

# ── Popover: Stock Selection & Filters ─────────────────────
# Initialize default variables in case popover is closed and lazy-loaded
fetch_btn = False
_pop_range = st.session_state.get("pop_range", "1 Year")
_today = datetime.today()
if _pop_range == "1 Year":
    _start_default = _today - timedelta(days=365)
elif _pop_range == "2 Years":
    _start_default = _today - timedelta(days=730)
elif _pop_range == "5 Years":
    _start_default = _today - timedelta(days=1825)
else:
    _start_default = _today - timedelta(days=365)

if _pop_range == "Custom":
    start_date = st.session_state.get("pop_from", _start_default.date())
    end_date = st.session_state.get("pop_to", _today.date())
else:
    start_date = _start_default.date()
    end_date = _today.date()

ma1 = st.session_state.get("pop_ma1", 20)
ma2 = st.session_state.get("pop_ma2", 50)

with st.popover("Enter a name or ticker.....", use_container_width=False):
    st.markdown('<p class="section-title" style="margin-top:0">Search NSE &amp; BSE</p>', unsafe_allow_html=True)
    if all_stocks is not None:
        labels = ["— Type or select a company —"] + all_stocks["LABEL"].tolist()
        selected = st.selectbox("Stock", labels, label_visibility="collapsed", key="pop_stock")
        auto_ticker = (
            all_stocks.loc[all_stocks["LABEL"] == selected, "TICKER"].values[0]
            if selected != "— Type or select a company —" else ""
        )
    else:
        auto_ticker = ""

    st.markdown('<p class="section-title">Custom Ticker / Company</p>', unsafe_allow_html=True)
    manual = st.text_input(
        "Search",
        value="",
        placeholder="e.g. Infosys / 500325.BO / ^NSEI",
        label_visibility="collapsed",
        key="pop_manual",
    )
    recommended_ticker = ""
    manual_clean = manual.strip()
    if manual_clean:
        looks_like_ticker = "." in manual_clean or manual_clean.startswith("^")
        if not looks_like_ticker and all_stocks is not None:
            query = manual_clean.lower()
            mask = all_stocks["LABEL"].str.lower().str.contains(query, regex=False)
            matches = all_stocks[mask].head(8)
            if not matches.empty:
                st.markdown('<p class="section-title" style="margin-top:10px">Recommendations</p>', unsafe_allow_html=True)
                rec_options = ["— Select a match —"] + matches["LABEL"].tolist()
                rec_choice = st.selectbox("Matches", rec_options, label_visibility="collapsed", key="pop_rec")
                if rec_choice != "— Select a match —":
                    recommended_ticker = all_stocks.loc[all_stocks["LABEL"] == rec_choice, "TICKER"].values[0]
            else:
                st.caption("No matches — try a direct ticker like INFY.NS or 500325.BO")

    # Resolution priority: direct ticker > recommendation > dropdown
    manual_upper = manual.strip().upper()
    looks_like_ticker = "." in manual_upper or manual_upper.startswith("^")
    popover_ticker = manual_upper if looks_like_ticker else (recommended_ticker if recommended_ticker else auto_ticker)
    if popover_ticker and not st.session_state.get("auto_fetch", False):
        st.session_state["ticker_input"] = popover_ticker

    st.markdown("---")
    st.markdown('<p class="section-title">Date Range</p>', unsafe_allow_html=True)
    range_opt = st.radio("Range", ["1 Year", "2 Years", "5 Years", "Custom"], label_visibility="collapsed", key="pop_range")
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
        _dc1, _dc2 = st.columns(2)
        with _dc1:
            start_date = st.date_input("From", value=start_default, key="pop_from")
        with _dc2:
            end_date = st.date_input("To", value=today, key="pop_to")
    else:
        start_date = start_default.date()
        end_date = today.date()

    st.markdown("---")
    st.markdown('<p class="section-title">Moving Averages</p>', unsafe_allow_html=True)
    ma1 = st.slider("Short MA (days)", 5, 50, 20, key="pop_ma1")
    ma2 = st.slider("Long MA (days)", 20, 200, 50, key="pop_ma2")
    fetch_btn = st.button("📡 Fetch & Analyse", key="pop_fetch", use_container_width=True)

ticker_input = st.session_state.get("ticker_input", "")
analysis_ready = (fetch_btn or st.session_state.get("auto_fetch", False)) and bool(ticker_input)
df = None

if not analysis_ready:
    st.markdown("""
    <div style="text-align:center;padding:80px 20px">
        <div style="font-size:48px;margin-bottom:16px">🔎</div>
        <div style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700;color:#6b7280;letter-spacing:1px">Search And Analyse</div>
        <div style="font-size:12px;color:#374151;margin-top:8px">Search</div>
    </div>
    """, unsafe_allow_html=True)
elif analysis_ready:
    with st.spinner(f"Fetching {ticker_input} from Yahoo Finance..."):
        df = get_data(ticker_input, start_date, end_date, ma1, ma2)
    st.session_state["auto_fetch"] = False

if analysis_ready and (df is None or df.empty):
    st.markdown(f"""
    <div style="background:#111827;border:1px solid #1f2937;border-left:3px solid #f59e0b;border-radius:6px;padding:24px 28px;margin-top:20px">
        <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:1.1rem;color:#e2e8f0;margin-bottom:8px">We couldn't find data for <span style="color:#f59e0b">{ticker_input}</span></div>
        <div style="font-size:0.88rem;color:#6b7280;line-height:1.8">
            This could be due to an incorrect ticker symbol or a temporary issue with the data source.<br><br>
            <span style="color:#9ca3af">Things to check:</span><br>
            &nbsp;&nbsp;· NSE stocks → <code style="background:#1a2236;padding:1px 6px;border-radius:3px;color:#00e5a0">RELIANCE.NS</code><br>
            &nbsp;&nbsp;· BSE stocks → <code style="background:#1a2236;padding:1px 6px;border-radius:3px;color:#00e5a0">RELIANCE.BO</code><br>
            &nbsp;&nbsp;· Indices → <code style="background:#1a2236;padding:1px 6px;border-radius:3px;color:#00e5a0">^NSEI</code>
        </div>
    </div>
    """, unsafe_allow_html=True)
elif analysis_ready:
    latest = df.iloc[-1]
    first = df.iloc[0]
    total_ret = float((latest["Close"] - first["Close"]) / first["Close"] * 100)
    avg_vol = float(df["Volatility_20d"].mean())

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Latest Close", f"₹{float(latest['Close']):.2f}")
    c2.metric("Total Return", f"{total_ret:+.2f}%", delta=f"{total_ret:+.2f}%")
    c3.metric(f"MA {ma1}d", f"₹{float(latest[f'MA_{ma1}']):.2f}")
    c4.metric(f"MA {ma2}d", f"₹{float(latest[f'MA_{ma2}']):.2f}")
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
        f"₹{_price_now:.2f}",
        delta=f"{_price_delta:+.2f}% today",
        delta_color="normal",
    )
    _m2.metric("52-Week High", f"₹{_week52_high:.2f}")
    _m3.metric("Avg Daily Volume", f"{_avg_volume:,.0f}")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

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

    with st.expander(" View Raw Data Table"):
        st.dataframe(df.style.format({
            "Close": "₹{:.2f}", f"MA_{ma1}": "₹{:.2f}", f"MA_{ma2}": "₹{:.2f}",
            "Daily_Return_%": "{:.3f}%", "Volatility_20d": "{:.3f}", "Cumulative_%": "{:.2f}%",
        }), use_container_width=True)
        buffer = io.BytesIO()
        df.to_excel(buffer, index=False, engine="openpyxl")
        st.download_button(
            label="⬇ Download as Excel",
            data=buffer.getvalue(),
            file_name=f"{ticker_input.replace('.', '_')}_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

chatbot_container = st.container()
with chatbot_container:
    render_chatbot_main(df, ticker_input if ticker_input else "")

# FAQ and Legal sections — rendered at the absolute bottom
render_faq()
render_legal_section()

st.markdown("---")
st.markdown(
    """
    <div style='text-align:center;line-height:1.9;'>
        <span>🔗 <a href='https://www.linkedin.com/in/ritam-biswas-71a036374/' target='_blank' rel='noopener noreferrer'>LinkedIn</a></span>
        <span> | </span>
        <span>💻 <a href='https://github.com/gitritam06' target='_blank' rel='noopener noreferrer'>GitHub</a></span>
        <span> | </span>
        <span>🌐 <a href='https://github.com/gitritam06' target='_blank' rel='noopener noreferrer'>Portfolio</a></span>
        <div style='font-size:0.8rem;color:#6b7280;margin-top:6px;'>
            Built by Ritam Biswas using Python, Groq & NVIDIA NIM | © 2026 Algometrics
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)
