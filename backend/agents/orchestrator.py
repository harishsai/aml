import os
import json
import uuid
import time
import boto3
from datetime import datetime
from dotenv import load_dotenv

# Load database environment variables (ensures keys are available for background tasks)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.dbenv'))
from backend.db import (
    get_connection,
    release_connection,
    update_onboarding_status,
    insert_agent_log
)
from backend.agents.kyc_agent import sanctions_check, lei_verify, email_domain_check
from backend.logger import logger_agents as logger

def get_bedrock_client(client_type='bedrock-agent-runtime'):
    """Returns a Bedrock client with explicit credentials from environment variables."""
    return boto3.client(
        client_type,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
        region_name=os.getenv("AWS_REGION", "us-west-2")
    )

# Agent IDs for fallback/reference (though we prefer direct orchestration)
# Agent IDs for the new account (us-west-2)
KYC_AGENT_ID = "UCW81NPRUR"
AML_EXPERT_AGENT_ID = "YITJZXCFJE"
AGENT_ALIAS_ID = "TSTALIASID"

def invoke_bedrock_agent(agent_id, alias_id, session_id, prompt, onboarding_id=None, stage=1):
    """Invokes a Bedrock Agent, parses traces for tool visibility, and extracts JSON."""
    start_time = time.time()
    # Combined prompt to ensure instructions + identifiers are passed correctly
    input_text = f"As a KYC/AML Specialist, process this request: {prompt}. Return ONLY valid JSON."
    
    try:
        client = get_bedrock_client('bedrock-agent-runtime')
        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId=session_id,
            inputText=input_text,
            enableTrace=True
        )
        
        full_text = ""
        observations = []
        # For deep debugging, let's log the raw traces to a file
        with open("agent_trace.log", "a") as trace_log:
            trace_log.write(f"\n--- SESSION: {session_id} START ---\n")
            
            for event in response['completion']:
                # Capture JSON Chunks
                if 'chunk' in event:
                    full_text += event['chunk']['bytes'].decode('utf-8')
                
                # Capture Traces for real-time visibility
                if 'trace' in event:
                    trace_data = event['trace'].get('trace', {})
                    orch = trace_data.get('orchestrationTrace', {})
                    
                    # 1. Detection of Tool Calls
                    inv_input = orch.get('invocationInput', {})
                    if 'actionGroupInvocationInput' in inv_input:
                        ag = inv_input['actionGroupInvocationInput']
                        func_name = ag.get('function', 'unknown_tool')
                        params = ag.get('parameters', [])
                        logger.info(f"[AgentTrace] INVOKING: {func_name} | {params}")
# Cleaned up comments here
                    # 2. Detection of Tool Results (Observations)
                    observation = orch.get('observation', {})
                    if 'actionGroupInvocationOutput' in observation:
                        ao = observation['actionGroupInvocationOutput']
                        text_res = ao.get('text', '')
                        logger.info(f"[AgentTrace] OBSERVATION: {text_res[:200]}...")
                        observations.append(text_res)
                        
                        if onboarding_id:
                            # snippet = text_res[:500] + "..." if len(text_res) > 500 else text_res
                            pass

        duration = int((time.time() - start_time) * 1000)
        logger.info(f"[Orchestrator] Agent {agent_id} finished in {duration}ms. Full Output: {full_text[:200]}...")
        
        # Wrap JSON extraction in a function
        return _extract_agent_json(full_text, agent_id, observations=observations)
    except Exception as e:
        logger.error(f"[Orchestrator] Bedrock error: {e}", exc_info=True)
        return {"error": str(e), "findings": "Deployment/Connectivity issue.", "_observations": []}

def _extract_agent_json(text, agent_id, observations=None):
    """Helper to find and parse JSON block from agent output."""
    try:
        # Look for { ... } block
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            json_str = text[start:end+1]
            data = json.loads(json_str)
            if observations:
                data["_observations"] = observations
            return data
        return {"findings": text, "error": "No JSON block", "_observations": observations}
    except Exception as e:
        return {"findings": text, "error": str(e), "_observations": observations}

def invoke_bedrock_model_direct(prompt, system_role="Institutional Onboarding Analyst"):
    """Direct Nova Lite call for risk reasoning and JSON consolidation."""
    try:
        bedrock_runtime_rt = get_bedrock_client('bedrock-runtime')
        message = {"role": "user", "content": [{"text": prompt}]}
        response = bedrock_runtime_rt.converse(
            modelId="us.amazon.nova-lite-v1:0",
            messages=[message],
            system=[{"text": system_role}],
            inferenceConfig={"maxTokens": 2000, "temperature": 0}
        )
        full_response = response['output']['message']['content'][0]['text']
        json_start = full_response.find('{')
        json_end = full_response.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            return json.loads(full_response[json_start:json_end])
        return {"error": "No JSON found", "ai_summary": full_response}
    except Exception as e:
        logger.error(f"Direct model analysis failed: {e}")
        return {"error": str(e)}

def invoke_bedrock_model_multimodal(prompt, s3_uris_dict):
    """Directly calls Nova Lite using the Converse API for Multimodal OCR."""
    print(f"[Orchestrator] Direct Multimodal OCR for: {list(s3_uris_dict.keys())}")
    try:
        bedrock_runtime_rt = get_bedrock_client('bedrock-runtime')
        content = [{"text": prompt}]
        for doc_type, s3_uri in s3_uris_dict.items():
            if not s3_uri or not s3_uri.startswith("s3://"): continue
            content.append({
                "document": {
                    "name": doc_type[:20].replace("_", ""),
                    "format": "pdf",
                    "source": {"s3Location": {"uri": s3_uri}}
                }
            })
        message = {"role": "user", "content": content}
        response = bedrock_runtime_rt.converse(
            modelId="us.amazon.nova-lite-v1:0",
            messages=[message],
            inferenceConfig={"maxTokens": 2000, "temperature": 0}
        )
        full_response = response['output']['message']['content'][0]['text']
        json_start = full_response.find('{')
        json_end = full_response.rfind('}') + 1
        return json.loads(full_response[json_start:json_end]) if (json_start != -1 and json_end != -1) else {"error": "No JSON"}
    except Exception as e:
        logger.error(f"Direct Multimodal failed: {e}")
        return {"error": str(e)}

# --- LOGIC HELPERS ---

def _find_key(data, keys, default=None):
    if not isinstance(data, dict): return default
    norm_data = {k.lower().replace("_", "").replace("-", ""): v for k, v in data.items()}
    for k in keys:
        norm_k = k.lower().replace("_", "").replace("-", "")
        if norm_k in norm_data: return norm_data[norm_k]
    return default

def _update_risk_level(onboarding_id, level):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE client_onboarding.onboarding_details SET ai_risk_level = %s WHERE id = %s", (level, onboarding_id))
        conn.commit()
    except Exception as e: logger.error(f"DB Risk update failed: {e}")
    finally: release_connection(conn)

def _get_onboarding_data(onboarding_id):
    conn = get_connection()
    if not conn: return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, company_name, registration_number, ein_number,
                       lei_identifier, website, country, email,
                       incorporation_doc_s3_uri, bank_statement_s3_uri, 
                       ein_certificate_s3_uri, ownership_s3_uri, 
                       financials_s3_uri, bod_list_s3_uri, ubo_id_s3_uri 
                FROM client_onboarding.onboarding_details 
                WHERE id = %s
            """, (onboarding_id,))
            row = cursor.fetchone()
            if not row: return None
            cols = [d[0] for d in cursor.description]
            return dict(zip(cols, row))
    finally: release_connection(conn)

def _get_onboarding_people(onboarding_id, table_name):
    """Fetches a list of full_names from directors or ubos table."""
    conn = get_connection()
    if not conn: return []
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT full_name FROM client_onboarding.{table_name} WHERE onboarding_id = %s", (onboarding_id,))
            return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Failed to fetch {table_name}: {e}")
        return []
    finally: release_connection(conn)

def _get_latest_kyc_findings(onboarding_id):
    """Retrieves the most recent KYC summary from logs to pass to the AML agent."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT ai_summary FROM client_onboarding.ai_agent_logs 
                WHERE onboarding_id = %s AND agent_name = 'KYC_SPECIALIST' 
                ORDER BY created_at DESC LIMIT 1
            """, (onboarding_id,))
            row = cursor.fetchone()
            return row[0] if row else "No prior KYC findings."
    except Exception: return "Error fetching KYC findings."
    finally: release_connection(conn)

def _get_latest_document_findings(onboarding_id):
    """Retrieves the Stage 1 OCR findings to pass to KYC."""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT ai_summary, output FROM client_onboarding.ai_agent_logs 
                WHERE onboarding_id = %s AND agent_name = 'DOCUMENT_AGENT' 
                ORDER BY created_at DESC LIMIT 1
            """, (onboarding_id,))
            row = cursor.fetchone()
            if row:
                summary, o_data = row
                return {"summary": summary, "output": o_data}
            return {"summary": "No Stage 1 Document findings available.", "output": {}}
    except Exception: return {"summary": "Error fetching Document findings.", "output": {}}
    finally: release_connection(conn)

# --- MAIN STAGES ---

def run_document_agent_stage(onboarding_id):
    """
    Stage 1: Document Verification (Truth Discovery)
    Extracts data from multiple S3 PDFs (Incorporation, BOD, Ownership, EIN)
    and validates against all corresponding form fields.
    """
    logger.info(f"Starting Stage 1: Multi-Doc Verification for {onboarding_id}")
    run_id = str(uuid.uuid4())
    
    data = _get_onboarding_data(onboarding_id)
    if not data: return {"error": "Onboarding record not found"}

    # Fetch declared people from lists
    form_directors = _get_onboarding_people(onboarding_id, "onboarding_directors")
    form_ubos = _get_onboarding_people(onboarding_id, "onboarding_ubos")
    
    # Documents to check
    s3_uris = {
        "incorporation_doc": data.get("incorporation_doc_s3_uri"),
        "bod_doc": data.get("bod_list_s3_uri"),
        "ownership_doc": data.get("ownership_s3_uri"),
        "ein_doc": data.get("ein_certificate_s3_uri")
    }
    # Filter empty URIs
    s3_uris = {k: v for k, v in s3_uris.items() if v and v.startswith("s3://")}
    
    if not s3_uris:
        return {"status": "skipped", "message": "No documents provided for verification"}

    # Expanded Multimodal Prompt
    prompt = (
        "Analyze the provided legal documents and extract the following information in a single JSON object:\n"
        "1. From Incorporation: Legal name ('legal_name') and Registration number ('registration_number').\n"
        "2. From BOD List: An array of all Director names ('directors').\n"
        "3. From Ownership Structure: An array of all UBO names ('ubos').\n"
        "4. From EIN Certificate: The Employer Identification Number ('ein_number').\n"
        "Return ONLY the JSON."
    )
    
    ocr_res = invoke_bedrock_model_multimodal(prompt, s3_uris)
    
    # Audit Trail Results
    audit_trail = []
    
    # 1. Incorporation Checks
    extracted_name = _find_key(ocr_res, ["legal_name"], "N/A")
    extracted_reg = _find_key(ocr_res, ["registration_number"], "N/A")
    
    name_status = "MATCH" if data.get("company_name", "").lower().strip() == extracted_name.lower().strip() else "MISMATCH"
    reg_status = "MATCH" if data.get("registration_number", "").lower().strip() == extracted_reg.lower().strip() else "MISMATCH"
    
    audit_trail.extend([
        {"label": "Legal Name (Incorporation)", "form_value": data.get("company_name"), "ocr_value": extracted_name, "status": name_status},
        {"label": "Registration # (Incorporation)", "form_value": data.get("registration_number"), "ocr_value": extracted_reg, "status": reg_status}
    ])

    # 2. EIN Check
    extracted_ein = _find_key(ocr_res, ["ein_number"], "N/A")
    ein_status = "MATCH" if data.get("ein_number", "").lower().strip().replace("-", "") == extracted_ein.lower().strip().replace("-", "") else "MISMATCH"
    audit_trail.append({"label": "EIN Number Verification", "form_value": data.get("ein_number"), "ocr_value": extracted_ein, "status": ein_status})

    # 3. People Lists Comparison (Detail Name Matching)
    ocr_directors = [n.strip() for n in _find_key(ocr_res, ["directors"], []) if isinstance(n, str)]
    dir_matches = [d for d in form_directors if any(d.lower() in od.lower() for od in ocr_directors)]
    dir_status = "MATCH" if len(dir_matches) == len(form_directors) and len(form_directors) > 0 else ("PARTIAL" if len(dir_matches) > 0 else "MISMATCH")
    
    audit_trail.append({
        "label": "Board of Directors List", 
        "form_value": ", ".join(form_directors) if form_directors else "None", 
        "ocr_value": ", ".join(ocr_directors) if ocr_directors else "None", 
        "status": dir_status
    })

    ocr_ubos = [n.strip() for n in _find_key(ocr_res, ["ubos"], []) if isinstance(n, str)]
    ubo_matches = [u for u in form_ubos if any(u.lower() in ou.lower() for ou in ocr_ubos)]
    ubo_status = "MATCH" if len(ubo_matches) == len(form_ubos) and len(form_ubos) > 0 else ("PARTIAL" if len(ubo_matches) > 0 else "MISMATCH")
    
    audit_trail.append({
        "label": "UBO Ownership List", 
        "form_value": ", ".join(form_ubos) if form_ubos else "None", 
        "ocr_value": ", ".join(ocr_ubos) if ocr_ubos else "None", 
        "status": ubo_status
    })

    # Final Risk Assessment
    fails = [a for a in audit_trail if a["status"] in ["MISMATCH", "PARTIAL/MISMATCH"]]
    risk_level = "LOW" if not fails else ("HIGH" if len(fails) > 1 else "MEDIUM")
    
    # Prepare Audit Trail Summary for UI (HTML Table for Side-by-Side Comparison)
    trail_summary = """<table style='width:100%; border-collapse:collapse; font-size:0.8rem; margin-top:8px;'>
<tr style='background:rgba(255,255,255,0.05); color:var(--dash-text-muted);'>
    <th style='padding:6px; text-align:left;'>Detail</th>
    <th style='padding:6px; text-align:left;'>Declared</th>
    <th style='padding:6px; text-align:left;'>Verified</th>
    <th style='padding:6px; text-align:center;'>Status</th>
</tr>"""
    for item in audit_trail:
        color = "#4ade80" if item['status'] == 'MATCH' else ("#fbbf24" if "PARTIAL" in item['status'] else "#f87171")
        trail_summary += f"""<tr style='border-bottom:1px solid rgba(255,255,255,0.02);'>
    <td style='padding:6px; color:var(--dash-text-muted);'>{item['label']}</td>
    <td style='padding:6px;'>{item['form_value']}</td>
    <td style='padding:6px; font-family:monospace;'>{item['ocr_value']}</td>
    <td style='padding:6px; text-align:center; color:{color}; font-weight:bold;'>{item['status']}</td>
</tr>"""
    trail_summary += "</table>"

    # Log to DB
    insert_agent_log({
        "run_id": run_id, "onboarding_id": onboarding_id, "agent_name": "DOCUMENT_AGENT", "stage": 1,
        "check_name": "multi_doc_truth_verification", "output": ocr_res, "risk_level": risk_level,
        "ai_summary": f"Multi-Doc OCR Complete. Risk: {risk_level}\n\n{trail_summary}",
        "duration_ms": 0
    })
    
    update_onboarding_status(onboarding_id, "DOCUMENT_COMPLETE", remarks=f"Stage 1: Multi-Doc Truth established. Risk: {risk_level}")
    
    return {"status": "success", "risk_level": risk_level, "audit_trail": audit_trail}

def run_kyc_stage(onboarding_id):
    """
    Stage 2: KYC - Institutional Identity Verification
    Focuses on Registry (LEI/EIN) and Identity Hygiene (Email/Website).
    """
    logger.info(f"Starting Native KYC Orchestration for {onboarding_id}")
    run_id = str(uuid.uuid4())
    session_id = f"kyc-{onboarding_id[:8]}"
    data = _get_onboarding_data(onboarding_id)
    if not data: return {"error": "Not Found"}
    
    # 1. Fetch Stage 1 Verification Context (The 'Truth' from documents)
    doc_context = _get_latest_document_findings(onboarding_id)
    
    # 2. Rule-Based Ground Truth Checks
    # Registry Check (EIN/LEI matches)
    registry_res = lei_verify(
        lei=data.get('lei_identifier'), 
        company_name=data['company_name'], 
        run_id=run_id, 
        onboarding_id=onboarding_id, 
        ein_number=data.get('ein_number')
    )
    
    # Hygiene Check (Email domain matches website)
    directors = _get_directors(onboarding_id)
    hygiene_res = email_domain_check(
        email=data.get('email'),
        run_id=run_id,
        onboarding_id=onboarding_id,
        website=data.get('website'),
        directors=directors
    )

    # 3. Invoke KYC Agent (Synthesizer & Verification)
    prompt = (
        f"Perform a high-fidelity Identity & Registry verification for {data['company_name']}.\n"
        "Focus on these 3 pillars:\n"
        "1. Institutional Registry Verification (LEI/EIN/Registration Status)\n"
        "2. Identity Hygiene (Email vs Website consistency)\n"
        "3. Document Proofing (Cross-referencing legal docs with form data)\n\n"
        f"ENTITY DATA: LEI: {data.get('lei_identifier')}, EIN: {data.get('ein_number')}, Website: {data.get('website')}, Country: {data.get('country')}\n"
        f"CONTEXT - TECHNICAL REGISTRY RESULTS: {json.dumps(registry_res)}\n"
        f"CONTEXT - TECHNICAL HYGIENE RESULTS: {json.dumps(hygiene_res)}\n"
        f"STAGE 1 - DOCUMENT OCR FINDINGS: {doc_context}\n\n"
        "MANDATORY INSTRUCTION:\n"
        "- Synthesize the document findings with the live registry results to prove the company's existence.\n"
        "- Do NOT perform Sanctions, PEP, or News searches. Those are Stage 3 AML tasks.\n"
        "Return ONLY a JSON result with ‘kyc_pillars’ list containing 'Institutional Registry', 'Identity Hygiene', and 'Document Proofing'."
    )
    kyc_res = invoke_bedrock_agent(KYC_AGENT_ID, AGENT_ALIAS_ID, session_id, prompt, onboarding_id, stage=2)
    
    risk_lvl = kyc_res.get("risk_level", "LOW")
    findings = kyc_res.get("findings") or kyc_res.get("ai_summary", "Institutional identity verification complete.")
    pillars = kyc_res.get("kyc_pillars", [])
    
    # --- AUDITOR FOR KYC STAGE ---
    auditor_prompt = (
        f"You are a KYC Identity Auditor. Map the following results for {data['company_name']} into a clean 3-pillar JSON.\n"
        f"TECHNICAL REGISTRY: {json.dumps(registry_res)}\n"
        f"TECHNICAL HYGIENE: {json.dumps(hygiene_res)}\n"
        f"DOC VERIFICATION: {doc_context}\n"
        f"SYNTHESIS FINDINGS: {findings}\n\n"
        "PILLAR DEFINITIONS:\n"
        "1. Institutional Registry: Must show LEI/EIN/Doc status.\n"
        "2. Identity Hygiene: Must show Email/Website domain match status.\n"
        "3. Document Proofing: Must show if OCR names/IDs match the form.\n"
        "Return ONLY JSON matching the evidence table schema with pillars 1, 2 and 3."
    )
    fallback_res = invoke_bedrock_model_direct(auditor_prompt, system_role="Institutional Identity Auditor")
    if "kyc_pillars" in fallback_res:
         pillars = fallback_res["kyc_pillars"]
         findings = fallback_res.get("ai_summary", findings)

    # Injecting Ground Truth explicitly (Safe-guarding table population)
    
    # 1. Extract Registry truth for detailed evidence
    reg_out = registry_res.get("output", {})
    reg_record = reg_out.get("registry_record") or {}
    reg_ein = reg_record.get("ein_number", "Not on file")
    reg_name = reg_record.get("company_name", "Not found")
    reg_recommendation = registry_res.get("recommendation", "PASS")
    
    # 2. Extract Document truth from Stage 1 context
    doc_out = doc_context.get("output", {})
    doc_ein = doc_out.get("ein_number", "MISSING")
    doc_name = doc_out.get("legal_name", "MISSING")
    
    doc_summary_text = "Verified against official registration documents."
    doc_status = "PASS"
    
    # Check for Document vs Registry/Form Mismatches
    mismatches = []
    submitted_ein = data.get('ein_number')
    if doc_ein != "MISSING":
        if doc_ein.replace("-","") != submitted_ein.replace("-",""):
            mismatches.append(f"Document EIN ({doc_ein}) mismatches Form ({submitted_ein})")
            doc_status = "FLAG"
        if doc_ein.replace("-","") != reg_ein.replace("-","") and reg_ein != "Not on file":
            mismatches.append(f"Document EIN ({doc_ein}) mismatches Registry ({reg_ein})")
            doc_status = "FLAG"

    if mismatches:
        doc_summary_text = f"Mismatch Detected: {'; '.join(mismatches)}"
    elif not doc_out:
        doc_summary_text = doc_context.get("summary", "Document verification pending.")
        doc_status = "FLAG"

    # 3. Build the 3 Strategic Pillars
    final_pillars = [
        {
            "pillar_name": "Institutional Registry", 
            "data_point": f"Form EIN: {submitted_ein or '—'}", 
            "evidence": f"Registry Value: '{reg_ein}'. {registry_res.get('ai_summary', '')}", 
            "result": reg_recommendation
        },
        {
            "pillar_name": "Identity Hygiene", 
            "data_point": f"Email: {data.get('email') or '—'}", 
            "evidence": hygiene_res.get("ai_summary", "Identity hygiene check."), 
            "result": hygiene_res.get("recommendation", "PASS")
        },
        {
            "pillar_name": "Document Proofing", 
            "data_point": f"Form Name: {data.get('company_name')}", 
            "evidence": doc_summary_text, 
            "result": doc_status
        }
    ]
    
    # 4. Integrate AI findings (Synthesis)
    for ai_p in pillars:
        obj = ai_p if isinstance(ai_p, dict) else {"pillar_name": str(ai_p)}
        name = obj.get("pillar_name", "").lower()
        
        for fp in final_pillars:
            if fp["pillar_name"].lower() in name or name in fp["pillar_name"].lower():
                # Allow AI to add more descriptive evidence if it found something extra
                if obj.get("evidence") and len(obj["evidence"]) > len(fp["evidence"]):
                    # Keep our technical mismatch text if we have one
                    if "Mismatch" not in fp["evidence"]:
                        fp["evidence"] = obj["evidence"]
                
                # If AI found a failure but we thought it was pass, trust AI (for secondary details)
                if obj.get("result") in ["FLAG", "REJECT", "FAIL"] and fp["result"] == "PASS":
                    fp["result"] = obj["result"]
    
    pillars = final_pillars

    # Format HTML UI Table
    formatted_summary = f"""<div>
    <h4 style='color:var(--dash-accent); margin-bottom:10px;'>### Institutional Identity Report (KYC)</h4>
    <p style='margin-bottom:15px; font-size:0.85rem;'>{findings}</p>
    
    <div style='background:rgba(255,255,255,0.03); padding:10px; border-radius:6px; margin-bottom:15px; border-left:4px solid var(--dash-accent);'>
        <b style='font-size:0.7rem; color:var(--dash-text-muted); text-transform:uppercase;'>What is Document Proofing?</b><br/>
        <p style='margin:5px 0 0 0; font-size:0.75rem;'>The process of cross-referencing extracted data from uploaded documents (Incorporation Docs, EIN Certs) against official registration databases and declared form data to ensure authenticity and identity consistency.</p>
    </div>"""
    
    formatted_summary += """<table style='width:100%; border-collapse:collapse; font-size:0.75rem; border:1px solid rgba(255,255,255,0.05);'>
<tr style='background:rgba(255,255,255,0.08); color:var(--dash-text-muted);'>
    <th style='padding:10px; text-align:left; border-bottom:2px solid var(--dash-border); width:20%;'>Pillar</th>
    <th style='padding:10px; text-align:left; border-bottom:2px solid var(--dash-border); width:35%;'>Submitted Value</th>
    <th style='padding:10px; text-align:left; border-bottom:2px solid var(--dash-border); width:35%;'>Evidence (Verified Resource)</th>
    <th style='padding:10px; text-align:center; border-bottom:2px solid var(--dash-border); width:10%;'>Status</th>
</tr>"""
    for p in pillars:
        res = str(p.get("result", "PASS")).upper()
        color = "#4ade80" if res == "PASS" or res == "MATCH" else ("#fbbf24" if res == "FLAG" else "#f87171")
        formatted_summary += f"""<tr style='border-bottom:1px solid rgba(255,255,255,0.03);'>
    <td style='padding:10px; font-weight:bold; vertical-align:top; background:rgba(255,255,255,0.01);'>{p['pillar_name']}</td>
    <td style='padding:10px; vertical-align:top; border-right:1px solid rgba(255,255,255,0.03); word-break:break-all;'>{p.get('data_point','—')}</td>
    <td style='padding:10px; vertical-align:top; color:var(--dash-text-muted); line-height:1.4; white-space:pre-wrap;'>{p.get('evidence','—')}</td>
    <td style='padding:10px; text-align:center; vertical-align:top; color:{color}; font-weight:bold;'>{res}</td>
</tr>"""
    formatted_summary += "</table></div>"
    
    insert_agent_log({
        "run_id": run_id, "onboarding_id": onboarding_id, "agent_name": "KYC_SPECIALIST", "stage": 2,
        "check_name": "identity_registry_verification", "output": kyc_res, "risk_level": risk_lvl, 
        "ai_summary": formatted_summary, "duration_ms": kyc_res.get("_duration_ms", 0)
    })
    
    _update_risk_level(onboarding_id, risk_lvl)
    update_onboarding_status(onboarding_id, "KYC_COMPLETE", remarks=f"KYC Identity Verification Complete. Status: {risk_lvl}")
    return {"composite_risk": risk_lvl, "composite_score": 10}

def run_aml_risk_stage(onboarding_id):
    """
    Stage 3: AML - Risk Screening & Scoring
    Performs Sanctions, PEP, and Adverse Media screening.
    """
    logger.info(f"Starting Native AML Risk Orchestration for {onboarding_id}")
    run_id = str(uuid.uuid4())
    session_id = f"aml-{onboarding_id[:8]}"
    
    data = _get_onboarding_data(onboarding_id)
    if not data: return {"error": "Not Found"}

    # 1. Fetch Contexts
    kyc_context = _get_latest_kyc_findings(onboarding_id)
    doc_context = _get_latest_document_findings(onboarding_id)
    
    # 2. Rule-Based Sanctions Screening (Internal DB)
    sanctions_res = sanctions_check(data['company_name'], run_id, onboarding_id)
    
    # 3. Invoke AML Expert Agent (Screener)
    prompt = (
        f"Perform an institutional AML risk screening for {data['company_name']} (ID: {onboarding_id}).\n"
        "YOUR TASKS:\n"
        "1. Sanctions & AML Screening: Cross-reference internal results and search global lists.\n"
        "2. PEP Detection: Search for Political Exposure among known associates.\n"
        "3. Adverse Media: Search for negative news, money laundering, or fraud indicators.\n"
        "4. Risk Scoring: Provide a final numerical score (0-100) and rationale.\n\n"
        f"CONTEXT - KYC IDENTITY RESULTS: {kyc_context}\n"
        f"CONTEXT - TECHNICAL SANCTIONS RESULTS: {json.dumps(sanctions_res)}\n"
        f"CONTEXT - DOC VERIFICATION: {doc_context}\n\n"
        "MANDATORY INSTRUCTION:\n"
        "- YOU MUST perform active search actions for PEP and Adverse Media.\n"
        "- Return a structured JSON with 'aml_pillars' (Sanctions, PEP, Adverse Media).\n"
        "- Each pillar must include 'data_point' (what you searched for) and 'evidence' (what you found)."
    )
    aml_res = invoke_bedrock_agent(AML_EXPERT_AGENT_ID, AGENT_ALIAS_ID, session_id, prompt, onboarding_id, stage=3)
    
    risk_lvl = aml_res.get("risk_rating", "LOW")
    risk_score = aml_res.get("final_risk_score", 10)
    findings = aml_res.get("ai_summary") or aml_res.get("rationale", "AML Risk Profile Complete.")
    pillars = aml_res.get("aml_pillars", [])

    # --- AUDITOR FOR AML STAGE ---
    auditor_prompt = (
        f"You are a Lead AML Risk Auditor. Map these results for {data['company_name']} into a 3-pillar JSON.\n"
        f"TECHNICAL SANCTIONS: {json.dumps(sanctions_res)}\n"
        f"AGENT SCREENING RESULTS: {findings}\n\n"
        "PILLAR DEFINITIONS:\n"
        "1. Sanctions & AML: Must show internal DB results + Global list hits.\n"
        "2. PEP Detection: Must show results of political exposure search.\n"
        "3. Adverse Media: Must show results of negative news search.\n"
        "Return ONLY JSON with 'aml_pillars' list."
    )
    fallback_res = invoke_bedrock_model_direct(auditor_prompt, system_role="Lead Institutional AML Auditor")
    if "aml_pillars" in fallback_res:
         pillars = fallback_res["aml_pillars"]
    
    # Inject Ground Truth for Sanctions
    normalized_pillars = []
    for p in pillars:
        # Ensure p is a dict
        obj = p if isinstance(p, dict) else {"pillar_name": str(p)}
        
        if "Sanctions" in obj.get("pillar_name", ""):
            obj["data_point"] = f"Entity: {data['company_name']}"
            obj["evidence"] = sanctions_res.get("ai_summary", "Sanctions database scrubbed.")
            obj["result"] = sanctions_res.get("recommendation", "PASS")
        
        normalized_pillars.append(obj)
    
    pillars = normalized_pillars

    # Format HTML UI Table
    formatted_summary = f"<div><h4 style='color:var(--dash-accent); margin-bottom:10px;'>### AML Risk & Screening Report</h4><p style='margin-bottom:15px;'>{findings}</p>"
    formatted_summary += """<table style='width:100%; border-collapse:collapse; font-size:0.75rem; border:1px solid rgba(255,255,255,0.05);'>
<tr style='background:rgba(255,255,255,0.08); color:var(--dash-text-muted);'>
    <th style='padding:10px; text-align:left; border-bottom:2px solid var(--dash-border); width:20%;'>Pillar</th>
    <th style='padding:10px; text-align:left; border-bottom:2px solid var(--dash-border); width:35%;'>Screened Value</th>
    <th style='padding:10px; text-align:left; border-bottom:2px solid var(--dash-border); width:35%;'>Evidence (Logic)</th>
    <th style='padding:10px; text-align:center; border-bottom:2px solid var(--dash-border); width:10%;'>Status</th>
</tr>"""
    for p in pillars:
        res = str(p.get("result", "PASS")).upper()
        color = "#4ade80" if res == "PASS" or res == "MATCH" else ("#fbbf24" if res == "FLAG" else "#f87171")
        formatted_summary += f"""<tr style='border-bottom:1px solid rgba(255,255,255,0.03);'>
    <td style='padding:10px; font-weight:bold; vertical-align:top; background:rgba(255,255,255,0.01);'>{p['pillar_name']}</td>
    <td style='padding:10px; vertical-align:top; border-right:1px solid rgba(255,255,255,0.03); word-break:break-all;'>{p.get('data_point','—')}</td>
    <td style='padding:10px; vertical-align:top; color:var(--dash-text-muted); line-height:1.4; white-space:pre-wrap;'>{p.get('evidence','—')}</td>
    <td style='padding:10px; text-align:center; vertical-align:top; color:{color}; font-weight:bold;'>{res}</td>
</tr>"""
    formatted_summary += "</table>"
    
    # Add Score Dashboard
    formatted_summary += f"""<div style='margin-top:20px; display:flex; gap:20px;'>
<div style='background:rgba(255,255,255,0.04); padding:10px 15px; border-radius:8px; border:1px solid rgba(255,255,255,0.08); flex:1;'>
    <span style='font-size:0.65rem; text-transform:uppercase; color:var(--dash-text-muted); tracking:0.1em;'>Final Risk Rating</span><br/>
    <b style='font-size:1.1rem; color:{"#f87171" if risk_lvl.upper() == "HIGH" else "#4ade80"};'>{risk_lvl.upper()}</b>
</div>
<div style='background:rgba(255,255,255,0.04); padding:10px 15px; border-radius:8px; border:1px solid rgba(255,255,255,0.08); flex:1;'>
    <span style='font-size:0.65rem; text-transform:uppercase; color:var(--dash-text-muted); tracking:0.1em;'>Weighted Risk Score</span><br/>
    <b style='font-size:1.1rem; color:var(--dash-accent);'>{risk_score}/100</b>
</div>
</div></div>"""

    insert_agent_log({
        "run_id": run_id, "onboarding_id": onboarding_id, "agent_name": "AML_EXPERT", "stage": 3,
        "check_name": "aml_final_profiling", "output": aml_res, "risk_level": risk_lvl,
        "ai_summary": formatted_summary, "duration_ms": aml_res.get("_duration_ms", 0)
    })
    
    _update_risk_level(onboarding_id, risk_lvl)
    update_onboarding_status(onboarding_id, "AML_COMPLETE", remarks=f"AI AML Risk Profile Complete. Final Rating: {risk_lvl}")
    return {"risk_rating": risk_lvl, "final_risk_score": risk_score}

def _get_directors(onboarding_id):
    conn = get_connection()
    if not conn: return []
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT full_name, role, nationality FROM client_onboarding.onboarding_directors WHERE onboarding_id = %s", (onboarding_id,))
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]
    finally: release_connection(conn)
