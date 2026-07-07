"""Current 7 days vs. the previous 7 days, per pollutant."""

from datetime import datetime, timedelta, timezone

import streamlit as st

from utils.calculations import pct_change
from utils.colors import PM_CARD_DEFS
from utils.data import fetch_readings


def render_weekly_comparison():
    now = datetime.now(timezone.utc)
    current = fetch_readings(int((now - timedelta(days=7)).timestamp()), int(now.timestamp()))
    previous = fetch_readings(int((now - timedelta(days=14)).timestamp()), int((now - timedelta(days=7)).timestamp()))

    if current.empty or previous.empty:
        st.info("Need at least two full weeks of history to compare week-over-week - this fills in automatically.")
        return

    cols = st.columns(len(PM_CARD_DEFS))
    for col, card in zip(cols, PM_CARD_DEFS):
        cur_avg = current[card["key"]].mean()
        prev_avg = previous[card["key"]].mean()
        change = pct_change(cur_avg, prev_avg)
        with col:
            st.markdown(f"**{card['label']}**")
            st.metric(
                "This week", f"{cur_avg:.1f} µg/m³",
                delta=f"{change:+.0f}% vs last week" if change is not None else None,
                delta_color="inverse",  # falling PM = improving, so a negative delta should read as good
            )
            st.caption(f"Last week: {prev_avg:.1f} µg/m³")
