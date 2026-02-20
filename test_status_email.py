import sys
import os
# Add current directory to path so we can import backend
sys.path.append(os.getcwd())

from backend.email_utils import send_status_update_email

def test_rejection_email():
    recipient = "harishsai@gmail.com"
    tracking_id = "KTX-202602-01014"
    status = "REJECTED"
    remarks = "Documentation provided is insufficient for entity verification. Please provide the UBO declaration."
    
    print(f"Testing Status Update Email for: {recipient}")
    success = send_status_update_email(recipient, tracking_id, status, remarks)
    
    if success:
        print("SUCCESS call returned True")
    else:
        print("FAILURE call returned False")

if __name__ == "__main__":
    test_rejection_email()
