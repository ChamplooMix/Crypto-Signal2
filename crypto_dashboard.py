"""crypto_dashboard.py
Streamlit-App – komplett ohne externe Abhängigkeiten jenseits von Pandas & yfinance.
Berechnet EMAs mit der Pandas-eigenen .ewm‑Funktion → kein pandas_ta mehr nötig.

Install & Run (lokal oder Streamlit Cloud):
    pip install -r requirements.txt
    streamlit run crypto_dashboard.py
"""

import streamlit as st
from streamlit_autorefresh import st_autorefresh
import yfinance as yf
import pandas as pd
import plotly.express as px

# -------------------------------------------------------------------------
# Branding – Corporate Colours
BRAND_MAIN = "#207373"   # Skobeloff
BRAND_LIGHT = "#99cccc"  # Powder Green
ACCENT_1    = "#ff9900"  # Tangerine
ACCENT_2    = "#990066"  # Flirt
BG_LIGHT    = "#cae3e3"  # Powder Green Light

st.set_page_config(page_title="Crypto Signal Dashboard", page_icon="📊", layout="wide")

st.markdown(
    f"""
    <style>
        .stApp {{ background-color:{BG_LIGHT}; font-family:'Inter',sans-serif; }}
        h1,h2,h3,h4 {{ color:{BRAND_MAIN}; }}
    </style>""",
    unsafe_allow_html=True,
)

# -------------------------------------------------------------------------
# Helper – TimeFrame Mapping
timeframe_map = {
    "5m":  ("7d",  "5m"),
    "15m": ("30d", "15m"),
    "1h":  ("60d", "60m"),
    "4h":  ("60d", "240m"),
    "1d":  ("365d","1d"),
}

# -------------------------------------------------------------------------
# Sidebar Inputs
st.sidebar.title("⚙️ Einstellungen")
selected_tf = st.sidebar.selectbox("Timeframe", list(timeframe_map.keys()), index=3)
alt_ticker  = st.sidebar.text_input("Altcoin‑Ticker (Yahoo)", value="ETH-USD")

st_autorefresh(interval=300_000, key="refresh")
period, interval = timeframe_map[selected_tf]

@st.cache_data(ttl=280, show_spinner=False)
def load_data(alt, per, inter):
    btc  = yf.download("BTC-USD", period=per, interval=inter, progress=False)["Adj Close"].rename("BTC")
    spx  = yf.download("^GSPC",  period=per, interval=inter, progress=False)["Adj Close"].rename("SPX")
    gold = yf.download("GC=F",   period=per, interval=inter, progress=False)["Adj Close"].rename("GOLD")
    altc = yf.download(alt,      period=per, interval=inter, progress=False)["Adj Close"].rename("ALT")
    return pd.concat([btc, spx, gold, altc], axis=1).dropna()

data = load_data(alt_ticker, period, interval)

# -------------------------------------------------------------------------
# Rolling 30‑Bar Correlations
window = 30
corr_df = pd.DataFrame({
    "date": data.index,
    "BTC‑SPX":  data["BTC"].rolling(window).corr(data["SPX"]),
    "BTC‑Gold": data["BTC"].rolling(window).corr(data["GOLD"]),
    "Alt‑BTC":  data["ALT"].rolling(window).corr(data["BTC"]),
}).dropna()

# -------------------------------------------------------------------------
# Simple EMA‑Crossover Signal (+ Korrelationsfilter ρ<0,5)
ema_fast = data["ALT"].ewm(span=8, adjust=False).mean()
ema_slow = data["ALT"].ewm(span=21, adjust=False).mean()
trend_ok = ema_fast > ema_slow
corr_ok  = corr_df.set_index("date")["Alt‑BTC"] < 0.5

signals = (
    pd.DataFrame({
        "timestamp": data.index,
        "direction": [
            "LONG" if trend_ok.loc[ts] and corr_ok.get(ts, False) else ""
            for ts in data.index
        ],
    })
    .query("direction != ''")
    .assign(confidence=75)
    .tail(20)
)

# -------------------------------------------------------------------------
# UI
st.title("📈 Crypto Signal Dashboard (Serverless)")

col1, col2 = st.columns([2,3])
with col1:
    st.subheader("30‑Bar‑Korrelationen")
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
    st.subheader(f"Signals {alt_ticker} – {selected_tf}")
    st.dataframe(signals, use_container_width=True, hide_index=True)

st.caption("Auto‑Refresh 5 Min · Daten: Yahoo Finance · © 2025")
