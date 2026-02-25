# app.py
import streamlit as st
import psycopg2
import pandas as pd
from psycopg2.extras import RealDictCursor
from datetime import datetime
import binascii

# ==========================================================
# Streamlit config
# ==========================================================
st.set_page_config(
    page_title="AcuFox Multi-Meter Dashboard",
    layout="wide"
)

# ==========================================================
# SUPABASE CONNECTION POOLER (PgBouncer – transaction mode)
# ==========================================================
DB_HOST = "aws-0-eu-west-1.pooler.supabase.com"
DB_HOSTADDR = "104.18.32.30"   # Force IPv4
DB_PORT = 6543
DB_NAME = "postgres"
DB_USER = "postgres"
DB_PASSWORD = "Acucomm@2808"

# ==========================================================
# Database connection
# ==========================================================
def get_connection():
    try:
        return psycopg2.connect(
            host=DB_HOST,
            hostaddr=DB_HOSTADDR,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            sslmode="require",
            connect_timeout=10
        )
    except Exception as e:
        st.error(f"❌ Database connection failed:\n\n{e}")
        st.stop()

# ==========================================================
# Sigfox payload decoder
# ==========================================================
def decode_sigfox_payload(hex_payload: str):
    """
    Payload example:
    bytes 0-1 : volume (uint16, /100)
    byte 2    : battery %
    byte 3    : flags (bit0=leak, bit1=tamper)
    """
    try:
        raw = binascii.unhexlify(hex_payload)

        volume_m3 = int.from_bytes(raw[0:2], "big") / 100.0
        battery_percent = raw[2]

        flags = raw[3]
        leak_flag = bool(flags & 0b00000001)
        tamper_flag = bool(flags & 0b00000010)

        return volume_m3, battery_percent, leak_flag, tamper_flag
    except Exception:
        return None, None, None, None

# ==========================================================
# Sigfox ingestion handler
# ==========================================================
def handle_sigfox_callback(params):
    device_id = params.get("device")
    payload = params.get("data")
    ts = params.get("time")

    if not device_id or not payload:
        return "Missing parameters", 400

    volume, battery, leak, tamper = decode_sigfox_payload(payload)

    if volume is None:
        return "Invalid payload", 400

    timestamp = (
        datetime.utcfromtimestamp(int(ts))
        if ts else datetime.utcnow()
    )

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO readings (
                    device_id,
                    timestamp,
                    volume_m3,
                    battery_percent,
                    leak_flag,
                    tamper_flag
                )
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (
                device_id,
                timestamp,
                volume,
                battery,
                leak,
                tamper
            ))
            conn.commit()
    finally:
        conn.close()

    return "OK", 200

# ==========================================================
# Handle Sigfox callback BEFORE UI renders
# ==========================================================
query_params = st.query_params

if "sigfox" in query_params:
    msg, status = handle_sigfox_callback(query_params)
    st.write(msg)
    st.stop()

# ==========================================================
# Cached data loaders
# ==========================================================
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
            return pd.DataFrame(cur.fetchall())
    finally:
        conn.close()

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
            return pd.DataFrame(cur.fetchall())
    finally:
        conn.close()

# ==========================================================
# Sidebar
# ==========================================================
st.sidebar.title("AcuFox Devices")

devices_df = load_devices()

if devices_df.empty:
    st.error("❌ No devices found.")
    st.stop()

selected_name = st.sidebar.selectbox(
    "Select Device",
    devices_df["name"].tolist()
)

device_id = devices_df[
    devices_df["name"] == selected_name
].iloc[0]["device_id"]

# ==========================================================
# Dashboard
# ==========================================================
st.title(f"📟 Device Dashboard: {selected_name}")

data_df = load_device_data(device_id)

if data_df.empty:
    st.warning("⚠️ No readings yet.")
else:
    latest = data_df.iloc[0]

    col1, col2 = st.columns(2)
    col1.metric("Latest Volume (m³)", f"{latest['volume_m3']:.2f}")
    col2.metric("Battery %", f"{latest['battery_percent']:.0f}%")

    st.write(f"💧 Leak: {'⚠️ YES' if latest['leak_flag'] else '✅ NO'}")
    st.write(f"🔐 Tamper: {'⚠️ YES' if latest['tamper_flag'] else '✅ NO'}")

    st.subheader("📋 Recent Readings")
    st.dataframe(data_df.head(20), use_container_width=True)

    st.subheader("📈 Volume Over Time")
    chart_df = data_df.sort_values("timestamp")
    st.line_chart(
        chart_df.set_index("timestamp")["volume_m3"]
    )

# ==========================================================
# End of file
# ==========================================================
