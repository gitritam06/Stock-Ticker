"""
market_indices.py
-----------------
Drop-in module for your Streamlit dashboard.
Provides two functions:
    get_index_data(ticker)       — fetches 1d/5m OHLCV via yfinance
    display_market_indices()     — renders Nifty 50 + Sensex cards with sparklines

Aesthetic: Glassmorphism / Cyberpunk dark theme.
Matches IBM Plex Sans font stack used in the rest of the dashboard.
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go


# =============================================================================
# CONSTANTS
# =============================================================================

INDICES = {
    "Nifty 50":  "^NSEI",
    "Sensex":    "^BSESN",
}

COLOR_POSITIVE = "#00e5a0"   # green — matches dashboard accent
COLOR_NEGATIVE = "#f87171"   # red
COLOR_NEUTRAL  = "#6b7280"   # grey — fallback

# Glassmorphism card CSS injected once
_CARD_CSS = """
<style>
.idx-card {
    background: linear-gradient(
        135deg,
        rgba(255,255,255,0.04) 0%,
        rgba(255,255,255,0.01) 100%
    );
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 20px 22px 14px 22px;
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    box-shadow:
        0 4px 24px rgba(0,0,0,0.4),
        inset 0 1px 0 rgba(255,255,255,0.06);
    margin-bottom: 4px;
}
.idx-label {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 10px;
    letter-spacing: 2.5px;
    text-transform: uppercase;
    color: #4b5563;
    margin-bottom: 6px;
}
.idx-price {
    font-family: 'Syne', sans-serif;
    font-size: 1.75rem;
    font-weight: 800;
    color: #f1f5f9;
    line-height: 1;
    margin-bottom: 4px;
}
.idx-change-pos {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.85rem;
    font-weight: 600;
    color: #00e5a0;
}
.idx-change-neg {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.85rem;
    font-weight: 600;
    color: #f87171;
}
.idx-change-neu {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 0.85rem;
    font-weight: 600;
    color: #6b7280;
}
.idx-timestamp {
    font-family: 'IBM Plex Sans', sans-serif;
    font-size: 10px;
    color: #374151;
    margin-top: 6px;
    letter-spacing: 0.5px;
}
</style>
"""


# =============================================================================
# FUNCTION 1 — DATA FETCHING
# =============================================================================

@st.cache_data(show_spinner=False, ttl=300)   # refresh every 5 minutes
def get_index_data(ticker: str) -> pd.DataFrame:
    """
    Fetch the last 1 trading day of OHLCV data at 5-minute intervals.

    Args:
        ticker: Yahoo Finance ticker string e.g. "^NSEI", "^BSESN"

    Returns:
        pd.DataFrame with columns [Open, High, Low, Close, Volume]
        and a DatetimeIndex. Returns an EMPTY DataFrame on any error.
    """
    try:
        df = yf.download(
            ticker,
            period="1d",
            interval="5m",
            auto_adjust=True,
            progress=False,
        )

        # yfinance sometimes returns multi-level columns for a single ticker
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if df is None or df.empty:
            return pd.DataFrame()

        # Keep only the columns we need, drop any NaN close rows
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.dropna(subset=["Close"], inplace=True)

        return df

    except Exception:
        # Swallow ALL exceptions — caller decides what to show
        return pd.DataFrame()


# =============================================================================
# FUNCTION 2 — SPARKLINE BUILDER (internal helper)
# =============================================================================

def _build_sparkline(df: pd.DataFrame, color: str) -> go.Figure:
    """
    Build a minimal area sparkline from a Close price series.
    No axes, no gridlines, no hover — purely decorative price shape.
    """
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["Close"],
        mode="lines",
        fill="tozeroy",
        line=dict(color=color, width=1.5, shape="spline", smoothing=1.2),
        fillcolor=color.replace(")", ", 0.08)").replace("rgb", "rgba")
                  if color.startswith("rgb")
                  else f"{color}14",   # hex + 14 = ~8% opacity fill
        hoverinfo="skip",
    ))

    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=0, b=0),
        height=60,
        xaxis=dict(
            visible=False,
            showgrid=False,
            zeroline=False,
        ),
        yaxis=dict(
            visible=False,
            showgrid=False,
            zeroline=False,
            # Pad y-range slightly so the line doesn't touch the edges
            range=[
                df["Close"].min() * 0.9995,
                df["Close"].max() * 1.0005,
            ],
        ),
        showlegend=False,
    )

    return fig


# =============================================================================
# FUNCTION 3 — MAIN DISPLAY FUNCTION
# =============================================================================

def display_market_indices() -> None:
    """
    Renders a two-column market indices widget.

    Layout per column:
        [ Glassmorphism card ]
            Label (NIFTY 50 / SENSEX)
            Current price  +  % change badge
            Sparkline (area chart, 5-min candles, last 1 day)
            Last updated timestamp

    Matches the dark IBM Plex Sans / Syne aesthetic of the main dashboard.
    Handles missing data gracefully with st.warning instead of crashing.
    """
    # Inject card CSS once per session
    st.markdown(_CARD_CSS, unsafe_allow_html=True)

    col_left, col_right = st.columns(2, gap="medium")
    columns = [col_left, col_right]

    for col, (name, ticker) in zip(columns, INDICES.items()):
        with col:
            df = get_index_data(ticker)

            # ── Missing data guard ─────────────────────────────────────
            if df.empty:
                st.warning(
                    f"Could not load data for **{name}** ({ticker}). "
                    f"This may be due to market closure or a data provider issue. "
                    f"Please refresh the page.",
                    icon="⚠️",
                )
                continue

            # ── Compute metrics ────────────────────────────────────────
            current_price = float(df["Close"].iloc[-1])
            open_price    = float(df["Open"].iloc[0])
            change_pts    = current_price - open_price
            change_pct    = (change_pts / open_price) * 100

            # Determine color and arrow
            if change_pct > 0:
                color       = COLOR_POSITIVE
                arrow       = "▲"
                change_cls  = "idx-change-pos"
            elif change_pct < 0:
                color       = COLOR_NEGATIVE
                arrow       = "▼"
                change_cls  = "idx-change-neg"
            else:
                color       = COLOR_NEUTRAL
                arrow       = "─"
                change_cls  = "idx-change-neu"

            # Format last timestamp
            last_ts = df.index[-1]
            try:
                ts_str = last_ts.strftime("%d %b %Y, %I:%M %p IST")
            except Exception:
                ts_str = str(last_ts)

            # ── Render glass card ──────────────────────────────────────
            st.markdown(f"""
            <div class="idx-card">
                <div class="idx-label">{name}</div>
                <div class="idx-price">
                    &#8377;{current_price:,.2f}
                </div>
                <span class="{change_cls}">
                    {arrow} {change_pts:+,.2f} &nbsp;({change_pct:+.2f}%)
                </span>
            </div>
            """, unsafe_allow_html=True)

            # ── Sparkline ──────────────────────────────────────────────
            fig = _build_sparkline(df, color)
            st.plotly_chart(
                fig,
                use_container_width=True,
                config={
                    "displayModeBar": False,
                    "staticPlot": True,       # no hover, no zoom — pure visual
                },
            )

            # ── Timestamp ──────────────────────────────────────────────
            st.markdown(
                f"<div class='idx-timestamp'>Last data point: {ts_str}</div>",
                unsafe_allow_html=True,
            )
