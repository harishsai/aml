import os
import secrets
import psycopg2
from datetime import datetime, timedelta
from psycopg2 import pool
from dotenv import load_dotenv

# Load database environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.dbenv'))

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "pgsdbtst")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_INIT_COMMAND = os.getenv("DB_INIT_COMMAND", "SET SESSION CHARACTERISTICS AS TRANSACTION READ WRITE;")

# Connection pool
try:
    connection_pool = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME
    )
    if connection_pool:
        print("Connection pool created successfully")
except (Exception, psycopg2.DatabaseError) as error:
    print(f"Error while connecting to PostgreSQL: {error}")
    connection_pool = None

def get_connection():
    if connection_pool:
        conn = connection_pool.getconn()
        # Set session characteristics and search path
        with conn.cursor() as cursor:
            cursor.execute(DB_INIT_COMMAND)
            cursor.execute("SET search_path TO client_onboarding, public;")
        return conn
    return None

def release_connection(conn):
    if connection_pool:
        connection_pool.putconn(conn)

def generate_tracking_id(cursor):
    """Generates a sequential tracking ID from the database sequence."""
    import datetime
    cursor.execute("SELECT nextval('client_onboarding.onboarding_tracking_seq')")
    seq_val = cursor.fetchone()[0]
    date_str = datetime.datetime.now().strftime("%Y%m")
    return f"KTX-{date_str}-{seq_val:05d}"

def log_onboarding_audit(onboarding_id, new_status, action_by=None, ip=None, workstation=None, remarks=None, old_status=None):
    """Logs an action to the onboarding_audit_log table."""
    conn = get_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            query = """
                INSERT INTO client_onboarding.onboarding_audit_log (
                    onboarding_id, old_status, new_status, action_by, ip_address, workstation_info, remarks
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (onboarding_id, old_status, new_status, action_by, ip, workstation, remarks))
            conn.commit()
            return True
    except Exception as e:
        print(f"Audit log failed: {e}")
        conn.rollback()
        return False
    finally:
        release_connection(conn)

def _generate_temp_password():
    """Generates a human-readable temporary password like Ktx-A7x2-mP9."""
    import string
    part1 = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(4))
    part2 = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(4))
    return f"Ktx-{part1}-{part2}"

def save_onboarding_details(data, ip=None, workstation=None):
    """
    Inserts data into onboarding_details, creates a participant user account
    with a temporary password, and writes the initial audit log.
    """
    conn = get_connection()
    if not conn:
        return False, "Database connection failed", None, None

    try:
        with conn.cursor() as cursor:
            tracking_id = generate_tracking_id(cursor)

            # Generate temporary password and hash it
            temp_password = _generate_temp_password()
            import bcrypt
            password_hash = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # 1. Insert onboarding details
            query = """
                INSERT INTO client_onboarding.onboarding_details (
                    company_name, company_address, city, state, country, zip_code,
                    phone_number, email, lei_identifier, entity_type,
                    bod_list_content, financials_content, ownership_content,
                    business_activity, source_of_funds, expected_volume, countries_operation,
                    aml_questions, status, tracking_id, submitted_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                RETURNING id;
            """
            cursor.execute(query, (
                data['company_name'], data['company_address'], data['city'], data['state'], data['country'], data['zip_code'],
                data['phone_number'], data['email'], data['lei_identifier'], data['entity_type'],
                psycopg2.Binary(data['bod_list_content']),
                psycopg2.Binary(data['financials_content']),
                psycopg2.Binary(data['ownership_content']),
                data['business_activity'], data['source_of_funds'], data['expected_volume'], data['countries_operation'],
                data['aml_questions'], 'PENDING_REVIEW', tracking_id
            ))
            onboarding_id = cursor.fetchone()[0]

            # 2. Create participant user account
            cursor.execute(
                "INSERT INTO client_onboarding.users (email, password_hash, full_name, must_change_password) VALUES (%s, %s, %s, TRUE) RETURNING id",
                (data['email'], password_hash, data['company_name'])
            )
            user_id = cursor.fetchone()[0]

            # 3. Assign PARTICIPANT role
            cursor.execute("SELECT id FROM client_onboarding.roles WHERE name = 'PARTICIPANT'")
            role_row = cursor.fetchone()
            if role_row:
                cursor.execute("INSERT INTO client_onboarding.user_roles (user_id, role_id) VALUES (%s, %s)", (user_id, role_row[0]))

            # 4. Link user to onboarding case
            cursor.execute("UPDATE client_onboarding.onboarding_details SET user_id = %s WHERE id = %s", (user_id, onboarding_id))

            # 5. Audit log
            audit_query = """
                INSERT INTO client_onboarding.onboarding_audit_log (
                    onboarding_id, old_status, new_status, ip_address, workstation_info, remarks
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(audit_query, (onboarding_id, None, 'PENDING_REVIEW', ip, workstation, 'Initial Application Submitted'))

            conn.commit()
            return True, onboarding_id, tracking_id, temp_password
    except Exception as e:
        if conn:
            conn.rollback()
        return False, str(e), None, None
    finally:
        if conn:
            release_connection(conn)

def get_all_tickets(status_filter=None):
    """Fetches all onboarding requests, optionally filtered by status."""
    conn = get_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            query = "SELECT id, company_name, tracking_id, status, submitted_at FROM client_onboarding.onboarding_details"
            params = []
            if status_filter:
                query += " WHERE status = %s"
                params.append(status_filter)
            query += " ORDER BY submitted_at DESC"
            cursor.execute(query, params)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error fetching tickets: {e}")
        return []
    finally:
        release_connection(conn)

def get_ticket_by_id(onboarding_id):
    """Fetches full details of a single ticket."""
    conn = get_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            query = "SELECT * FROM client_onboarding.onboarding_details WHERE id = %s"
            cursor.execute(query, (onboarding_id,))
            row = cursor.fetchone()
            if not row:
                return None
            columns = [desc[0] for desc in cursor.description]
            ticket = dict(zip(columns, row))
            
            # Binary fields cleanup
            for key in ['bod_list_content', 'financials_content', 'ownership_content']:
                if ticket.get(key):
                    ticket[key] = f"FILE_BLOB_{len(ticket[key])}_BYTES"
            
            # Fetch audit history
            audit_query = "SELECT * FROM client_onboarding.onboarding_audit_log WHERE onboarding_id = %s ORDER BY action_timestamp DESC"
            cursor.execute(audit_query, (onboarding_id,))
            audit_cols = [desc[0] for desc in cursor.description]
            ticket['history'] = [dict(zip(audit_cols, r)) for r in cursor.fetchall()]
            
            return ticket
    except Exception as e:
        print(f"Error fetching ticket detail: {e}")
        return None
    finally:
        release_connection(conn)

def get_user_by_email(email):
    """Fetches user details and their roles for authentication."""
    conn = get_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            # Fetch user
            query = "SELECT id, email, password_hash, full_name, is_active, must_change_password FROM client_onboarding.users WHERE email = %s"
            cursor.execute(query, (email,))
            row = cursor.fetchone()
            if not row:
                return None
            
            columns = [desc[0] for desc in cursor.description]
            user = dict(zip(columns, row))
            
            # Fetch roles
            role_query = """
                SELECT r.name 
                FROM client_onboarding.roles r
                JOIN client_onboarding.user_roles ur ON r.id = ur.role_id
                WHERE ur.user_id = %s
            """
            cursor.execute(role_query, (user['id'],))
            user['roles'] = [r[0] for r in cursor.fetchall()]
            
            return user
    except Exception as e:
        print(f"Error fetching user: {e}")
        return None
    finally:
        release_connection(conn)

def update_onboarding_status(onboarding_id, new_status, action_by=None, ip=None, workstation=None, remarks=None):
    """Updates ticket status and logs the audit entry."""
    conn = get_connection()
    if not conn:
        return False, "Database connection failed"
    try:
        with conn.cursor() as cursor:
            # Get old status
            cursor.execute("SELECT status FROM client_onboarding.onboarding_details WHERE id = %s", (onboarding_id,))
            old_status_row = cursor.fetchone()
            old_status = old_status_row[0] if old_status_row else None
            
            # Update status
            cursor.execute(
                "UPDATE client_onboarding.onboarding_details SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (new_status, onboarding_id)
            )
            
            # Log audit
            audit_query = """
                INSERT INTO client_onboarding.onboarding_audit_log (
                    onboarding_id, old_status, new_status, action_by, ip_address, workstation_info, remarks
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(audit_query, (onboarding_id, old_status, new_status, action_by, ip, workstation, remarks))
            
            conn.commit()
            return True, "Status updated successfully"
    except Exception as e:
        if conn:
            conn.rollback()
        return False, str(e)
    finally:
        if conn:
            release_connection(conn)

def get_document_content(onboarding_id, doc_type):
    """Retrieves binary content of a specific document."""
    conn = get_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            col_name = ""
            if doc_type == "bod": col_name = "bod_list_content"
            elif doc_type == "financials": col_name = "financials_content"
            elif doc_type == "ownership": col_name = "ownership_content"
            else: return None
            
            query = f"SELECT {col_name} FROM client_onboarding.onboarding_details WHERE id = %s"
            cursor.execute(query, (onboarding_id,))
            row = cursor.fetchone()
            return row[0] if row else None
    except Exception as e:
        print(f"Error fetching document: {e}")
        return None
    finally:
        release_connection(conn)

def verify_setup_token(token):
    """Checks if a setup token is valid and not expired."""
    conn = get_connection()
    if not conn: return None
    try:
        with conn.cursor() as cursor:
            query = "SELECT id, email, company_name FROM client_onboarding.onboarding_details WHERE setup_token = %s AND setup_token_expiry > CURRENT_TIMESTAMP"
            cursor.execute(query, (token,))
            row = cursor.fetchone()
            if not row: return None
            return {"id": row[0], "email": row[1], "company_name": row[2]}
    except: return None
    finally: release_connection(conn)

def complete_participant_setup(token, password_hash):
    """Creates user, assigns role, and links to onboarding case."""
    conn = get_connection()
    if not conn: return False, "DB Connection Error"
    try:
        with conn.cursor() as cursor:
            # 1. Get onboarding detail
            cursor.execute("SELECT id, email, company_name FROM client_onboarding.onboarding_details WHERE setup_token = %s", (token,))
            row = cursor.fetchone()
            if not row: return False, "Invalid or expired token"
            onb_id, email, name = row
            
            # 2. Create User
            cursor.execute(
                "INSERT INTO client_onboarding.users (email, password_hash, full_name) VALUES (%s, %s, %s) RETURNING id",
                (email, password_hash, name)
            )
            user_id = cursor.fetchone()[0]
            
            # 3. Assign Role (PARTICIPANT)
            cursor.execute("SELECT id FROM client_onboarding.roles WHERE name = 'PARTICIPANT'")
            role_p = cursor.fetchone()
            if not role_p:
                 # Ensure role exists if seeding was skipped
                 cursor.execute("INSERT INTO client_onboarding.roles (name, description) VALUES ('PARTICIPANT', 'Standard institution onboarding') RETURNING id")
                 role_id = cursor.fetchone()[0]
            else:
                 role_id = role_p[0]
                 
            cursor.execute("INSERT INTO client_onboarding.user_roles (user_id, role_id) VALUES (%s, %s)", (user_id, role_id))
            
            # 4. Link Onboarding
            cursor.execute("UPDATE client_onboarding.onboarding_details SET user_id = %s, setup_token = NULL WHERE id = %s", (user_id, onb_id))
            
            conn.commit()
            return True, "Setup complete"
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally: release_connection(conn)
