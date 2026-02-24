import os
import boto3
import psycopg2
import smtplib
from dotenv import load_dotenv

# Load environment
ENV_PATH = ".dbenv"
load_dotenv(ENV_PATH)

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_SESSION_TOKEN = os.getenv("AWS_SESSION_TOKEN")  # Might be None
AWS_REGION = os.getenv("AWS_REGION", "us-west-2")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "postgres")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_SSL_MODE = os.getenv("DB_SSL_MODE", "require")

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = os.getenv("SMTP_PORT")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

def test_aws():
    print("\n--- AWS Connectivity Check ---")
    print(f"Region: {AWS_REGION}")
    print(f"Bucket: {S3_BUCKET_NAME}")
    print(f"Access Key ID: {AWS_ACCESS_KEY_ID[:10]}... (Type: {'Temporary' if AWS_ACCESS_KEY_ID.startswith('ASIA') else 'Permanent'})")
    
    if AWS_ACCESS_KEY_ID.startswith("ASIA") and not AWS_SESSION_TOKEN:
        print("WARNING: Access Key starts with 'ASIA' but AWS_SESSION_TOKEN is missing in .dbenv!")

    try:
        session = boto3.Session(
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            aws_session_token=AWS_SESSION_TOKEN,
            region_name=AWS_REGION
        )
        sts = session.client('sts')
        identity = sts.get_caller_identity()
        print(f"SUCCESS: Connected to AWS as {identity['Arn']}")
        
        s3 = session.client('s3')
        try:
            s3.head_bucket(Bucket=S3_BUCKET_NAME)
            print(f"SUCCESS: S3 Bucket '{S3_BUCKET_NAME}' is accessible.")
        except Exception as e:
            print(f"ERROR: S3 Bucket access failed: {e}")
            
    except Exception as e:
        print(f"FAILURE: AWS Connectivity check failed: {e}")

def test_db():
    print("\n--- Database Connectivity Check ---")
    print(f"Host: {DB_HOST}")
    print(f"DB: {DB_NAME}")
    print(f"User: {DB_USER}")
    
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            sslmode=DB_SSL_MODE
        )
        print("SUCCESS: Connected to Postgres.")
        
        with conn.cursor() as cursor:
            # Check for website column
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'client_onboarding' 
                  AND table_name = 'onboarding_details' 
                  AND column_name = 'website';
            """)
            if cursor.fetchone():
                print("SUCCESS: 'website' column exists in onboarding_details.")
            else:
                print("FAILURE: 'website' column is MISSING from onboarding_details.")
        conn.close()
    except Exception as e:
        print(f"FAILURE: Database connectivity check failed: {e}")

def test_smtp():
    print("\n--- SMTP Connectivity Check ---")
    print(f"Server: {SMTP_SERVER}:{SMTP_PORT}")
    print(f"User: {SMTP_USER}")
    
    try:
        server = smtplib.SMTP(SMTP_SERVER, int(SMTP_PORT))
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        print("SUCCESS: SMTP Authentication successful.")
        server.quit()
    except Exception as e:
        print(f"FAILURE: SMTP Authentication failed: {e}")

if __name__ == "__main__":
    test_aws()
    test_db()
    test_smtp()
