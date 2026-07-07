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
