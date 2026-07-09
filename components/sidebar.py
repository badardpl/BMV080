"""Sidebar: date-range/auto-refresh/theme/postprocessing/office-hours/device controls."""

from datetime import datetime, timezone, timedelta

import streamlit as st

DATE_RANGES = {
    "Last 24 Hours": (24, None),
    "Last 48 Hours": (48, None),
    "Last 7 Days": (24 * 7, "1h"),
    "Last 30 Days": (24 * 30, "1D"),
}

AUTO_REFRESH_OPTIONS = {"Off": 0, "1 min": 60, "5 min": 300, "15 min": 900}


def render_sidebar():
    """Returns (tz_offset_int, hours_back, resample_rule, range_label,
               post_enabled, smoothing_window)."""
    with st.sidebar:
        tz_offset_int = 5

        range_label = st.selectbox("📅 Date Range", list(DATE_RANGES.keys()), index=1)
        hours_back, resample_rule = DATE_RANGES[range_label]

        refresh_choice = st.selectbox("🔁 Auto Refresh", list(AUTO_REFRESH_OPTIONS.keys()), index=0)
        seconds = AUTO_REFRESH_OPTIONS[refresh_choice]
        if seconds > 0:
            _auto_refresh_tick(seconds)

        st.toggle("🌙 Dark Mode", key="dark_mode")

        st.markdown("---")
        post_enabled = st.toggle("🔧 Smoothing & filtering", value=False, key="post_enabled")
        if post_enabled:
            smoothing_window = st.slider("Window (points)", 3, 15, 5, key="smoothing_window")
        else:
            smoothing_window = 1

        st.markdown("---")
        st.markdown("**🏢 Office Hours**")
        office_start = st.slider("Start hour", 0, 23, 10, key="office_start")
        office_end   = st.slider("End hour",   0, 23, 21, key="office_end")
        local_now = datetime.now(timezone(timedelta(hours=tz_offset_int)))
        if office_start <= local_now.hour < office_end:
            st.success("🔵 Office hours now")
        else:
            st.warning("⚪ Non-office hours now")

        st.markdown("---")
        device_id = st.secrets.get("device_id", "unknown")
        st.markdown(f"**Device:** `{device_id}`")

    return tz_offset_int, hours_back, resample_rule, range_label, post_enabled, smoothing_window


def _auto_refresh_tick(seconds: int):
    @st.fragment(run_every=seconds)
    def _tick():
        st.cache_data.clear()
        st.rerun()
    _tick()
