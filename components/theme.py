"""Global CSS injection, driven by utils.colors.THEME/DARK_THEME."""

import streamlit as st

from utils.colors import DARK_THEME, THEME


def inject_global_css():
    t = DARK_THEME if st.session_state.get("dark_mode") else THEME
    st.markdown(
        f"""
        <style>
            .stApp {{ background: {t["bg"]}; }}
            h1 {{ font-weight: 700; color: {t["text_primary"]}; font-size: 28px; }}
            .stTabs [data-baseweb="tab-list"] {{
                gap: 4px; background: {t["card"]}; padding: 6px; border-radius: 12px;
                box-shadow: {t["shadow"]};
            }}
            .stTabs [data-baseweb="tab"] {{ border-radius: 8px; padding: 6px 20px; font-weight: 500; font-size: 14px; }}
            .stTabs [aria-selected="true"] {{ background: #2a78d6 !important; color: #fff !important; }}
            [data-testid="stMetricValue"] {{ font-size: 28px; font-weight: 700; }}
            .stDataFrame {{ border: none; border-radius: {t["radius"]}; box-shadow: {t["shadow"]}; }}
            .st-ef {{ border-radius: {t["radius"]}; }}
            section[data-testid="stSidebar"] > div {{
                background: {t["card"]}; border-right: 1px solid {t["border"]}; padding: 20px 16px;
            }}
            section[data-testid="stSidebar"] .stSelectbox label {{
                font-size: 13px; font-weight: 600; color: {t["text_secondary"]};
            }}
            .stAlert {{ border-radius: 10px; }}
            footer {{ display: none; }}
            div[data-testid="stExpander"] {{
                border: 1px solid {t["border"]}; border-radius: {t["radius"]};
                background: {t["card"]}; box-shadow: {t["shadow"]};
            }}
            div[data-testid="stExpander"] summary {{ font-weight: 600; color: {t["text_secondary"]}; padding: 8px 12px; }}
            .stInfo, .stSuccess, .stWarning {{ border-radius: 10px; }}

            /* Stat cards - shared shell for today's PM cards and any future card */
            .metric-card {{
                background: {t["card"]};
                border-radius: {t["radius"]};
                padding: 16px 18px;
                border-left: 5px solid var(--card-accent, #2a78d6);
                box-shadow: {t["shadow"]};
                margin-bottom: 8px;
                transition: transform 0.15s ease, box-shadow 0.15s ease;
            }}
            .metric-card:hover {{
                transform: translateY(-3px);
                box-shadow: 0 8px 20px rgba(0,0,0,0.08);
            }}
            .metric-card-label {{
                font-size: 12px; color: {t["text_secondary"]}; font-weight: 600;
                text-transform: uppercase; letter-spacing: 0.5px;
            }}
            .metric-card-value-row {{ display: flex; align-items: baseline; gap: 8px; margin: 6px 0 2px; }}
            .metric-card-value {{ font-size: 32px; font-weight: 700; color: {t["text_primary"]}; }}
            .metric-card-unit {{ font-size: 12px; color: {t["text_secondary"]}; font-weight: 400; }}
            .metric-card-delta {{ font-size: 12px; font-weight: 700; }}
            .metric-card-footer {{ font-size: 11px; color: {t["text_secondary"]}; margin-top: 6px; }}
            .metric-card-badge {{
                display: inline-block; font-size: 11px; font-weight: 700;
                padding: 2px 12px; border-radius: 12px;
            }}

            /* Header */
            .bmv-header {{
                background: {t["card"]}; border: 1px solid {t["border"]}; border-radius: {t["radius"]};
                box-shadow: {t["shadow"]}; padding: 16px 22px; margin-bottom: 18px;
                display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;
            }}
            .bmv-header-title {{ font-size: 20px; font-weight: 700; color: {t["text_primary"]}; }}
            .bmv-header-sub {{ font-size: 12px; color: {t["text_secondary"]}; margin-top: 2px; }}
            .bmv-status-badge {{
                display: inline-block; font-size: 12px; font-weight: 600;
                padding: 4px 12px; border-radius: 12px;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )
