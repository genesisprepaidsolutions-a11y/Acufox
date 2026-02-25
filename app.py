# app.py
import streamlit as st
import psycopg2
import pandas as pd
from psycopg2.extras import RealDictCursor

# ================================
# Streamlit config
# ================================
st.set_page_config(
    page_title="AcuFox Multi-Meter Dashboard",
    layout="wide"
)

# ================================
# Database connection (Supabase)
# ================================
DB_HOST = "db.uxtddangntejpwaovnmv.supabase.co"
DB_PORT = 5432
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "Acucomm@2808"


def get_connection():
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            sslmode="require"
        )
        return conn
    except Exception as e:
        st.error(f"❌ Database connection failed: {e}")
        st.stop()

# ================================
# Load devices (cached)
# ================================
@st.cache_data(ttl=300)
def load_devices():
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT device_id, name, location, status
                FROM devices
                ORDER BY name;
            """)
            devices = cur.fetchall()
            return pd.DataFrame(devices)
    finally:
        conn.close()

# ================================
# Load device readings (cached)
# ================================
@st.cache_data(ttl=300)
def load_device_data(device_id):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    timestamp,
                    volume_m3,
                    battery_percent,
                    leak_flag,
                    tamper_flag
                FROM readings
                WHERE device_id = %s
                ORDER BY timestamp DESC
                LIMIT 1000;
            """, (device_id,))
            data = cur.fetchall()
            return pd.DataFrame(data)
    finally:
        conn.close()

# ================================
# Sidebar – device selector
# ================================
st.sidebar.title("AcuFox Devices")

devices_df = load_devices()

if devices_df.empty:
    st.error("❌ No devices found in the database.")
    st.stop()

device_options = devices_df["name"].tolist()
selected_device_name = st.sidebar.selectbox(
    "Select Device",
    device_options
)

selected_device = devices_df[
    devices_df["name"] == selected_device_name
].iloc[0]

device_id = selected_device["device_id"]

# ================================
# Main dashboard
# ================================
st.title(f"📟 Device Dashboard: {selected_device_name}")

data_df = load_device_data(device_id)

if data_df.empty:
    st.warning("⚠️ No data available for this device.")
else:
    latest = data_df.iloc[0]

    # ---- Metrics ----
    col1, col2 = st.columns(2)
    col1.metric(
        "Latest Volume (m³)",
        f"{latest['volume_m3']:.2f}"
    )
    col2.metric(
        "Battery %",
        f"{latest['battery_percent']:.0f}%"
    )

    # ---- Status flags ----
    leak_flag = bool(latest.get("leak_flag"))
    tamper_flag = bool(latest.get("tamper_flag"))

    st.write(
        f"💧 Leak Status: {'⚠️ Leak Detected' if leak_flag else '✅ No Leak'}"
    )
    st.write(
        f"🔐 Tamper Status: {'⚠️ Tamper Detected' if tamper_flag else '✅ No Tamper'}"
    )

    # ---- Recent readings ----
    st.subheader("📋 Recent Readings")
    st.dataframe(data_df.head(20), use_container_width=True)

    # ---- Chart ----
    st.subheader("📈 Volume Over Time")
    chart_df = data_df.sort_values("timestamp")
    st.line_chart(
        chart_df.set_index("timestamp")["volume_m3"]
    )

# ================================
# Sigfox placeholder
# ================================
st.subheader("📡 Sigfox API")
st.info(
    "Sigfox API integration will automatically fetch live readings here."
)

# ================================
# End of file
# ================================
