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

def get_conn():

    return psycopg2.connect(
        host="aws-1-eu-central-1.pooler.supabase.com",
        port=6543,
        database="postgres",
        user="postgres.uxtddangntejpwaovnmv",
        password="Acucomm2808",
        sslmode="require",
        connect_timeout=10
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

# =====================================================
# SIGFOX INGESTION (FIXED FOR PRODUCTION)
# =====================================================
def handle_sigfox():
    """
    Handles incoming Sigfox callback safely:
    - Decodes payload
    - Uses fresh DB connection
    - Handles errors gracefully
    - Avoids cached/closed connection issues
    """

    params = st.query_params

    # No device? skip
    if "device" not in params:
        return False

    device = params["device"]
    payload = params.get("data")
    ts = params.get("time")

    # No payload? skip
    if not payload:
        return True

    # Decode payload safely
    try:
        volume, battery, leak, tamper = decode_payload(payload)
    except Exception as e:
        st.error(f"❌ Failed to decode payload: {e}")
        return True

    # Timestamp handling
    try:
        timestamp = datetime.utcfromtimestamp(int(ts)) if ts else datetime.utcnow()
    except Exception:
        timestamp = datetime.utcnow()

    # Insert into DB using a fresh connection
    try:
        conn = get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT insert_sigfox_reading(
                    %s, %s, %s, %s, %s, %s
                )
                """,
                (device, timestamp, volume, battery, leak, tamper)
            )
            conn.commit()
    except Exception as e:
        st.error(f"❌ Failed to insert reading: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass  # Ignore if connection already closed

    st.write("✅ Sigfox payload ingested successfully")

    return True


# =====================================================
# LOAD DEVICES
# =====================================================

@st.cache_data(ttl=60)
def load_devices():

    conn = get_conn()

    try:

        df = pd.read_sql(
            "SELECT device_id FROM devices ORDER BY device_id",
            conn
        )

        return df

    finally:

        conn.close()


# =====================================================
# LOAD READINGS
# =====================================================

@st.cache_data(ttl=60)
def load_readings(device):

    conn = get_conn()

    try:

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

        return df

    finally:

        conn.close()


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
