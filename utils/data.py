"""DynamoDB access. get_table() and fetch_readings() are unchanged from the
original app.py - only get_latest_reading() is new (additive, read-only)."""

from typing import Optional

import boto3
import pandas as pd
import streamlit as st
from boto3.dynamodb.conditions import Key

# How stale the most recent reading can be before the header shows Offline.
# Generous relative to the firmware's hourly flush cycle.
ONLINE_THRESHOLD_MINUTES = 120


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


@st.cache_data(ttl=300)
def fetch_all_readings() -> pd.DataFrame:
    """Fetch ALL readings for the device (no date range filter).
    Powers the daily view which shows a card for every day with data."""
    table = get_table()
    device_id = st.secrets["device_id"]

    items = []
    query_kwargs = {
        "KeyConditionExpression": Key("device_id").eq(device_id)
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


@st.cache_data(ttl=60)
def get_latest_reading() -> Optional[dict]:
    """Single cheapest-possible lookup of the most recent item, independent
    of any tab's time range - powers the header's Last Updated/Online badge."""
    table = get_table()
    device_id = st.secrets["device_id"]

    response = table.query(
        KeyConditionExpression=Key("device_id").eq(device_id),
        ScanIndexForward=False,
        Limit=1,
    )
    items = response.get("Items", [])
    return items[0] if items else None
