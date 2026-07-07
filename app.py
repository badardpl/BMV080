"""
BMV080 Air Quality Dashboard

Reads PM1/PM2.5/PM10 hourly averages published by the ESP32 firmware
(via AWS IoT -> DynamoDB) and shows hourly/weekly/monthly trends.

Required st.secrets keys (see .streamlit/secrets.toml.example):
  aws_access_key_id, aws_secret_access_key, aws_region, table_name, device_id
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import boto3
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from boto3.dynamodb.conditions import Key

# ── Backend (unchanged) ──────────────────────────────────────────────

SERIES_COLORS = {"pm1": "#2a78d6", "pm2_5": "#1baf7a", "pm10": "#eda100"}


@st.cache_resource
def get_table():
    resource = boto3.resource(
        "dynamodb",
        region_name=st.secrets["aws_region"],
        aws_access_key_id=st.secrets["aws_access_key_id"],
        aws_secret_access_key=st.secrets["aws_secret_access_key"],
    )
    return resource.Table(st.secrets["table_name"])


@st.cache_data(ttl=300)
def fetch_readings(start_ts: int, end_ts: int) -> pd.DataFrame:
    table = get_table()
    device_id = st.secrets["device_id"]

    items = []
    query_kwargs = {
        "KeyConditionExpression": Key("device_id").eq(device_id) & Key("ts").between(start_ts, end_ts)
    }
    while True:
        response = table.query(**query_kwargs)
        items.extend(response.get("Items", []))
        if "LastEvaluatedKey" not in response:
            break
        query_kwargs["ExclusiveStartKey"] = response["LastEvaluatedKey"]

    if not items:
        return pd.DataFrame(columns=["timestamp", "pm1", "pm2_5", "pm10"])

    df = pd.DataFrame(items)
    for col in ["pm1", "pm2_5", "pm10"]:
        df[col] = df[col].apply(float)
    df["timestamp"] = pd.to_datetime(df["ts"].apply(int), unit="s", utc=True)
    return df[["timestamp", "pm1", "pm2_5", "pm10"]].sort_values("timestamp")


# ── AQI / Health constants ──────────────────────────────────────────

AQI_CATEGORIES = [
    ("Good", "#00e400", 0),
    ("Moderate", "#ffff00", 1),
    ("Unhealthy for Sensitive", "#ff7e00", 2),
    ("Unhealthy", "#ff0000", 3),
    ("Very Unhealthy", "#8f3f97", 4),
    ("Hazardous", "#7e0023", 5),
]

PM1_THRESH = [15, 40, 80, 150, 250, 1e9]
PM25_THRESH = [12.0, 35.4, 55.4, 150.4, 250.4, 1e9]
PM10_THRESH = [54, 154, 254, 354, 424, 1e9]

HEALTH_MESSAGES = [
    "Air quality is satisfactory. Enjoy your day!",
    "Air quality is acceptable. Sensitive individuals should limit prolonged outdoor exertion.",
    "Members of sensitive groups may experience health effects. Limit outdoor activity.",
    "Everyone may begin to experience health effects. Avoid prolonged outdoor exertion.",
    "Health alert: everyone may experience more serious health effects. Avoid outdoor activities.",
    "Health warning of emergency conditions. Everyone should avoid all outdoor exertion.",
]

HEALTH_ICONS = ["\U0001f60a", "\U0001f610", "\U0001f637", "\u26a0\ufe0f", "\U0001f6a8", "\u2620\ufe0f"]

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


# ── UI: trend chart ─────────────────────────────────────────────────

def _office_hours_shading(fig: go.Figure, index: pd.DatetimeIndex):
    if index.empty:
        return
    dr = pd.date_range(start=index.min().floor("1D"), end=index.max().ceil("1D"), freq="1D", tz=index.tz)
    for d in dr:
        fig.add_vrect(
            x0=d + timedelta(hours=OFFICE_START),
            x1=d + timedelta(hours=OFFICE_END),
            fillcolor="rgba(0, 228, 0, 0.08)",
            layer="below",
            line_width=0,
        )


# PM1/PM2.5/PM10 run at different scales (PM10 typically 2-3x PM1), so one
# shared y-axis flattens the smaller series - three separate single-series
# charts (small multiples), each auto-scaled to its own data, reads correctly.
def single_metric_chart(df: pd.DataFrame, pm_key: str, label: str,
                        resample_rule: Optional[str], tz_offset: int) -> go.Figure:
    plot_df = df.set_index("timestamp")
    if resample_rule:
        plot_df = plot_df.resample(resample_rule).mean()
    plot_df.index = plot_df.index.tz_convert(timezone(timedelta(hours=tz_offset)))

    fig = go.Figure(go.Scatter(
        x=plot_df.index,
        y=plot_df[pm_key],
        mode="lines",
        line=dict(color=SERIES_COLORS[pm_key], width=2),
        hovertemplate="%{y:.1f} \u00b5g/m\u00b3<extra></extra>",
    ))
    _office_hours_shading(fig, plot_df.index)

    fig.update_layout(
        title=dict(text=label, font=dict(size=14, color="#111827")),
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=36, b=10),
        showlegend=False,
        yaxis_title="\u00b5g/m\u00b3",
        hovermode="x unified",
        height=280,
    )
    # Plotly's default tick count assumes a full-width chart; in a 3-column
    # row each chart is ~1/3 as wide, so the default crowds/overlaps labels.
    # Cap the tick count and pick a format that matches what's meaningful at
    # each zoom level - a date is useless on a 48h view, a time is useless
    # on a 30-day view.
    if resample_rule is None:
        tick_format, n_ticks = "%a %H:%M", 6
    elif resample_rule == "1h":
        tick_format, n_ticks = "%b %d", 7
    else:
        tick_format, n_ticks = "%b %d", 8

    fig.update_xaxes(showgrid=False, nticks=n_ticks, tickformat=tick_format, tickangle=0)
    fig.update_yaxes(showgrid=True, gridcolor="#e1e0d9")
    return fig


def trend_charts_row(df: pd.DataFrame, resample_rule: Optional[str], tz_offset: int, tab_id: str):
    cols = st.columns(len(PM_CARD_DEFS))
    for col, card in zip(cols, PM_CARD_DEFS):
        with col:
            st.plotly_chart(
                single_metric_chart(df, card["key"], card["label"], resample_rule, tz_offset),
                use_container_width=True,
                key=f"trend_{tab_id}_{card['key']}",
            )


# ── UI: insights widgets ────────────────────────────────────────────

# Card definitions for the top row. Add a new dict here to add a card
# tomorrow - metrics_row() lays out however many entries this list has,
# no other code needs to change.
PM_CARD_DEFS = [
    {"key": "pm1", "label": "PM1"},
    {"key": "pm2_5", "label": "PM2.5"},
    {"key": "pm10", "label": "PM10"},
]


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


def _metric_card(col, df: pd.DataFrame, pm_key: str, label: str, tz_offset: int, tab_id: str):
    border_color = SERIES_COLORS[pm_key]
    local_tz = timezone(timedelta(hours=tz_offset))
    latest = df.iloc[-1]
    latest_val = latest[pm_key]
    latest_local = latest["timestamp"].tz_convert(local_tz).strftime("%Y-%m-%d %H:%M")
    aqi_idx = worst_aqi(latest["pm1"], latest["pm2_5"], latest["pm10"])
    cat_name = AQI_CATEGORIES[aqi_idx][0]
    cat_color = AQI_CATEGORIES[aqi_idx][1]
    fg = "#000" if aqi_idx < 2 else "#fff"

    period_mean = df[pm_key].mean()
    delta = latest_val - period_mean
    # Higher pollution is always the "bad" direction, regardless of arrow sign.
    delta_color = "#9ca3af" if abs(delta) < 0.05 else ("#dc2626" if delta > 0 else "#16a34a")
    arrow = "▲" if delta > 0 else ("▼" if delta < 0 else "▬")

    with col:
        st.markdown(
            f"""
            <div class="metric-card" style="--card-accent:{border_color}">
                <div class="metric-card-label">{label}</div>
                <div class="metric-card-value-row">
                    <span class="metric-card-value">{latest_val:.1f}</span>
                    <span class="metric-card-unit">µg/m³</span>
                    <span class="metric-card-delta" style="color:{delta_color}">
                        {arrow} {abs(delta):.1f}
                    </span>
                </div>
                <span class="metric-card-badge" style="background:{cat_color};color:{fg}">
                    {cat_name}
                </span>
                <div class="metric-card-footer">as of {latest_local}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.plotly_chart(_sparkline(df[pm_key], border_color), use_container_width=True,
                         config={"displayModeBar": False}, key=f"spark_{tab_id}_{pm_key}")


def metrics_row(df: pd.DataFrame, tz_offset: int, tab_id: str):
    cols = st.columns(len(PM_CARD_DEFS))
    for col, card in zip(cols, PM_CARD_DEFS):
        _metric_card(col, df, card["key"], card["label"], tz_offset, tab_id)


def stats_section(df: pd.DataFrame, tz_offset: int):
    local_tz = timezone(timedelta(hours=tz_offset))
    df_local = df.copy()
    df_local["local_hour"] = df_local["timestamp"].dt.tz_convert(local_tz).dt.hour
    df_local["is_office"] = df_local["local_hour"].between(OFFICE_START, OFFICE_END - 1)

    stats_rows = []
    for pm_key, label in [("pm1", "PM1"), ("pm2_5", "PM2.5"), ("pm10", "PM10")]:
        v = df[pm_key]
        stats_rows.append({
            "Parameter": label,
            "Min": f"{v.min():.1f}",
            "Max": f"{v.max():.1f}",
            "Avg": f"{v.mean():.1f}",
            "Median": f"{v.median():.1f}",
            "Std Dev": f"{v.std():.1f}",
            "Count": len(v),
        })
    st.dataframe(pd.DataFrame(stats_rows), use_container_width=True, hide_index=True)

    st.markdown("##### Office Hours (10AM\u20139PM) vs Non-Office Hours")
    comp = []
    for pm_key, label in [("pm1", "PM1"), ("pm2_5", "PM2.5"), ("pm10", "PM10")]:
        off = df_local[df_local["is_office"]][pm_key]
        noff = df_local[~df_local["is_office"]][pm_key]
        comp.append({
            "Parameter": label,
            "Office Avg": f"{off.mean():.1f}" if not off.empty else "\u2014",
            "Non-Office Avg": f"{noff.mean():.1f}" if not noff.empty else "\u2014",
            "Difference": f"{off.mean() - noff.mean():.1f}" if not off.empty and not noff.empty else "\u2014",
        })
    st.dataframe(pd.DataFrame(comp), use_container_width=True, hide_index=True)


def health_recommendation(df: pd.DataFrame):
    cats = df.apply(lambda r: worst_aqi(r["pm1"], r["pm2_5"], r["pm10"]), axis=1)
    worst_idx = int(cats.max())
    cat_name = AQI_CATEGORIES[worst_idx][0]
    cat_color = AQI_CATEGORIES[worst_idx][1]
    icon = HEALTH_ICONS[worst_idx]
    avg_pm1 = df["pm1"].mean()
    avg_pm25 = df["pm2_5"].mean()
    avg_pm10 = df["pm10"].mean()

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
                    <div style="font-size:18px;font-weight:700;color:{cat_color};">
                        {cat_name}
                    </div>
                    <div style="font-size:13px;color:#374151;margin-top:2px;">
                        {HEALTH_MESSAGES[worst_idx]}
                    </div>
                    <div style="font-size:12px;color:#6b7280;margin-top:4px;">
                        Period avg &mdash; PM1: {avg_pm1:.1f} &middot; PM2.5: {avg_pm25:.1f} &middot; PM10: {avg_pm10:.1f} µg/m³
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def office_hours_donuts(df: pd.DataFrame, tz_offset: int, tab_id: str):
    local_tz = timezone(timedelta(hours=tz_offset))
    d = df.copy()
    d["local_hour"] = d["timestamp"].dt.tz_convert(local_tz).dt.hour
    d["is_office"] = d["local_hour"].between(OFFICE_START, OFFICE_END - 1)
    d["aqi_cat"] = d.apply(lambda r: worst_aqi(r["pm1"], r["pm2_5"], r["pm10"]), axis=1)

    c1, c2 = st.columns(2)
    for col, label, mask, slot in [
        (c1, "Office Hours (10AM\u20139PM)", True, "office"),
        (c2, "Non-Office Hours (9PM\u201310AM)", False, "nonoffice"),
    ]:
        sub = d[d["is_office"] == mask]
        with col:
            if sub.empty:
                st.info(f"No readings during {label.split(' (')[0]}")
                continue
            cnt = sub["aqi_cat"].value_counts().sort_index()
            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=[AQI_CATEGORIES[i][0] for i in cnt.index],
                        values=cnt.values,
                        marker=dict(colors=[AQI_CATEGORIES[i][1] for i in cnt.index]),
                        hole=0.5,
                        textinfo="label+percent",
                        textposition="outside",
                    )
                ]
            )
            fig.update_layout(
                title=dict(text=label, font=dict(size=13)),
                height=300,
                margin=dict(l=10, r=10, t=40, b=10),
                showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True, key=f"donut_{tab_id}_{slot}")


# ── Main render function ────────────────────────────────────────────

def render_tab(hours_back: int, resample_rule: Optional[str], title: str,
               empty_message: str, tz_offset: int = 5):
    now = datetime.now(timezone.utc)
    start_ts = int((now - timedelta(hours=hours_back)).timestamp())
    end_ts = int(now.timestamp())

    df = fetch_readings(start_ts, end_ts)
    if df.empty:
        st.info(empty_message)
        return

    tab_id = f"h{hours_back}"

    health_recommendation(df)
    metrics_row(df, tz_offset, tab_id)
    st.caption(title)
    trend_charts_row(df, resample_rule, tz_offset, tab_id)

    with st.expander("Details \u2014 AQI distribution & statistics"):
        st.markdown("##### Office vs Non-Office \u2014 AQI Distribution")
        office_hours_donuts(df, tz_offset, tab_id)
        st.markdown("---")
        stats_section(df, tz_offset)

    with st.expander("Raw data"):
        tz = timezone(timedelta(hours=tz_offset))
        disp = df.copy()
        disp["local_time"] = disp["timestamp"].dt.tz_convert(tz).dt.strftime("%Y-%m-%d %H:%M")
        disp["utc_time"] = disp["timestamp"].dt.strftime("%Y-%m-%d %H:%M")
        st.dataframe(disp[["utc_time", "local_time", "pm1", "pm2_5", "pm10"]],
                     use_container_width=True, hide_index=True)


# ── Page configuration ──────────────────────────────────────────────

st.set_page_config(page_title="BMV080 Air Quality", page_icon="\U0001f32b\ufe0f", layout="wide")

# ── Custom CSS ───────────────────────────────────────────────────────

st.markdown(
"""
<style>
    .stApp { background: #f5f7fb; }
    h1 { font-weight: 700; color: #111827; font-size: 28px; }
    .stTabs [data-baseweb="tab-list"] { gap: 4px; background: #fff; padding: 6px; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
    .stTabs [data-baseweb="tab"] { border-radius: 8px; padding: 6px 20px; font-weight: 500; font-size: 14px; }
    .stTabs [aria-selected="true"] { background: #2a78d6 !important; color: #fff !important; }
    [data-testid="stMetricValue"] { font-size: 28px; font-weight: 700; }
    .stDataFrame { border: none; border-radius: 12px; box-shadow: 0 1px 4px rgba(0,0,0,0.04); }
    .st-ef { border-radius: 12px; }
    section[data-testid="stSidebar"] > div { background: #ffffff; border-right: 1px solid #e5e7eb; padding: 20px 16px; }
    section[data-testid="stSidebar"] .stSelectbox label { font-size: 13px; font-weight: 600; color: #374151; }
    .stAlert { border-radius: 10px; }
    footer { display: none; }
    div[data-testid="stExpander"] { border: 1px solid #e5e7eb; border-radius: 12px; background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.03); }
    div[data-testid="stExpander"] summary { font-weight: 600; color: #374151; padding: 8px 12px; }
    .stInfo, .stSuccess, .stWarning { border-radius: 10px; }

    /* Stat cards - shared shell for today's PM cards and any future card */
    .metric-card {
        background: linear-gradient(135deg,#ffffff,#f8f9fa);
        border-radius: 14px;
        padding: 16px 18px;
        border-left: 5px solid var(--card-accent, #2a78d6);
        box-shadow: 0 1px 4px rgba(0,0,0,0.05);
        margin-bottom: 8px;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .metric-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 20px rgba(0,0,0,0.08);
    }
    .metric-card-label {
        font-size: 12px; color: #6b7280; font-weight: 600;
        text-transform: uppercase; letter-spacing: 0.5px;
    }
    .metric-card-value-row { display: flex; align-items: baseline; gap: 8px; margin: 6px 0 2px; }
    .metric-card-value { font-size: 32px; font-weight: 700; color: #111827; }
    .metric-card-unit { font-size: 12px; color: #6b7280; font-weight: 400; }
    .metric-card-delta { font-size: 12px; font-weight: 700; }
    .metric-card-footer { font-size: 11px; color: #9ca3af; margin-top: 6px; }
    .metric-card-badge {
        display: inline-block; font-size: 11px; font-weight: 700;
        padding: 2px 12px; border-radius: 12px;
    }

    /* Chart card wrapper for the three per-pollutant charts */
    .chart-card-title {
        font-size: 14px; font-weight: 700; color: #111827; margin: 4px 0 0;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ── Sidebar ──────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## \U0001f32b\ufe0f BMV080")
    st.markdown("<p style='color:#6b7280;font-size:13px;margin-top:-8px;'>Air Quality Dashboard</p>",
                unsafe_allow_html=True)
    st.markdown("---")

    tz_offset = st.selectbox(
        "\U0001f30d Timezone",
        options=[f"UTC{'+' if h >= 0 else ''}{h}" for h in range(-12, 15)],
        index=17,
        help="Display timestamps in your local timezone",
    )
    tz_offset_int = int(tz_offset.replace("UTC", "").replace("+", ""))

    st.markdown("---")
    st.markdown("### \U0001f3e2 Office Hours")
    st.markdown("10:00 AM \u2013 9:00 PM")
    local_now = datetime.now(timezone(timedelta(hours=tz_offset_int)))
    st.caption(f"Current local: {local_now.strftime('%Y-%m-%d %H:%M')}")
    if OFFICE_START <= local_now.hour < OFFICE_END:
        st.success("\U0001f535 Office hours now")
    else:
        st.warning("\u26aa Non-office hours now")

    st.markdown("---")
    st.markdown("### \U0001f7e7 AQI Reference")
    for name, color, _ in AQI_CATEGORIES:
        fg = "#000" if name in ("Good", "Moderate") else "#fff"
        st.markdown(
            f'<span style="display:inline-block;background:{color};color:{fg};'
            f'font-size:11px;font-weight:600;padding:2px 14px;border-radius:10px;margin:2px 0;">'
            f'{name}</span>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    device_id = st.secrets.get("device_id", "unknown")
    st.markdown(f"**Device:** `{device_id}`")
    st.caption(f"Page updated: {datetime.now().strftime('%H:%M:%S')}")

# ── Main body ────────────────────────────────────────────────────────

st.title("BMV080 Particulate Matter Dashboard")
st.markdown(
    f"<p style='color:#6b7280;font-size:14px;margin-top:-10px;'>"
    f"Real-time PM1 &middot; PM2.5 &middot; PM10 monitoring &mdash; "
    f"Device: <strong>{st.secrets.get('device_id', 'unknown')}</strong></p>",
    unsafe_allow_html=True,
)

tab_hourly, tab_weekly, tab_monthly = st.tabs([
    "\U0001f4ca Hourly (48h)",
    "\U0001f4c8 Weekly (7d)",
    "\U0001f4c9 Monthly (30d)",
])

with tab_hourly:
    render_tab(48, None, "Last 48 hours", "No readings in the last 48 hours yet.", tz_offset_int)

with tab_weekly:
    render_tab(24 * 7, "1h", "Last 7 days (hourly mean)", "No readings in the last 7 days yet.", tz_offset_int)

with tab_monthly:
    render_tab(24 * 30, "1D", "Last 30 days (daily mean)", "No readings in the last 30 days yet.", tz_offset_int)
