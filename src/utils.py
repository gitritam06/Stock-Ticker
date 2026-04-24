import os
import yfinance as yf
from openai import OpenAI
from groq import Groq


# ---------------------------------------------------------------------------
# AI Client Initialization
# ---------------------------------------------------------------------------

# NVIDIA NIM client – powers the ArthBot chat assistant.
nim_client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get("NVIDIA_API_KEY"),
)

# Groq client – powers the Nifty Movers analysis for fast, low-latency results.
groq_client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)


# ---------------------------------------------------------------------------
# yfinance helper
# ---------------------------------------------------------------------------

def get_data_with_fallback(symbols, **kwargs):
    """
    Wrapper around yfinance download with a conservative fallback pass.
    Keeps refactored app imports stable while preserving prior behavior.
    """
    data = yf.download(symbols, auto_adjust=True, progress=False, threads=True, **kwargs)
    if data is None:
        return data
    if hasattr(data, "empty") and not data.empty:
        return data

    # Fallback pass for transient upstream/download edge cases.
    return yf.download(symbols, progress=False, threads=True, **kwargs)


# ---------------------------------------------------------------------------
# ArthBot Chat  (NVIDIA NIM  –  meta/llama3-70b-instruct)
# ---------------------------------------------------------------------------

def get_chat_response(prompt, history):
    """
    Generate a chat response for ArthBot using the NVIDIA NIM endpoint.

    Parameters
    ----------
    prompt : str
        The latest user message.
    history : list[dict]
        Conversation history as a list of {"role": ..., "content": ...} dicts.

    Returns
    -------
    str
        The assistant's reply, or a friendly error message on failure.
    """
    try:
        messages = list(history) + [{"role": "user", "content": prompt}]
        response = nim_client.chat.completions.create(
            model="meta/llama3-70b-instruct",
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[ArthBot] NIM API error: {e}")
        return (
            "I'm sorry, I'm having trouble connecting right now. "
            "Please try again in a moment."
        )


# ---------------------------------------------------------------------------
# Nifty Movers Analysis  (Groq  –  llama3-70b-8192)
# ---------------------------------------------------------------------------

def get_mover_analysis(ticker, price, change):
    """
    Return a concise AI-generated analysis for a Nifty mover stock.

    Uses Groq for fast, low-latency inference.

    Parameters
    ----------
    ticker : str
        NSE/BSE ticker symbol (e.g. "RELIANCE.NS").
    price : float | str
        Current trading price.
    change : float | str
        Percentage change for the session.

    Returns
    -------
    str
        A short analysis paragraph, or a fallback string on failure.
    """
    try:
        prompt = (
            f"Give a brief 2-3 sentence analysis for the Indian stock {ticker} "
            f"which is currently trading at ₹{price} with a change of {change}%. "
            f"Focus on possible reasons for the move and short-term outlook."
        )
        response = groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=256,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[MoverAnalysis] Groq API error: {e}")
        return "Analysis unavailable."
