# Computer Vision Attention Monitoring System

A real-time edge-cloud attention monitoring system for online learning using MediaPipe and AWS.

## Features
- On-device facial landmark detection using MediaPipe
- Eye Aspect Ratio (EAR) based attention scoring
- Real-time data streaming to AWS backend (no raw video sent)
- Data stored in Amazon RDS as time-series
- Interactive Streamlit dashboard for teachers
- PDF report generation and storage in AWS S3

## Tech Stack
- **Computer Vision**: OpenCV, MediaPipe
- **Backend**: FastAPI
- **Dashboard**: Streamlit
- **Cloud**: AWS EC2, RDS PostgreSQL, S3
- **Database**: PostgreSQL

## Architecture
- Student laptop → MediaPipe processing → Attention score → FastAPI (EC2) → RDS
- Teacher views live dashboard + generates reports stored in S3

## How to Run

### 1. Client (Student Side)
```bash
cd client
python attention_client.py