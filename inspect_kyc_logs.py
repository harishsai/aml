import json
from backend.db import get_connection

def inspect_logs():
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Get the last KYC_AGENT log (synthesizer)
            cur.execute("""
                SELECT check_name, output, ai_summary 
                FROM client_onboarding.ai_agent_logs 
                WHERE agent_name = 'KYC_AGENT' 
                ORDER BY created_at DESC LIMIT 5
            """)
            logs = cur.fetchall()
            print("--- RECENT KYC_AGENT LOGS ---")
            for log in logs:
                print(f"Check: {log[0]}")
                print(f"Summary: {log[2]}")
                # print(f"Output: {json.dumps(log[1], indent=2)}")
                print("-" * 20)
                
            # Get the last email_domain_check
            cur.execute("""
                SELECT output, ai_summary 
                FROM client_onboarding.ai_agent_logs 
                WHERE check_name = 'email_domain_check' 
                ORDER BY created_at DESC LIMIT 1
            """)
            hygiene = cur.fetchone()
            if hygiene:
                print("\n--- EMAIL DOMAIN CHECK ---")
                print(f"Summary: {hygiene[1]}")
                print(f"Output: {json.dumps(hygiene[0], indent=2)}")

    finally:
        conn.close()

if __name__ == "__main__":
    inspect_logs()
