import os
import bcrypt
import psycopg2
from dotenv import load_dotenv

# Load environment
load_dotenv(".dbenv")

def reset_admin_password():
    print("\n--- Resetting Admin Password ---")
    new_password = "Admin@123"
    password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT", "5432"),
            database=os.getenv("DB_NAME", "postgres"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            sslmode=os.getenv("DB_SSL_MODE", "require")
        )
        print("SUCCESS: Connected to Postgres.")
        
        with conn.cursor() as cursor:
            cursor.execute("SET search_path TO client_onboarding, public;")
            email = "admin@kinetix.com"
            cursor.execute("""
                UPDATE users 
                SET password_hash = %s, 
                    must_change_password = FALSE,
                    updated_at = CURRENT_TIMESTAMP 
                WHERE email = %s
            """, (password_hash, email))
            
            if cursor.rowcount > 0:
                print(f"SUCCESS: Password for {email} has been reset to: {new_password}")
                conn.commit()
            else:
                print(f"FAILURE: User {email} not found during update.")

        conn.close()
    except Exception as e:
        print(f"FAILURE: {e}")

if __name__ == "__main__":
    reset_admin_password()
