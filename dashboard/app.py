import os
from datetime import datetime

import boto3
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine

from data import build_report_pdf, list_students, load_records, summarize

st.set_page_config(page_title="Attention Dashboard", layout="wide")
st.title("Computer Vision Attention Monitoring System")

# Configuration comes from environment variables (see .env.example)
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    st.error("DATABASE_URL is not set. See .env.example for the expected format.")
    st.stop()

# Optional: report upload is disabled when S3_BUCKET is unset
BUCKET_NAME = os.environ.get("S3_BUCKET")


@st.cache_resource
def get_engine():
    return create_engine(DATABASE_URL, pool_pre_ping=True)


@st.cache_resource
def get_s3_client():
    return boto3.client("s3")


engine = get_engine()

# ---- Sidebar controls ----
with st.sidebar:
    st.header("Controls")
    auto_refresh = st.toggle("Auto-refresh (5s)", value=True)
    limit = st.slider("Max records", 100, 5000, 1000, step=100)
    try:
        selected = st.multiselect("Students", list_students(engine), placeholder="All students")
    except Exception as e:
        st.error(f"Could not reach the database ({type(e).__name__}). Is it running?")
        st.stop()


def live_view():
    try:
        df = load_records(engine, selected, limit)
    except Exception as e:
        st.error(f"Could not load records ({type(e).__name__}).")
        return

    if df.empty:
        st.info("No data yet. Run the client or `python scripts/seed_demo_data.py`.")
        return

    col1, col2, col3 = st.columns(3)
    col1.metric("Avg Attention", f"{df['attention_score'].mean():.1f}%")
    col2.metric("Records", len(df))
    col3.metric("Students", df["student_id"].nunique())

    fig = px.line(df.sort_values("timestamp"), x="timestamp", y="attention_score",
                  color="student_id", title="Attention Trends")
    fig.update_yaxes(range=[0, 100])
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Per-student summary")
    st.dataframe(summarize(df), use_container_width=True, hide_index=True)

    st.subheader("Latest records")
    st.dataframe(df.head(15), use_container_width=True, hide_index=True)

    pdf = build_report_pdf(df)
    filename = f"attention_report_{datetime.now():%Y%m%d_%H%M}.pdf"
    st.download_button("Download PDF report", pdf, file_name=filename, mime="application/pdf")
    if BUCKET_NAME and st.button("Upload report to S3"):
        try:
            get_s3_client().put_object(Bucket=BUCKET_NAME, Key=filename, Body=pdf)
            st.success(f"Report uploaded to s3://{BUCKET_NAME}/{filename}")
        except Exception as e:
            st.error(f"Upload failed ({type(e).__name__}).")


if auto_refresh:
    st.fragment(live_view, run_every=5)()
else:
    live_view()
