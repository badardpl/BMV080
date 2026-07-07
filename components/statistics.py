"""Statistics as cards (Min/Max/Avg/Median/StdDev/Count/Data Availability)."""

import pandas as pd
import streamlit as st

from utils.colors import PM_CARD_DEFS


def _data_availability_pct(df: pd.DataFrame, hours_back: int) -> float:
    """% of hours in the requested range that have at least one reading -
    interval-agnostic, so it doesn't assume any particular firmware cadence."""
    if df.empty or hours_back <= 0:
        return 0.0
    covered_hours = df["timestamp"].dt.floor("h").nunique()
    return min(covered_hours / hours_back * 100, 100.0)


def render_statistics_cards(df: pd.DataFrame, hours_back: int):
    availability = _data_availability_pct(df, hours_back)

    for card in PM_CARD_DEFS:
        v = df[card["key"]]
        st.markdown(f"**{card['label']}**")
        cols = st.columns(6)
        cols[0].metric("Min", f"{v.min():.1f}")
        cols[1].metric("Max", f"{v.max():.1f}")
        cols[2].metric("Avg", f"{v.mean():.1f}")
        cols[3].metric("Median", f"{v.median():.1f}")
        cols[4].metric("Std Dev", f"{v.std():.1f}")
        cols[5].metric("Count", f"{len(v)}")

    st.markdown("---")
    st.metric("Data Availability", f"{availability:.0f}%",
              help="Share of hours in the selected range with at least one reading")
