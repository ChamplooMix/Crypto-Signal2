"""crypto_dashboard.py
Streamlit‑Version des Crypto Signal Dashboards.
Install:
  pip install streamlit streamlit-autorefresh plotly requests pandas
Run:
  streamlit run crypto_dashboard.py
Set API endpoint via Streamlit secrets (st.secrets["API_BASE"]).
"""
import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import requests
import plotly.express as px

# --- Branding Farben -----------------------------------------------------
BRAND_MAIN = "#207373"   # Skobeloff
BRAND_LIGHT = "#99cccc"  # Powder Green
ACCENT_1 = "#ff9900"     # Tangerine
ACCENT_2 = "#990066"     # Flirt
BG_LIGHT = "#cae3e3"     # Powder Green Light

# --- Page Config ---------------------------------------------------------
st.set_page_config(
    page_title="Crypto Signal Dashboard",
    page_icon="📊",
    layout="wide",
)

st.markdown(
    f"""
    <style>
        .stApp {{
            background-color: {BG_LIGHT};
            font-family: 'Inter', sans-serif;
        }}
        .css-1n76uvr p {{
            color: {BRAND_MAIN};
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Helper --------------------------------------------------------------
API_BASE = st.secrets.get("API_BASE", "https://api.example.com")

def fetch_json(endpoint: str):
    """ GET JSON helper with basic error handling """
    r = requests.get(endpoint, timeout=8)
    r.raise_for_status()
    return r.json()

# --- Sidebar -------------------------------------------------------------
st.sidebar.title("⚙️ Einstellungen")
timeframes = ["5m", "15m", "1h", "4h", "1d"]
selected_tf = st.sidebar.selectbox("Timeframe", timeframes, index=3)

# Auto‑Refresh alle 5 Minuten (300 000 ms)
st_autorefresh(interval=300_000, key="datarefresh")

# --- Load Data -----------------------------------------------------------
@st.cache_data(ttl=280)
def load_data(tf: str):
    try:
        corr = fetch_json(f"{API_BASE}/correlation?tf={tf}")
        sig = fetch_json(f"{API_BASE}/signals?tf={tf}")
        return pd.DataFrame(corr), pd.DataFrame(sig), None
    except Exception as exc:
        demo_corr = [
            {"date": "2025-04-01", "btc_sp500": 0.62, "btc_gold": 0.08, "alt_btc": 0.47},
            {"date": "2025-04-08", "btc_sp500": 0.67, "btc_gold": 0.05, "alt_btc": 0.44},
            {"date": "2025-04-15", "btc_sp500": 0.66, "btc_gold": 0.09, "alt_btc": 0.42},
            {"date": "2025-04-22", "btc_sp500": 0.69, "btc_gold": 0.07, "alt_btc": 0.39},
        ]
        demo_sig = [
            {"timestamp": "2025-04-27 09:15", "symbol": "SOLUSDT", "direction": "LONG", "confidence": 78},
            {"timestamp": "2025-04-27 11:30", "symbol": "RNDRUSDT", "direction": "SHORT", "confidence": 65},
        ]
        return pd.DataFrame(demo_corr), pd.DataFrame(demo_sig), str(exc)

corr_df, sig_df, err_msg = load_data(selected_tf)

# --- UI ------------------------------------------------------------------
if err_msg:
    st.warning("Fehler beim Laden der Live‑Daten – Demo‑Werte werden angezeigt.\n" + err_msg)

st.title("📈 Crypto Signal Dashboard (Streamlit)")

# 1) Correlation Chart -----------------------------------------------------
col1, col2 = st.columns([2, 3])
with col1:
    st.subheader("BTC ↔ Märkte – 30‑Tage‑Korrelation")
    fig = px.line(
        corr_df,
        x="date",
        y=["btc_sp500", "btc_gold", "alt_btc"],
        labels={"value": "Korrelation", "variable": "Pair", "date": "Datum"},
        template="simple_white",
        color_discrete_sequence=[ACCENT_1, ACCENT_2, BRAND_MAIN],
    )
    fig.update_layout(legend_title="Pair", yaxis=dict(range=[-1, 1]))
    st.plotly_chart(fig, use_container_width=True)

# 2) Signal Table ---------------------------------------------------------
with col2:
    st.subheader(f"Live‑Trading‑Signale ({selected_tf.upper()})")
    st.dataframe(sig_df, use_container_width=True, hide_index=True)

st.caption("Auto‑Refresh alle 5 Minuten · © 2025 Crypto Signal Dashboard")
