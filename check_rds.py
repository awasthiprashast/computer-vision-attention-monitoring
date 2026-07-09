import psycopg2
from datetime import datetime

# === UPDATE THESE WITH YOUR DETAILS ===
RDS_HOST = "REDACTED_RDS_HOST"
RDS_USER = "REDACTED_USER"
RDS_PASSWORD = "REDACTED_PASSWORD"   # ← CHANGE THIS
RDS_DB = "attentiondb"

try:
    conn = psycopg2.connect(
        host=RDS_HOST,
        user=RDS_USER,
        password=RDS_PASSWORD,
        dbname=RDS_DB,
        port=5432
    )
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, student_id, timestamp, attention_score, ear 
        FROM attention_records 
        ORDER BY timestamp DESC LIMIT 15
    """)
    
    rows = cur.fetchall()
    
    print(f"\n✅ Total records found: {len(rows)}\n")
    for row in rows:
        print(f"ID: {row[0]} | Student: {row[1]} | Time: {row[2]} | Attention: {row[3]}% | EAR: {row[4]}")
    
    cur.close()
    conn.close()

except Exception as e:
    print("❌ Error:", str(e))