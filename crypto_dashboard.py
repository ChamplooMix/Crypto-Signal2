"""crypto_dashboard.py
Streamlit‑App ohne serverseitiges Backend.
Zieht Daten via yfinance und filtert fehlende Serien, um KeyErrors zu vermeiden.
"""

import streamlit as st
from streamlit_autorefresh import st_autorefresh
import yfinance as yf
import pandas as pd
import plotly.express as px

# -------------------------------------------------------------------------
# Farben & Layout
BRAND_MAIN = "#207373"; BRAND_LIGHT = "#99cccc"; ACCENT_1 = "#ff9900"; ACCENT_2 = "#990066"; BG_LIGHT = "#cae3e3"
st.set_page_config(page_title="Crypto Signal Dashboard", page_icon="📊", layout="wide")
st.markdown(f"""<style>.stApp {{background:{BG_LIGHT};font-family:'Inter',sans-serif}} h1,h2,h3,h4{{color:{BRAND_MAIN}}}</style>""",unsafe_allow_html=True)

# -------------------------------------------------------------------------
TIMEFRAME_MAP = {
    "5m": ("7d", "5m"),
    "15m": ("30d", "15m"),
    "1h": ("60d", "60m"),
    "4h": ("60d", "240m"),
    "1d": ("365d", "1d"),
}

st.sidebar.title("⚙️ Einstellungen")
tf = st.sidebar.selectbox("Timeframe", list(TIMEFRAME_MAP), index=3)
alt_ticker = st.sidebar.text_input("Altcoin-Ticker (Yahoo)", value="ETH-USD")
st_autorefresh(interval=300_000, key="refresh")
period, interval = TIMEFRAME_MAP[tf]

# -------------------------------------------------------------------------

def get_price(ticker: str, col_name: str) -> pd.Series:
    """Lädt eine Preisspalte (Adj Close oder Close) und gibt sie als Series mit
    korrektem .name zurück. Falls keine Daten, liefert leere Series."""
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    if df.empty:
        return pd.Series(dtype=float, name=col_name)
    price_col = "Adj Close" if "Adj Close" in df.columns else "Close"
    ser = df[price_col].copy()
    ser.name = col_name  # Series.rename(name=...) wäre in pandas>=2 notwendig
    return ser

@st.cache_data(ttl=280, show_spinner=False)
def load_data(alt: str) -> pd.DataFrame:
    btc  = get_price("BTC-USD", "BTC")
    spx  = get_price("^GSPC",  "SPX")
    gold = get_price("GC=F",   "GOLD")
    altc = get_price(alt,       "ALT")
    df = pd.concat([btc, spx, gold, altc], axis=1)
    return df.dropna(how="all")(how="all")

data = load_data(alt_ticker)

if data.empty or {"BTC", "ALT"}.issubset(data.columns) is False:
    st.error("Daten konnten nicht geladen werden – Prüfe Ticker/Intervall.")
    st.stop()

# -------------------------------------------------------------------------
window = 30
corr_df = pd.DataFrame({
    "date": data.index,
    "BTC-SPX":  data["BTC"].rolling(window).corr(data.get("SPX")),
    "BTC-Gold": data["BTC"].rolling(window).corr(data.get("GOLD")),
    "Alt-BTC":  data["ALT"].rolling(window).corr(data["BTC"]),
}).dropna()

ema_fast = data["ALT"].ewm(span=8, adjust=False).mean()
ema_slow = data["ALT"].ewm(span=21, adjust=False).mean()
trend_ok = ema_fast > ema_slow
corr_ok = corr_df.set_index("date").get("Alt-BTC", pd.Series(index=data.index, data=1)) < 0.5

signals = (
    pd.DataFrame({
        "timestamp": data.index,
        "direction": ["LONG" if trend_ok.loc[ts] and corr_ok.get(ts, False) else "" for ts in data.index],
    })
    .query("direction != ''")
    .assign(confidence=75)
    .tail(20)
)

# -------------------------------------------------------------------------
st.title("📈 Crypto Signal Dashboard (Serverless)")
col1, col2 = st.columns([2,3])
with col1:
    st.subheader("30‑Bar‑Korrelationen")
    if corr_df.empty:
        st.info("Nicht genügend Daten für Korrelationen im gewählten Timeframe")
    else:
        fig = px.line(corr_df, x="date", y=[c for c in ["BTC-SPX","BTC-Gold","Alt-BTC"] if c in corr_df],
                      template="simple_white", labels={"value":"Korrelation","variable":"Pair","date":"Datum"},
                      color_discrete_sequence=[ACCENT_1, ACCENT_2, BRAND_MAIN])
        fig.update_layout(legend_title="Pair", yaxis=dict(range=[-1,1]))
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader(f"Signals {alt_ticker} – {tf}")
    if signals.empty:
        st.info("Keine Signale im aktuellen Zeitraum")
    else:
        st.dataframe(signals, use_container_width=True, hide_index=True)

st.caption("Auto‑Refresh 5 Min · Daten: Yahoo Finance · © 2025")
