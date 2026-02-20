import requests
import os

# Base URL of the FastAPI server
BASE_URL = "http://localhost:8000"

def test_signup_submission():
    print("Starting Signup Submission Test...")
    
    # Path to mock documents
    mock_docs_dir = os.path.join(os.path.dirname(__file__), '..', 'mock_docs')
    
    # Prepare files
    files = {
        'file_bod': open(os.path.join(mock_docs_dir, 'bod_list.pdf'), 'rb'),
        'file_financials': open(os.path.join(mock_docs_dir, 'financials.pdf'), 'rb'),
        'file_ownership': open(os.path.join(mock_docs_dir, 'ownership_structure.pdf'), 'rb')
    }
    
    # Prepare form data
    data = {
        'fname': 'Test',
        'lname': 'User',
        'email': 'test.user@evergreen.com',
        'company': 'Evergreen Financial Group',
        'address': '120 Wall Street, New York, NY 10005',
        'country': 'US',
        'state': 'New York',
        'city': 'New York City',
        'zip': '10005',
        'phone': '+11234567890',
        'lei': '5493001KJY7UW9K12345',
        'entity_type': 'bank',
        'product': 'compliance',
        'reg_num': 'REG-12345-NX',
        'ownership_type': 'Publicly Traded',
        'business_activity': 'Investment Banking',
        'source_of_funds': 'Operating Revenues',
        'expected_volume': '$10M - $100M',
        'countries_op': 'US, UK, SG',
        'sanctions': 'no',
        'aml': 'yes'
    }
    
    try:
        response = requests.post(f"{BASE_URL}/signup", data=data, files=files)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("SUCCESS: Signup response received.")
            print(f"Response Body: {response.json()}")
        else:
            print(f"FAILED: {response.text}")
    except Exception as e:
        print(f"ERROR: Could not connect to server: {e}")
    finally:
        for f in files.values():
            f.close()

if __name__ == "__main__":
    test_signup_submission()
