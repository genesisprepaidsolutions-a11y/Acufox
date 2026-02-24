
import requests
import psycopg2
import base64
import time
import os

SIGFOX_LOGIN = os.environ["SIGFOX_LOGIN"]
SIGFOX_PASSWORD = os.environ["SIGFOX_PASSWORD"]
DEVICE_TYPE = os.environ["SIGFOX_DEVICE_TYPE"]

DB = {
    "host": os.environ["DB_HOST"],
    "database": os.environ["DB_NAME"],
    "user": os.environ["DB_USER"],
    "password": os.environ["DB_PASSWORD"],
    "port": os.environ.get("DB_PORT", 5432)
}

def connect():
    return psycopg2.connect(**DB)

def get_devices():
    url = f"https://backend.sigfox.com/api/devicetypes/{DEVICE_TYPE}/devices"
    r = requests.get(url, auth=(SIGFOX_LOGIN, SIGFOX_PASSWORD))
    return r.json()["data"]

def get_messages(device_id):
    url = f"https://backend.sigfox.com/api/devices/{device_id}/messages"
    r = requests.get(url, auth=(SIGFOX_LOGIN, SIGFOX_PASSWORD))
    return r.json()["data"]

def decode_payload(payload):
    raw = base64.b64decode(payload)
    volume = int.from_bytes(raw[0:4], "big") / 1000
    battery = raw[4] / 255 * 100
    flags = raw[5]
    leak = bool(flags & 0x01)
    tamper = bool(flags & 0x02)
    return volume, battery, leak, tamper

def run():
    conn = connect()
    cur = conn.cursor()

    devices = get_devices()

    for d in devices:
        device_id = d["id"]

        cur.execute("INSERT INTO devices(device_id) VALUES(%s) ON CONFLICT DO NOTHING", (device_id,))

        messages = get_messages(device_id)

        for m in messages:
            volume, battery, leak, tamper = decode_payload(m["data"])

            cur.execute(
                """
                INSERT INTO messages(device_id, timestamp, volume_m3, battery_percent, leak_flag, tamper_flag)
                VALUES(%s, to_timestamp(%s), %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (device_id, m["time"], volume, battery, leak, tamper)
            )

        conn.commit()

    conn.close()

if __name__ == "__main__":
    run()
