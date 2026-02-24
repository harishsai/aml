import json
import uuid
from backend.db import get_connection, get_agent_logs

def get_logs_by_tracking_id(tracking_id):
    conn = get_connection()
    if not conn:
        print("No connection")
        return
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM client_onboarding.onboarding_details WHERE tracking_id = %s", (tracking_id,))
            row = cur.fetchone()
            if not row:
                print(f"Tracking ID {tracking_id} not found")
                return
            onboarding_id = row[0]
            print(f"UUID for {tracking_id}: {onboarding_id}")
            logs = get_agent_logs(onboarding_id)
            print(json.dumps(logs, indent=2, default=str))
    finally:
        conn.close()

if __name__ == "__main__":
    get_logs_by_tracking_id("KTX-202602-01001")
