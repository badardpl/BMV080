"""Expanded data views for the dashboard's More page."""

from datetime import timedelta, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.colors import PM_CARD_DEFS, PM_ZONE_MAP, SERIES_COLORS


PM_COLUMNS = ["pm1", "pm2_5", "pm10"]
PM_LABELS = {"pm1": "PM1", "pm2_5": "PM2.5", "pm10": "PM10"}
SENSOR_COLUMNS = [*PM_COLUMNS, "temp_c", "humidity"]
SENSOR_LABELS = {**PM_LABELS, "temp_c": "Temperature (°C)", "humidity": "Humidity (%)"}


def _local_readings(df: pd.DataFrame, tz_offset: int) -> pd.DataFrame:
    local = df.copy()
    local["local_time"] = local["timestamp"].dt.tz_convert(timezone(timedelta(hours=tz_offset)))
    return local


def _summary(local: pd.DataFrame, period: str) -> pd.DataFrame:
    grouped = local.set_index("local_time")[SENSOR_COLUMNS].resample(period).agg(["mean", "min", "max", "count"])
    grouped.columns = [f"{SENSOR_LABELS[column]} {stat.title()}" for column, stat in grouped.columns]
    return grouped.reset_index().rename(columns={"local_time": "Period"})


def _trend_chart(data: pd.DataFrame, time_col: str, pm_key: str, title: str) -> go.Figure:
    """Draw a pollutant trend using the same air-quality bands as Analytics."""
    values = data[pm_key]
    y_min = max(0, values.min() - max(2, values.max() * 0.08))
    y_max = values.max() + max(5, values.max() * 0.12)
    fig = go.Figure()

    for low, high, label, color, fill in PM_ZONE_MAP[pm_key]:
        if max(low, y_min) < min(high, y_max):
            fig.add_hrect(
                y0=max(low, y_min), y1=min(high, y_max), fillcolor=fill,
                line_width=0, annotation_text=label, annotation_position="right",
                annotation=dict(font_size=10, font_color=color),
            )

    fig.add_trace(go.Scatter(
        x=data[time_col], y=values, mode="lines+markers",
        line=dict(color=SERIES_COLORS[pm_key], width=2), marker=dict(size=5),
        hovertemplate="%{x|%b %d, %Y %H:%M}<br><b>%{y:.1f} µg/m³</b><extra></extra>",
    ))
    fig.update_layout(
        title=title, height=360, margin=dict(l=0, r=75, t=40, b=0),
        paper_bgcolor="white", plot_bgcolor="white", showlegend=False,
        xaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
        yaxis=dict(range=[y_min, y_max], ticksuffix=" µg/m³", showgrid=True, gridcolor="#f0f0f0"),
    )
    return fig


def _show_summary(local: pd.DataFrame, period: str, title: str, key: str, pm_key: str) -> None:
    """Allow the user to select a period and inspect its detailed trend."""
    if period == "MS":
        period_starts = local["local_time"].dt.strftime("%Y-%m-01")
        options = sorted(period_starts.unique(), reverse=True)
        selected = st.selectbox("Select month", options, format_func=lambda value: pd.Timestamp(value).strftime("%B %Y"), key="more_month")
        chosen_start = pd.Timestamp(selected, tz=local["local_time"].dt.tz)
        chosen_end = chosen_start + pd.DateOffset(months=1)
        selected_data = local[(local["local_time"] >= chosen_start) & (local["local_time"] < chosen_end)]
        graph_title = f"{pd.Timestamp(selected).strftime('%B %Y')} — {PM_LABELS[pm_key]}"
    else:
        local_dates = local["local_time"].dt.normalize()
        week_starts = local_dates - pd.to_timedelta(local["local_time"].dt.weekday, unit="D")
        options = sorted(week_starts.unique(), reverse=True)
        selected = st.selectbox(
            "Select week", options,
            format_func=lambda value: f"{pd.Timestamp(value).strftime('%b %d')} – {(pd.Timestamp(value) + pd.Timedelta(days=6)).strftime('%b %d, %Y')}",
            key="more_week",
        )
        chosen_start = pd.Timestamp(selected)
        chosen_end = chosen_start + pd.Timedelta(days=7)
        selected_data = local[(local["local_time"] >= chosen_start) & (local["local_time"] < chosen_end)]
        graph_title = f"Week of {pd.Timestamp(selected).strftime('%b %d, %Y')} — {PM_LABELS[pm_key]}"

    st.plotly_chart(
        _trend_chart(selected_data, "local_time", pm_key, graph_title),
        width="stretch", key=f"{key}_{pm_key}_trend",
    )
    summary = _summary(local, period)
    summary["Period"] = summary["Period"].dt.strftime("%b %d, %Y" if period == "W-MON" else "%B %Y")
    st.subheader(title)
    st.caption("Average, minimum, maximum, and number of readings for each period.")
    st.dataframe(summary, width="stretch", hide_index=True)
    st.download_button(
        "Download summary CSV",
        data=summary.to_csv(index=False).encode("utf-8"),
        file_name=f"bmv080_{key}_summary.csv",
        mime="text/csv",
        key=f"download_{key}_summary",
    )


def render_more_data(df: pd.DataFrame, tz_offset: int) -> None:
    """Render complete, month-wise, and week-wise historical data."""
    st.title("More data")
    st.caption("Explore the full measurement history, grouped by week or month.")
    local = _local_readings(df, tz_offset)
    labels = [item["label"] for item in PM_CARD_DEFS]
    selected_label = st.selectbox("Pollutant", labels, index=1, key="more_pollutant")
    pm_key = next(item["key"] for item in PM_CARD_DEFS if item["label"] == selected_label)

    complete_tab, monthly_tab, weekly_tab = st.tabs(["Complete data", "Month-wise", "Weekly"])
    with complete_tab:
        st.plotly_chart(
            _trend_chart(local, "local_time", pm_key, f"Complete history — {selected_label}"),
            width="stretch", key=f"complete_{pm_key}_trend",
        )
        display = local[["local_time", *SENSOR_COLUMNS]].copy()
        display["local_time"] = display["local_time"].dt.strftime("%Y-%m-%d %H:%M")
        display = display.rename(columns={
            "local_time": "Local time", **SENSOR_LABELS,
        })
        st.dataframe(display, width="stretch", hide_index=True)
        st.caption(f"{len(display):,} readings")
        st.download_button(
            "Download complete data CSV",
            data=display.to_csv(index=False).encode("utf-8"),
            file_name="bmv080_complete_data.csv",
            mime="text/csv",
            key="download_complete_data",
        )

    with monthly_tab:
        _show_summary(local, "MS", "Monthly summary", "monthly", pm_key)

    with weekly_tab:
        _show_summary(local, "W-MON", "Weekly summary", "weekly", pm_key)
