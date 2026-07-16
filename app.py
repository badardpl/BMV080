"""
BMV080 Indoor Air Quality Dashboard

Reads PM1/PM2.5/PM10 averages published by the ESP32 firmware (via AWS IoT
-> DynamoDB) and shows a single-page analytics dashboard: KPI cards, trend
chart, heatmap, AI insights, WHO/office comparisons, weekly comparison,
peak detection, a pollution calendar, a simple forecast, statistics, and
raw data - all scoped to one Date Range control in the sidebar.

Required st.secrets keys (see .streamlit/secrets.toml.example):
  aws_access_key_id, aws_secret_access_key, aws_region, table_name, device_id
"""

from datetime import datetime, timedelta, timezone

import streamlit as st

from components.daily_view import render_daily_view
from components.header import render_header
from components.sidebar import render_sidebar
from components.theme import inject_global_css
from utils.data import fetch_all_readings

st.set_page_config(page_title="BMV080 Air Quality", page_icon="🌫️", layout="wide")
inject_global_css()

tz_offset_int, post_enabled, smoothing_window = render_sidebar()
device_id = st.secrets.get("device_id", "unknown")
render_header(device_id, tz_offset_int)

df = fetch_all_readings()

# ── Postprocessing ──────────────────────────────────────────────────────────
# 1. Filter invalid zeros (toggle-controlled)
if post_enabled and not df.empty:
    before = len(df)
    valid = (df["pm1"] >= 0.5) | (df["pm2_5"] >= 0.5) | (df["pm10"] >= 0.5)
    df = df[valid].copy()

# 2. Spike detection & replacement (always applied)
if not df.empty and len(df) >= 3:
    for col in ["pm1", "pm2_5", "pm10"]:
        values = df[col].values.copy()
        for i in range(1, len(values) - 1):
            if abs(values[i] - values[i - 1]) > 10 and abs(values[i] - values[i + 1]) > 7:
                values[i] = (values[i - 1] + values[i + 1]) / 2
        df[col] = values

# 3. Rolling mean smoothing (toggle-controlled)
if post_enabled and not df.empty and smoothing_window > 1 and len(df) >= smoothing_window:
    for col in ["pm1", "pm2_5", "pm10"]:
        df[col] = df[col].rolling(window=smoothing_window, center=True).mean()
    df = df.dropna().reset_index(drop=True)


if df.empty:
    st.info("No readings yet.")
else:
    render_daily_view(df, tz_offset_int)
