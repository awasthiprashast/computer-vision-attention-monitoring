"""Print the latest rows of attention_records to verify the database connection.

Usage:
    DATABASE_URL=postgresql://user:pass@host:5432/dbname python scripts/db_check.py
"""
import os
import sys

from sqlalchemy import create_engine, text

database_url = os.environ.get("DATABASE_URL")
if not database_url:
    sys.exit("DATABASE_URL is not set. See .env.example.")

try:
    engine = create_engine(database_url)
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT id, student_id, timestamp, attention_score, ear "
            "FROM attention_records ORDER BY timestamp DESC LIMIT 15"
        )).fetchall()
except Exception as e:
    sys.exit(f"Error: {e}")

print(f"\nLatest {len(rows)} records:\n")
for row in rows:
    print(f"ID: {row[0]} | Student: {row[1]} | Time: {row[2]} | Attention: {row[3]}% | EAR: {row[4]}")
