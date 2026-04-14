import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import io

# ─── Page config ────────────────────────────────────────────
st.set_page_config(
    page_title="Indian Stock Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;800&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'JetBrains Mono', monospace; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0e1117;
    border-right: 1px solid #1f2937;
}
section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stTextInput label,
section[data-testid="stSidebar"] .stSlider label {
    font-size: 11px !important;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #6b7280 !important;
}

/* Metric cards */
[data-testid="stMetric"] {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 6px;
    padding: 14px 18px;
}
[data-testid="stMetricLabel"] { font-size: 10px !important; letter-spacing: 1.5px; text-transform: uppercase; color: #6b7280 !important; }
[data-testid="stMetricValue"] { font-family: 'Syne', sans-serif !important; font-size: 1.6rem !important; font-weight: 800 !important; }

/* Main bg */
.main .block-container { background: #0b0f1a; padding-top: 24px; max-width: 1200px; }
body { background-color: #0b0f1a; }

/* Section headers */
.section-title {
    font-family: 'Syne', sans-serif;
    font-size: 11px;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: #4b5563;
    margin: 28px 0 10px;
    border-bottom: 1px solid #1f2937;
    padding-bottom: 6px;
}

/* Download button */
.stDownloadButton button {
    background: #00e5a0 !important;
    color: #000 !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 1px !important;
    border: none !important;
    border-radius: 4px !important;
}
.stDownloadButton button:hover { opacity: 0.85 !important; }

/* Fetch button */
.stButton button {
    background: #1a5276 !important;
    color: #fff !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 12px !important;
    letter-spacing: 1px !important;
    border: 1px solid #2471a3 !important;
    border-radius: 4px !important;
    width: 100%;
    padding: 10px !important;
}
.stButton button:hover { background: #2471a3 !important; }
</style>
""", unsafe_allow_html=True)

# ─── Sidebar ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🇮🇳 Indian Stock Dashboard")
    st.markdown("---")

    # Popular NSE stocks quick-pick
    POPULAR = {
        "— Type manually —": "",
        "Reliance Industries": "RELIANCE.NS",
        "TCS": "TCS.NS",
        "Infosys": "INFY.NS",
        "HDFC Bank": "HDFCBANK.NS",
        "ICICI Bank": "ICICIBANK.NS",
        "SBI": "SBIN.NS",
        "Wipro": "WIPRO.NS",
        "Bajaj Finance": "BAJFINANCE.NS",
        "Adani Enterprises": "ADANIENT.NS",
        "HUL": "HINDUNILVR.NS",
        "Nifty 50 Index": "^NSEI",
        "BSE Sensex": "^BSESN",
    }

    st.markdown('<p class="section-title">Quick Pick</p>', unsafe_allow_html=True)
    preset = st.selectbox("Popular Stocks", list(POPULAR.keys()), label_visibility="collapsed")

    st.markdown('<p class="section-title">Or Type a Ticker</p>', unsafe_allow_html=True)
    manual = st.text_input(
        "Ticker",
        value=POPULAR[preset] if POPULAR[preset] else "",
        placeholder="e.g. RELIANCE.NS",
        label_visibility="collapsed",
    )

    ticker_input = manual.strip().upper()

    st.markdown('<p class="section-title">Date Range</p>', unsafe_allow_html=True)
    range_opt = st.radio(
        "Range",
        ["1 Year", "2 Years", "5 Years", "Custom"],
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

    fetch_btn = st.button("📡 Fetch & Analyse")

# ─── Main header ────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:8px">
  <span style="font-family:'Syne',sans-serif;font-size:2rem;font-weight:800;color:#e2e8f0;letter-spacing:-1px;">
    Stock Market <span style="color:#00e5a0;">Analyser</span>
  </span><br>
  <span style="font-size:11px;color:#4b5563;letter-spacing:2px;text-transform:uppercase;">
    NSE · BSE · Real-time via Yahoo Finance
  </span>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# ─── Helper: download + compute ─────────────────────────────
@st.cache_data(show_spinner=False)
def get_data(ticker, start, end, ma_short, ma_long):
    df = yf.download(ticker, start=str(start), end=str(end), auto_adjust=True, progress=False)
    if df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.reset_index(inplace=True)
    df[f"MA_{ma_short}"] = df["Close"].rolling(ma_short).mean().round(2)
    df[f"MA_{ma_long}"]  = df["Close"].rolling(ma_long).mean().round(2)
    df["Daily_Return_%"] = (df["Close"].pct_change() * 100).round(4)
    df["Volatility_20d"] = df["Daily_Return_%"].rolling(20).std().round(4)
    df["Cumulative_%"]   = ((df["Close"] / df["Close"].iloc[0] - 1) * 100).round(2)
    df.dropna(subset=[f"MA_{ma_long}"], inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

# ─── Chart builders ─────────────────────────────────────────
PLOT_LAYOUT = dict(
    paper_bgcolor="#0b0f1a",
    plot_bgcolor="#0b0f1a",
    font=dict(family="JetBrains Mono, monospace", color="#9ca3af", size=11),
    xaxis=dict(gridcolor="#1f2937", showgrid=True, zeroline=False),
    yaxis=dict(gridcolor="#1f2937", showgrid=True, zeroline=False),
    margin=dict(l=12, r=12, t=40, b=12),
    legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", yanchor="bottom", y=1.02),
)

def chart_ma(df, ma1, ma2, ticker):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Close"],
        name="Close", line=dict(color="#e2e8f0", width=1.5)))
    fig.add_trace(go.Scatter(x=df["Date"], y=df[f"MA_{ma1}"],
        name=f"MA {ma1}d", line=dict(color="#00e5a0", width=1.5, dash="dot")))
    fig.add_trace(go.Scatter(x=df["Date"], y=df[f"MA_{ma2}"],
        name=f"MA {ma2}d", line=dict(color="#3b82f6", width=1.5, dash="dot")))
    fig.update_layout(**PLOT_LAYOUT, title=dict(text=f"Price & Moving Averages — {ticker}", font=dict(size=13, color="#e2e8f0")), hovermode="x unified")
    return fig

def chart_volatility(df, ticker):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Volatility_20d"],
        name="20d Volatility", fill="tozeroy",
        line=dict(color="#f59e0b", width=1.5),
        fillcolor="rgba(245,158,11,0.1)"))
    fig.update_layout(**PLOT_LAYOUT, title=dict(text=f"20-Day Rolling Volatility — {ticker}", font=dict(size=13, color="#e2e8f0")))
    return fig

def chart_returns(df, ticker):
    colors = ["#00e5a0" if v >= 0 else "#f87171" for v in df["Daily_Return_%"]]
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["Date"], y=df["Daily_Return_%"],
        name="Daily Return %", marker_color=colors))
    fig.add_hline(y=0, line_color="#4b5563", line_width=1)
    fig.update_layout(**PLOT_LAYOUT, title=dict(text=f"Daily Returns (%) — {ticker}", font=dict(size=13, color="#e2e8f0")))
    return fig

def chart_cumulative(df, ticker):
    color = "#00e5a0" if df["Cumulative_%"].iloc[-1] >= 0 else "#f87171"
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Date"], y=df["Cumulative_%"],
        name="Cumulative Return", fill="tozeroy",
        line=dict(color=color, width=2),
        fillcolor=f"rgba({'0,229,160' if color=='#00e5a0' else '248,113,113'},0.08)"))
    fig.add_hline(y=0, line_color="#4b5563", line_width=1)
    fig.update_layout(**PLOT_LAYOUT, title=dict(text=f"Cumulative Return (%) — {ticker}", font=dict(size=13, color="#e2e8f0")))
    return fig

# ─── Main logic ─────────────────────────────────────────────
if not fetch_btn:
    st.markdown("""
    <div style="text-align:center;padding:80px 20px;color:#374151">
      <div style="font-size:48px;margin-bottom:16px">📊</div>
      <div style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700;color:#6b7280;letter-spacing:1px">
        SELECT A STOCK AND CLICK FETCH
      </div>
      <div style="font-size:12px;color:#374151;margin-top:8px">
        Pick from the sidebar quick-list or type any NSE/BSE ticker
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

if not ticker_input:
    st.error("⚠️ Please enter a stock ticker in the sidebar.")
    st.stop()
# Auto-collapse sidebar after fetch
st.markdown("""
    <script>
        var btn = window.parent.document.querySelector(
            '[data-testid="baseButton-headerNoPadding"]'
        );
        if (btn) btn.click();
    </script>
""", unsafe_allow_html=True)
# ── Fetch
with st.spinner(f"Fetching {ticker_input} from Yahoo Finance..."):
    df = get_data(ticker_input, start_date, end_date, ma1, ma2)

if df is None or df.empty:
    st.error(f"❌ No data found for **{ticker_input}**. Check the ticker — NSE stocks need `.NS` (e.g. `RELIANCE.NS`), BSE use `.BO`.")
    st.stop()

# ── Metrics row
latest   = df.iloc[-1]
first    = df.iloc[0]
total_ret = ((latest["Close"] - first["Close"]) / first["Close"] * 100)
avg_vol   = df["Volatility_20d"].mean()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Latest Close",   f"₹{latest['Close']:.2f}")
c2.metric("Total Return",   f"{total_ret:+.2f}%",   delta=f"{total_ret:+.2f}%")
c3.metric(f"MA {ma1}d",     f"₹{latest[f'MA_{ma1}']:.2f}")
c4.metric(f"MA {ma2}d",     f"₹{latest[f'MA_{ma2}']:.2f}")
c5.metric("Avg Volatility", f"{avg_vol:.2f}%")

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

# ── Charts
st.plotly_chart(chart_ma(df, ma1, ma2, ticker_input),        use_container_width=True)

col_l, col_r = st.columns(2)
with col_l:
    st.plotly_chart(chart_volatility(df, ticker_input),       use_container_width=True)
with col_r:
    st.plotly_chart(chart_cumulative(df, ticker_input),       use_container_width=True)

st.plotly_chart(chart_returns(df, ticker_input),              use_container_width=True)

# ── Raw data + download
with st.expander("📋 View Raw Data Table"):
    st.dataframe(df.style.format({
        "Close": "₹{:.2f}", f"MA_{ma1}": "₹{:.2f}", f"MA_{ma2}": "₹{:.2f}",
        "Daily_Return_%": "{:.3f}%", "Volatility_20d": "{:.3f}",
        "Cumulative_%": "{:.2f}%",
    }), use_container_width=True)

    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    st.download_button(
        label="⬇ Download as Excel",
        data=buffer.getvalue(),
        file_name=f"{ticker_input.replace('.','_')}_data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.markdown("---")
st.markdown(
    "<div style='font-size:10px;color:#374151;text-align:center;letter-spacing:1px'>"
    "DATA VIA YAHOO FINANCE · NSE CLOSES 3:30 PM IST · RUN AFTER 4 PM FOR LATEST CLOSE"
    "</div>", unsafe_allow_html=True
)
