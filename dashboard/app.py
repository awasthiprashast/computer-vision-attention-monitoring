import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
import time
from datetime import datetime
import boto3
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet

st.set_page_config(page_title="Attention Dashboard", layout="wide")
st.title("📊 Computer Vision Attention Monitoring System")

# RDS Connection
engine = create_engine("postgresql://adminCV:Mishu123@attention-rds.cp6mg60yymuj.ap-south-1.rds.amazonaws.com/attentiondb")

# S3 Client
s3_client = boto3.client('s3')
BUCKET_NAME = "attention-reports-prashast"   # Change if your bucket name is different

if st.button("🔄 Refresh Data"):
    st.rerun()

df = pd.read_sql("SELECT * FROM attention_records ORDER BY timestamp DESC LIMIT 1000", engine)
df['timestamp'] = pd.to_datetime(df['timestamp'])

if df.empty:
    st.warning("No data yet. Run the client.")
    st.stop()

# Metrics
col1, col2, col3 = st.columns(3)
col1.metric("Avg Attention", f"{df['attention_score'].mean():.1f}%")
col2.metric("Records", len(df))
col3.metric("Students", df['student_id'].nunique())

# Chart
fig = px.line(df, x='timestamp', y='attention_score', color='student_id', title="Attention Trends")
st.plotly_chart(fig, use_container_width=True)

# Generate Report Button
if st.button("📄 Generate & Upload PDF Report to S3"):
    with st.spinner("Generating PDF and uploading to S3..."):
        try:
            filename = f"attention_report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
            doc = SimpleDocTemplate(filename, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []

            story.append(Paragraph("Attention Monitoring Session Report", styles['Title']))
            story.append(Spacer(1, 12))
            story.append(Paragraph(f"Generated on: {datetime.now()}", styles['Normal']))
            story.append(Spacer(1, 24))

            # Summary Table
            data = [["Student ID", "Avg Attention", "Min Attention", "Max Attention"]]
            for student in df['student_id'].unique():
                student_data = df[df['student_id'] == student]
                data.append([
                    student,
                    f"{student_data['attention_score'].mean():.1f}%",
                    f"{student_data['attention_score'].min()}%",
                    f"{student_data['attention_score'].max()}%"
                ])

            table = Table(data)
            table.setStyle(TableStyle([('GRID', (0,0), (-1,-1), 1, colors.black)]))
            story.append(table)

            doc.build(story)

            # Upload to S3
            s3_client.upload_file(filename, BUCKET_NAME, filename)
            st.success(f"✅ Report uploaded to S3: {filename}")
        except Exception as e:
            st.error(f"Error: {e}")

st.dataframe(df.head(15), use_container_width=True)