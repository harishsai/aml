import os
import json
import uuid
from backend.agents.orchestrator import run_kyc_stage, run_aml_risk_stage
from backend.db import get_connection, release_connection

# Seeded Case: Evergreen Financial Group
TRACKING_ID = "KTX-202602-01001"

def get_id():
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM client_onboarding.onboarding_details WHERE tracking_id = %s", (TRACKING_ID,))
        row = cur.fetchone()
        return str(row[0]) if row else None

onboarding_id = get_id()
if not onboarding_id:
    print(f"[ERROR] Tracking ID {TRACKING_ID} not found. Please ensure seed data is present.")
    exit(1)

print(f"--- STARTING FINAL INTEGRITY PROOF FOR {TRACKING_ID} ({onboarding_id}) ---")

try:
    print("\n[STEP 1] Running KYC Stage (Sanctions + News)...")
    kyc_res = run_kyc_stage(onboarding_id)
    print(f"KYC COMPLETED. Composite Risk: {kyc_res.get('composite_risk')}")
    
    print("\n[STEP 2] Running AML Risk Stage (Final Profiling)...")
    aml_res = run_aml_risk_stage(onboarding_id)
    print(f"AML COMPLETED. Risk Rating: {aml_res.get('risk_rating')}")
    
    print("\n--- AUDIT LOG VERIFICATION ---")
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute("SELECT agent_name, check_name, output FROM client_onboarding.ai_agent_logs WHERE onboarding_id = %s ORDER BY created_at DESC LIMIT 5", (onboarding_id,))
        logs = cursor.fetchall()
        if not logs:
            print("No logs found in ai_agent_logs.")
        for log in logs:
            print(f"\nAgent: {log[0]} | Check: {log[1]}")
            output = log[2]
            if isinstance(output, str):
                output = json.loads(output)
            
            # Print a snippet of the output
            print(f"Output Logic: {str(output.get('decision_logic') or output.get('ai_summary'))[:200]}...")
    release_connection(conn)

except Exception as e:
    print(f"\n[FAILED] Integrity Test Error: {str(e)}")
    import traceback
    traceback.print_exc()
