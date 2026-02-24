
CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    device_id TEXT,
    timestamp TIMESTAMP,
    volume_m3 FLOAT,
    battery_percent FLOAT,
    leak_flag BOOLEAN,
    tamper_flag BOOLEAN
);

CREATE INDEX IF NOT EXISTS idx_device_time ON messages(device_id, timestamp);
