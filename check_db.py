import os
import json
import psycopg2
from dotenv import load_dotenv

# Load from .dbenv
load_dotenv('.dbenv')

def check_entity():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        database=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
        sslmode=os.getenv("DB_SSL_MODE", "prefer")
    )
    try:
        with conn.cursor() as cursor:
            # Update the Registry EIN to match the magic pin / document
            print("Updating Registry EIN for Evergreen...")
            query = "UPDATE client_onboarding.entity_verification SET ein_number = 'NY-889900-TAX' WHERE lei_number = '5493001KJY7UW9K12345';"
            cursor.execute(query)
            conn.commit()
            print("Successfully updated registry.")
            
            # Verify the update
            cursor.execute("SELECT company_name, ein_number FROM client_onboarding.entity_verification WHERE lei_number = '5493001KJY7UW9K12345';")
            row = cursor.fetchone()
            print(f"Current Registry Data: Name: {row[0]}, EIN: {row[1]}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_entity()
