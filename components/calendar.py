"""GitHub-style monthly calendar, colored by each day's worst AQI category.
Always shows the current calendar month, independent of the page's selected
date range (a "monthly overview" should mean the month, not whatever window
is picked elsewhere)."""

import calendar as _calendar
from datetime import datetime, timezone, timedelta

import streamlit as st

from utils.analytics import worst_aqi
from utils.colors import AQI_CATEGORIES
from utils.data import fetch_readings


def render_pollution_calendar(tz_offset: int):
    local_tz = timezone(timedelta(hours=tz_offset))
    now_local = datetime.now(local_tz)
    month_start = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month = (month_start + timedelta(days=32)).replace(day=1)

    df = fetch_readings(int(month_start.astimezone(timezone.utc).timestamp()),
                         int(min(now_local, next_month).astimezone(timezone.utc).timestamp()))

    st.markdown(f"##### {month_start.strftime('%B %Y')}")

    if df.empty:
        st.info("No readings yet this month.")
        return

    d = df.copy()
    d["local_date"] = d["timestamp"].dt.tz_convert(local_tz).dt.date
    daily_worst = d.groupby("local_date").apply(
        lambda g: worst_aqi(g["pm1"].mean(), g["pm2_5"].mean(), g["pm10"].mean())
    )

    cal = _calendar.Calendar(firstweekday=0)  # Monday first
    weeks = cal.monthdatescalendar(now_local.year, now_local.month)

    header_cols = st.columns(7)
    for col, name in zip(header_cols, ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
        col.markdown(f"<div style='text-align:center;font-size:11px;color:#64748B;'>{name}</div>",
                     unsafe_allow_html=True)

    for week in weeks:
        cols = st.columns(7)
        for col, day in zip(cols, week):
            if day.month != now_local.month:
                col.markdown("&nbsp;", unsafe_allow_html=True)
                continue
            if day in daily_worst.index:
                idx = int(daily_worst.loc[day])
                color = AQI_CATEGORIES[idx][1]
            else:
                color = "#E2E8F0"  # no data that day
            col.markdown(
                f"""
                <div style="background:{color};border-radius:6px;padding:6px 0;text-align:center;
                            font-size:11px;color:#0F172A;font-weight:600;">
                    {day.day}
                </div>
                """,
                unsafe_allow_html=True,
            )
