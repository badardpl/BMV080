"""Sidebar: device/timezone/date-range/auto-refresh/theme controls, plus
(rendered later, once data exists) the CSV/PDF export buttons.
"""

from datetime import datetime, timezone, timedelta

import pandas as pd
import streamlit as st

from utils.analytics import OFFICE_START, OFFICE_END
from utils.colors import AQI_CATEGORIES

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
        st.markdown("## 🌫️ BMV080")
        st.markdown("<p style='color:#64748B;font-size:13px;margin-top:-8px;'>Air Quality Dashboard</p>",
                    unsafe_allow_html=True)
        st.markdown("---")

        tz_offset = st.selectbox(
            "🌍 Timezone",
            options=[f"UTC{'+' if h >= 0 else ''}{h}" for h in range(-12, 15)],
            index=17,
            help="Display timestamps in your local timezone",
        )
        tz_offset_int = int(tz_offset.replace("UTC", "").replace("+", ""))

        range_label = st.selectbox("📅 Date Range", list(DATE_RANGES.keys()), index=1)
        hours_back, resample_rule = DATE_RANGES[range_label]

        refresh_choice = st.selectbox("🔁 Auto Refresh", list(AUTO_REFRESH_OPTIONS.keys()), index=0)
        seconds = AUTO_REFRESH_OPTIONS[refresh_choice]
        if seconds > 0:
            _auto_refresh_tick(seconds)

        st.toggle("🌙 Dark Mode", key="dark_mode")

        st.markdown("---")
        st.markdown("### 🔧 Postprocessing")
        post_enabled = st.toggle("Enable smoothing & filtering", value=False, key="post_enabled")
        if post_enabled:
            smoothing_window = st.slider("Smoothing window (points)", 3, 15, 5, key="smoothing_window")
        else:
            smoothing_window = 1
        st.caption("Filters invalid zeros & applies rolling mean when enabled.")

        st.markdown("---")
        st.markdown("### 🏢 Office Hours")
        st.markdown("10:00 AM – 9:00 PM")
        local_now = datetime.now(timezone(timedelta(hours=tz_offset_int)))
        st.caption(f"Current local: {local_now.strftime('%Y-%m-%d %H:%M')}")
        if OFFICE_START <= local_now.hour < OFFICE_END:
            st.success("🔵 Office hours now")
        else:
            st.warning("⚪ Non-office hours now")

        st.markdown("---")
        st.markdown("### 🟧 AQI Reference")
        for name, color, _ in AQI_CATEGORIES:
            fg = "#000" if name in ("Good", "Moderate") else "#fff"
            st.markdown(
                f'<span style="display:inline-block;background:{color};color:{fg};'
                f'font-size:11px;font-weight:600;padding:2px 14px;border-radius:10px;margin:2px 0;">'
                f'{name}</span>',
                unsafe_allow_html=True,
            )

        st.markdown("---")
        device_id = st.secrets.get("device_id", "unknown")
        st.markdown(f"**Device:** `{device_id}`")
        st.caption(f"Page updated: {datetime.now().strftime('%H:%M:%S')}")

    return tz_offset_int, hours_back, resample_rule, range_label, post_enabled, smoothing_window


def _auto_refresh_tick(seconds: int):
    @st.fragment(run_every=seconds)
    def _tick():
        st.cache_data.clear()
        st.rerun()
    _tick()


def render_sidebar_export(df: pd.DataFrame, device_id: str, range_label: str,
                          insights: list, recommendations: list):
    """Called after data/insights are available - appends export buttons to
    the same sidebar (Streamlit allows multiple `with st.sidebar:` blocks)."""
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📤 Export")
        st.download_button(
            "⬇️ Download CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="bmv080_readings.csv",
            mime="text/csv",
            key="sidebar_csv_export",
        )
        try:
            from utils.report import generate_pdf_report
            pdf_bytes = generate_pdf_report(df, device_id, range_label, insights, recommendations)
            st.download_button(
                "⬇️ Download PDF Report",
                data=pdf_bytes,
                file_name="bmv080_report.pdf",
                mime="application/pdf",
                key="sidebar_pdf_export",
            )
        except Exception as e:
            st.caption(f"PDF export unavailable: {e}")
