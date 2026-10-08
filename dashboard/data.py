"""Data access and report generation for the dashboard (no Streamlit imports, so it is testable)."""
from datetime import datetime
from io import BytesIO

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import bindparam, text


def list_students(engine):
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT DISTINCT student_id FROM attention_records ORDER BY student_id"))
        return [r[0] for r in rows]


def load_records(engine, student_ids=None, limit=1000):
    """Latest `limit` records (newest first), optionally restricted to some students."""
    query = "SELECT * FROM attention_records"
    params = {"limit": limit}
    if student_ids:
        query += " WHERE student_id IN :ids"
        params["ids"] = list(student_ids)
    query += " ORDER BY timestamp DESC LIMIT :limit"
    stmt = text(query)
    if student_ids:
        stmt = stmt.bindparams(bindparam("ids", expanding=True))
    df = pd.read_sql(stmt, engine, params=params)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def summarize(df):
    """Per-student attention statistics."""
    summary = (
        df.groupby("student_id")["attention_score"]
        .agg(avg="mean", min="min", max="max", samples="count")
        .reset_index()
    )
    summary["avg"] = summary["avg"].round(1)
    return summary


def build_report_pdf(df, generated_at=None):
    """Render the summary report and return it as PDF bytes."""
    generated_at = generated_at or datetime.now()
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    story = [
        Paragraph("Attention Monitoring Session Report", styles["Title"]),
        Spacer(1, 12),
        Paragraph(f"Generated on: {generated_at:%Y-%m-%d %H:%M}", styles["Normal"]),
        Spacer(1, 24),
    ]
    rows = [["Student ID", "Avg Attention", "Min Attention", "Max Attention", "Samples"]]
    for r in summarize(df).itertuples():
        rows.append([r.student_id, f"{r.avg:.1f}%", f"{r.min}%", f"{r.max}%", str(r.samples)])
    table = Table(rows)
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 1, colors.black)]))
    story.append(table)

    doc.build(story)
    return buffer.getvalue()
