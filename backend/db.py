import os
import secrets
import psycopg2
from datetime import datetime, timedelta
from psycopg2 import pool
from dotenv import load_dotenv
from .logger import logger_db as logger

# Load database environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.dbenv'))

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "pgsdbtst")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_SSL_MODE = os.getenv("DB_SSL_MODE", "prefer")
DB_INIT_COMMAND = os.getenv("DB_INIT_COMMAND", "SET SESSION CHARACTERISTICS AS TRANSACTION READ WRITE;")

# AWS Configuration
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "kinetix-onboarding-docs")
AWS_REGION = os.getenv("AWS_REGION", "us-west-2")

# Connection pool
try:
    connection_pool = psycopg2.pool.SimpleConnectionPool(
        1, 10,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT,
        database=DB_NAME,
        sslmode=DB_SSL_MODE
    )
    if connection_pool:
        logger.info("Connection pool created successfully")
except (Exception, psycopg2.DatabaseError) as error:
    logger.error(f"Error while connecting to PostgreSQL: {error}")
    connection_pool = None

def get_connection():
    if connection_pool:
        conn = connection_pool.getconn()
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
    cursor.execute("SELECT nextval('client_onboarding.onboarding_tracking_seq')")
    seq_val = cursor.fetchone()[0]
    date_str = datetime.now().strftime("%Y%m")
    return f"KTX-{date_str}-{seq_val:05d}"

def get_next_tracking_id():
    """Public helper to pre-generate a tracking ID before full database insertion."""
    conn = get_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            return generate_tracking_id(cursor)
    finally:
        release_connection(conn)

def _generate_temp_password():
    """Generates a human-readable temporary password like Ktx-A7x2-mP9."""
    import string
    part1 = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(4))
    part2 = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(4))
    return f"Ktx-{part1}-{part2}"

def save_onboarding_details(data, ip=None, workstation=None, provided_tracking_id=None):
    """
    Inserts data into onboarding_details, creates a participant user account
    with a temporary password, inserts UBOs and Directors, and writes the initial audit log.
    Accepts an optional provided_tracking_id to skip auto-generation.
    """
    conn = get_connection()
    if not conn:
        return False, "Database connection failed", None, None

    try:
        with conn.cursor() as cursor:
            tracking_id = provided_tracking_id or generate_tracking_id(cursor)

            # Generate temporary password and hash it
            temp_password = _generate_temp_password()
            import bcrypt
            password_hash = bcrypt.hashpw(temp_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

            # 1. Insert onboarding details
            #
            # countries_operation: the form sends a comma-separated string;
            # we split it into a Python list which psycopg2 serialises → TEXT[].
            raw_countries = data.get('countries_operation') or ''
            countries_list = [c.strip() for c in raw_countries.split(',') if c.strip()] if isinstance(raw_countries, str) else (raw_countries or [])

            # business_need: maps directly from the Step-1 "product" dropdown.
            # Also kept in aml_questions JSONB as product_interest for query convenience.
            business_need_val = data.get('product') or data.get('business_need')

            # aml_questions JSONB: sanctions_exposure, aml_program_confirmed,
            # trading_address_different ONLY. pep_declaration lives in its own
            # boolean column — never duplicate it here.
            import json as _json
            raw_aml = data.get('aml_questions', '{}')
            aml_dict = _json.loads(raw_aml) if isinstance(raw_aml, str) else (raw_aml or {})
            aml_dict.pop('pep_declaration', None)   # enforce single-source-of-truth
            aml_dict['product_interest'] = business_need_val  # convenience copy

            query = """
                INSERT INTO client_onboarding.onboarding_details (
                    company_name, company_address, city, state, country, zip_code,
                    phone_number, email, lei_identifier, entity_type,
                    registration_number, incorporation_date, ownership_type,
                    regulatory_status, regulatory_authority,
                    business_need,
                    bod_list_s3_uri, financials_s3_uri, ownership_s3_uri,
                    incorporation_doc_s3_uri,
                    bank_statement_s3_uri, ein_certificate_s3_uri, ubo_id_s3_uri,
                    business_activity, source_of_funds, source_of_wealth,
                    expected_volume, countries_operation, tax_residency_country,
                    pep_declaration, adverse_media_consent, website,
                    correspondent_bank, aml_program_description, trading_address,
                    aml_questions, status, tracking_id, submitted_at,
                    dba_name, ein_number, routing_number, account_number, mcc_code, bank_name
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s,
                    %s, %s, %s,
                    %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, 'PENDING_REVIEW', %s, CURRENT_TIMESTAMP,
                    %s, %s, %s, %s, %s, %s
                ) RETURNING id;
            """
            cursor.execute(query, (
                data['company_name'], data['company_address'], data['city'], data['state'],
                data['country'], data['zip_code'],
                data['phone_number'], data['email'], data['lei_identifier'], data['entity_type'],
                data.get('registration_number'), data.get('incorporation_date'), data.get('ownership_type'),
                data.get('regulatory_status'), data.get('regulatory_authority'),
                business_need_val,
                data.get('bod_list_s3_uri'),
                data.get('financials_s3_uri'),
                data.get('ownership_s3_uri'),
                data.get('incorporation_doc_s3_uri'),
                data.get('bank_statement_s3_uri'),
                data.get('ein_certificate_s3_uri'),
                data.get('ubo_id_s3_uri'),
                data['business_activity'], data['source_of_funds'], data.get('source_of_wealth'),
                data['expected_volume'], countries_list, data.get('tax_residency_country'),
                data.get('pep_declaration', False), data.get('adverse_media_consent', False), data.get('website'),
                data.get('correspondent_bank'), data.get('aml_program_description'), data.get('trading_address'),
                _json.dumps(aml_dict), tracking_id,
                data.get('dba_name'), data.get('ein_number'), data.get('routing_number'),
                data.get('account_number'), data.get('mcc_code'), data.get('bank_name')
            ))
            onboarding_id = cursor.fetchone()[0]

            # 2. Insert directors
            directors = data.get('directors', [])
            for d in directors:
                cursor.execute(
                    """INSERT INTO client_onboarding.onboarding_directors
                       (onboarding_id, full_name, role, nationality, country_of_residence)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (onboarding_id, d.get('full_name'), d.get('role'),
                     d.get('nationality'), d.get('country_of_residence'))
                )

            # 3. Insert UBOs
            ubos = data.get('ubos', [])
            for u in ubos:
                cursor.execute(
                    """INSERT INTO client_onboarding.onboarding_ubos
                       (onboarding_id, full_name, stake_percent, nationality,
                        country_of_residence, date_of_birth, is_pep, tax_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                    (onboarding_id, u.get('full_name'), u.get('stake_percent'),
                     u.get('nationality'), u.get('country_of_residence'),
                     u.get('date_of_birth'), u.get('is_pep', False), u.get('tax_id'))
                )

            # 4. Create participant user account
            cursor.execute(
                "INSERT INTO client_onboarding.users (email, password_hash, full_name, must_change_password) VALUES (%s, %s, %s, TRUE) RETURNING id",
                (data['email'], password_hash, data['company_name'])
            )
            user_id = cursor.fetchone()[0]

            # 5. Assign PARTICIPANT role
            cursor.execute("SELECT id FROM client_onboarding.roles WHERE name = 'PARTICIPANT'")
            role_row = cursor.fetchone()
            if role_row:
                cursor.execute("INSERT INTO client_onboarding.user_roles (user_id, role_id) VALUES (%s, %s)", (user_id, role_row[0]))

            # 6. Link user to onboarding case
            cursor.execute("UPDATE client_onboarding.onboarding_details SET user_id = %s WHERE id = %s", (user_id, onboarding_id))

            # 7. Initial audit log
            audit_query = """
                INSERT INTO client_onboarding.onboarding_audit_log (
                    onboarding_id, old_status, new_status, ip_address, workstation_info, remarks
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(audit_query, (onboarding_id, None, 'PENDING_REVIEW', ip, workstation, 'Initial Application Submitted'))

            conn.commit()
            return True, onboarding_id, tracking_id, temp_password
    except Exception as e:
        logger.error(f"Failed to save onboarding details: {e}", exc_info=True)
        if conn:
            conn.rollback()
        return False, str(e), None, None
    finally:
        if conn:
            release_connection(conn)

def get_all_tickets(status_filter=None):
    """Fetches all onboarding requests with counts, optionally filtered by status."""
    conn = get_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            query = """
                SELECT id, company_name, tracking_id, status, submitted_at,
                       email, country, entity_type, ai_risk_level
                FROM client_onboarding.onboarding_details
            """
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
    """Fetches full details of a single ticket including related UBOs and directors."""
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

            # Binary fields cleanup (Legacy - keeping for fallback)
            for key in ['bod_list_content', 'financials_content', 'ownership_content', 'incorporation_doc_content']:
                if ticket.get(key):
                    ticket[key] = f"FILE_BLOB_{len(ticket[key])}_BYTES"

            # Parse aml_questions JSONB
            if ticket.get('aml_questions') and isinstance(ticket['aml_questions'], str):
                try:
                    ticket['aml_questions'] = __import__('json').loads(ticket['aml_questions'])
                except:
                    pass

            # Fetch audit history
            audit_query = """
                SELECT id, onboarding_id, old_status, new_status, action_by,
                       action_timestamp, ip_address, workstation_info, remarks
                FROM client_onboarding.onboarding_audit_log
                WHERE onboarding_id = %s ORDER BY action_timestamp DESC
            """
            cursor.execute(audit_query, (onboarding_id,))
            audit_cols = [desc[0] for desc in cursor.description]
            ticket['history'] = [dict(zip(audit_cols, r)) for r in cursor.fetchall()]

            # Fetch directors
            cursor.execute(
                "SELECT full_name, role, nationality, country_of_residence FROM client_onboarding.onboarding_directors WHERE onboarding_id = %s",
                (onboarding_id,)
            )
            dir_cols = [desc[0] for desc in cursor.description]
            ticket['directors'] = [dict(zip(dir_cols, r)) for r in cursor.fetchall()]

            # Fetch UBOs
            cursor.execute(
                "SELECT full_name, stake_percent, nationality, country_of_residence, date_of_birth, is_pep, tax_id FROM client_onboarding.onboarding_ubos WHERE onboarding_id = %s",
                (onboarding_id,)
            )
            ubo_cols = [desc[0] for desc in cursor.description]
            ticket['ubos'] = [dict(zip(ubo_cols, r)) for r in cursor.fetchall()]

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
            query = "SELECT id, email, password_hash, full_name, is_active, must_change_password FROM client_onboarding.users WHERE email = %s"
            cursor.execute(query, (email,))
            row = cursor.fetchone()
            if not row:
                return None

            columns = [desc[0] for desc in cursor.description]
            user = dict(zip(columns, row))

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
        logger.error(f"Error fetching user {email}: {e}", exc_info=True)
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
            cursor.execute("SELECT status FROM client_onboarding.onboarding_details WHERE id = %s", (onboarding_id,))
            old_status_row = cursor.fetchone()
            old_status = old_status_row[0] if old_status_row else None

            cursor.execute(
                "UPDATE client_onboarding.onboarding_details SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (new_status, onboarding_id)
            )

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
            col_map = {
                "bod": "bod_list_content",
                "financials": "financials_content",
                "ownership": "ownership_content",
                "incorporation": "incorporation_doc_content"
            }
            col_name = col_map.get(doc_type)
            if not col_name:
                return None

            query = f"SELECT {col_name} FROM client_onboarding.onboarding_details WHERE id = %s"
            cursor.execute(query, (onboarding_id,))
            row = cursor.fetchone()
            return row[0] if row else None
    except Exception as e:
        print(f"Error fetching document: {e}")
        return None
    finally:
        release_connection(conn)

def get_audit_logs(onboarding_id):
    """Returns all audit log entries for an onboarding ticket."""
    conn = get_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, old_status, new_status, action_by, action_timestamp,
                       ip_address, workstation_info, remarks
                FROM client_onboarding.onboarding_audit_log
                WHERE onboarding_id = %s
                ORDER BY action_timestamp DESC
            """, (onboarding_id,))
            cols = [desc[0] for desc in cursor.description]
            return [dict(zip(cols, r)) for r in cursor.fetchall()]
    except Exception as e:
        print(f"Error fetching audit logs: {e}")
        return []
    finally:
        release_connection(conn)

def add_audit_log(onboarding_id, old_status, new_status, remarks=None, action_by=None, ip=None, workstation=None):
    """Writes a single audit entry — for use by the AML agent."""
    conn = get_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO client_onboarding.onboarding_audit_log
                    (onboarding_id, old_status, new_status, action_by, ip_address, workstation_info, remarks)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (onboarding_id, old_status, new_status, action_by, ip, workstation, remarks))
        conn.commit()
        return True
    except Exception as e:
        print(f"Audit log write failed: {e}")
        conn.rollback()
        return False
    finally:
        release_connection(conn)


def insert_agent_log(log_data: dict) -> bool:
    """Inserts one row into ai_agent_logs — called by every agent check."""
    import json as _json
    conn = get_connection()
    if not conn:
        return False
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO client_onboarding.ai_agent_logs (
                    run_id, onboarding_id, agent_name, stage, check_name,
                    input_context, output, flags, risk_level, recommendation,
                    ai_summary, model_used, duration_ms
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                log_data.get("run_id"),
                log_data.get("onboarding_id"),
                log_data.get("agent_name"),
                log_data.get("stage"),
                log_data.get("check_name"),
                _json.dumps(log_data.get("input_context", {})),
                _json.dumps(log_data.get("output", {})),
                log_data.get("flags", []),
                log_data.get("risk_level"),
                log_data.get("recommendation"),
                log_data.get("ai_summary"),
                log_data.get("model_used", "rule-based"),
                log_data.get("duration_ms", 0)
            ))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB] insert_agent_log failed: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        release_connection(conn)


def get_agent_logs(onboarding_id: str) -> list:
    """Returns all ai_agent_logs rows for a given onboarding_id, ordered by created_at ASC."""
    import json as _json
    conn = get_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT run_id, agent_name, stage, check_name, flags,
                       risk_level, recommendation, ai_summary, model_used,
                       duration_ms, created_at, input_context, output
                FROM client_onboarding.ai_agent_logs
                WHERE onboarding_id = %s
                ORDER BY created_at ASC
            """, (onboarding_id,))
            cols = [d[0] for d in cursor.description]
            rows = []
            for r in cursor.fetchall():
                row = dict(zip(cols, r))
                # Ensure flags is a plain list
                if row.get("flags") and not isinstance(row["flags"], list):
                    try:
                        row["flags"] = _json.loads(row["flags"])
                    except Exception:
                        row["flags"] = list(row["flags"]) if row["flags"] else []
                # Ensure input_context and output are objects
                for field in ["input_context", "output"]:
                    if row.get(field) and isinstance(row[field], str):
                        try:
                            row[field] = _json.loads(row[field])
                        except Exception:
                            pass
                # Serialise timestamps
                if row.get("created_at"):
                    row["created_at"] = row["created_at"].isoformat()
                rows.append(row)
            return rows
    except Exception as e:
        logger.error(f"get_agent_logs failed for ticket {onboarding_id}: {e}", exc_info=True)
        return []
    finally:
        release_connection(conn)


def get_onboarding_by_user_id(user_id: str) -> dict | None:
    """Fetch the onboarding record linked to a participant user_id."""
    conn = get_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, company_name, tracking_id, status, ai_risk_level, submitted_at, email
                FROM client_onboarding.onboarding_details
                WHERE user_id = %s
                ORDER BY submitted_at DESC
                LIMIT 1
            """, (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cursor.description]
            result = dict(zip(cols, row))
            if result.get("submitted_at"):
                result["submitted_at"] = result["submitted_at"].isoformat()
            return result
    except Exception as e:
        print(f"[DB] get_onboarding_by_user_id failed: {e}")
        return None
    finally:
        release_connection(conn)
