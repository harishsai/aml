import os
import psycopg2
from dotenv import load_dotenv

# Load environment
load_dotenv(".dbenv")

def check_admin_user():
    print("\n--- Checking Admin User in Database ---")
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
            cursor.execute("SELECT id, email, is_active FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            
            if user:
                print(f"User FOUND: ID={user[0]}, Email={user[1]}, Active={user[2]}")
                # Check roles
                cursor.execute("""
                    SELECT r.name 
                    FROM roles r 
                    JOIN user_roles ur ON r.id = ur.role_id 
                    WHERE ur.user_id = %s
                """, (user[0],))
                roles = cursor.fetchall()
                print(f"Roles: {[r[0] for r in roles]}")
            else:
                print("User NOT FOUND: admin@kinetix.com")
                
                # List all users to see what's there
                cursor.execute("SELECT email FROM users LIMIT 10")
                users = cursor.fetchall()
                print(f"Existing users (limit 10): {[u[0] for u in users]}")

        conn.close()
    except Exception as e:
        print(f"FAILURE: {e}")

if __name__ == "__main__":
    check_admin_user()
