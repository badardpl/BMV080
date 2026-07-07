"""Derived analytics: numeric EPA-style AQI, an estimated Indoor Air Quality
Score, WHO-limit comparisons, a simple moving-average forecast, and
peak/spike detection. Everything here is a documented estimate, not an
official regulatory calculation - good enough for an indoor consumer
dashboard, not for compliance reporting.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import pandas as pd

from utils.analytics import PM1_THRESH as _PM1, PM25_THRESH as _PM25, PM10_THRESH as _PM10

# ---------------------------------------------------------------------------
# Numeric EPA-style AQI (0-500). Breakpoints match the existing categorical
# buckets in utils/analytics.py so the numeric score and the category badge
# always agree. PM10/PM2.5 breakpoints are the standard EPA 24-hr table;
# PM1 has no official standard, so it reuses the same AQI_LOW/HIGH scale as
# an unofficial extension (documented, not a regulatory figure).
# ---------------------------------------------------------------------------

_AQI_BANDS = [(0, 50), (51, 100), (101, 150), (151, 200), (201, 300), (301, 500)]


def _epa_aqi(conc: float, breakpoints: list) -> float:
    lo_bp = 0.0
    for (bp_hi, (aqi_lo, aqi_hi)) in zip(breakpoints, _AQI_BANDS):
        if conc <= bp_hi:
            bp_lo = lo_bp
            return (aqi_hi - aqi_lo) / (bp_hi - bp_lo) * (conc - bp_lo) + aqi_lo
        lo_bp = bp_hi
    return 500.0


def numeric_aqi(pm1: float, pm2_5: float, pm10: float) -> int:
    """Worst-of-three numeric AQI, matching worst_aqi()'s category choice."""
    return round(max(
        _epa_aqi(pm1, _PM1),
        _epa_aqi(pm2_5, _PM25),
        _epa_aqi(pm10, _PM10),
    ))


# ---------------------------------------------------------------------------
# Indoor Air Quality Score (0-100, higher = better) - an estimate, not a
# standard. Starts at 100 and subtracts a penalty proportional to how far
# PM2.5/PM10 exceed the WHO 24-hour guideline.
# ---------------------------------------------------------------------------

WHO_24H_LIMITS = {"pm1": 15.0, "pm2_5": 15.0, "pm10": 45.0}  # µg/m³
# Note: WHO has no official PM1 guideline; the PM2.5 figure is reused as an
# approximation since PM1 is a subset of PM2.5 by definition.


def iaq_score(pm1: float, pm2_5: float, pm10: float) -> int:
    penalty = 0.0
    for key, val in [("pm1", pm1), ("pm2_5", pm2_5), ("pm10", pm10)]:
        ratio = val / WHO_24H_LIMITS[key]
        penalty += min(ratio, 4.0) * 12.5  # each pollutant can cost up to 50 pts at 4x the limit
    score = 100 - penalty / 3
    return int(max(0, min(100, round(score))))


def iaq_label(score: int) -> str:
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 50:
        return "Fair"
    if score >= 25:
        return "Poor"
    return "Very Poor"


# ---------------------------------------------------------------------------
# Trend vs. a prior period
# ---------------------------------------------------------------------------

def pct_change(current: float, previous: float) -> Optional[float]:
    if previous is None or previous == 0 or pd.isna(previous):
        return None
    return (current - previous) / previous * 100


def day_over_day_change(pm_key: str) -> Optional[float]:
    """% change of the last 24h average vs. the preceding 24h average.
    Always fetches its own fixed 48h window (independent of whatever date
    range the page is showing) so this figure is meaningful even when the
    user has a 24h range selected.
    """
    from utils.data import fetch_readings  # local import: avoids a data<->calculations import cycle

    now = datetime.now(timezone.utc)
    df48 = fetch_readings(int((now - timedelta(hours=48)).timestamp()), int(now.timestamp()))
    if df48.empty:
        return None
    cutoff = pd.Timestamp(now - timedelta(hours=24))  # already tz-aware (UTC) from `now`
    today = df48[df48["timestamp"] >= cutoff]
    yesterday = df48[df48["timestamp"] < cutoff]
    if today.empty or yesterday.empty:
        return None
    return pct_change(today[pm_key].mean(), yesterday[pm_key].mean())


# ---------------------------------------------------------------------------
# Forecast - simple moving average, not ML. Explicitly a first pass per the
# spec ("simple moving average is acceptable initially").
# ---------------------------------------------------------------------------

def moving_average_forecast(df: pd.DataFrame, pm_key: str) -> Optional[dict]:
    """Returns {"next_hour", "next_6h", "tomorrow"} estimates, or None if
    there isn't enough history (need at least 3 points) to make one."""
    series = df.set_index("timestamp")[pm_key].sort_index()
    if len(series) < 3:
        return None

    recent = series.tail(6).mean()
    trend_window = series.tail(min(12, len(series)))
    slope = (trend_window.iloc[-1] - trend_window.iloc[0]) / max(len(trend_window) - 1, 1)

    def _project(steps: int) -> float:
        return max(0.0, recent + slope * steps)

    return {
        "next_hour": _project(1),
        "next_6h": _project(6),
        "tomorrow": _project(24),
    }


# ---------------------------------------------------------------------------
# Peak detection - flags points that jump well above the local baseline.
# Heuristic, not a statistical anomaly model: a spike is a reading more than
# 2 standard deviations above the trailing rolling mean.
# ---------------------------------------------------------------------------

def detect_peaks(df: pd.DataFrame, pm_key: str, window: int = 12, z: float = 2.0) -> pd.DataFrame:
    d = df[["timestamp", pm_key]].copy().sort_values("timestamp").reset_index(drop=True)
    if len(d) < window + 1:
        return d.iloc[0:0]

    roll_mean = d[pm_key].rolling(window, min_periods=window).mean()
    roll_std = d[pm_key].rolling(window, min_periods=window).std()
    threshold = roll_mean + z * roll_std
    spikes = d[d[pm_key] > threshold].copy()
    spikes["baseline"] = roll_mean[spikes.index]
    return spikes


def guess_peak_cause(local_hour: int) -> str:
    if local_hour in (7, 8, 12, 13, 19, 20, 21):
        return "Possible cooking event"
    if 22 <= local_hour or local_hour <= 5:
        return "Possible indoor activity"
    return "Possible outdoor/dust event"
