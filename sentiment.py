"""
sentiment.py
Scrapes Google News RSS for a stock ticker/name,
sends headlines to NVIDIA NIM, returns sentiment + confidence.
"""

import os
import re
import json
import feedparser
import requests
from dotenv import load_dotenv

load_dotenv()  # loads .env file — keys never hardcoded

NVIDIA_API_KEY  = os.environ.get("NVIDIA_API_KEY")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
NIM_MODEL       = os.environ.get("NIM_MODEL", "meta/llama-3.1-70b-instruct")

MAX_HEADLINES = 10  # send top 10 headlines to NIM


def scrape_headlines(query: str) -> list[str]:
    """
    Fetch recent news headlines from Google News RSS.
    query: stock name or ticker e.g. 'Zomato' or 'RELIANCE NSE'
    Returns list of headline strings.
    """
    rss_url = f"https://news.google.com/rss/search?q={requests.utils.quote(query)}+stock&hl=en-IN&gl=IN&ceid=IN:en"
    feed    = feedparser.parse(rss_url)

    headlines = []
    for entry in feed.entries[:MAX_HEADLINES]:
        # Strip HTML tags from title if any
        clean = re.sub(r"<[^>]+>", "", entry.title)
        headlines.append(clean.strip())

    return headlines


def analyze_sentiment(stock_name: str, headlines: list[str]) -> dict:
    """
    Send headlines to NVIDIA NIM model.
    Returns dict: { sentiment, confidence, reasoning, headlines }
    """
    if not NVIDIA_API_KEY:
        return {
            "error": "NVIDIA_API_KEY not set. Check your .env file.",
            "sentiment": "Unknown",
            "confidence": 0,
            "reasoning": "",
            "headlines": headlines
        }

    if not headlines:
        return {
            "sentiment": "Neutral",
            "confidence": 50,
            "reasoning": "No recent headlines found.",
            "headlines": []
        }

    headlines_text = "\n".join(f"- {h}" for h in headlines)

    prompt = f"""You are a financial sentiment analyst. Analyze these recent news headlines for {stock_name} stock.

Headlines:
{headlines_text}

Based ONLY on these headlines, respond with a JSON object in this exact format:
{{
  "sentiment": "Bullish" or "Bearish" or "Neutral",
  "confidence": <integer 0-100>,
  "reasoning": "<one sentence explanation>"
}}

Rules:
- Bullish = positive outlook, good news, growth signals
- Bearish = negative outlook, bad news, decline signals  
- Neutral = mixed or no strong signal
- confidence: how sure you are (0=no idea, 100=very clear)
- reasoning: max 20 words

Respond with JSON only. No extra text."""

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": NIM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 150,
        "temperature": 0.1  # low temp for consistent structured output
    }

    try:
        response = requests.post(
            f"{NVIDIA_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=15
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"].strip()

        # Extract JSON from response (sometimes model adds extra text)
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            result = json.loads(match.group())
        else:
            result = json.loads(raw)

        return {
            "sentiment":  result.get("sentiment", "Neutral"),
            "confidence": int(result.get("confidence", 50)),
            "reasoning":  result.get("reasoning", ""),
            "headlines":  headlines
        }

    except requests.exceptions.Timeout:
        return {"error": "NIM API timed out.", "sentiment": "Neutral", "confidence": 0, "reasoning": "", "headlines": headlines}
    except requests.exceptions.HTTPError as e:
        return {"error": f"NIM API error: {e.response.status_code}", "sentiment": "Neutral", "confidence": 0, "reasoning": "", "headlines": headlines}
    except (json.JSONDecodeError, KeyError) as e:
        return {"error": f"Parse error: {str(e)}", "sentiment": "Neutral", "confidence": 0, "reasoning": "", "headlines": headlines}


def get_stock_sentiment(stock_name: str) -> dict:
    """
    Main entry point. Call this from Flask.
    Returns full sentiment report for a stock.
    """
    headlines = scrape_headlines(stock_name)
    result    = analyze_sentiment(stock_name, headlines)
    result["stock"] = stock_name
    return result
