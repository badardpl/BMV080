"""Dynamically generated health recommendations - all sentences are filled
from real computed numbers, never hardcoded text with fabricated values.
"""

from datetime import timezone, timedelta

import pandas as pd

from utils.analytics import worst_aqi

HEALTH_MESSAGES = [
    "Air quality is satisfactory. Enjoy your day!",
    "Air quality is acceptable. Sensitive individuals should limit prolonged outdoor exertion.",
    "Members of sensitive groups may experience health effects. Limit outdoor activity.",
    "Everyone may begin to experience health effects. Avoid prolonged outdoor exertion.",
    "Health alert: everyone may experience more serious health effects. Avoid outdoor activities.",
    "Health warning of emergency conditions. Everyone should avoid all outdoor exertion.",
]

HEALTH_ICONS = ["\U0001f60a", "\U0001f610", "\U0001f637", "⚠️", "\U0001f6a8", "☠️"]


def best_ventilation_hour(df: pd.DataFrame, tz_offset: int) -> int:
    """Local hour with the lowest average PM2.5 - a reasonable "open the
    windows now" suggestion given only what this sensor has actually seen."""
    local_tz = timezone(timedelta(hours=tz_offset))
    d = df.copy()
    d["local_hour"] = d["timestamp"].dt.tz_convert(local_tz).dt.hour
    return int(d.groupby("local_hour")["pm2_5"].mean().idxmin())


def build_recommendations(df: pd.DataFrame, tz_offset: int, office_start: int = 10, office_end: int = 21) -> list:
    worst_idx = int(df.apply(lambda r: worst_aqi(r["pm1"], r["pm2_5"], r["pm10"]), axis=1).max())
    best_hour = best_ventilation_hour(df, tz_offset)
    recs = [f"Best ventilation time based on your data: {best_hour:02d}:00"]

    if worst_idx <= 1:
        recs.append("Indoor exercise is safe at current air quality levels")
    else:
        recs.append("Consider limiting strenuous indoor activity until levels improve")

    local_tz = timezone(timedelta(hours=tz_offset))
    d = df.copy()
    d["local_hour"] = d["timestamp"].dt.tz_convert(local_tz).dt.hour
    d["is_office"] = d["local_hour"].between(office_start, office_end - 1)
    off_mean = d[d["is_office"]]["pm2_5"].mean()
    noff_mean = d[~d["is_office"]]["pm2_5"].mean()
    if pd.notna(off_mean) and pd.notna(noff_mean) and noff_mean > off_mean * 1.15:
        recs.append("Non-office hours run notably dustier - reduce cleaning/vacuuming during that window if possible")

    if worst_idx >= 3:
        recs.append("Reduce dust-generating activity (cleaning, cooking without ventilation) until air quality improves")

    return recs
