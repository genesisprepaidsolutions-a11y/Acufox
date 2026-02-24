# app.py
import streamlit as st
import psycopg2
import pandas as pd
from psycopg2.extras import RealDictCursor

st.set_page_config(page_title="AcuFox Multi-Meter Dashboard", layout="wide")

# ================================
# Database connection
# ================================
def get_connection():
    try:
        conn = psycopg2.connect(
            host=st.secrets["postgres"]["db.uxtddangntejpwaovnmv.supabase.co"],
            database=st.secrets["postgres"]["postgres"],
            user=st.secrets["postgres"]["postgres"],
            password=st.secrets["postgres"]["@db.uxtddangntejpwaovnmv.supabase.co:5432/postgres"],
            port=st.secrets["postgres"].get("DB_PORT", 5432),
            sslmode="require"  # Use SSL if your DB requires it
        )
        return conn
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        st.stop()

# ================================
# Load devices with caching
# ================================
@st.cache_data(ttl=300)
def load_devices():
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT device_id, name, location, status FROM devices ORDER BY name;")
            devices = cur.fetchall()
            return pd.DataFrame(devices)
    finally:
        conn.close()

# ================================
# Load data for a specific device
# ================================
@st.cache_data(ttl=300)
def load_device_data(device_id):
    conn = get_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT timestamp, volume_m3, battery_percent, leak_flag, tamper_flag
                FROM readings
                WHERE device_id = %s
                ORDER BY timestamp DESC
                LIMIT 1000
            """, (device_id,))
            data = cur.fetchall()
            return pd.DataFrame(data)
    finally:
        conn.close()

# ================================
# Sidebar: Select device
# ================================
st.sidebar.title("AcuFox Devices")
devices_df = load_devices()
device_options = devices_df["name"].tolist()
selected_device_name = st.sidebar.selectbox("Select Device", device_options)
selected_device = devices_df[devices_df["name"] == selected_device_name].iloc[0]
device_id = selected_device["device_id"]

# ================================
# Main dashboard
# ================================
st.title(f"Device Dashboard: {selected_device_name}")

data_df = load_device_data(device_id)

if data_df.empty:
    st.warning("No data available for this device.")
else:
    # Volume in m³
    st.metric("Latest Volume (m³)", f"{data_df.iloc[0]['volume_m3']:.2f}")
    
    # Battery %
    st.metric("Battery %", f"{data_df.iloc[0]['battery_percent']:.0f}%")
    
    # Leak/Tamper flags
    leak_flag = "⚠️ Leak Detected" if data_df.iloc[0]['leak_flag'] else "No Leak"
    tamper_flag = "⚠️ Tamper Detected" if data_df.iloc[0]['tamper_flag'] else "No Tamper"
    st.write(f"Leak Status: {leak_flag}")
    st.write(f"Tamper Status: {tamper_flag}")
    
    # Display last 20 readings
    st.subheader("Recent Readings")
    st.dataframe(data_df.head(20))
    
    # Optional: chart
    st.subheader("Volume over Time")
    st.line_chart(data_df.set_index("timestamp")["volume_m3"])

# ================================
# Auto Sigfox API integration (placeholder)
# ================================
st.subheader("Sigfox API")
st.info("Sigfox API integration would automatically fetch live readings here.")

# ================================
# End of app.py
# ================================
