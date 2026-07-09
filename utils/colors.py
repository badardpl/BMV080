"""Theme and color constants shared across components."""

THEME = {
    "bg": "#F8FAFC",
    "card": "#FFFFFF",
    "text_primary": "#0F172A",
    "text_secondary": "#64748B",
    "border": "#E2E8F0",
    "radius": "16px",
    "shadow": "0 4px 12px rgba(0,0,0,0.05)",
}

# Dark variant of THEME - same roles, values only. Covers the global page
# surfaces (background/cards/borders/sidebar/expanders); a handful of
# widgets still use hardcoded inline text colors for their content (e.g.
# the health-recommendation banner) rather than these roles, so those
# won't fully flip yet - a known follow-up, not silently broken.
DARK_THEME = {
    "bg": "#0F172A",
    "card": "#1E293B",
    "text_primary": "#F1F5F9",
    "text_secondary": "#94A3B8",
    "border": "#334155",
    "radius": "16px",
    "shadow": "0 4px 12px rgba(0,0,0,0.35)",
}

SERIES_COLORS = {"pm1": "#2a78d6", "pm2_5": "#1baf7a", "pm10": "#eda100"}

AQI_CATEGORIES = [
    ("Good", "#00e400", 0),
    ("Moderate", "#ffff00", 1),
    ("Unhealthy for Sensitive", "#ff7e00", 2),
    ("Unhealthy", "#ff0000", 3),
    ("Very Unhealthy", "#8f3f97", 4),
    ("Hazardous", "#7e0023", 5),
]

# Shared pollutant list. Add a dict here to add a new sensor metric (e.g.
# temperature/humidity) everywhere it's used - KPI cards, the chart
# dropdown, etc. - without touching their layout code.
PM_CARD_DEFS = [
    {"key": "pm1", "label": "PM1"},
    {"key": "pm2_5", "label": "PM2.5"},
    {"key": "pm10", "label": "PM10"},
]

# AQI zone bands for Daily View zone-colored line charts.
# Each entry: (lo, hi, label, solid_color, fill_rgba).
# Thresholds match the breakpoints in utils/analytics.py.
PM1_ZONES = [
    (0,    15.0,  "Good",     "#00e400", "rgba(0,228,0,0.15)"),
    (15.0, 40.0,  "Moderate", "#d4ac0d", "rgba(212,172,13,0.20)"),
    (40.0, 80.0,  "Sensitive","#ff7e00", "rgba(255,126,0,0.15)"),
    (80.0, 150.0, "Unhealthy","#ff0000", "rgba(255,0,0,0.15)"),
    (150.0,250.0, "Very Bad", "#8f3f97", "rgba(143,63,151,0.15)"),
    (250.0, 1e9,  "Hazardous","#7e0023", "rgba(126,0,35,0.18)"),
]

PM25_ZONES = [
    (0,    12.0,  "Good",     "#00e400", "rgba(0,228,0,0.15)"),
    (12.0, 35.4,  "Moderate", "#d4ac0d", "rgba(212,172,13,0.20)"),
    (35.4, 55.4,  "Sensitive","#ff7e00", "rgba(255,126,0,0.15)"),
    (55.4, 150.4, "Unhealthy","#ff0000", "rgba(255,0,0,0.15)"),
    (150.4,250.4, "Very Bad", "#8f3f97", "rgba(143,63,151,0.15)"),
    (250.4, 1e9,  "Hazardous","#7e0023", "rgba(126,0,35,0.18)"),
]

PM10_ZONES = [
    (0,    54.0,  "Good",     "#00e400", "rgba(0,228,0,0.15)"),
    (54.0, 154.0, "Moderate", "#d4ac0d", "rgba(212,172,13,0.20)"),
    (154.0,254.0, "Sensitive","#ff7e00", "rgba(255,126,0,0.15)"),
    (254.0,354.0, "Unhealthy","#ff0000", "rgba(255,0,0,0.15)"),
    (354.0,424.0, "Very Bad", "#8f3f97", "rgba(143,63,151,0.15)"),
    (424.0, 1e9,  "Hazardous","#7e0023", "rgba(126,0,35,0.18)"),
]

# Lookup from pollutant key to its zone list.
PM_ZONE_MAP = {"pm1": PM1_ZONES, "pm2_5": PM25_ZONES, "pm10": PM10_ZONES}
