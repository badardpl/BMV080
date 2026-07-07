"""Raw data table: text search, a numeric column filter, and CSV export.
Column sorting is free - st.dataframe already supports click-to-sort."""

from datetime import timezone, timedelta

import pandas as pd
import streamlit as st

from utils.colors import PM_CARD_DEFS


def render_raw_data(df: pd.DataFrame, tz_offset: int, tab_id: str):
    tz = timezone(timedelta(hours=tz_offset))
    disp = df.copy()
    disp["local_time"] = disp["timestamp"].dt.tz_convert(tz).dt.strftime("%Y-%m-%d %H:%M")
    disp["utc_time"] = disp["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
    disp = disp[["utc_time", "local_time", "pm1", "pm2_5", "pm10"]]

    search = st.text_input("Search", placeholder="Filter rows (matches any column)...", key=f"raw_search_{tab_id}")

    labels = [c["label"] for c in PM_CARD_DEFS]
    filter_col = st.selectbox("Filter by", ["(none)"] + labels, key=f"raw_filter_col_{tab_id}")

    filtered = disp
    if filter_col != "(none)":
        pm_key = next(c["key"] for c in PM_CARD_DEFS if c["label"] == filter_col)
        lo, hi = float(disp[pm_key].min()), float(disp[pm_key].max())
        if lo < hi:
            selected = st.slider(f"{filter_col} range (µg/m³)", lo, hi, (lo, hi), key=f"raw_filter_range_{tab_id}")
            filtered = filtered[(filtered[pm_key] >= selected[0]) & (filtered[pm_key] <= selected[1])]

    if search:
        mask = filtered.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
        filtered = filtered[mask]

    st.dataframe(filtered, width="stretch", hide_index=True)
    st.caption(f"{len(filtered)} of {len(disp)} readings shown")

    st.download_button(
        "⬇️ Download CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="bmv080_readings.csv",
        mime="text/csv",
        key=f"raw_csv_{tab_id}",
    )
