"""
src/ai_services.py
------------------
Centralized AI Service Layer.

Separation of Concerns:
    This file owns ALL AI client initialization and prompt execution.
    app2.py calls the functions here and never needs to know which
    client, model, or API endpoint is being used.

Two clients, two purposes:
    groq_client  ->  Groq API  ->  get_mover_analysis()
                     Fast inference, used for real-time market mover cards.

    nim_client   ->  NVIDIA NIM (OpenAI-compatible)  ->  get_chat_analysis()
                     Used for the full ArthBot conversation interface.

Both clients read API keys from environment variables (Render env vars).
Neither key is ever hardcoded or logged.
"""

import os
from groq import Groq
from openai import OpenAI

# =============================================================================
# CLIENT INITIALIZATION
# Clients are module-level singletons — initialized once at import time.
# If a key is missing, the client still initializes but calls will fail
# gracefully inside the try-except blocks in each function.
# =============================================================================

groq_client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

nim_client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.environ.get("NVIDIA_API_KEY"),
)

# =============================================================================
# SYSTEM PROMPTS
# Defined here so both prompts live in one place and are easy to update.
# =============================================================================

_MOVER_SYSTEM_PROMPT = (
    "You are a concise Senior Analyst specializing in Indian equity markets. "
    "You explain daily stock price movements in 2-3 clear sentences. "
    "You cite likely fundamental or macro reasons specific to Indian markets: "
    "RBI policy, FII/DII flows, sector rotation, earnings, SEBI actions, or "
    "global risk events. You never fabricate data. No disclaimers."
)

_CHAT_SYSTEM_PROMPT = """
You are ArthBot, a Quantitative Analyst in Indian financial markets. You work exclusively with NSE, BSE, RBI, SEBI,
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
2. Decline and redirect using the template below for any off-topic request.
3. NEVER give personalised investment advice or say buy this stock.
4. Add a brief disclaimer when discussing specific stocks or funds.
5. Never fabricate data, prices, or news.
6. Use Indian financial terminology naturally (crore, lakh, NSE, SEBI).

REFUSAL TEMPLATE:
I am ArthBot, your Indian markets analyst. I can only help with topics
related to Indian financial markets, investing, and economics. For [topic],
I would suggest consulting a relevant expert. Can I help you with any
market analysis instead?
"""


# =============================================================================
# FUNCTIONS
# =============================================================================

def get_mover_analysis(ticker: str, price: float, change: float) -> str:
    """
    Ask Groq (Llama 3-70B) why a Nifty 50 stock moved today.

    Used by: market movers widget in app2.py.
    Client: groq_client (fast inference, suitable for real-time cards).

    Args:
        ticker: Stock symbol e.g. "RELIANCE.NS"
        price:  Latest closing price as a float
        change: Percentage change for the day e.g. +3.24 or -1.87

    Returns:
        str: 2-3 sentence analysis, or a user-friendly error message.
    """
    direction = "gain" if change >= 0 else "decline"
    symbol = ticker.replace(".NS", "").replace(".BO", "")
    prompt = (
        f"{symbol} stock closed at Rs.{price:.2f} with a {change:+.2f}% {direction} today "
        f"on the NSE. In 2-3 sentences, what is the most likely reason for this move? "
        f"Be specific to Indian market context."
    )

    try:
        response = groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[
                {"role": "system", "content": _MOVER_SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            max_tokens=150,
            temperature=0.4,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        # Return a clean string — caller renders it in the UI, no crash
        return (
            f"AI analysis temporarily unavailable "
            f"({type(e).__name__}). Please try refreshing."
        )


def get_chat_analysis(
    user_prompt: str,
    conversation_history: list[dict] | None = None,
) -> str:
    """
    Send a user message (with optional history) to NVIDIA NIM (Llama 3-70B)
    and return ArthBot's reply.

    Used by: ArthBot chat interface in app2.py.
    Client: nim_client (NVIDIA NIM, OpenAI-compatible endpoint).

    Args:
        user_prompt:          The latest user message string.
        conversation_history: Optional list of prior {"role", "content"} dicts.
                              If provided, injected between system prompt and
                              the new user message so the model has context.
                              Caller (app2.py) owns and manages this history.

    Returns:
        str: ArthBot's reply, or a user-friendly error message.
    """
    # Build message list: system -> history -> new user message
    messages = [{"role": "system", "content": _CHAT_SYSTEM_PROMPT}]

    if conversation_history:
        messages.extend(conversation_history)

    messages.append({"role": "user", "content": user_prompt})

    try:
        response = nim_client.chat.completions.create(
            model="meta/llama3-70b-instruct",
            messages=messages,
            max_tokens=512,
            temperature=0.3,
            top_p=0.9,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return (
            f"ArthBot is temporarily unavailable "
            f"({type(e).__name__}). Please try again in a moment."
        )
