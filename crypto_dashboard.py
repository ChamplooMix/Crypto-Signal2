"""crypto_dashboard.py
Streamlit‑App ohne externes Backend – zieht die Daten direkt aus öffentlichen APIs
(Yahoo Finance & Coin‑Tickers). Keine eigene Server‑Infrastruktur nötig.

Install & Run (in Streamlit Cloud genügt requirements.txt):
    pip install -r requirements.txt
    streamlit run crypto_dashboard.py
"""
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.express as px
from datetime import datetime, timedelta

# -------------------------------------------------------------------------
# Branding ‑ Corporate Colours (Skobeloff usw.)
BRAND_MAIN = "#207373"
BRAND_LIGHT = "#99cccc"
ACCENT_1 = "#ff9900"
ACCENT_2 = "#990066"
BG_LIGHT  = "#cae3e3"

st.set_page_config(page_title="Crypto Signal Dashboard", page_icon="📊", layout="wide")

st.markdown(
    f"""
    <style>
        .stApp {{ background-color:{BG_LIGHT}; font-family: 'Inter',sans-serif; }}
        h1,h2,h3,h4 {{ color:{BRAND_MAIN}; }}
    </style>""",
    unsafe_allow_html=True,
)

# -------------------------------------------------------------------------
# Helper – Mapping Streamlit timeframe → yfinance period/interval
TF_MAP = {
    "5m":  ("7d",  "5m"),   # max 7 Tage
    "15m": ("30d", "15m"),  # max 30 Tage
    "1h":  ("60d", "60m"),  # ca. 2 Monate
    "4h":  ("60d", "240m"), # 4‑Stunden‑Kerzen
    "1d":  ("365d","1d"),   # 1 Jahr Daily
}

# -------------------------------------------------------------------------
# Sidebar – User‑Inputs
st.sidebar.title("⚙️ Einstellungen")
timeframe = st.sidebar.selectbox("Timeframe", list(TF_MAP.keys()), index=3)
alt_ticker = st.sidebar.text_input("Altcoin‑Ticker (Yahoo‑Symbol)", value="ETH-USD")

# Auto‑Refresh alle 5 Min
st_autorefresh(interval=300_000, key="datarefresh")

period, interval = TF_MAP[timeframe]

@st.cache_data(ttl=280, show_spinner=False)
def load_market_data(alt: str, period: str, interval: str):
    btc = yf.download("BTC-USD", period=period, interval=interval, progress=False)["Adj Close"].rename("BTC")
    spx = yf.download("^GSPC",  period=period, interval=interval, progress=False)["Adj Close"].rename("SP500")
    gold = yf.download("GC=F",   period=period, interval=interval, progress=False)["Adj Close"].rename("GOLD")
    altc = yf.download(alt,       period=period, interval=interval, progress=False)["Adj Close"].rename("ALT")
    df = pd.concat([btc, spx, gold, altc], axis=1).dropna()
    return df

data = load_market_data(alt_ticker, period, interval)

# -------------------------------------------------------------------------
# Correlations – rolling window 30 Kerzen
window = 30
corr_btc_spx  = data["BTC"].rolling(window).corr(data["SP500"])
corr_btc_gold = data["BTC"].rolling(window).corr(data["GOLD"])
corr_alt_btc  = data["ALT"].rolling(window).corr(data["BTC"])

corr_df = pd.DataFrame({
    "date": data.index,
    "BTC‑SPX":  corr_btc_spx,
    "BTC‑Gold": corr_btc_gold,
    "Alt‑BTC":  corr_alt_btc,
}).dropna()

# -------------------------------------------------------------------------
# Simple Signal – EMA‑Crossover + Korrelationsfilter
SIG_CONF = 75
ema_fast = ta.ema(data["ALT"], length=8)
ema_slow = ta.ema(data["ALT"], length=21)
trend_ok  = ema_fast > ema_slow
corr_ok   = corr_alt_btc < 0.5

signals = pd.DataFrame({
    "timestamp": data.index,
    "price": data["ALT"],
    "direction": ["LONG" if trend and corr else "" for trend, corr in zip(trend_ok, corr_ok)],
}).query("direction != ''")

# Nur letzte 20 Signale, Konf. simuliert
signals = signals.tail(20).assign(confidence=SIG_CONF)

# -------------------------------------------------------------------------
# UI
st.title("📈 Crypto Signal Dashboard (Streamlit – No Server Needed)")

col1, col2 = st.columns([2,3])
with col1:
    st.subheader("BTC vs. Märkte – 30‑Bar‑Korrelation")
    fig = px.line(
        corr_df,
        x="date",
        y=["BTC‑SPX", "BTC‑Gold", "Alt‑BTC"],
        template="simple_white",
        labels={"value":"Korrelation", "variable":"Pair", "date":"Datum"},
        color_discrete_sequence=[ACCENT_1, ACCENT_2, BRAND_MAIN],
    )
    fig.update_layout(legend_title="Pair", yaxis=dict(range=[-1,1]))
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader(f"Trading‑Signale für {alt_ticker} ({timeframe}) – EMA‑Cross & ρ<0,5")
    st.dataframe(signals[["timestamp","direction","confidence"]], use_container_width=True, hide_index=True)

st.caption("Auto‑Refresh alle 5 Min · Daten via Yahoo Finance · © 2025 Crypto Dashboard")
