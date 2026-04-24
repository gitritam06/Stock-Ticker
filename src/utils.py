"""
src/utils.py
------------
Separation of Concerns: owns all data-fetching resilience logic.
app.py calls get_data_with_fallback() and never needs to know the
retry/fallback mechanics.

Why this matters:
    yfinance is a third-party scraper of Yahoo Finance. It is not an
    official API and can fail due to rate limits, Yahoo infrastructure
    changes, or transient network errors. A bare yf.download() call
    crashing the whole Streamlit app is a poor user experience.
    This module provides a single robust wrapper that:
        1. Attempts the live download
        2. On failure, serves the last known-good result from session_state
        3. Shows a non-blocking warning rather than an exception traceback
"""

import streamlit as st
import yfinance as yf
import pandas as pd
from typing import Optional
# Session state key prefix for caching last successful fetches
_CACHE_KEY_PREFIX = "_utils_last_fetch_"
def get_data_with_fallback(
    ticker: str,
    period: Optional[str] = None,
    interval: str = "1d",
    start: Optional[str] = None,
    end: Optional[str] = None,
    group_by: Optional[str] = None,
    auto_adjust: bool = True,
    threads: bool = True,
    **kwargs,
) -> Optional[pd.DataFrame]:
  """
    Attempt to download data from Yahoo Finance. On failure, return the
    last successful result from st.session_state with a user-friendly warning.

    Args:
        ticker:       Single ticker string (e.g. "RELIANCE.NS") or a list of
                      tickers for bulk download (used by get_movers).
        period:       yfinance period string e.g. "5d", "1mo", "1y".
                      Mutually exclusive with start/end.
        interval:     yfinance interval string e.g. "1d", "1h". Default "1d".
        start:        Start date string "YYYY-MM-DD". Used instead of period.
        end:          End date string "YYYY-MM-DD". Used instead of period.
        group_by:     Passed to yf.download for multi-ticker downloads ("ticker").
        auto_adjust:  Adjust OHLC for splits/dividends. Default True.
        threads:      Use threading for multi-ticker downloads. Default True.
        **kwargs:     Any additional keyword arguments forwarded to yf.download.

    Returns:
        pd.DataFrame on success or from cache.
        None if both live fetch and cache are unavailable.
"""
    # Build a deterministic cache key from all parameters that affect the result
    ticker_key = ticker if isinstance(ticker, str) else "_".join(sorted(ticker))
    cache_key = (
        f"{_CACHE_KEY_PREFIX}"
        f"{ticker_key}_{period}_{interval}_{start}_{end}"
    )

    # Build the yf.download kwargs dict
    dl_kwargs = dict(
        auto_adjust=auto_adjust,
        progress=False,
        threads=threads,
        **kwargs,
    )
    if period:
        dl_kwargs["period"] = period
        dl_kwargs["interval"] = interval
    if start:
        dl_kwargs["start"] = start
    if end:
        dl_kwargs["end"] = end
    if group_by:
        dl_kwargs["group_by"] = group_by

    # Attempt live fetch
    try:
        df = yf.download(ticker, **dl_kwargs)

        if df is None or (hasattr(df, "empty") and df.empty):
            raise ValueError("yfinance returned an empty DataFrame.")

        # Success — persist to session_state for future fallback use
        st.session_state[cache_key] = df
        return df

    except Exception as live_error:
        # Live fetch failed — try the session_state cache
        cached = st.session_state.get(cache_key)

        if cached is not None:
            st.warning(
                f"Could not fetch fresh data for **{ticker}** "
                f"({type(live_error).__name__}: {live_error}). "
                f"Showing the last successfully loaded data instead. "
                f"Please refresh or try again shortly.",
                icon="⚠️",
            )
            return cached

        # No cache available either — surface a clear, non-technical message
        st.warning(
            f"Data for **{ticker}** is currently unavailable "
            f"({type(live_error).__name__}). "
            f"This may be due to a Yahoo Finance rate limit or a network issue. "
            f"Please wait a moment and try again.",
            icon="⚠️",
  )
        return None
