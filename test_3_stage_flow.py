import os
import json
import uuid
from backend.agents.orchestrator import run_document_agent_stage, run_kyc_stage, run_aml_risk_stage
from backend.db import get_connection

def test_full_flow(tracking_id):
    print(f"--- STARTING EXPANDED 3-STAGE FLOW TEST FOR {tracking_id} ---")
    
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, email FROM client_onboarding.onboarding_details WHERE tracking_id = %s", (tracking_id,))
            row = cur.fetchone()
            if not row:
                print(f"Error: {tracking_id} not found")
                return
            onboarding_id = str(row[0])
            email = row[1]
    finally:
        conn.close()

    print(f"\n>> [STAGE 1] Running Expanded Document Agent (Multi-Doc)...")
    doc_res = run_document_agent_stage(onboarding_id)
    print(f"Result: {json.dumps(doc_res, indent=2)}")

    print(f"\n>> [STAGE 2] Running KYC Agent (Enhanced Logs)...")
    kyc_res = run_kyc_stage(onboarding_id)
    print(f"Result: {json.dumps(kyc_res, indent=2)}")

    print(f"\n>> [STAGE 3] Running AML Risk Agent...")
    aml_res = run_aml_risk_stage(onboarding_id)
    print(f"Result: {json.dumps(aml_res, indent=2)}")

    print("\n--- FLOW TEST COMPLETE ---")

if __name__ == "__main__":
    test_full_flow("KTX-202602-01001")
