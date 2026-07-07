"""Hour-of-day x calendar-date heatmap - reveals when pollution peaks
without needing weeks of history to be useful (unlike a weekday-aggregated
version, which would need several full weeks to fill in every cell)."""

from datetime import timezone, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.colors import PM_CARD_DEFS

MIN_DAYS_FOR_HEATMAP = 2
MIN_POINTS_FOR_HEATMAP = 10


def render_heatmap(df: pd.DataFrame, tz_offset: int, tab_id: str):
    local_tz = timezone(timedelta(hours=tz_offset))
    d = df.copy()
    d["local_dt"] = d["timestamp"].dt.tz_convert(local_tz)
    d["date"] = d["local_dt"].dt.strftime("%b %d")
    d["hour"] = d["local_dt"].dt.hour

    n_days = d["date"].nunique()
    if n_days < MIN_DAYS_FOR_HEATMAP or len(d) < MIN_POINTS_FOR_HEATMAP:
        st.info(
            f"Not enough data yet for an hour-vs-day heatmap "
            f"(have {n_days} day(s), {len(d)} reading(s) - need at least "
            f"{MIN_DAYS_FOR_HEATMAP} days and {MIN_POINTS_FOR_HEATMAP} readings). "
            f"This fills in automatically as more data arrives."
        )
        return

    labels = [c["label"] for c in PM_CARD_DEFS]
    choice = st.selectbox("Pollutant", labels, index=1 if "PM2.5" in labels else 0, key=f"heatmap_select_{tab_id}")
    pm_key = next(c["key"] for c in PM_CARD_DEFS if c["label"] == choice)

    pivot = d.pivot_table(index="hour", columns="date", values=pm_key, aggfunc="mean")
    # Keep calendar order (not alphabetical string order) and a full 0-23 hour axis.
    date_order = d.drop_duplicates("date").sort_values("local_dt")["date"].tolist()
    pivot = pivot.reindex(index=range(24), columns=date_order)

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=[f"{h:02d}:00" for h in pivot.index],
        colorscale=[[0, "#e6f7e6"], [0.5, "#ffe680"], [1, "#ff4d4d"]],
        colorbar=dict(title="µg/m³"),
        hovertemplate="%{x} %{y}<br>%{z:.1f} µg/m³<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
        height=460,
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig, width="stretch", key=f"heatmap_{tab_id}_{pm_key}")
