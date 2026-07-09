"""WHO-guideline progress bars and Office vs. Non-Office comparison bars."""

from datetime import timezone, timedelta

import pandas as pd
import streamlit as st

from utils.calculations import WHO_24H_LIMITS
from utils.colors import PM_CARD_DEFS, SERIES_COLORS


def render_who_comparison(df: pd.DataFrame):
    latest = df.iloc[-1]
    st.markdown("##### WHO 24-Hour Guideline Comparison (current reading)")
    for card in PM_CARD_DEFS:
        val = latest[card["key"]]
        limit = WHO_24H_LIMITS[card["key"]]
        pct = val / limit * 100
        status = "Above Recommended" if pct > 100 else "Within Recommended"
        st.markdown(
            f"**{card['label']}** — Current: {val:.1f} µg/m³ &middot; WHO Limit: {limit:.0f} µg/m³"
        )
        st.progress(min(pct, 100) / 100, text=f"{pct:.0f}% of WHO limit — {status}")


def _bar_row(label: str, value: float, max_value: float, color: str):
    width_pct = 0 if max_value == 0 else min(value / max_value * 100, 100)
    st.markdown(
        f"""
        <div style="margin-bottom:10px;">
            <div style="display:flex;justify-content:space-between;font-size:12px;color:#64748B;">
                <span>{label}</span><span>{value:.1f} µg/m³</span>
            </div>
            <div style="background:#E2E8F0;border-radius:6px;height:14px;overflow:hidden;">
                <div style="background:{color};width:{width_pct:.0f}%;height:100%;"></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_office_comparison(df: pd.DataFrame, tz_offset: int):
    local_tz = timezone(timedelta(hours=tz_offset))
    d = df.copy()
    d["local_hour"] = d["timestamp"].dt.tz_convert(local_tz).dt.hour
    os_start = st.session_state.get("office_start", 10)
    os_end = st.session_state.get("office_end", 21)
    d["is_office"] = d["local_hour"].between(os_start, os_end - 1)

    office_df, nonoffice_df = d[d["is_office"]], d[~d["is_office"]]
    if office_df.empty or nonoffice_df.empty:
        st.info("Need readings from both office and non-office hours to compare.")
        return

    for card in PM_CARD_DEFS:
        off_val = office_df[card["key"]].mean()
        noff_val = nonoffice_df[card["key"]].mean()
        max_val = max(off_val, noff_val, 1)
        color = SERIES_COLORS[card["key"]]

        st.markdown(f"**{card['label']}**")
        _bar_row("Office", off_val, max_val, color)
        _bar_row("Non-Office", noff_val, max_val, color)

        if off_val < noff_val:
            pct = (noff_val - off_val) / noff_val * 100 if noff_val else 0
            st.caption(f"Office is {pct:.0f}% cleaner than non-office hours")
        elif noff_val < off_val:
            pct = (off_val - noff_val) / off_val * 100 if off_val else 0
            st.caption(f"Office is {pct:.0f}% worse than non-office hours")
        else:
            st.caption("No measurable difference")
