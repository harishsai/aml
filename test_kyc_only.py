import sys
import os
# Ensure the root directory is in the path
sys.path.append(os.getcwd())

from backend.agents.orchestrator import run_kyc_stage
from backend.db import get_connection

def test_kyc_only():
    onboarding_id = "972e0d2b-31cb-4113-bdc7-98c4329a7d6b" # KTX-202602-01001
    print(f"Testing KYC ONLY for {onboarding_id}...")
    try:
        res = run_kyc_stage(onboarding_id)
        print(f"Result: {res}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_kyc_only()
