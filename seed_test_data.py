import uuid
from backend.db import get_connection, release_connection

def seed():
    conn = get_connection()
    if not conn:
        print("Failed to connect to DB")
        return
    try:
        with conn.cursor() as cursor:
            # 1. Get Admin User
            cursor.execute("SELECT id FROM client_onboarding.users WHERE email = %s", ('admin@kinetix.com',))
            user_row = cursor.fetchone()
            if not user_row:
                print("Admin user not found")
                return
            user_id = user_row[0]
            
            # 2. Insert Test Record
            onboarding_id = str(uuid.uuid4())
            tracking_id = "TEST-" + onboarding_id[:8].upper()
            
            cursor.execute("""
                INSERT INTO client_onboarding.onboarding_details (
                    id, user_id, tracking_id, company_name, registration_number, 
                    email, country, status, business_activity
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tracking_id) DO NOTHING
                RETURNING id
            """, (
                onboarding_id, user_id, tracking_id, 
                "Evergreen Financial Group", "REG-123456",
                "compliance@evergreen.com", "United States", "KYC_COMPLETE",
                "Financial Services"
            ))
            row = cursor.fetchone()
            if row:
                print(f"Seeded onboarding_id: {row[0]}")
            else:
                # Fallback if conflict or somehow already exists
                cursor.execute("SELECT id FROM client_onboarding.onboarding_details WHERE company_name = %s LIMIT 1", ("Evergreen Financial Group",))
                row = cursor.fetchone()
                print(f"Existing onboarding_id: {row[0]}")
                
        conn.commit()
    except Exception as e:
        print(f"Seeding failed: {e}")
        conn.rollback()
    finally:
        release_connection(conn)

if __name__ == "__main__":
    seed()
