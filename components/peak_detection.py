"""Detected pollution spikes - a reading more than 2 std devs above its
trailing rolling mean (see utils.calculations.detect_peaks)."""

from datetime import timezone, timedelta

import pandas as pd
import streamlit as st

from utils.calculations import detect_peaks, guess_peak_cause
from utils.colors import PM_CARD_DEFS


def render_peak_events(df: pd.DataFrame, tz_offset: int):
    local_tz = timezone(timedelta(hours=tz_offset))
    all_events = []
    for card in PM_CARD_DEFS:
        spikes = detect_peaks(df, card["key"])
        for _, row in spikes.iterrows():
            local_time = row["timestamp"].tz_convert(local_tz)
            all_events.append({
                "time": local_time,
                "metric": card["label"],
                "value": row[card["key"]],
                "cause": guess_peak_cause(local_time.hour),
            })

    if not all_events:
        st.info("No pollution spikes detected in this period (or not enough history yet to establish a baseline).")
        return

    all_events.sort(key=lambda e: e["time"], reverse=True)
    for e in all_events[:10]:
        st.markdown(
            f"**{e['time'].strftime('%b %d, %H:%M')}** &middot; {e['metric']} "
            f"reached **{e['value']:.1f} µg/m³** &mdash; {e['cause']}"
        )
        st.markdown("---")
