import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import io
from datetime import datetime, timedelta

st.set_page_config(
    page_title="AlgoMetrics — Indian Stock Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
html, body, [class*="css"] { font-family: 'JetBrains Mono', monospace; }
section[data-testid="stSidebar"] { background: #0e1117; border-right: 1px solid #1f2937; }
section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stMetric"] { background: #111827; border: 1px solid #1f2937; border-radius: 6px; padding: 14px 18px; }
[data-testid="stMetricLabel"] { font-size: 10px !important; letter-spacing: 1.5px; text-transform: uppercase; color: #6b7280 !important; }
[data-testid="stMetricValue"] { font-family: 'Syne', sans-serif !important; font-size: 1.6rem !important; font-weight: 800 !important; }
.main .block-container { background: #0b0f1a; padding-top: 24px; max-width: 1200px; }
body { background-color: #0b0f1a; }
.section-title { font-family: 'Syne', sans-serif; font-size: 11px; letter-spacing: 3px; text-transform: uppercase; color: #4b5563; margin: 28px 0 10px; border-bottom: 1px solid #1f2937; padding-bottom: 6px; }
footer { visibility: hidden; }
#MainMenu { visibility: hidden; }
[data-testid="stToolbar"] { display: none !important; }
[data-testid="stDecoration"] { display: none !important; }
[data-testid="stStatusWidget"] { display: none !important; }
.stDeployButton { display: none !important; }
#stDecoration { display: none !important; }
.stDownloadButton button { background: #00e5a0 !important; color: #000 !important; font-family: 'JetBrains Mono', monospace !important; font-size: 11px !important; font-weight: 600 !important; letter-spacing: 1px !important; border: none !important; border-radius: 4px !important; }
.stButton button { background: #1a5276 !important; color: #fff !important; font-family: 'JetBrains Mono', monospace !important; font-size: 12px !important; letter-spacing: 1px !important; border: 1px solid #2471a3 !important; border-radius: 4px !important; width: 100%; padding: 10px !important; }
.stButton button:hover { background: #2471a3 !important; }
</style>
""", unsafe_allow_html=True)


@st.cache_data(show_spinner=False, ttl=86400)
def load_nse_stocks():
    url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    try:
        df = pd.read_csv(url)
        df = df[["SYMBOL", "NAME OF COMPANY"]].dropna()
        df["TICKER"] = df["SYMBOL"].str.strip() + ".NS"
        df["LABEL"] = df["NAME OF COMPANY"].str.strip() + " (" + df["SYMBOL"].str.strip() + ")"
        return df.sort_values("LABEL").reset_index(drop=True)
    except Exception:
        return None


@st.cache_data(show_spinner=False, ttl=300)
def get_data(ticker, start, end, ma_short, ma_long):
    df = yf.download(ticker, start=str(start), end=str(end), auto_adjust=True, progress=False, threads=True)
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
    fig.update_layout(
        **PLOT_LAYOUT,
        title=dict(text=f"Candlestick & Moving Averages — {ticker}", font=dict(size=13, color="#e2e8f0")),
        xaxis_rangeslider_visible=False,
    )
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


# ── Sidebar ────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🇮🇳 Indian Stock Dashboard")
    st.markdown("---")
    nse_stocks = load_nse_stocks()
    if nse_stocks is not None:
        st.markdown('<p class="section-title">Search by Company Name</p>', unsafe_allow_html=True)
        labels = ["— Type or select a company —"] + nse_stocks["LABEL"].tolist()
        selected = st.selectbox("Stock", labels, label_visibility="collapsed")
        auto_ticker = nse_stocks.loc[nse_stocks["LABEL"] == selected, "TICKER"].values[0] if selected != "— Type or select a company —" else ""
    else:
        auto_ticker = ""

    recommended_ticker = ""
    with st.expander("Custom ticker or company name", expanded=(auto_ticker == "")):
        st.markdown('<p class="section-title" style="margin-top:4px">Type a name or ticker</p>', unsafe_allow_html=True)
        manual = st.text_input(
            "Search",
            value="",
            placeholder="e.g. Infosys / RELIANCE.BO / ^NSEI",
            label_visibility="collapsed",
        )
        manual_clean = manual.strip()
        if manual_clean:
            looks_like_ticker = "." in manual_clean or manual_clean.startswith("^")
            if not looks_like_ticker and nse_stocks is not None:
                query = manual_clean.lower()
                mask = nse_stocks["LABEL"].str.lower().str.contains(query, regex=False)
                matches = nse_stocks[mask].head(6)
                if not matches.empty:
                    st.markdown('<p class="section-title" style="margin-top:10px">Recommendations</p>', unsafe_allow_html=True)
                    rec_options = ["— Select a match —"] + matches["LABEL"].tolist()
                    rec_choice = st.selectbox("Matches", rec_options, label_visibility="collapsed")
                    if rec_choice != "— Select a match —":
                        recommended_ticker = nse_stocks.loc[nse_stocks["LABEL"] == rec_choice, "TICKER"].values[0]
                else:
                    st.caption("No companies matched — try a direct ticker like INFY.NS")

    # Resolution priority: direct ticker > recommendation > dropdown
    manual_upper = manual.strip().upper()
    looks_like_ticker = "." in manual_upper or manual_upper.startswith("^")
    ticker_input = manual_upper if looks_like_ticker else (recommended_ticker if recommended_ticker else auto_ticker)

    st.markdown('<p class="section-title">Date Range</p>', unsafe_allow_html=True)
    range_opt = st.radio("Range", ["1 Year", "2 Years", "5 Years", "Custom"], label_visibility="collapsed")
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


# ── Header ─────────────────────────────────────────────────
st.markdown("""
<div style="margin-bottom:8px">
  <span style="font-family:'Syne',sans-serif;font-size:2rem;font-weight:800;color:#e2e8f0;letter-spacing:-1px;">
    Stock Market <span style="color:#00e5a0;">Analyser</span>
  </span><br>
  <span style="font-size:11px;color:#4b5563;letter-spacing:2px;text-transform:uppercase;">NSE · BSE · Real-time via Yahoo Finance</span>
</div>
""", unsafe_allow_html=True)
st.markdown("---")

if not fetch_btn:
    st.markdown("""
    <div style="text-align:center;padding:80px 20px">
        <div style="font-size:48px;margin-bottom:16px">📊</div>
        <div style="font-family:'Syne',sans-serif;font-size:1.1rem;font-weight:700;color:#6b7280;letter-spacing:1px">SELECT A STOCK AND CLICK FETCH</div>
        <div style="font-size:12px;color:#374151;margin-top:8px">Pick from the sidebar dropdown or type any NSE / BSE ticker</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

if not ticker_input:
    st.markdown("""
    <div style="background:#111827;border:1px solid #1f2937;border-left:3px solid #f59e0b;border-radius:6px;padding:20px 24px;margin-top:20px">
        <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:1rem;color:#f59e0b;margin-bottom:6px">No Stock Selected</div>
        <div style="font-size:0.88rem;color:#6b7280">Please select a stock from the dropdown or type a ticker in the sidebar.</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

st.markdown("""
    <script>
    (function() {
        /* Selectors Streamlit has used across versions for the sidebar collapse button */
        var SELECTORS = [
            '[data-testid="baseButton-headerNoPadding"]',
            '[data-testid="collapsedControl"]',
            'button[aria-label="Close sidebar"]',
            'button[aria-label="Collapse sidebar"]',
            'section[data-testid="stSidebar"] button[kind="header"]',
        ];

        var attempts = 0;
        var maxAttempts = 30;   /* 30 × 100 ms = 3 s max */

        var timer = setInterval(function() {
            attempts++;
            for (var i = 0; i < SELECTORS.length; i++) {
                var btn = window.parent.document.querySelector(SELECTORS[i]);
                if (btn) {
                    btn.click();
                    clearInterval(timer);
                    return;
                }
            }
            if (attempts >= maxAttempts) clearInterval(timer);
        }, 100);
    })();
    </script>
""", unsafe_allow_html=True)

with st.spinner(f"Fetching {ticker_input} from Yahoo Finance..."):
    df = get_data(ticker_input, start_date, end_date, ma1, ma2)

if df is None or df.empty:
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
    st.stop()

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

# ── Snapshot metrics ───────────────────────────────────────
_price_now   = float(latest["Close"])
_price_delta = float(latest["Daily_Return_%"])
_week52_high = float(df["High"].iloc[-min(252, len(df)):].max())
_avg_volume  = float(df["Volume"].mean())

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

with st.expander("📋 View Raw Data Table"):
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

st.markdown("---")
st.markdown("<div style='font-size:10px;color:#374151;text-align:center;letter-spacing:1px'>DATA VIA YAHOO FINANCE · NSE CLOSES 3:30 PM IST · RUN AFTER 4 PM FOR LATEST CLOSE</div>", unsafe_allow_html=True)
