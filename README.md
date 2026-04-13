# 🇮🇳 Indian Stock Market Dashboard

An interactive stock market analyser for **NSE and BSE** stocks, built with Python, Streamlit, and Plotly.

## Features

- 🔍 Search any NSE (`.NS`) or BSE (`.BO`) stock by ticker
- 📈 Moving Average chart (customizable short & long windows)
- 🌊 20-day Rolling Volatility
- 📊 Daily Returns (green/red bar chart)
- 🚀 Cumulative Return since chosen start date
- ⬇️ Download data as Excel

## Tech Stack

| Tool | Role |
|------|------|
| `yfinance` | Fetches live stock data from Yahoo Finance |
| `pandas` | Data processing & indicator calculations |
| `plotly` | Interactive charts |
| `streamlit` | Web app UI & deployment |

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Ticker Format

| Exchange | Format | Example |
|----------|--------|---------|
| NSE | `TICKER.NS` | `RELIANCE.NS` |
| BSE | `TICKER.BO` | `RELIANCE.BO` |
| Nifty 50 | `^NSEI` | `^NSEI` |
| Sensex | `^BSESN` | `^BSESN` |

## Deployed on Streamlit Cloud

[Live App →](https://your-app-name.streamlit.app)
