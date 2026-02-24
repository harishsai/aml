import json
from backend.db import get_connection

def verify_lei():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT agent_name, input_context, output 
                FROM client_onboarding.ai_agent_logs 
                WHERE agent_name = 'KYC_SPECIALIST' 
                ORDER BY created_at DESC LIMIT 1
            """)
            row = cur.fetchone()
            if row:
                print(f"AGENT: {row[0]}")
                print(f"INPUT_CONTEXT: {json.dumps(row[1], indent=2)}")
                print(f"OUTPUT: {json.dumps(row[2], indent=2)}")
            else:
                print("No log found.")
    finally:
        conn.close()

if __name__ == "__main__":
    verify_lei()
