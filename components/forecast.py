"""Next-hour/6-hour/tomorrow estimate via simple moving average + trend
slope (utils.calculations.moving_average_forecast) - explicitly a first
pass per the spec; a real model is future work."""

import pandas as pd
import streamlit as st

from utils.calculations import moving_average_forecast
from utils.colors import PM_CARD_DEFS


def render_forecast(df: pd.DataFrame, tab_id: str):
    labels = [c["label"] for c in PM_CARD_DEFS]
    choice = st.selectbox("Pollutant", labels, index=1 if "PM2.5" in labels else 0, key=f"forecast_select_{tab_id}")
    pm_key = next(c["key"] for c in PM_CARD_DEFS if c["label"] == choice)

    forecast = moving_average_forecast(df, pm_key)
    if forecast is None:
        st.info("Not enough history yet for a forecast (need at least 3 readings).")
        return

    st.caption("Simple moving-average projection, not machine learning - a first pass.")
    c1, c2, c3 = st.columns(3)
    c1.metric("Next Hour", f"{forecast['next_hour']:.1f} µg/m³")
    c2.metric("Next 6 Hours", f"{forecast['next_6h']:.1f} µg/m³")
    c3.metric("Tomorrow", f"{forecast['tomorrow']:.1f} µg/m³")
