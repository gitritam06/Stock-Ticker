"""
src/faq.py
----------
Separation of Concerns: owns all FAQ copy and rendering.
app.py calls render_faq() and never needs to know the questions or answers.
To add/edit FAQs, edit only this file.
"""

import streamlit as st

# ---------------------------------------------------------------------------
# FAQ data — defined as a list of dicts so content is easy to maintain.
# Adding a new FAQ = adding one dict to this list. No UI code changes needed.
# ---------------------------------------------------------------------------
_FAQS = [
    {
        "q": "How does the AI Chatbot work?",
        "a": (
            "The chatbot (ArthBot) is powered by "
            "<strong>NVIDIA NIM</strong>, NVIDIA's cloud inference platform, "
            "running the <strong>Meta Llama 3.1-70B Instruct</strong> large "
            "language model. When you type a question, your message — along with "
            "a system prompt that restricts the model to Indian financial markets — "
            "is sent to NVIDIA's API endpoint "
            "(<code>integrate.api.nvidia.com/v1/chat/completions</code>). "
            "The model generates a response and it is displayed in the chat window. "
            "Full conversation history is maintained in your browser session via "
            "<code>st.session_state</code> so ArthBot remembers context across "
            "turns. No history is stored after you close or refresh the page."
        ),
    },
    {
        "q": "Is this real-time data?",
        "a": (
            "Stock data is sourced from <strong>Yahoo Finance</strong> via the "
            "open-source <code>yfinance</code> library. Yahoo Finance imposes a "
            "<strong>15-20 minute delay</strong> on NSE/BSE price data for "
            "non-premium users. This means the 'latest close' shown on the "
            "dashboard reflects the most recently available delayed quote, not "
            "the live traded price. For intraday trading decisions, always "
            "cross-reference with your broker's live feed. The Market Movers "
            "widget refreshes every 15 minutes and the main stock data is "
            "cached for 5 minutes to reduce redundant API calls."
        ),
    },
    {
        "q": "How are the technical indicators calculated?",
        "a": (
            "All indicators are computed using <strong>Pandas rolling window "
            "functions</strong> on the adjusted closing price series downloaded "
            "from Yahoo Finance:<br><br>"
            "<strong>Simple Moving Average (SMA)</strong> — "
            "<code>df['Close'].rolling(N).mean()</code> — "
            "the arithmetic mean of the last N closing prices, recalculated "
            "each trading day as new data arrives.<br><br>"
            "<strong>20-Day Rolling Volatility</strong> — "
            "<code>df['Daily_Return_%'].rolling(20).std()</code> — "
            "the standard deviation of the last 20 daily percentage returns. "
            "Higher values indicate greater price uncertainty.<br><br>"
            "<strong>Daily Return (%)</strong> — "
            "<code>df['Close'].pct_change() * 100</code> — "
            "the percentage change in closing price from the previous trading day.<br><br>"
            "<strong>Cumulative Return (%)</strong> — "
            "<code>(df['Close'] / df['Close'].iloc[0] - 1) * 100</code> — "
            "the total percentage gain or loss from the first day of the "
            "selected date range to the current day."
        ),
    },
    {
        "q": "What exchanges and asset types are supported?",
        "a": (
            "The dashboard currently supports equities listed on the "
            "<strong>NSE</strong> (National Stock Exchange, suffix <code>.NS</code>) "
            "and <strong>BSE</strong> (Bombay Stock Exchange, suffix <code>.BO</code>). "
            "Major <strong>Nifty/Sensex indices</strong> are also supported using "
            "Yahoo Finance's caret format (e.g. <code>^NSEI</code> for Nifty 50, "
            "<code>^BSESN</code> for Sensex). Mutual funds, derivatives (F&O), "
            "and intraday tick data are not currently supported."
        ),
    },
    {
        "q": "Why does the app sometimes show stale or missing data?",
        "a": (
            "This can occur for three reasons: (1) <strong>Yahoo Finance rate "
            "limiting</strong> — if many requests are made in a short window, "
            "Yahoo Finance may temporarily throttle responses. The app uses "
            "<code>st.session_state</code> caching to serve the last successful "
            "fetch rather than crashing. (2) <strong>Market closure</strong> — "
            "NSE/BSE are closed on weekends and public holidays; no new data is "
            "available on these days. (3) <strong>Ticker format errors</strong> — "
            "ensure NSE tickers end in <code>.NS</code> and BSE tickers use the "
            "numeric scrip code with <code>.BO</code> suffix."
        ),
    },
]


def render_faq() -> None:
    """
    Renders the Technical FAQ section inside a clean st.container.
    Intended to be called near the bottom of app.py, before render_legal_section.
    """
    st.markdown("---")
    st.markdown(
        '<p class="section-title">Frequently Asked Questions</p>',
        unsafe_allow_html=True,
    )

    with st.container():
        for i, item in enumerate(_FAQS):
            with st.expander(item["q"]):
                st.markdown(
                    f"<div style='font-size:0.87rem;color:#9ca3af;"
                    f"line-height:1.85;'>{item['a']}</div>",
                    unsafe_allow_html=True,
                )
            # Small gap between expanders except after the last one
            if i < len(_FAQS) - 1:
                st.markdown(
                    "<div style='height:4px'></div>",
                    unsafe_allow_html=True,
                )
