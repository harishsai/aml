import requests
import os

url = "http://localhost:8000/signup"
files = {
    'file_bod': ('bod.pdf', b'fake pdf content', 'application/pdf'),
    'file_financials': ('fin.pdf', b'fake pdf content', 'application/pdf'),
    'file_ownership': ('own.pdf', b'fake pdf content', 'application/pdf')
}
data = {
    'fname': 'Participant',
    'lname': 'Test',
    'email': 'participant@example.com',
    'company': 'Alpha Corp',
    'address': '123 Tech Lane',
    'country': 'USA',
    'city': 'San Francisco',
    'zip': '94105',
    'phone': '555-0199',
    'lei': 'LEI123456789',
    'entity_type': 'FinTech',
    'product': 'Gateway',
    'reg_num': 'REG999',
    'ownership_type': 'Private',
    'business_activity': 'Strategic Trading',
    'source_of_funds': 'Operating Revenue',
    'expected_volume': '10M+',
    'countries_op': 'Global',
    'sanctions': 'No',
    'aml': 'Yes'
}

print("Submitting signup...")
response = requests.post(url, data=data, files=files)
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")

if response.status_code == 200:
    import psycopg2
    from dotenv import load_dotenv
    load_dotenv(dotenv_path='.dbenv')
    
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        database=os.getenv("DB_NAME", "pgsdbtst"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "")
    )
    cur = conn.cursor()
    cur.execute("SET search_path TO client_onboarding;")
    cur.execute("SELECT setup_token FROM onboarding_details WHERE email = 'participant@example.com' ORDER BY submitted_at DESC LIMIT 1")
    token = cur.fetchone()[0]
    print(f"\nSUCCESS! Found Setup Token: {token}")
    print(f"URL: http://localhost:8000/set-password.html?token={token}")
    cur.close()
    conn.close()
