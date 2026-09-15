import os
import yfinance as yf
from openai import OpenAI
from groq import Groq


def _get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


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

# Updated get_chat_response using Groq
def get_chat_response(prompt, history):
    """
    Generate a chat response for ArthBot using Groq.
    """
    client = _get_groq_client()
    if client is None:
        return "GROQ_API_KEY is not configured. Please set the GROQ_API_KEY environment variable to enable ArthBot."
    try:
        # Prepare messages
        messages = [{"role": "system", "content": "You are a helpful financial assistant."}] + list(history) + [{"role": "user", "content": prompt}]
        
        # Call Groq client
        response = client.chat.completions.create(
            model="llama3-70b-8192", 
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[ArthBot] Groq API error: {e}")
        return "I'm having trouble connecting to the AI right now. Please try again."


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
    client = _get_groq_client()
    if client is None:
        return "Analysis unavailable."
    try:
        prompt = (
            f"Give a brief 2-3 sentence analysis for the Indian stock {ticker} "
            f"which is currently trading at ₹{price} with a change of {change}%. "
            f"Focus on possible reasons for the move and short-term outlook."
        )
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=256,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[MoverAnalysis] Groq API error: {e}")
        return "Analysis unavailable."
