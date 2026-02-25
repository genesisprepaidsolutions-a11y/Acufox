import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime
import binascii

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(
    page_title="AcuFox Dashboard",
    layout="wide"
)

DB_HOST = "aws-1-eu-central-1.pooler.supabase.com"
DB_PORT = 6543
DB_NAME = "postgres"
DB_USER = "postgres.uxtddangntejpwaovnmv"
DB_PASSWORD = "Acucomm2808"


# =====================================================
# CONNECTION
# =====================================================

@st.cache_resource
def get_conn():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        sslmode="require"
    )


# =====================================================
# SIGFOX DECODER
# =====================================================

def decode_payload(payload):

    raw = binascii.unhexlify(payload)

    volume = int.from_bytes(raw[0:2], "big") / 100
    battery = raw[2]
    flags = raw[3]

    leak = bool(flags & 1)
    tamper = bool(flags & 2)

    return volume, battery, leak, tamper


# =====================================================
# SIGFOX INGESTION
# =====================================================

def handle_sigfox():

    params = st.query_params

    if "device" not in params:
        return False

    device = params["device"]
    payload = params.get("data")
    ts = params.get("time")

    if payload is None:
        return True

    volume, battery, leak, tamper = decode_payload(payload)

    timestamp = (
        datetime.utcfromtimestamp(int(ts))
        if ts else datetime.utcnow()
    )

    conn = get_conn()

    with conn.cursor() as cur:

        cur.execute(
            """
            SELECT insert_sigfox_reading(
                %s,%s,%s,%s,%s,%s
            )
            """,
            (
                device,
                timestamp,
                volume,
                battery,
                leak,
                tamper
            )
        )

        conn.commit()

    conn.close()

    st.write("OK")

    return True


# Run ingestion
if handle_sigfox():
    st.stop()


# =====================================================
# LOAD DEVICES
# =====================================================

@st.cache_data(ttl=60)
def load_devices():

    conn = get_conn()

    df = pd.read_sql(
        "SELECT device_id FROM devices ORDER BY device_id",
        conn
    )

    conn.close()

    return df


# =====================================================
# LOAD READINGS
# =====================================================

@st.cache_data(ttl=60)
def load_readings(device):

    conn = get_conn()

    df = pd.read_sql(
        """
        SELECT *
        FROM readings
        WHERE device_id=%s
        ORDER BY timestamp DESC
        LIMIT 500
        """,
        conn,
        params=(device,)
    )

    conn.close()

    return df


# =====================================================
# UI
# =====================================================

st.sidebar.title("Devices")

devices = load_devices()

if devices.empty:
    st.warning("Waiting for Sigfox data...")
    st.stop()

device = st.sidebar.selectbox(
    "Select Device",
    devices["device_id"]
)

st.title(f"AcuFox Dashboard — {device}")

data = load_readings(device)

if data.empty:
    st.warning("No readings yet")
    st.stop()

latest = data.iloc[0]

col1, col2, col3 = st.columns(3)

col1.metric("Volume (m³)", round(latest.volume_m3, 2))
col2.metric("Battery (%)", latest.battery_percent)
col3.metric("Leak", "YES" if latest.leak_flag else "NO")

st.subheader("Volume History")

chart = data.sort_values("timestamp")

st.line_chart(
    chart.set_index("timestamp")["volume_m3"]
)

st.subheader("Recent Readings")

st.dataframe(data, use_container_width=True)
