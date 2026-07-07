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

# Fixed categorical color assignment (blue/aqua/yellow, in that order) so a
# series always keeps the same color regardless of which tab/range is shown.
SERIES_COLORS = {"pm1": "#2a78d6", "pm2_5": "#1baf7a", "pm10": "#eda100"}
SERIES_LABELS = {"pm1": "PM1", "pm2_5": "PM2.5", "pm10": "PM10"}


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


def trend_chart(df: pd.DataFrame, resample_rule: Optional[str], title: str) -> go.Figure:
    plot_df = df.set_index("timestamp")
    if resample_rule:
        plot_df = plot_df.resample(resample_rule).mean()

    fig = go.Figure()
    for col in ["pm1", "pm2_5", "pm10"]:
        fig.add_trace(
            go.Scatter(
                x=plot_df.index,
                y=plot_df[col],
                mode="lines",
                name=SERIES_LABELS[col],
                line=dict(color=SERIES_COLORS[col], width=2),
            )
        )

    fig.update_layout(
        title=title,
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        yaxis_title="µg/m³",
        hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#e1e0d9")
    return fig


def render_tab(hours_back: int, resample_rule: Optional[str], title: str, empty_message: str):
    now = datetime.now(timezone.utc)
    start_ts = int((now - timedelta(hours=hours_back)).timestamp())
    end_ts = int(now.timestamp())

    df = fetch_readings(start_ts, end_ts)
    if df.empty:
        st.info(empty_message)
        return

    st.plotly_chart(trend_chart(df, resample_rule, title), use_container_width=True)
    with st.expander("Raw data"):
        st.dataframe(df, use_container_width=True)


st.set_page_config(page_title="BMV080 Air Quality", page_icon="\U0001f32b️", layout="wide")
st.title("BMV080 Particulate Matter Dashboard")
st.caption(f"Device: {st.secrets.get('device_id', 'unknown')}")

tab_hourly, tab_weekly, tab_monthly = st.tabs(["Hourly (48h)", "Weekly (7d)", "Monthly (30d)"])

with tab_hourly:
    render_tab(48, None, "Last 48 hours", "No readings in the last 48 hours yet.")

with tab_weekly:
    render_tab(24 * 7, "1h", "Last 7 days (hourly mean)", "No readings in the last 7 days yet.")

with tab_monthly:
    render_tab(24 * 30, "1D", "Last 30 days (daily mean)", "No readings in the last 30 days yet.")
