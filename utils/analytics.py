"""AQI classification logic, moved verbatim from the original app.py."""

PM1_THRESH = [15, 40, 80, 150, 250, 1e9]
PM25_THRESH = [12.0, 35.4, 55.4, 150.4, 250.4, 1e9]
PM10_THRESH = [54, 154, 254, 354, 424, 1e9]

OFFICE_START = 10
OFFICE_END = 21


def _aqi_level(value: float, thresholds: list) -> int:
    for i, t in enumerate(thresholds):
        if value <= t:
            return i
    return len(thresholds) - 1


def worst_aqi(pm1: float, pm2_5: float, pm10: float) -> int:
    return max(
        _aqi_level(pm1, PM1_THRESH),
        _aqi_level(pm2_5, PM25_THRESH),
        _aqi_level(pm10, PM10_THRESH),
    )
