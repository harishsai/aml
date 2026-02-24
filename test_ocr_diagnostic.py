import os
import json
import boto3
from backend.agents.orchestrator import invoke_bedrock_model_multimodal
from backend.db import get_connection

TRACKING_ID = "KTX-202602-01001"

def test_ocr():
    print(f"--- STARTING OCR DIAGNOSTIC FOR {TRACKING_ID} ---")
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT company_name, registration_number, incorporation_doc_s3_uri 
            FROM client_onboarding.onboarding_details 
            WHERE tracking_id = %s
        """, (TRACKING_ID,))
        row = cur.fetchone()
        if not row:
            print("Tracking ID not found.")
            return
        
        form_name, form_reg, s3_uri = row
        print(f"Form Data: Name={form_name}, Reg={form_reg}")
        print(f"S3 URI: {s3_uri}")
        
    prompt = (
        "Extract the 'Legal Name' and 'Registration Number' from this incorporation document. "
        "Return a JSON object with keys 'extracted_name', 'reg_number', and 'confidence_score'."
    )
    
    res = invoke_bedrock_model_multimodal(prompt, {"incorporation_doc": s3_uri})
    print("\nOCR RESULT:")
    print(json.dumps(res, indent=2))
    
    # Simulate the audit_trail format
    audit_trail = [
        {
            "label": "Document Verification",
            "form_value": form_name,
            "ocr_value": res.get("extracted_name", "N/A"),
            "status": "MATCH" if form_name.lower() in res.get("extracted_name", "").lower() else "MISMATCH"
        },
        {
            "label": "Reg Number Check",
            "form_value": form_reg,
            "ocr_value": res.get("reg_number", "N/A"),
            "status": "MATCH" if str(form_reg) == str(res.get("reg_number")) else "MISMATCH"
        }
    ]
    print("\nPROPOSED AUDIT TRAIL:")
    print(json.dumps(audit_trail, indent=2))

if __name__ == "__main__":
    test_ocr()
