"""
chatbot_engine.py
-----------------
Separation of Concerns: This file owns ONLY the AI logic.
It knows nothing about Streamlit, session state, or UI rendering.
The app.py imports this and handles all display concerns.
"""

import os
import requests

# ── Constants ─────────────────────────────────────────────────────────────────

NIM_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NIM_MODEL   = "meta/llama-3.1-70b-instruct"
TIMEOUT_SEC = 30

# ── System Prompt ──────────────────────────────────────────────────────────────
# This is the single source of truth for the chatbot's persona and guardrails.
# Keeping it here (not in app.py) means the UI layer never needs to know about it.

SYSTEM_PROMPT = """
You are ArthBot, a Quantitative Analyst with 20 years of experience
in Indian financial markets. You work exclusively with data from NSE, BSE,
RBI, SEBI, and AMFI.

YOUR EXPERTISE:
- Indian equities: NSE/BSE listed stocks, Nifty/Sensex indices
- Derivatives: F&O strategies, options Greeks, IV analysis on NSE
- Macroeconomics: RBI monetary policy, repo rate, CPI, IIP, FII/DII flows
- Fundamental analysis: P/E, EV/EBITDA, ROCE, balance sheet reading
- Technical analysis: Moving averages, RSI, MACD, candlestick patterns
- Mutual funds: AMFI NAV, SIP strategies, fund categories under SEBI
- Regulations: SEBI circulars, FEMA, insider trading rules, PMLA

STRICT RULES - YOU MUST FOLLOW THESE WITHOUT EXCEPTION:
1. You ONLY answer questions about Indian financial markets and investing.
2. If asked about sports, politics, entertainment, relationships, health,
   or any non-finance topic, you must politely decline and redirect.
3. You NEVER give personalised investment advice or say "buy this stock."
   Instead, frame answers as analysis: "Historically, stocks with X tend to..."
4. You always add a brief disclaimer when discussing specific stocks or funds.
5. If you don't know something, say so. Never fabricate data or news.
6. You respond in clear, professional English. Use Indian financial terminology
   (e.g., "crore", "lakh", "NSE", "SEBI") naturally.

REFUSAL TEMPLATE (use this exact format when declining):
"I'm ArthBot, your Indian markets analyst. I can only help with topics related
to Indian financial markets, investing, and economics. For [topic they asked],
I'd suggest consulting a relevant expert. Can I help you with any market
analysis instead?"
"""


# ── Core Engine Function ───────────────────────────────────────────────────────

def get_chat_response(conversation_history: list[dict]) -> str:
    """
    Send the full conversation history to NVIDIA NIM and return the reply.

    Args:
        conversation_history: List of {"role": "user"/"assistant", "content": str}
                               This is the FULL history — the engine is stateless.
                               State lives in app.py's session_state.

    Returns:
        str: The assistant's reply, or a user-friendly error message.
    """
    api_key = os.environ.get("NVIDIA_API_KEY", "")
    if not api_key:
        return (
            "Configuration error: NVIDIA_API_KEY is not set. "
            "Please add it to your Render environment variables."
        )

    # Prepend the system prompt to every request.
    # The system message is never stored in session_state — it's injected here
    # so the UI layer never needs to manage it.
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + conversation_history

    try:
        response = requests.post(
            NIM_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": NIM_MODEL,
                "messages": messages,
                "max_tokens": 512,
                "temperature": 0.3,    # Lower = more factual, less creative
                "top_p": 0.9,
            },
            timeout=TIMEOUT_SEC,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    except requests.exceptions.Timeout:
        return (
            "The model took too long to respond (>{} seconds). "
            "This can happen during peak hours. Please try again.".format(TIMEOUT_SEC)
        )
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else "unknown"
        if status == 401:
            return "Authentication failed. Please check your NVIDIA_API_KEY."
        if status == 429:
            return "Rate limit reached. Please wait a moment before sending another message."
        return f"API error (HTTP {status}). Please try again shortly."
    except requests.exceptions.ConnectionError:
        return "Could not reach the NVIDIA NIM API. Please check your internet connection."
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"


# ── Conversation Utilities ─────────────────────────────────────────────────────

def build_user_message(text: str) -> dict:
    """Helper: wrap a user string into the OpenAI message format."""
    return {"role": "user", "content": text}


def build_assistant_message(text: str) -> dict:
    """Helper: wrap an assistant string into the OpenAI message format."""
    return {"role": "assistant", "content": text}


def get_welcome_message() -> str:
    """Returns the initial greeting shown when the chat is first opened."""
    return (
        "Namaste! I'm **ArthBot**, your Senior Quant Analyst for Indian markets. "
        "I can help you with:\n\n"
        "- **Stock analysis** (NSE/BSE fundamentals & technicals)\n"
        "- **Macro insights** (RBI policy, inflation, FII flows)\n"
        "- **Derivatives** (F&O strategies, options pricing)\n"
        "- **Mutual funds** (AMFI categories, SIP planning concepts)\n\n"
        "What would you like to analyse today?"
    )
