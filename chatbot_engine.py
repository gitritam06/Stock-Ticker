"""
chatbot_engine.py
-----------------
Separation of Concerns: Pure AI logic only.
No Streamlit imports. No UI. No state.
Reads NVIDIA_API_KEY from environment (Render env var).
"""

import os
import requests

# ── Constants ──────────────────────────────────────────────
NIM_API_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NIM_MODEL   = "meta/llama-3.1-70b-instruct"
TIMEOUT_SEC = 30

# ── System Prompt ──────────────────────────────────────────
SYSTEM_PROMPT = """
You are ArthBot, a Senior Quantitative Analyst with 20 years of experience
in Indian financial markets. You work exclusively with NSE, BSE, RBI, SEBI,
and AMFI data.

YOUR EXPERTISE:
- Indian equities: NSE/BSE stocks, Nifty/Sensex indices
- Derivatives: F&O strategies, options Greeks, IV analysis on NSE
- Macroeconomics: RBI policy, repo rate, CPI, IIP, FII/DII flows
- Fundamental analysis: P/E, EV/EBITDA, ROCE, balance sheet reading
- Technical analysis: Moving averages, RSI, MACD, candlestick patterns
- Mutual funds: AMFI NAV, SIP strategies, SEBI fund categories
- Regulations: SEBI circulars, FEMA, insider trading rules

STRICT RULES:
1. ONLY answer questions about Indian financial markets and investing.
2. If asked about sports, politics, entertainment, relationships, health,
   or any non-finance topic — decline and redirect using the template below.
3. NEVER give personalised investment advice or say "buy this stock."
   Frame answers as analysis only.
4. Add a brief disclaimer when discussing specific stocks or funds.
5. Never fabricate data, prices, or news.
6. Use Indian financial terminology naturally (crore, lakh, NSE, SEBI).

REFUSAL TEMPLATE:
"I am ArthBot, your Indian markets analyst. I can only help with topics
related to Indian financial markets, investing, and economics. For [topic],
I would suggest consulting a relevant expert. Can I help you with any
market analysis instead?"
"""


def get_chat_response(conversation_history: list[dict]) -> str:
    """
    Send full conversation history to NVIDIA NIM, return assistant reply.

    Args:
        conversation_history: List of {"role": "user"/"assistant", "content": str}
                               Stateless — caller owns history.
    Returns:
        str: Assistant reply or user-friendly error message.
    """
    # Render stores secrets as plain environment variables
    api_key = os.environ.get("NVIDIA_API_KEY", "")
    if not api_key:
        return (
            "Configuration error: NVIDIA_API_KEY is not set. "
            "Add it in your Render service > Environment settings."
        )

    # System prompt injected here — never stored in session_state
    # This prevents prompt injection via conversation history
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
                "temperature": 0.3,
                "top_p": 0.9,
            },
            timeout=TIMEOUT_SEC,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    except requests.exceptions.Timeout:
        return (
            f"The model took too long to respond (>{TIMEOUT_SEC}s). "
            "This can happen during peak hours. Please try again."
        )
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if e.response else "unknown"
        if status == 401:
            return "Authentication failed. Check your NVIDIA_API_KEY in Render env vars."
        if status == 429:
            return "Rate limit reached. Please wait a moment before sending another message."
        return f"API error (HTTP {status}). Please try again shortly."
    except requests.exceptions.ConnectionError:
        return "Could not reach the NVIDIA NIM API. Check your network connection."
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"


def build_user_message(text: str) -> dict:
    """Wrap user string into OpenAI message format."""
    return {"role": "user", "content": text}


def build_assistant_message(text: str) -> dict:
    """Wrap assistant string into OpenAI message format."""
    return {"role": "assistant", "content": text}


def get_welcome_message() -> str:
    """Initial greeting shown when chat is first rendered."""
    return (
        "Namaste! I am **ArthBot**, your Senior Quant Analyst for Indian markets. "
        "I can help you with:\n\n"
        "- **Stock analysis** (NSE/BSE fundamentals and technicals)\n"
        "- **Macro insights** (RBI policy, inflation, FII flows)\n"
        "- **Derivatives** (F&O strategies, options pricing)\n"
        "- **Mutual funds** (AMFI categories, SIP planning concepts)\n\n"
        "Fetch a stock above to analyse it, or ask me any market question."
    )
