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

from components.calendar import render_pollution_calendar
from components.charts import render_histogram, render_main_chart
from components.comparisons import render_office_comparison, render_who_comparison
from components.forecast import render_forecast
from components.header import render_header
from components.heatmap import render_heatmap
from components.insights import render_health_recommendation, render_insights_panel, generate_insights
from components.kpi_cards import render_kpi_cards
from components.peak_detection import render_peak_events
from components.raw_data import render_raw_data
from components.sidebar import render_sidebar, render_sidebar_export
from components.statistics import render_statistics_cards
from components.theme import inject_global_css
from components.weekly_comparison import render_weekly_comparison
from utils.data import fetch_readings
from utils.health import build_recommendations

st.set_page_config(page_title="BMV080 Air Quality", page_icon="🌫️", layout="wide")
inject_global_css()

tz_offset_int, hours_back, resample_rule, range_label = render_sidebar()
device_id = st.secrets.get("device_id", "unknown")
render_header(device_id, tz_offset_int)

now = datetime.now(timezone.utc)
df = fetch_readings(int((now - timedelta(hours=hours_back)).timestamp()), int(now.timestamp()))
tab_id = f"h{hours_back}"

if df.empty:
    st.info(f"No readings in the {range_label.lower()} yet.")
else:
    render_kpi_cards(df, tab_id)
    st.divider()

    st.subheader("📈 Air Quality Trend")
    render_main_chart(df, resample_rule, tz_offset_int, tab_id)
    st.divider()

    col_heat, col_insights = st.columns([3, 2])
    with col_heat:
        st.subheader("🗓️ Hourly Pattern")
        render_heatmap(df, tz_offset_int, tab_id)
    with col_insights:
        st.subheader("💡 Key Insights")
        render_insights_panel(df, tz_offset_int)
    st.divider()

    st.subheader("🩺 Health Recommendation")
    render_health_recommendation(df, tz_offset_int)
    st.divider()

    col_who, col_office = st.columns(2)
    with col_who:
        st.subheader("🌍 WHO Standard Comparison")
        render_who_comparison(df)
    with col_office:
        st.subheader("🏢 Office vs. Non-Office")
        render_office_comparison(df, tz_offset_int)
    st.divider()

    st.subheader("📊 Pollution Distribution")
    render_histogram(df, tab_id)
    st.divider()

    st.subheader("📆 Week-over-Week Comparison")
    render_weekly_comparison()
    st.divider()

    col_forecast, col_calendar = st.columns([2, 3])
    with col_forecast:
        st.subheader("🔮 Forecast")
        render_forecast(df, tab_id)
    with col_calendar:
        st.subheader("🗓️ Pollution Calendar")
        render_pollution_calendar(tz_offset_int)
    st.divider()

    st.subheader("⚡ Pollution Events")
    render_peak_events(df, tz_offset_int)
    st.divider()

    with st.expander("📈 Detailed Statistics"):
        render_statistics_cards(df, hours_back)

    with st.expander("🗂️ Raw Data"):
        render_raw_data(df, tz_offset_int, tab_id)

    insights = generate_insights(df, tz_offset_int)
    recommendations = build_recommendations(df, tz_offset_int)
    render_sidebar_export(df, device_id, range_label, insights, recommendations)
