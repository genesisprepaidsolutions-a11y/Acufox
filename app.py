
import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px

st.set_page_config(page_title="Aquaflow Enterprise Dashboard", layout="wide")

def get_connection():
    return psycopg2.connect(
        host=st.secrets["DB_HOST"],
        database=st.secrets["DB_NAME"],
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        port=st.secrets.get("DB_PORT", 5432)
    )

@st.cache_data(ttl=60)
def load_devices():
    conn = get_connection()
    df = pd.read_sql("SELECT device_id FROM devices ORDER BY device_id", conn)
    conn.close()
    return df

@st.cache_data(ttl=60)
def load_messages(device_id):
    conn = get_connection()
    df = pd.read_sql(
        "SELECT timestamp, volume_m3, battery_percent, leak_flag, tamper_flag FROM messages WHERE device_id=%s ORDER BY timestamp",
        conn,
        params=(device_id,)
    )
    conn.close()
    return df

st.title("Aquaflow Enterprise Fleet Dashboard")

devices = load_devices()

if len(devices) == 0:
    st.warning("No devices found in database")
    st.stop()

device_id = st.selectbox("Select Device", devices["device_id"])

df = load_messages(device_id)

if len(df) == 0:
    st.warning("No messages for selected device")
    st.stop()

latest = df.iloc[-1]

col1, col2, col3, col4 = st.columns(4)

col1.metric("Latest Volume (m³)", f"{latest.volume_m3:.2f}")
col2.metric("Battery (%)", f"{latest.battery_percent:.1f}")
col3.metric("Leak", "YES" if latest.leak_flag else "NO")
col4.metric("Tamper", "YES" if latest.tamper_flag else "NO")

fig = px.line(df, x="timestamp", y="volume_m3", title="Volume Trend")
st.plotly_chart(fig, use_container_width=True)

st.dataframe(df)
