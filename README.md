# AlgoMetrics — Indian Stock Market Dashboard

A professional, AI-powered financial analysis dashboard for **NSE and BSE** listed stocks. Built with Python and deployed on Render.

---

---

## Features

### Market Intelligence
- **Today's Market Movers** — scans Nifty 50 every 15 minutes to surface the top gainer and loser, powered by AI-generated context from **Groq (Llama 3-70B)**
- **Candlestick Chart** — interactive OHLCV chart with configurable Moving Average overlays (SMA) and range selector buttons (1M / 3M / 6M / 1Y / All)
- **20-Day Rolling Volatility** — visualises risk as a standard deviation of daily returns
- **Daily Returns** — green/red bar chart of daily percentage moves
- **Cumulative Return** — total compounded gain/loss from any chosen start date

### AI Analysis
- **Analyst Notes** — every chart has a dynamic interpretation panel that reads the actual data and generates a contextual signal (Bullish / Bearish / Mixed, Golden Cross, Death Cross, volatility regime)
- **ArthBot** — a Senior Quant Analyst chatbot restricted to Indian financial markets, powered by **NVIDIA NIM (Llama 3-70B)**. Context-aware: automatically reads the currently loaded stock's price, volatility, and return on first message

### Data & Search
- **Full NSE equity list** — live-fetched from NSE archives (~2000+ stocks), with a comprehensive fallback list if the server is unreachable
- **Full BSE equity list** — fetched from BSE API
- **Smart search** — type a company name to get a filtered recommendation list, or paste a direct ticker
- **Custom date ranges** — 1Y / 2Y / 5Y or fully custom start/end dates
- **Excel download** — export the full computed dataset (OHLCV + indicators) as `.xlsx`

---

## Project Structure

```
algometrics/
├── app.py                  # Main Streamlit application
├── chatbot_engine.py       # ArthBot conversation logic (legacy layer)
├── render.yaml             # Render deployment config
├── requirements.txt        # Python dependencies
└── src/
    ├── __init__.py
    ├── ai_services.py      # Centralized AI service layer (Groq + NVIDIA NIM)
    ├── faq.py              # FAQ section renderer
    ├── legal.py            # Legal disclaimers renderer
    └── utils.py            # Resilient yfinance wrapper with session_state fallback
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Streamlit + custom CSS (IBM Plex Sans) |
| Charts | Plotly (interactive candlestick, line, bar, area) |
| Market Data | yfinance (Yahoo Finance) |
| AI — Movers | Groq API · `llama3-70b-8192` |
| AI — Chatbot | NVIDIA NIM · `meta/llama3-70b-instruct` |
| Deployment | Render (Web Service) |

---

## Ticker Format Reference

| Exchange | Format | Example |
|----------|--------|---------|
| NSE | `TICKER.NS` | `RELIANCE.NS` |
| BSE | `SCRIP_CODE.BO` | `500325.BO` |
| Nifty 50 | `^NSEI` | `^NSEI` |
| Sensex | `^BSESN` | `^BSESN` |
| Nifty Bank | `^NSEBANK` | `^NSEBANK` |
| Nifty IT | `^CNXIT` | `^CNXIT` |

---

## Environment Variables

Set these in **Render → your service → Environment**:

| Variable | Required | Source |
|----------|----------|--------|
| `NVIDIA_API_KEY` | Yes | [build.nvidia.com](https://build.nvidia.com) |
| `GROQ_API_KEY` | Yes | [console.groq.com](https://console.groq.com) |

---

## Run Locally

```bash
# 1. Clone the repo
git clone https://github.com/gitritam06/Stock-Ticker.git
cd Stock-Ticker

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set environment variables
export NVIDIA_API_KEY="nvapi-xxxxxxxxxxxx"
export GROQ_API_KEY="gsk_xxxxxxxxxxxx"

# 4. Run
streamlit run app.py
```

---

## Deploy on Render

1. Fork or push this repo to GitHub
2. Go to [render.com](https://render.com) → **New → Web Service**
3. Connect your GitHub repo — Render auto-detects `render.yaml`
4. Add `NVIDIA_API_KEY` and `GROQ_API_KEY` under **Environment**
5. Click **Deploy** — live in ~3 minutes at `your-app.onrender.com`

To update: `git push` — Render redeploys automatically.

---

## Data Notes

- Stock data is sourced from **Yahoo Finance** via `yfinance` — subject to a 15–20 minute delay
- NSE closes at **3:30 PM IST** — run after 4 PM for the latest complete trading day
- Market Movers refresh every **15 minutes** during trading hours
- If Yahoo Finance rate-limits a request, `src/utils.py` serves the last successful fetch from `session_state` with a non-blocking warning instead of crashing

---

## Disclaimer

AlgoMetrics is an independent educational tool and is not registered with or endorsed by SEBI. All content is for informational purposes only and does not constitute investment advice. See the in-app **Privacy Policy & Terms of Use** section for full details.

---

*Built with Python · Streamlit · NVIDIA NIM · Groq*
## Deployed on Render Cloud

[Live App →]**[algo-metrics.onrender.com]([https://algo-metrics.onrender.com](https://stock-ticker-zjp5.onrender.com))**
