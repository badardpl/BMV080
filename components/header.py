"""Dashboard header: title, device, live clock, last-updated, online/offline, refresh."""

from datetime import datetime, timezone, timedelta

import streamlit as st

from utils.data import get_latest_reading, ONLINE_THRESHOLD_MINUTES


def render_header(device_id: str, tz_offset_int: int):
    local_tz = timezone(timedelta(hours=tz_offset_int))
    local_now = datetime.now(local_tz)

    latest = get_latest_reading()
    if latest is not None:
        latest_dt_utc = datetime.fromtimestamp(int(latest["ts"]), tz=timezone.utc)
        age_minutes = (datetime.now(timezone.utc) - latest_dt_utc).total_seconds() / 60
        is_online = age_minutes <= ONLINE_THRESHOLD_MINUTES
        last_updated_str = latest_dt_utc.astimezone(local_tz).strftime("%Y-%m-%d %H:%M")
    else:
        is_online = False
        last_updated_str = "never"

    status_html = (
        '<span class="bmv-status-badge" style="background:#dcfce7;color:#166534;">🟢 Online</span>'
        if is_online else
        '<span class="bmv-status-badge" style="background:#fee2e2;color:#991b1b;">🔴 Offline</span>'
    )

    with st.container(border=True):
        left, right, btn_col = st.columns([3, 2, 1])
        with left:
            st.markdown(
                '<div class="bmv-header-title">BMV080 Indoor Air Quality Dashboard</div>'
                f'<div class="bmv-header-sub">Device: <strong>{device_id}</strong> '
                f'&middot; Current time: {local_now.strftime("%Y-%m-%d %H:%M")}</div>',
                unsafe_allow_html=True,
            )
        with right:
            st.markdown(
                f'<div class="bmv-header-sub">Last updated: {last_updated_str}</div>'
                f'<div style="margin-top:4px;">{status_html}</div>',
                unsafe_allow_html=True,
            )
        with btn_col:
            if st.button("🔄 Refresh", width="stretch"):
                st.cache_data.clear()
                st.rerun()
