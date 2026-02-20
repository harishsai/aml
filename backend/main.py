from fastapi import FastAPI, Form, UploadFile, File, BackgroundTasks, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
from pydantic import BaseModel
import bcrypt
from .db import (
    save_onboarding_details, 
    get_all_tickets, 
    get_ticket_by_id, 
    update_onboarding_status, 
    get_document_content,
    get_user_by_email,
    verify_setup_token,
    complete_participant_setup
)
from .email_utils import send_confirmation_email, send_status_update_email

class ActionRequest(BaseModel):
    action: str
    remarks: str = None

class SetupPasswordRequest(BaseModel):
    token: str
    password: str

app = FastAPI(title="Kinetix Signup Backend")

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
    product: str = Form(...),
    reg_num: str = Form(...),
    ownership_type: str = Form(...),
    business_activity: str = Form(...),
    source_of_funds: str = Form(...),
    expected_volume: str = Form(...),
    countries_op: str = Form(...),
    sanctions: str = Form(...),
    aml: str = Form(...),
    # File uploads
    file_bod: UploadFile = File(...),
    file_financials: UploadFile = File(...),
    file_ownership: UploadFile = File(...)
):
    # Read file contents
    bod_content = await file_bod.read()
    financials_content = await file_financials.read()
    ownership_content = await file_ownership.read()
    
    # Prepare data for DB
    # We combine Step 2 questionnaire into a JSON object
    aml_questions = {
        "reg_num": reg_num,
        "ownership_type": ownership_type,
        "sanctions_exposure": sanctions,
        "aml_program_confirmed": aml,
        "product_interest": product
    }
    
    db_data = {
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
        "bod_list_content": bod_content,
        "financials_content": financials_content,
        "ownership_content": ownership_content,
        "business_activity": business_activity,
        "source_of_funds": source_of_funds,
        "expected_volume": expected_volume,
        "countries_operation": countries_op,
        "aml_questions": json.dumps(aml_questions)
    }
    
    # Capture metadata
    client_ip = request.client.host
    user_agent = request.headers.get("user-agent", "Unknown")
    
    # Save to database
    success, result, tracking_id, setup_token = save_onboarding_details(db_data, ip=client_ip, workstation=user_agent)
    
    if not success:
        raise HTTPException(status_code=500, detail=f"Database insertion failed: {result}")
    
    # Send confirmation email in background
    background_tasks.add_task(send_confirmation_email, email, fname, setup_token)
    
    return {
        "status": "success",
        "message": "Signup recorded successfully",
        "onboarding_id": str(result),
        "tracking_id": tracking_id
    }

@app.post("/admin/login")
async def admin_login(data: dict):
    username = data.get("username")
    password = data.get("password")
    print(f"DEBUG LOGIN: Received username='{username}'", flush=True)
    
    user = get_user_by_email(username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.get('is_active'):
        raise HTTPException(status_code=401, detail="Account is inactive")

    # Verify password with bcrypt
    password_bytes = password.encode('utf-8')
    hash_bytes = user['password_hash'].encode('utf-8')
    
    if bcrypt.checkpw(password_bytes, hash_bytes):
        # In a real app, generate a JWT token here
        return {
            "status": "success", 
            "role": user['roles'][0] if user['roles'] else "staff",
            "user_id": str(user['id']),
            "full_name": user['full_name']
        }
    
    raise HTTPException(status_code=401, detail="Invalid credentials")

# --- PARTICIPANT AUTH ENDPOINTS ---

@app.post("/auth/participant-login")
async def participant_login(data: dict):
    email = data.get("username")
    password = data.get("password")

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
                "UPDATE client_onboarding.users SET password_hash = %s, must_change_password = FALSE WHERE email = %s",
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
    status_map = {
        "approve": "APPROVED",
        "reject": "REJECTED",
        "cancel": "CANCELLED",
        "clarify": "CLARIFICATION_REQUIRED"
    }

    new_status = status_map.get(req.action.lower())
    if not new_status:
        raise HTTPException(status_code=400, detail="Invalid action")

    success, message = update_onboarding_status(
        ticket_id,
        new_status,
        action_by=None,
        ip=request.client.host,
        workstation=request.headers.get("user-agent", "Unknown"),
        remarks=req.remarks
    )

    if not success:
        raise HTTPException(status_code=500, detail=message)

    ticket = get_ticket_by_id(ticket_id)
    if ticket and ticket.get('email'):
        background_tasks.add_task(send_status_update_email, ticket['email'], ticket['tracking_id'], new_status, req.remarks)

    return {"status": "success", "message": f"Ticket {req.action} successful"}

@app.get("/admin/tickets/{id}/docs/{doc_type}")
async def get_ticket_doc(id: str, doc_type: str):
    content = get_document_content(id, doc_type)
    if not content:
        raise HTTPException(status_code=404, detail="Document not found")
    return Response(content=content, media_type="application/pdf")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
