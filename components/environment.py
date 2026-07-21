"""Temperature and humidity panel populated by optional SHT31 readings."""

from datetime import timedelta, timezone

import plotly.graph_objects as go
import pandas as pd
import streamlit as st


def render_environmental_data(df, tz_offset: int) -> None:
    """Render environmental readings when the device has published SHT31 data."""
    available = df.dropna(subset=["temp_c", "humidity"], how="all")
    if available.empty:
        return

    latest = available.iloc[-1]
    temp_col, humidity_col = st.columns(2)
    temp_col.metric("Temperature", f"{latest['temp_c']:.1f} °C" if pd.notna(latest["temp_c"]) else "—")
    humidity_col.metric("Humidity", f"{latest['humidity']:.1f}%" if pd.notna(latest["humidity"]) else "—")

    local = available.copy()
    local["local_time"] = local["timestamp"].dt.tz_convert(timezone(timedelta(hours=tz_offset)))
    fig = go.Figure()
    if local["temp_c"].notna().any():
        fig.add_trace(go.Scatter(x=local["local_time"], y=local["temp_c"], name="Temperature", mode="lines+markers", line=dict(color="#e45756")))
    if local["humidity"].notna().any():
        fig.add_trace(go.Scatter(x=local["local_time"], y=local["humidity"], name="Humidity", mode="lines+markers", line=dict(color="#378add"), yaxis="y2"))
    fig.update_layout(
        title="Temperature & humidity", height=310, margin=dict(l=0, r=0, t=42, b=0),
        paper_bgcolor="white", plot_bgcolor="white",
        yaxis=dict(title="Temperature (°C)", showgrid=True, gridcolor="#f0f0f0"),
        yaxis2=dict(title="Humidity (%)", overlaying="y", side="right", rangemode="tozero"),
        legend=dict(orientation="h", y=1.12),
    )
    st.plotly_chart(fig, width="stretch", key="environmental_trend")
