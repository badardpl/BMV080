"""Rule-based (not LLM) AI Insights panel and the health recommendation
card. Every sentence is filled from a real computed number - nothing here
is a fixed hardcoded string with fabricated values.
"""

from datetime import timezone, timedelta

import pandas as pd
import streamlit as st

from utils.analytics import OFFICE_START, OFFICE_END, worst_aqi
from utils.calculations import day_over_day_change
from utils.colors import AQI_CATEGORIES
from utils.health import HEALTH_ICONS, HEALTH_MESSAGES, best_ventilation_hour, build_recommendations


def generate_insights(df: pd.DataFrame, tz_offset: int) -> list:
    insights = []
    local_tz = timezone(timedelta(hours=tz_offset))
    d = df.copy()
    d["local_hour"] = d["timestamp"].dt.tz_convert(local_tz).dt.hour

    change = day_over_day_change("pm2_5")
    if change is not None and abs(change) >= 3:
        direction = "increased" if change > 0 else "decreased"
        insights.append(f"PM2.5 has {direction} by {abs(change):.0f}% compared to the same period yesterday.")

    hourly_pm25 = d.groupby("local_hour")["pm2_5"].mean()
    if len(hourly_pm25) >= 3:
        best_hour, worst_hour = int(hourly_pm25.idxmin()), int(hourly_pm25.idxmax())
        insights.append(f"Air quality is typically best around {best_hour:02d}:00.")
        insights.append(f"Highest pollution typically occurs around {worst_hour:02d}:00.")

    d["is_office"] = d["local_hour"].between(OFFICE_START, OFFICE_END - 1)
    off_mean, noff_mean = d[d["is_office"]]["pm2_5"].mean(), d[~d["is_office"]]["pm2_5"].mean()
    if pd.notna(off_mean) and pd.notna(noff_mean):
        if off_mean < noff_mean:
            pct = (noff_mean - off_mean) / noff_mean * 100 if noff_mean else 0
            insights.append(f"Office hours are {pct:.0f}% cleaner than non-office hours on average.")
        else:
            pct = (off_mean - noff_mean) / off_mean * 100 if off_mean else 0
            insights.append(f"Non-office hours are {pct:.0f}% cleaner than office hours on average.")

    pm10_cv = df["pm10"].std() / df["pm10"].mean() * 100 if df["pm10"].mean() else 0
    if pm10_cv < 15:
        insights.append("PM10 has remained stable across the selected period.")

    worst_idx = int(df.apply(lambda r: worst_aqi(r["pm1"], r["pm2_5"], r["pm10"]), axis=1).max())
    if worst_idx <= 2:
        insights.append("No hazardous readings detected in the selected period.")
    else:
        insights.append(f"Readings reached the '{AQI_CATEGORIES[worst_idx][0]}' category during this period.")

    return insights


def render_insights_panel(df: pd.DataFrame, tz_offset: int):
    insights = generate_insights(df, tz_offset)
    if not insights:
        st.info("Not enough data yet to generate insights.")
        return
    st.markdown("##### Key Insights")
    for line in insights:
        st.markdown(f"- {line}")


def render_health_recommendation(df: pd.DataFrame, tz_offset: int):
    cats = df.apply(lambda r: worst_aqi(r["pm1"], r["pm2_5"], r["pm10"]), axis=1)
    worst_idx = int(cats.max())
    cat_name, cat_color = AQI_CATEGORIES[worst_idx][0], AQI_CATEGORIES[worst_idx][1]
    icon = HEALTH_ICONS[worst_idx]
    avg_pm1, avg_pm25, avg_pm10 = df["pm1"].mean(), df["pm2_5"].mean(), df["pm10"].mean()
    recommendations = build_recommendations(df, tz_offset)
    rec_html = "".join(f'<div style="margin-top:4px;">✓ {r}</div>' for r in recommendations)

    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,{cat_color}08,{cat_color}18);
                    border:1px solid {cat_color}40;border-radius:14px;padding:18px 20px;
                    margin:8px 0 16px;">
            <div style="display:flex;align-items:center;gap:14px;">
                <div style="background:{cat_color};width:52px;height:52px;border-radius:50%;
                            display:flex;align-items:center;justify-content:center;font-size:24px;
                            color:{'#000' if worst_idx < 2 else '#fff'};flex-shrink:0;">
                    {icon}
                </div>
                <div>
                    <div style="font-size:18px;font-weight:700;color:{cat_color};">{cat_name}</div>
                    <div style="font-size:13px;color:#374151;margin-top:2px;">{HEALTH_MESSAGES[worst_idx]}</div>
                    <div style="font-size:12px;color:#6b7280;margin-top:4px;">
                        Period avg &mdash; PM1: {avg_pm1:.1f} &middot; PM2.5: {avg_pm25:.1f} &middot; PM10: {avg_pm10:.1f} µg/m³
                    </div>
                </div>
            </div>
            <div style="margin-top:12px;font-size:13px;color:#374151;">{rec_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
