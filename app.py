import os
import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import io
import requests
from datetime import datetime, timedelta

st.set_page_config(
    page_title="AlgoMetrics — Indian Stock Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── FONT & STYLE UPDATES ──────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&display=swap');

html, body, [class*="st-"] { 
    font-family: 'IBM Plex Sans', sans-serif; 
}

/* Tabular numbers for better price alignment */
[data-testid="stMetricValue"] { 
    font-family: 'IBM Plex Sans', sans-serif !important; 
    font-variant-numeric: tabular-nums;
    font-size: 1.8rem !important; 
    font-weight: 700 !important; 
}

section[data-testid="stSidebar"] { background: #0e1117; border-right: 1px solid #1f2937; }
section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stMetric"] { background: #111827; border: 1px solid #1f2937; border-radius: 6px; padding: 14px 18px; }
[data-testid="stMetricLabel"] { font-size: 10px !important; letter-spacing: 1.5px; text-transform: uppercase; color: #6b7280 !important; }

.main .block-container { background: #0b0f1a; padding-top: 24px; max-width: 1200px; }
body { background-color: #0b0f1a; }

.section-title { 
    font-family: 'IBM Plex Sans', sans-serif; 
    font-weight: 600;
    font-size: 11px; 
    letter-spacing: 3px; 
    text-transform: uppercase; 
    color: #4b5563; 
    margin: 28px 0 10px; 
    border-bottom: 1px solid #1f2937; 
    padding-bottom: 6px; 
}

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

@media (max-width: 768px) {
  .main .block-container { padding-top: 24px !important; padding-left: 16px !important; padding-right: 16px !important; }
  header[data-testid="stHeader"] { display: block !important; }
  [data-testid="stToolbar"] { display: block !important; }
  [data-testid="collapsedControl"] { display: inline-flex !important; }
}

.stDownloadButton button { background: #00e5a0 !important; color: #000 !important; font-family: 'IBM Plex Sans', sans-serif !important; font-size: 11px !important; font-weight: 600 !important; letter-spacing: 1px !important; border: none !important; border-radius: 4px !important; }
.stButton button { background: #1a5276 !important; color: #fff !important; font-family: 'IBM Plex Sans', sans-serif !important; font-size: 12px !important; letter-spacing: 1px !important; border: 1px solid #2471a3 !important; border-radius: 4px !important; width: 100%; padding: 10px !important; }
</style>
""", unsafe_allow_html=True)

# ── LOGIC FUNCTIONS ───────────────────────────────────────

@st.cache_data(show_spinner=False, ttl=86400)
def load_nse_stocks():
    headers = {"User-Agent": "Mozilla/5.0"}
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
        df["LABEL"] = df["NAME OF COMPANY"].str.strip() + " (" + df["SYMBOL"].str.strip() + " · NSE)"
        return df[["TICKER", "LABEL"]].sort_values("LABEL").reset_index(drop=True)
    except Exception:
        return _nse_fallback()

def _nse_fallback():
    stocks = [("^NSEI","Nifty 50 Index (^NSEI)"), ("RELIANCE.NS","Reliance (RELIANCE · NSE)"), ("HDFCBANK.NS","HDFC Bank (HDFCBANK · NSE)")]
    return pd.DataFrame(stocks, columns=["TICKER", "LABEL"])

@st.cache_data(show_spinner=False, ttl=86400)
def load_bse_stocks():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w?Group=&Scripcode=&industry=&segment=Equity&status=Active"
        resp = requests.get(url, headers=headers, timeout=15)
        rows = resp.json().get("Table", [])
        df = pd.DataFrame(rows)[["SCRIP_CD", "Scrip_Name"]].dropna()
        df["TICKER"] = df["SCRIP_CD"].astype(str).str.strip() + ".BO"
        df["LABEL"] = df["Scrip_Name"].str.strip() + " (" + df["SCRIP_CD"].astype(str).str.strip() + " · BSE)"
        return df[["TICKER", "LABEL"]].sort_values("LABEL").reset_index(drop=True)
    except Exception: return None

@st.cache_data(show_spinner=False, ttl=300)
def get_data(ticker, start, end, ma_short, ma_long):
    df = yf.download(ticker, start=str(start), end=str(end), auto_adjust=True, progress=False)
    if df.empty: return None
    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.reset_index(inplace=True)
    df[f"MA_{ma_short}"] = df["Close"].rolling(ma_short).mean().round(2)
    df[f"MA_{ma_long}"] = df["Close"].rolling(ma_long).mean().round(2)
    df["Daily_Return_%"] = (df["Close"].pct_change() * 100).round(4)
    df["Volatility_20d"] = df["Daily_Return_%"].rolling(20).std().round(4)
    df["Cumulative_%"] = ((df["Close"] / df["Close"].iloc[0] - 1) * 100).round(2)
    df.dropna(subset=[f"MA_{ma_long}"], inplace=True)
    return df

NIFTY50 = ["RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS","TRENT.NS","ZOMATO.NS"]

@st.cache_data(show_spinner=False, ttl=900)
def get_movers():
    try:
        records = []
        raw = yf.download(NIFTY50, period="2d", auto_adjust=True, progress=False)
        for ticker in NIFTY50:
            try:
                closes = raw["Close"][ticker].dropna()
                prev_close, curr_close = float(closes.iloc[-2]), float(closes.iloc[-1])
                records.append({"ticker": ticker, "name": ticker.replace(".NS", ""), "close": curr_close, "pct": (curr_close - prev_close) / prev_close * 100})
            except: continue
        df = pd.DataFrame(records)
        return df.loc[df["pct"].idxmax()].to_dict(), df.loc[df["pct"].idxmin()].to_dict()
    except: return None, None

@st.cache_data(show_spinner=False, ttl=3600)
def get_nim_context(ticker, pct, direction):
    api_key = os.environ.get("NVIDIA_API_KEY", "")
    if not api_key: return "⚠️ API Key missing."
    
    prompt = f"Analyst role: {ticker} moved {pct:+.2f}% today in India. 2 sentences why. No disclaimers."
    try:
        resp = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": "meta/llama-3.1-70b-instruct", "messages": [{"role": "user", "content": prompt}], "max_tokens": 100, "temperature": 0.4},
            timeout=30 # INCREASED TIMEOUT TO FIX ERROR
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except requests.exceptions.Timeout:
        return "⚡ NVIDIA servers are taking too long to respond. The move was likely driven by high intraday volume or sectoral sentiment."
    except: return "AI insight currently unavailable."

PLOT_LAYOUT = dict(
    paper_bgcolor="#0b0f1a", plot_bgcolor="#0b0f1a",
    font=dict(family="IBM Plex Sans, sans-serif", color="#9ca3af", size=11),
    xaxis=dict(gridcolor="#1f2937", showgrid=True), yaxis=dict(gridcolor="#1f2937", showgrid=True),
    margin=dict(l=12, r=12, t=40, b=12), hovermode="x unified",
)

# ── Sidebar ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🇮🇳 Indian Stock Dashboard")
    st.markdown("---")
    nse_stocks, bse_stocks = load_nse_stocks(), load_bse_stocks()
    all_stocks = pd.concat([s for s in [nse_stocks, bse_stocks] if s is not None]).sort_values("LABEL").reset_index(drop=True)

    labels = ["— Select Company —"] + all_stocks["LABEL"].tolist()
    selected = st.selectbox("Stock", labels, label_visibility="collapsed")
    auto_ticker = all_stocks.loc[all_stocks["LABEL"] == selected, "TICKER"].values[0] if selected != "— Select Company —" else ""

    manual = st.text_input("Custom Ticker", placeholder="e.g. RELIANCE.NS").strip().upper()
    ticker_input = manual if "." in manual or manual.startswith("^") else auto_ticker

    range_opt = st.radio("Range", ["1 Year", "2 Years", "5 Years"])
    ma1, ma2 = st.slider("Short MA", 5, 50, 20), st.slider("Long MA", 20, 200, 50)
    fetch_btn = st.button("📡 Fetch & Analyse")

# ── Header ─────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:8px;display:flex;align-items:flex-start;justify-content:space-between;">
  <div>
    <span style="font-family:'IBM Plex Sans',sans-serif;font-size:2rem;font-weight:700;color:#e2e8f0;letter-spacing:-1px;">
      Stock Market <span style="color:#00e5a0;">Analyser</span>
    </span><br>
    <span style="font-size:11px;color:#4b5563;letter-spacing:2px;text-transform:uppercase;">NSE · BSE · Real-time via Yahoo Finance</span>
  </div>
</div>
""", unsafe_allow_html=True)
st.markdown("---")

# ── STOP AUTO-OPENING ──────────────────────────────────────
if not fetch_btn:
    st.markdown("""
    <div style="text-align:center;padding:120px 20px">
        <div style="font-size:48px;margin-bottom:16px">📊</div>
        <div style="font-family:'IBM Plex Sans',sans-serif;font-size:1.1rem;font-weight:600;color:#6b7280;letter-spacing:1px">SELECT A STOCK AND CLICK FETCH</div>
        <div style="font-size:12px;color:#374151;margin-top:8px">Your analysis will appear here. No data is loaded until requested.</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── ANALYSIS VIEW (ONLY AFTER FETCH) ───────────────────────
st.markdown('<p class="section-title">Today\'s Market Movers — Nifty 50</p>', unsafe_allow_html=True)
with st.spinner("Fetching Market Movers..."):
    gainer, loser = get_movers()

if gainer and loser:
    # ADDED gap="large" FOR PROFESSIONAL SPACING
    mg, ml = st.columns(2, gap="large") 
    with mg:
        nim_up = get_nim_context(gainer["ticker"], gainer["pct"], "up")
        st.markdown(f"""<div style="background:#0d1f12;border:1px solid #1a3a20;border-left:4px solid #00e5a0;border-radius:8px;padding:20px 22px;height:100%"><div style="font-size:10px;text-transform:uppercase;color:#4b5563;margin-bottom:8px">🟢 Top Gainer</div><div style="font-size:1.4rem;font-weight:700;color:#00e5a0;line-height:1">{gainer['name']}</div><div style="font-size:1.1rem;font-weight:700;color:#e2e8f0;margin:4px 0 2px">₹{gainer['close']:.2f}<span style="color:#00e5a0;font-size:0.95rem">&nbsp;{gainer['pct']:+.2f}%</span></div><div style="margin-top:12px;padding-top:12px;border-top:1px solid #1a3a20;font-size:0.83rem;color:#6b7280;line-height:1.7"><span style="color:#4b5563;font-size:10px;text-transform:uppercase">🤖 NIM Analysis</span><br>{nim_up}</div></div>""", unsafe_allow_html=True)
    with ml:
        nim_dn = get_nim_context(loser["ticker"], loser["pct"], "down")
        st.markdown(f"""<div style="background:#1f0d0d;border:1px solid #3a1a1a;border-left:4px solid #f87171;border-radius:8px;padding:20px 22px;height:100%"><div style="font-size:10px;text-transform:uppercase;color:#4b5563;margin-bottom:8px">🔴 Top Loser</div><div style="font-size:1.4rem;font-weight:700;color:#f87171;line-height:1">{loser['name']}</div><div style="font-size:1.1rem;font-weight:700;color:#e2e8f0;margin:4px 0 2px">₹{loser['close']:.2f}<span style="color:#f87171;font-size:0.95rem">&nbsp;{loser['pct']:+.2f}%</span></div><div style="margin-top:12px;padding-top:12px;border-top:1px solid #3a1a1a;font-size:0.83rem;color:#6b7280;line-height:1.7"><span style="color:#4b5563;font-size:10px;text-transform:uppercase">🤖 NIM Analysis</span><br>{nim_dn}</div></div>""", unsafe_allow_html=True)

st.markdown("---")
with st.spinner(f"Analysing {ticker_input}..."):
    start_date = datetime.today() - timedelta(days=365) # Logic for 1yr default
    df = get_data(ticker_input, start_date, datetime.today(), ma1, ma2)

if df is not None:
    latest = df.iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Close", f"₹{latest['Close']:.2f}")
    c2.metric("Return", f"{((latest['Close']/df.iloc[0]['Close'])-1)*100:+.2f}%")
    c3.metric(f"MA {ma1}", f"₹{latest[f'MA_{ma1}']:.2f}")
    c4.metric("Volatility", f"{latest['Volatility_20d']:.2f}%")

    fig = go.Figure(data=[go.Candlestick(x=df['Date'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.update_layout(**PLOT_LAYOUT, title=f"{ticker_input} Price Action")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.error("Data not found. Use .NS for NSE (e.g. TCS.NS) or .BO for BSE.")
