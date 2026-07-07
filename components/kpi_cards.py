"""Six KPI cards: PM1, PM2.5, PM10, AQI Score, Indoor Air Quality Score, Trend.

Card defs live in utils.colors.PM_CARD_DEFS - add an entry there to add a
pollutant card tomorrow without touching this layout code.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.analytics import worst_aqi
from utils.calculations import day_over_day_change, iaq_label, iaq_score, numeric_aqi
from utils.colors import AQI_CATEGORIES, PM_CARD_DEFS, SERIES_COLORS


def _sparkline(series: pd.Series, color: str) -> go.Figure:
    fig = go.Figure(go.Scatter(
        y=series.tail(20).values, mode="lines", line=dict(color=color, width=2),
    ))
    fig.update_layout(
        height=36, margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig


def _pm_card(col, df: pd.DataFrame, pm_key: str, label: str, tab_id: str):
    color = SERIES_COLORS[pm_key]
    latest_val = df[pm_key].iloc[-1]
    avg_val = df[pm_key].mean()
    daily_change = day_over_day_change(pm_key)
    aqi_idx = worst_aqi(df["pm1"].iloc[-1], df["pm2_5"].iloc[-1], df["pm10"].iloc[-1])
    cat_name, cat_color = AQI_CATEGORIES[aqi_idx][0], AQI_CATEGORIES[aqi_idx][1]
    fg = "#000" if aqi_idx < 2 else "#fff"

    if daily_change is None:
        change_html = '<span class="metric-card-delta" style="color:#9ca3af">— vs yesterday</span>'
    else:
        arrow = "▲" if daily_change > 0 else ("▼" if daily_change < 0 else "▬")
        change_color = "#9ca3af" if abs(daily_change) < 1 else ("#dc2626" if daily_change > 0 else "#16a34a")
        change_html = f'<span class="metric-card-delta" style="color:{change_color}">{arrow} {abs(daily_change):.0f}% vs yesterday</span>'

    with col:
        st.markdown(
            f"""
            <div class="metric-card" style="--card-accent:{color}">
                <div class="metric-card-label">{label}</div>
                <div class="metric-card-value-row">
                    <span class="metric-card-value">{latest_val:.1f}</span>
                    <span class="metric-card-unit">µg/m³</span>
                </div>
                <div class="metric-card-footer">Avg: {avg_val:.1f} µg/m³</div>
                <div style="margin-top:4px">{change_html}</div>
                <span class="metric-card-badge" style="background:{cat_color};color:{fg};margin-top:6px;display:inline-block;">
                    {cat_name}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.plotly_chart(_sparkline(df[pm_key], color), width="stretch",
                         config={"displayModeBar": False}, key=f"kpi_spark_{tab_id}_{pm_key}")


def _aqi_score_card(col, df: pd.DataFrame):
    latest = df.iloc[-1]
    aqi_val = numeric_aqi(latest["pm1"], latest["pm2_5"], latest["pm10"])
    aqi_idx = worst_aqi(latest["pm1"], latest["pm2_5"], latest["pm10"])
    cat_name, cat_color = AQI_CATEGORIES[aqi_idx][0], AQI_CATEGORIES[aqi_idx][1]
    fg = "#000" if aqi_idx < 2 else "#fff"
    with col:
        st.markdown(
            f"""
            <div class="metric-card" style="--card-accent:{cat_color}">
                <div class="metric-card-label">AQI Score</div>
                <div class="metric-card-value-row">
                    <span class="metric-card-value">{aqi_val}</span>
                </div>
                <span class="metric-card-badge" style="background:{cat_color};color:{fg};margin-top:6px;display:inline-block;">
                    {cat_name.upper()}
                </span>
                <div class="metric-card-footer">EPA-style estimate (worst of PM1/PM2.5/PM10)</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _iaq_score_card(col, df: pd.DataFrame):
    latest = df.iloc[-1]
    score = iaq_score(latest["pm1"], latest["pm2_5"], latest["pm10"])
    label = iaq_label(score)
    color = "#16a34a" if score >= 75 else ("#eda100" if score >= 50 else "#dc2626")
    with col:
        st.markdown(
            f"""
            <div class="metric-card" style="--card-accent:{color}">
                <div class="metric-card-label">Indoor Air Quality Score</div>
                <div class="metric-card-value-row">
                    <span class="metric-card-value">{score}</span>
                    <span class="metric-card-unit">/100</span>
                </div>
                <span class="metric-card-badge" style="background:{color};color:#fff;margin-top:6px;display:inline-block;">
                    {label}
                </span>
                <div class="metric-card-footer">Estimated from WHO guideline exceedance</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _trend_card(col):
    change = day_over_day_change("pm2_5")
    with col:
        if change is None:
            body = '<div class="metric-card-value" style="font-size:20px;">Not enough data yet</div>'
            color = "#9ca3af"
        else:
            improving = change < 0  # falling PM2.5 = improving air quality
            color = "#16a34a" if improving else "#dc2626"
            word = "Improving" if improving else "Getting Worse"
            arrow = "↓" if improving else "↑"
            body = (
                f'<div class="metric-card-value" style="font-size:22px;color:{color}">{word}</div>'
                f'<div class="metric-card-footer">{arrow}{abs(change):.0f}% PM2.5 vs yesterday</div>'
            )
        st.markdown(
            f"""
            <div class="metric-card" style="--card-accent:{color}">
                <div class="metric-card-label">Trend</div>
                {body}
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_kpi_cards(df: pd.DataFrame, tab_id: str):
    cols = st.columns(6)
    for i, card in enumerate(PM_CARD_DEFS):
        _pm_card(cols[i], df, card["key"], card["label"], tab_id)
    _aqi_score_card(cols[3], df)
    _iaq_score_card(cols[4], df)
    _trend_card(cols[5])
