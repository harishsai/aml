import os
import json
from backend.db import get_connection

def check_discrepancy():
    tracking_id = 'KTX-202602-01001'
    conn = get_connection()
    if not conn:
        print("Failed to get DB connection")
        return
        
    try:
        with conn.cursor() as cur:
            # 1. Get Onboarding Details
            cur.execute("""
                SELECT company_name, lei_identifier, registration_number 
                FROM client_onboarding.onboarding_details 
                WHERE tracking_id = %s
            """, (tracking_id,))
            form_data = cur.fetchone()
            
            if not form_data:
                print(f"Tracking ID {tracking_id} not found in onboarding_details.")
                return
            
            form_company = form_data[0]
            form_lei = form_data[1]
            print(f"--- FORM DATA ---")
            print(f"Company: '{form_company}'")
            print(f"LEI:     '{form_lei}'")
            
            # 2. Get Registry Details
            cur.execute("""
                SELECT company_name, lei_number 
                FROM client_onboarding.entity_verification 
                WHERE lei_number = %s OR company_name ILIKE %s
            """, (form_lei, f"%{form_company}%"))
            registry_data = cur.fetchall()
            
            print(f"\n--- REGISTRY DATA ---")
            if not registry_data:
                print("No matches found in entity_verification.")
            for row in registry_data:
                print(f"Name Match: '{row[0]}' (LEI: {row[1]})")
                
    finally:
        conn.close()

if __name__ == "__main__":
    check_discrepancy()
