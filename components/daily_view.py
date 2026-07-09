"""Daily View — day-wise chart cards with AQI zone coloring,
bubble metrics, and office/non-office breakdown pie charts.

Mirrors the "Daily View" page of the reference aircognition CO₂ dashboard.
User can pick which pollutant (PM1 / PM2.5 / PM10) to display.
"""

from datetime import timezone, timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.colors import PM_CARD_DEFS, PM_ZONE_MAP

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
        "Saturday", "Sunday"]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _zone_for(conc: float, zones: list):
    for lo, hi, label, color, fill in zones:
        if lo <= conc < hi:
            return label, color, fill
    return "Hazardous", "#7e0023", "rgba(126,0,35,0.18)"


def _level_counts(series: pd.Series, zones: list) -> dict:
    counts = {}
    for lo, hi, label, *_ in zones:
        if hi >= 1e9:
            counts[label] = int((series >= lo).sum())
        else:
            counts[label] = int(((series >= lo) & (series < hi)).sum())
    return counts


# ── Bubble HTML ───────────────────────────────────────────────────────────────

def _bubble_html(value: float, label: str, zones: list) -> str:
    _, color, _ = _zone_for(value, zones)
    bg = color + "18"
    border = color + "55"
    display_val = f"{value:.0f}" if value >= 10 else f"{value:.1f}"
    return f"""
<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
            width:72px;height:72px;border-radius:50%;
            background:{bg};border:1.5px solid {border};text-align:center;gap:2px">
  <div style="font-size:1rem;font-weight:600;color:{color};line-height:1">{display_val}</div>
  <div style="font-size:9px;color:#888;text-transform:uppercase;letter-spacing:.04em;margin-top:2px">{label}</div>
</div>"""


# ── Chart builders ────────────────────────────────────────────────────────────

def _line_chart(day_df: pd.DataFrame, tz_offset: int, pm_key: str, zones: list) -> go.Figure:
    local_tz = timezone(timedelta(hours=tz_offset))
    loc = day_df["timestamp"].dt.tz_convert(local_tz)
    vals = day_df[pm_key]
    y_min = max(0, (vals.min() // 5) * 5 - 5)
    y_max = (vals.max() // 5) * 5 + 10

    fig = go.Figure()

    for lo, hi, label, color, fill in zones:
        y0 = max(lo, y_min)
        y1 = min(hi, y_max)
        if y0 >= y1:
            continue
        fig.add_hrect(
            y0=y0, y1=y1,
            fillcolor=fill, line_width=0,
            annotation_text=label,
            annotation_position="right",
            annotation=dict(font_size=10, font_color=color),
        )

    lo, *_, hi = zones[0]
    for _, hi_end, _, _, _ in zones[:-1]:
        bound = hi_end
        if y_min < bound < y_max:
            fig.add_hline(
                y=bound,
                line=dict(color="rgba(0,0,0,0.15)", width=1, dash="dot"),
            )

    fig.add_trace(go.Scatter(
        x=loc,
        y=vals,
        mode="lines+markers",
        line=dict(color="#2c3e50", width=2),
        marker=dict(
            color=[_zone_for(v, zones)[1] for v in vals],
            size=5,
            line=dict(color="white", width=1),
        ),
        hovertemplate="%{x|%H:%M}<br><b>%{y:.1f} µg/m³</b><extra></extra>",
    ))

    fig.update_layout(
        height=340,
        margin=dict(l=0, r=80, t=10, b=0),
        paper_bgcolor="white",
        plot_bgcolor="white",
        showlegend=False,
        xaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0",
                   ticksuffix=" µg/m³", range=[y_min, y_max]),
    )
    return fig


def _pie_chart(counts: dict, title: str, zones: list) -> go.Figure:
    zone_labels = [z[2] for z in zones]
    zone_colors = [z[3] for z in zones]
    pairs = [(l, c, counts.get(l, 0)) for l, c in zip(zone_labels, zone_colors) if counts.get(l, 0) > 0]
    total = sum(v for *_, v in pairs)

    if total == 0:
        fig = go.Figure(go.Pie(
            labels=["No data"], values=[1],
            marker_colors=["#e0e0e0"], textinfo="label", hoverinfo="skip",
        ))
    else:
        labels, colors, values = zip(*pairs)
        fig = go.Figure(go.Pie(
            labels=list(labels), values=list(values),
            marker=dict(colors=list(colors), line=dict(color="white", width=2)),
            textinfo="percent",
            hole=0.55,
            hovertemplate="%{label}<br><b>%{value} readings</b> (%{percent})<extra></extra>",
        ))

    fig.update_layout(
        title=dict(text=title, font=dict(size=11), x=0, xanchor="left"),
        height=160,
        margin=dict(l=0, r=0, t=28, b=0),
        paper_bgcolor="white",
        showlegend=False,
    )
    return fig


# ── Main renderer ─────────────────────────────────────────────────────────────

def render_daily_view(df: pd.DataFrame, tz_offset_int: int):
    """Render the Daily View tab — one card per day with chart + bubbles + pies."""
    local_tz = timezone(timedelta(hours=tz_offset_int))

    # Pollutant selector
    labels = [c["label"] for c in PM_CARD_DEFS]
    choice = st.selectbox("Pollutant", labels, index=1, key="daily_view_pollutant")
    pm_key = next(c["key"] for c in PM_CARD_DEFS if c["label"] == choice)
    zones = PM_ZONE_MAP[pm_key]

    df_local = df.copy()
    df_local["ts_local"] = df_local["timestamp"].dt.tz_convert(local_tz)
    df_local["date_local"] = df_local["ts_local"].dt.date
    days = sorted(df_local["date_local"].unique(), reverse=True)
    total_all = len(df_local)

    date_range = (
        df_local["ts_local"].iloc[0].strftime("%B %d, %Y")
        if len(days) == 1
        else f"{df_local['ts_local'].iloc[0].strftime('%B %d, %Y')} – "
             f"{df_local['ts_local'].iloc[-1].strftime('%B %d, %Y')}"
    )

    tz_label = f"UTC+{tz_offset_int}" if tz_offset_int >= 0 else f"UTC{tz_offset_int}"

    st.caption(
        f"{date_range}  ·  {tz_label}  ·  "
        f"{total_all} readings across {len(days)} day(s)"
    )

    for day_date in days:
        day_df = df_local[df_local["date_local"] == day_date].copy()
        if day_df.empty:
            continue
        day_name = DAYS[pd.Timestamp(day_date).weekday()]
        total = len(day_df)

        mean_val = day_df[pm_key].mean()
        max_val = day_df[pm_key].max()
        min_val = day_df[pm_key].min()
        duration = (day_df["ts_local"].iloc[-1] - day_df["ts_local"].iloc[0]).total_seconds() / 3600

        hour = day_df["ts_local"].dt.hour
        os_start = st.session_state.get("office_start", 10)
        os_end = st.session_state.get("office_end", 21)
        office_df = day_df[(hour >= os_start) & (hour < os_end)]
        non_office_df = day_df[(hour < os_start) | (hour >= os_end)]
        oc = _level_counts(office_df[pm_key], zones) if not office_df.empty else {}
        noc = _level_counts(non_office_df[pm_key], zones) if not non_office_df.empty else {}

        st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
            background:linear-gradient(135deg,#e8f1fb,#dbeafe);
            border-left:4px solid #378ADD;
            border-radius:12px;padding:1rem 1.5rem;margin-bottom:.75rem">
  <div>
    <div style="font-size:1rem;font-weight:600;color:#1e293b">
      {day_name}
      <span style="font-weight:400;color:#64748b;font-size:.9rem">
        &nbsp;{pd.Timestamp(day_date).strftime("%B %d, %Y")}
      </span>
    </div>
    <div style="font-size:12px;color:#94a3b8;margin-top:3px">
      {day_df["ts_local"].iloc[0].strftime("%I:%M %p").lstrip("0")} –
      {day_df["ts_local"].iloc[-1].strftime("%I:%M %p").lstrip("0")} {tz_label}
      &nbsp;·&nbsp; {total} readings &nbsp;·&nbsp; {duration:.1f} h
    </div>
  </div>
  <div style="display:flex;gap:10px">
    {_bubble_html(mean_val, "Average", zones)}
    {_bubble_html(max_val,  "Peak", zones)}
    {_bubble_html(min_val,  "Min", zones)}
  </div>
</div>
""", unsafe_allow_html=True)

        col_line, col_pies = st.columns([3, 1.2])

        with col_line:
            st.plotly_chart(_line_chart(day_df, tz_offset_int, pm_key, zones),
                            width="stretch", key=f"line_{pm_key}_{day_date}")

        with col_pies:
            st.plotly_chart(
                _pie_chart(oc, f"☀️ Office ({os_start:02d}:00–{os_end:02d}:00)", zones),
                width="stretch", key=f"pie_o_{pm_key}_{day_date}"
            )
            st.plotly_chart(
                _pie_chart(noc, "🌙 Non-office hours", zones),
                width="stretch", key=f"pie_n_{pm_key}_{day_date}"
            )

        st.divider()
