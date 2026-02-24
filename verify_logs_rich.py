import psycopg2
from dotenv import load_dotenv
import os

load_dotenv('.dbenv')
conn = psycopg2.connect(
    host=os.getenv('DB_HOST'),
    port=os.getenv('DB_PORT'),
    user=os.getenv('DB_USER'),
    password=os.getenv('DB_PASSWORD'),
    dbname=os.getenv('DB_NAME')
)
with conn.cursor() as cur:
    cur.execute("""
        SELECT check_name, ai_summary 
        FROM client_onboarding.ai_agent_logs 
        WHERE onboarding_id = '972e0d2b-31cb-4113-bdc7-98c4329a7d6b' 
        ORDER BY created_at DESC
    """)
    for row in cur.fetchall():
        print(f"CHECK: {row[0]}")
        print(f"SUMMARY:\n{row[1]}")
        print("-" * 40)
conn.close()
