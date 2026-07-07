"""One consolidated trend chart (metric dropdown + Compare All) and the
pollution-distribution histogram. Zoom/pan/download-image are Plotly's
default modebar behavior - nothing extra needed as long as the modebar
isn't disabled (it isn't, here).
"""

from datetime import timezone, timedelta
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.analytics import OFFICE_START, OFFICE_END
from utils.colors import PM_CARD_DEFS, SERIES_COLORS


def _office_hours_shading(fig: go.Figure, index: pd.DatetimeIndex):
    if index.empty:
        return
    # end must NOT be ceil()'d - see git history: rounding up into a day with
    # no data adds a phantom shaded region that drags the axis autorange wide.
    dr = pd.date_range(start=index.min().floor("1D"), end=index.max(), freq="1D", tz=index.tz)
    for d in dr:
        fig.add_vrect(
            x0=d + timedelta(hours=OFFICE_START), x1=d + timedelta(hours=OFFICE_END),
            fillcolor="rgba(0, 228, 0, 0.08)", layer="below", line_width=0,
        )


def _tick_settings(resample_rule: Optional[str]):
    if resample_rule is None:
        return "%a %H:%M", 8
    if resample_rule == "1h":
        return "%b %d", 8
    return "%b %d", 10


def render_main_chart(df: pd.DataFrame, resample_rule: Optional[str], tz_offset: int, tab_id: str):
    labels = [c["label"] for c in PM_CARD_DEFS] + ["Compare All"]
    choice = st.selectbox("Metric", labels, index=1 if "PM2.5" in labels else 0, key=f"metric_select_{tab_id}")

    plot_df = df.set_index("timestamp")
    if resample_rule:
        plot_df = plot_df.resample(resample_rule).mean()
    plot_df.index = plot_df.index.tz_convert(timezone(timedelta(hours=tz_offset)))

    fig = go.Figure()
    if choice == "Compare All":
        for card in PM_CARD_DEFS:
            fig.add_trace(go.Scatter(
                x=plot_df.index, y=plot_df[card["key"]], mode="lines", name=card["label"],
                line=dict(color=SERIES_COLORS[card["key"]], width=2),
                hovertemplate="%{y:.1f} µg/m³<extra>" + card["label"] + "</extra>",
            ))
        show_legend = True
        selected_keys = [c["key"] for c in PM_CARD_DEFS]
    else:
        pm_key = next(c["key"] for c in PM_CARD_DEFS if c["label"] == choice)
        fig.add_trace(go.Scatter(
            x=plot_df.index, y=plot_df[pm_key], mode="lines",
            line=dict(color=SERIES_COLORS[pm_key], width=2),
            hovertemplate="%{y:.1f} µg/m³<extra></extra>",
        ))
        show_legend = False
        selected_keys = [pm_key]

    _office_hours_shading(fig, plot_df.index)
    tick_format, n_ticks = _tick_settings(resample_rule)
    x_range = [plot_df.index.min(), plot_df.index.max()] if not plot_df.empty else None

    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=20, b=10),
        showlegend=show_legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        yaxis_title="µg/m³",
        hovermode="x unified",
        height=380,
        transition={"duration": 300},
    )
    fig.update_xaxes(showgrid=False, nticks=n_ticks, tickformat=tick_format, tickangle=0, range=x_range)
    fig.update_yaxes(showgrid=True, gridcolor="#e1e0d9")

    st.plotly_chart(fig, width="stretch", key=f"main_chart_{tab_id}_{choice}")

    stat_cols = st.columns(len(selected_keys) * 3)
    i = 0
    for key in selected_keys:
        label = next(c["label"] for c in PM_CARD_DEFS if c["key"] == key)
        stat_cols[i].metric(f"{label} Avg", f"{plot_df[key].mean():.1f}")
        stat_cols[i + 1].metric(f"{label} Min", f"{plot_df[key].min():.1f}")
        stat_cols[i + 2].metric(f"{label} Max", f"{plot_df[key].max():.1f}")
        i += 3


def render_histogram(df: pd.DataFrame, tab_id: str):
    labels = [c["label"] for c in PM_CARD_DEFS]
    choice = st.selectbox("Pollutant", labels, index=1 if "PM2.5" in labels else 0, key=f"hist_select_{tab_id}")
    pm_key = next(c["key"] for c in PM_CARD_DEFS if c["label"] == choice)

    fig = go.Figure(go.Histogram(
        x=df[pm_key], marker=dict(color=SERIES_COLORS[pm_key]),
        xbins=dict(size=5),
    ))
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title=f"{choice} (µg/m³)",
        yaxis_title="Frequency",
        height=300,
        bargap=0.05,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#e1e0d9")
    st.plotly_chart(fig, width="stretch", key=f"hist_{tab_id}_{pm_key}")
