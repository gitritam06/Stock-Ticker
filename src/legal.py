"""
src/legal.py
------------
Separation of Concerns: owns all legal copy.
app.py calls render_legal_section() and never needs to know the text.
To update disclaimers, edit only this file.
"""

import streamlit as st


def render_legal_section() -> None:
    """
    Renders a collapsible Privacy Policy & Terms of Use section.
    Intended to be called once at the absolute bottom of app.py.
    """
    with st.expander("Privacy Policy & Terms of Use"):

        st.markdown(
            """
            <div style="font-size:0.83rem;color:#6b7280;line-height:1.9;">

            <p style="font-family:'Syne',sans-serif;font-size:0.9rem;
            font-weight:700;color:#e2e8f0;margin-bottom:4px;">
            SEBI Disclaimer - Educational Use Only
            </p>
            <p>
            AlgoMetrics is an <strong style="color:#9ca3af;">independent, educational
            research tool</strong> and is not registered with or endorsed by the
            Securities and Exchange Board of India (SEBI). All content, charts,
            indicators, and AI-generated analysis presented on this platform are
            strictly for <strong style="color:#9ca3af;">informational and educational
            purposes only</strong>. Nothing on this platform constitutes investment
            advice, a solicitation to buy or sell any security, or a recommendation
            of any investment strategy. Past performance of any stock is not indicative
            of future results. Users must consult a SEBI-registered investment advisor
            before making any financial decisions.
            </p>

            <p style="font-family:'Syne',sans-serif;font-size:0.9rem;
            font-weight:700;color:#e2e8f0;margin:16px 0 4px;">
            Data Privacy
            </p>
            <p>
            AlgoMetrics does not collect, store, or sell any personally identifiable
            information. Stock searches and ticker queries entered by users are
            processed exclusively through
            <strong style="color:#9ca3af;">Yahoo Finance (via the yfinance library)</strong>
            for market data retrieval. AI-generated commentary is processed via
            <strong style="color:#9ca3af;">NVIDIA NIM (Llama 3.1-70B)</strong> — your
            queries are transmitted to NVIDIA's inference API under their standard
            data processing terms. No conversation history is persisted beyond your
            active browser session. Refreshing or closing the page clears all
            session data permanently.
            </p>

            <p style="font-family:'Syne',sans-serif;font-size:0.9rem;
            font-weight:700;color:#e2e8f0;margin:16px 0 4px;">
            No Liability Clause
            </p>
            <p>
            The creators and operators of AlgoMetrics shall not be held liable for
            any financial losses, missed opportunities, or damages of any kind arising
            directly or indirectly from the use of this platform or reliance on any
            information, analysis, or AI-generated content presented herein. Market
            data sourced from Yahoo Finance may be subject to delays of up to
            15-20 minutes and may contain inaccuracies. All use of this platform
            is entirely at the user's own risk.
            </p>

            <p style="color:#4b5563;font-size:0.78rem;margin-top:16px;">
            Last updated: April 2026. Subject to change without notice.
            </p>

            </div>
            """,
            unsafe_allow_html=True,
        )
