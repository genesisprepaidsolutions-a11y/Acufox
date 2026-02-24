
# Aquaflow Enterprise

## Features
- PostgreSQL backend
- Sigfox automatic sync
- 100k+ device support
- Enterprise Streamlit dashboard

## Setup

1. Create PostgreSQL database
2. Run schema.sql
3. Set Streamlit secrets

Example secrets.toml:

SIGFOX_LOGIN=""
SIGFOX_PASSWORD=""
SIGFOX_DEVICE_TYPE=""

DB_HOST=""
DB_NAME=""
DB_USER=""
DB_PASSWORD=""
DB_PORT="5432"

## Run sync
python sync.py

## Run dashboard
streamlit run app.py
