import os
import psycopg2
from dotenv import load_dotenv

# Load DB env
load_dotenv(dotenv_path='.dbenv')

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "pgsdbtst")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

def sync_mock_docs():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SET search_path TO client_onboarding, public;")
            
            # Read local PDFs
            with open('mock_docs/bod_list.pdf', 'rb') as f: bod = f.read()
            with open('mock_docs/financials.pdf', 'rb') as f: fin = f.read()
            with open('mock_docs/ownership_structure.pdf', 'rb') as f: own = f.read()
            
            # Update Evergreen Financial Group
            cur.execute("""
                UPDATE onboarding_details 
                SET bod_list_content = %s, financials_content = %s, ownership_content = %s
                WHERE company_name = 'Evergreen Financial Group';
            """, (psycopg2.Binary(bod), psycopg2.Binary(fin), psycopg2.Binary(own)))
            
            # Update North Star Asset Management as well
            cur.execute("""
                UPDATE onboarding_details 
                SET bod_list_content = %s, financials_content = %s, ownership_content = %s
                WHERE company_name = 'North Star Asset Management';
            """, (psycopg2.Binary(bod), psycopg2.Binary(fin), psycopg2.Binary(own)))
            
            conn.commit()
            print("Successfully synced mock PDFs to database for primary records.")
    finally:
        conn.close()

if __name__ == "__main__":
    sync_mock_docs()
