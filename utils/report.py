"""PDF report generation via fpdf2 (pure-Python, no system dependencies -
safe on Streamlit Community Cloud). First cut is text/tables only (summary,
insights, recommendations); embedding chart images is a natural follow-up
once kaleido's cloud footprint has been evaluated.
"""

from datetime import datetime

import pandas as pd
from fpdf import FPDF

from utils.calculations import iaq_label, iaq_score, numeric_aqi
from utils.analytics import worst_aqi
from utils.colors import AQI_CATEGORIES, PM_CARD_DEFS


def generate_pdf_report(df: pd.DataFrame, device_id: str, range_label: str,
                        insights: list, recommendations: list) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "BMV080 Indoor Air Quality Report", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Device: {device_id}  |  Range: {range_label}  |  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.ln(4)

    latest = df.iloc[-1]
    aqi_val = numeric_aqi(latest["pm1"], latest["pm2_5"], latest["pm10"])
    aqi_idx = worst_aqi(latest["pm1"], latest["pm2_5"], latest["pm10"])
    score = iaq_score(latest["pm1"], latest["pm2_5"], latest["pm10"])

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Summary", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"AQI Score: {aqi_val} ({AQI_CATEGORIES[aqi_idx][0]})", ln=True)
    pdf.cell(0, 6, f"Indoor Air Quality Score: {score}/100 ({iaq_label(score)})", ln=True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Period Statistics", ln=True)
    pdf.set_font("Helvetica", "", 10)
    for card in PM_CARD_DEFS:
        v = df[card["key"]]
        pdf.cell(0, 6, f"{card['label']}: avg {v.mean():.1f}, min {v.min():.1f}, max {v.max():.1f} ug/m3", ln=True)
    pdf.ln(2)

    if insights:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Key Insights", ln=True)
        pdf.set_font("Helvetica", "", 10)
        for line in insights:
            pdf.multi_cell(0, 6, f"- {line}")
        pdf.ln(2)

    if recommendations:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Recommendations", ln=True)
        pdf.set_font("Helvetica", "", 10)
        for line in recommendations:
            pdf.multi_cell(0, 6, f"- {line}")

    return bytes(pdf.output())
