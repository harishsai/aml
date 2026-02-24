from fastapi import FastAPI, Form, UploadFile, File, BackgroundTasks, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from .logger import logger_main as logger
import uvicorn
import json
import os
import boto3
from botocore.exceptions import ClientError
from pydantic import BaseModel
import bcrypt
from .db import (
    save_onboarding_details,
    get_all_tickets,
    get_ticket_by_id,
    update_onboarding_status,
    get_document_content,
    get_user_by_email,
    get_connection,
    release_connection,
    get_agent_logs, get_onboarding_by_user_id,
    get_next_tracking_id
)
from .email_utils import (
    send_confirmation_email,
    send_status_update_email,
    send_kyc_complete_email,
    send_aml_stage_complete_email,
    send_kyc_rejected_email
)
from .agents.orchestrator import run_document_agent_stage, run_kyc_stage, run_aml_risk_stage

class ActionRequest(BaseModel):
    action: str
    remarks: str = None

# S3 Client Configuration
S3_BUCKET = os.getenv("S3_BUCKET_NAME", "kinetix-onboarding-docs")
s3_client = boto3.client(
    's3', 
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
    region_name=os.getenv("AWS_REGION", "us-west-2")
)

def upload_to_s3(file_obj, onboarding_id, filename):
    """Uploads a file to S3 and returns the S3 URI."""
    s3_key = f"uploads/{onboarding_id}/{filename}"
    try:
        s3_client.upload_fileobj(file_obj, S3_BUCKET, s3_key)
        return f"s3://{S3_BUCKET}/{s3_key}"
    except ClientError as e:
        logger.error(f"S3 Upload failed for {filename} (Onboarding ID: {onboarding_id}): {e}", exc_info=True)
        return None

app = FastAPI(title="Kinetix AML Onboarding Backend")

# Enable CORS for frontend interaction
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/signup")
async def signup(
    request: Request,
    background_tasks: BackgroundTasks,
    # Step 1: Entity Information
    fname: str = Form(...),
    lname: str = Form(...),
    email: str = Form(...),
    company: str = Form(...),
    address: str = Form(...),
    country: str = Form(...),
    state: str = Form(None),
    city: str = Form(...),
    zip: str = Form(...),
    phone: str = Form(...),
    lei: str = Form(...),
    entity_type: str = Form(...),
    registration_number: str = Form(...),
    incorporation_date: str = Form(...),
    ownership_type: str = Form(...),
    regulatory_status: str = Form(...),
    regulatory_authority: str = Form(None),
    website: str = Form(None),
    # Step 2: Documents
    file_bod: UploadFile = File(...),
    file_financials: UploadFile = File(...),
    file_ownership: UploadFile = File(...),
    file_incorporation: UploadFile = File(None),
    file_bank_statement: UploadFile = File(None),
    file_ein: UploadFile = File(None),
    file_ubo_id: UploadFile = File(None),
    # Step 2b: Directors (JSON string from frontend)
    directors: str = Form(...),
    # Step 2c: UBOs (JSON string from frontend — empty if public)
    ubos: str = Form("[]"),
    # Step 3: AML Questionnaire
    product: str = Form(...),
    business_activity: str = Form(...),
    source_of_funds: str = Form(...),
    source_of_wealth: str = Form(...),
    expected_volume: str = Form(...),
    countries_operation: str = Form(...),
    tax_residency_country: str = Form(...),
    sanctions: str = Form(...),
    pep_declaration: str = Form(...),
    aml: str = Form(...),
    aml_program_description: str = Form(None),
    trading_address_different: str = Form("no"),
    trading_address: str = Form(None),
    correspondent_bank: str = Form(None),
    adverse_media_consent: str = Form("yes"),
    dba_name: str = Form(None),
    ein_number: str = Form(None),
    routing_number: str = Form(None),
    account_number: str = Form(None),
    mcc_code: str = Form(None),
    bank_name: str = Form(None),
):
    # Read file contents
    bod_content = await file_bod.read()
    financials_content = await file_financials.read()
    ownership_content = await file_ownership.read()
    incorporation_content = await file_incorporation.read() if file_incorporation else None
    bank_statement_content = await file_bank_statement.read() if file_bank_statement else None
    ein_content = await file_ein.read() if file_ein else None
    ubo_id_content = await file_ubo_id.read() if file_ubo_id else None

    # Parse JSON fields from frontend
    try:
        directors_list = json.loads(directors)
    except:
        directors_list = []
    try:
        ubos_list = json.loads(ubos)
    except:
        ubos_list = []

    # Build AML JSONB payload
    aml_questions = {
        "product_interest": product,
        "sanctions_exposure": sanctions,
        "aml_program_confirmed": aml,
        "trading_address_different": trading_address_different,
    }

    # Pre-generate Tracking ID to use as S3 folder name (organized auditing)
    tracking_id = get_next_tracking_id()
    if not tracking_id:
        logger.error("Failed to pre-generate tracking ID for S3 upload")
        raise HTTPException(status_code=500, detail="Internal server error pre-generating ID")

    folder_id = tracking_id

    # Stream uploads to S3
    # Reset file pointers to 0 before upload since they might have been read
    await file_bod.seek(0)
    bod_s3_uri = upload_to_s3(file_bod.file, folder_id, "bod_list.pdf")
    
    await file_financials.seek(0)
    financials_s3_uri = upload_to_s3(file_financials.file, folder_id, "financials_2024.pdf")
    
    await file_ownership.seek(0)
    ownership_s3_uri = upload_to_s3(file_ownership.file, folder_id, "ownership_structure.pdf")
    
    if file_incorporation:
        await file_incorporation.seek(0)
        incorporation_s3_uri = upload_to_s3(file_incorporation.file, folder_id, "certificate_of_incorporation.pdf")

    bank_statement_s3_uri = None
    if file_bank_statement:
        await file_bank_statement.seek(0)
        bank_statement_s3_uri = upload_to_s3(file_bank_statement.file, folder_id, "bank_statement.pdf")

    ein_s3_uri = None
    if file_ein:
        await file_ein.seek(0)
        ein_s3_uri = upload_to_s3(file_ein.file, folder_id, "ein_certificate.pdf")

    ubo_id_s3_uri = None
    if file_ubo_id:
        await file_ubo_id.seek(0)
        ubo_id_s3_uri = upload_to_s3(file_ubo_id.file, folder_id, "ubo_id.pdf")

    db_data = {
        # Entity identity
        "company_name": company,
        "company_address": address,
        "city": city,
        "state": state if state else "",
        "country": country,
        "zip_code": zip,
        "phone_number": phone,
        "email": email,
        "lei_identifier": lei,
        "entity_type": entity_type,
        "registration_number": registration_number,
        "incorporation_date": incorporation_date,
        "ownership_type": ownership_type,
        "regulatory_status": regulatory_status,
        "regulatory_authority": regulatory_authority,
        "website": website,
        # S3 URIs (Replacing binary content)
        "bod_list_s3_uri": bod_s3_uri,
        "financials_s3_uri": financials_s3_uri,
        "ownership_s3_uri": ownership_s3_uri,
        "incorporation_doc_s3_uri": incorporation_s3_uri,
        "bank_statement_s3_uri": bank_statement_s3_uri,
        "ein_certificate_s3_uri": ein_s3_uri,
        "ubo_id_s3_uri": ubo_id_s3_uri,
        # Legacy support (empty byte strings to avoid NULL constraints if any)
        "bod_list_content": b"",
        "financials_content": b"",
        "ownership_content": b"",
        "incorporation_doc_content": b"",
        # AML fields
        "business_activity": business_activity,
        "source_of_funds": source_of_funds,
        "source_of_wealth": source_of_wealth,
        "expected_volume": expected_volume,
        "countries_operation": countries_operation,    # stays as string; db.py parses to list
        "product": product,                            # db.py writes this to business_need column
        "tax_residency_country": tax_residency_country,
        "pep_declaration": pep_declaration.lower() == "yes",
        "adverse_media_consent": adverse_media_consent.lower() == "yes",
        "correspondent_bank": correspondent_bank,
        "aml_program_description": aml_program_description,
        "trading_address": trading_address if trading_address_different == "yes" else None,
        "aml_questions": json.dumps(aml_questions),
        # New Industry Fields
        "dba_name": dba_name,
        "ein_number": ein_number,
        "routing_number": routing_number,
        "account_number": account_number,
        "mcc_code": mcc_code,
        "bank_name": bank_name,
        # Structured lists
        "directors": directors_list,
        "ubos": ubos_list,
    }

    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "Unknown")

    # Save to database using the pre-generated tracking ID
    success, result, _, temp_password = save_onboarding_details(db_data, ip=client_ip, workstation=user_agent, provided_tracking_id=tracking_id)

    if not success:
        raise HTTPException(status_code=500, detail=f"Database insertion failed: {result}")

    # Send confirmation email with tracking ID and temp password
    logger.info(f"Signup successful for {email}. Tracking ID: {tracking_id}. Triggering background tasks.")
    background_tasks.add_task(send_confirmation_email, email, fname, tracking_id, temp_password)

    # Trigger Document Agent automatically after signup (Stage 1)
    onboarding_id_str = str(result)
    background_tasks.add_task(_run_doc_agent_and_notify, onboarding_id_str, email, tracking_id)

    return {
        "status": "success",
        "message": "Application submitted successfully",
        "onboarding_id": onboarding_id_str,
        "tracking_id": tracking_id
    }


def _run_doc_agent_and_notify(onboarding_id: str, email: str, tracking_id: str):
    """Background task: run Document Verification stage."""
    try:
        run_document_agent_stage(onboarding_id)
    except Exception as e:
        logger.error(f"Document background task failed for {onboarding_id}: {e}", exc_info=True)


def _run_kyc_and_notify(onboarding_id: str, email: str, tracking_id: str):
    """Background task: run KYC stage and send completion email."""
    try:
        result = run_kyc_stage(onboarding_id)
        risk = result.get("composite_risk", "UNKNOWN")
        send_kyc_complete_email(email, tracking_id, risk)
    except Exception as e:
        logger.error(f"KYC background task failed for {onboarding_id}: {e}", exc_info=True)


@app.post("/admin/login")
async def admin_login(data: dict):
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    logger.info(f"Admin login attempt for: {username}")

    user = get_user_by_email(username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.get('is_active'):
        raise HTTPException(status_code=401, detail="Account is inactive")

    if 'ADMIN' not in user.get('roles', []):
        raise HTTPException(status_code=403, detail="Access denied. Admin credentials required.")

    password_bytes = password.encode('utf-8')
    hash_bytes = user['password_hash'].encode('utf-8')

    if bcrypt.checkpw(password_bytes, hash_bytes):
        return {
            "status": "success",
            "role": "ADMIN",
            "user_id": str(user['id']),
            "full_name": user['full_name']
        }

    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/auth/participant-login")
async def participant_login(data: dict):
    email = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    user = get_user_by_email(email)
    if not user or not user.get('is_active'):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if 'ADMIN' in user.get('roles', []):
        raise HTTPException(status_code=403, detail="Please use the admin portal to log in.")

    if bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        return {
            "status": "success",
            "user_id": str(user['id']),
            "full_name": user['full_name'],
            "email": email,
            "must_change_password": user.get('must_change_password', False)
        }

    raise HTTPException(status_code=401, detail="Invalid credentials")


class ChangePasswordRequest(BaseModel):
    email: str
    current_password: str
    new_password: str


@app.post("/auth/change-password")
async def change_password(req: ChangePasswordRequest):
    user = get_user_by_email(req.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not bcrypt.checkpw(req.current_password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        raise HTTPException(status_code=401, detail="Current password is incorrect")

    new_hash = bcrypt.hashpw(req.new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE client_onboarding.users SET password_hash = %s, must_change_password = FALSE, updated_at = CURRENT_TIMESTAMP WHERE email = %s",
                (new_hash, req.email)
            )
        conn.commit()
        return {"status": "success", "message": "Password updated successfully"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        release_connection(conn)


# --- ADMIN TICKET ENDPOINTS ---

@app.get("/admin/tickets")
async def list_tickets(status: str = None):
    tickets = get_all_tickets(status)
    return {"status": "success", "tickets": tickets}


@app.get("/admin/tickets/{ticket_id}")
async def ticket_detail(ticket_id: str):
    ticket = get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"status": "success", "ticket": ticket}


@app.post("/admin/tickets/{ticket_id}/action")
async def ticket_action(ticket_id: str, req: ActionRequest, request: Request, background_tasks: BackgroundTasks):
    """
    Stage-aware ticket action endpoint.
    - If current status = AML_STAGE1_COMPLETE + action = approve → triggers AML Risk Agent
    - Otherwise maps action → status directly.
    """
    action = req.action.lower()

    # Fetch current ticket to determine stage
    ticket = get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    current_status = ticket.get("status", "")
    email = ticket.get("email", "")
    tracking_id = ticket.get("tracking_id", "")

    # --- Stage-aware routing ---
    if action == "approve" and current_status == "DOCUMENT_COMPLETE":
        # Document check approved by admin → trigger KYC Screening
        success, message = update_onboarding_status(
            ticket_id, "KYC_IN_PROGRESS",
            action_by="ADMIN",
            ip=request.client.host,
            workstation=request.headers.get("user-agent", "Unknown"),
            remarks=req.remarks or "Documents verified. KYC Screening initiated."
        )
        if not success:
            raise HTTPException(status_code=500, detail=message)
        background_tasks.add_task(_run_kyc_and_notify, ticket_id, email, tracking_id)
        return {"status": "success", "message": "Documents approved. KYC Agent started."}

    if action == "approve" and current_status == "KYC_COMPLETE":
        # KYC approved by admin → trigger AML Risk stage
        success, message = update_onboarding_status(
            ticket_id, "AML_IN_PROGRESS",
            action_by="ADMIN",
            ip=request.client.host,
            workstation=request.headers.get("user-agent", "Unknown"),
            remarks=req.remarks or "KYC approved. AML Risk assessment initiated."
        )
        if not success:
            raise HTTPException(status_code=500, detail=message)
        background_tasks.add_task(_run_aml_and_notify, ticket_id, email, tracking_id)
        return {"status": "success", "message": "KYC approved. AML Risk assessment started."}

    if action == "reject" and current_status == "KYC_COMPLETE":
        # KYC rejected → notify participant
        new_status = "REJECTED"
        success, message = update_onboarding_status(
            ticket_id, new_status,
            action_by="ADMIN",
            ip=request.client.host,
            workstation=request.headers.get("user-agent", "Unknown"),
            remarks=req.remarks or "Rejected at KYC stage."
        )
        if not success:
            raise HTTPException(status_code=500, detail=message)
        if email:
            background_tasks.add_task(send_kyc_rejected_email, email, tracking_id, req.remarks or "")
        return {"status": "success", "message": "Rejected at KYC stage."}

    # --- Default status map (all other combinations) ---
    status_map = {
        "approve": "APPROVED",
        "reject": "REJECTED",
        "cancel": "CANCELLED",
        "clarify": "CLARIFICATION_REQUIRED"
    }
    new_status = status_map.get(action)
    if not new_status:
        raise HTTPException(status_code=400, detail="Invalid action")

    success, message = update_onboarding_status(
        ticket_id, new_status,
        action_by="ADMIN",
        ip=request.client.host,
        workstation=request.headers.get("user-agent", "Unknown"),
        remarks=req.remarks
    )
    if not success:
        raise HTTPException(status_code=500, detail=message)

    if email:
        background_tasks.add_task(send_status_update_email, email, tracking_id, new_status, req.remarks)

    return {"status": "success", "message": f"Ticket {action} successful"}


def _run_aml_and_notify(onboarding_id: str, email: str, tracking_id: str):
    """Background task: run AML Risk stage and send completion email."""
    try:
        result = run_aml_risk_stage(onboarding_id)
        risk = result.get("composite_risk", "UNKNOWN")
        send_aml_stage_complete_email(email, tracking_id, risk)
    except Exception as e:
        print(f"[main] AML Risk background task failed for {onboarding_id}: {e}")


@app.post("/admin/tickets/{ticket_id}/run-kyc")
async def run_kyc_manual(ticket_id: str, background_tasks: BackgroundTasks):
    """Manually trigger KYC agent for a ticket (admin can re-run)."""
    ticket = get_ticket_by_id(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    background_tasks.add_task(
        _run_kyc_and_notify,
        ticket_id,
        ticket.get("email", ""),
        ticket.get("tracking_id", "")
    )
    return {"status": "success", "message": "KYC agent started in background"}


@app.get("/admin/tickets/{ticket_id}/agent-logs")
async def get_ticket_agent_logs(ticket_id: str):
    """Returns all AI agent log entries for a ticket."""
    logs = get_agent_logs(ticket_id)
    return {"status": "success", "logs": logs}


@app.get("/portal/status/{user_id}")
async def portal_status(user_id: str):
    """Returns the onboarding status for a participant's user_id."""
    record = get_onboarding_by_user_id(user_id)
    if not record:
        raise HTTPException(status_code=404, detail="No onboarding record found")
    return {"status": "success", "record": record}


@app.get("/admin/tickets/{id}/docs/{doc_type}")
async def get_ticket_doc(id: str, doc_type: str):
    ticket = get_ticket_by_id(id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Map doc_type to S3 URI column
    s3_col_map = {
        "bod": "bod_list_s3_uri",
        "financials": "financials_s3_uri",
        "ownership": "ownership_s3_uri",
        "incorporation": "incorporation_doc_s3_uri",
        "bank": "bank_statement_s3_uri",
        "ein": "ein_certificate_s3_uri",
        "ubo_id": "ubo_id_s3_uri"
    }
    s3_uri = ticket.get(s3_col_map.get(doc_type))

    if s3_uri and s3_uri.startswith("s3://"):
        try:
            # Parse S3 URI: s3://bucket/key
            path_parts = s3_uri.replace("s3://", "").split("/", 1)
            bucket = path_parts[0]
            key = path_parts[1]
            # Use explicit client for fetching
            obj = s3_client.get_object(Bucket=bucket, Key=key)
            return Response(content=obj['Body'].read(), media_type="application/pdf")
        except Exception as e:
            print(f"[S3] Download failed for {s3_uri}: {e}")

    # Fallback to Database Binary
    content = get_document_content(id, doc_type)
    if not content:
        raise HTTPException(status_code=404, detail=" Document not found in S3 or DB")
    return Response(content=content, media_type="application/pdf")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
