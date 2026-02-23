"""
Orchestrator Agent — Coordinates KYCAgent and AMLRiskAgent.
Local stub implementation: runs real rule-based checks against PostgreSQL.
AWS Bedrock replacement: swap run_kyc_stage() / run_aml_risk_stage()
bodies with boto3 bedrock-agent-runtime invoke_agent() calls.
"""

import uuid
import json
import time
import os
import boto3
from botocore.exceptions import ClientError
from ..db import get_connection, release_connection, insert_agent_log, update_onboarding_status
from ..logger import logger_agents as logger

# Composite risk score weights (must sum to 1.0)
_RISK_WEIGHTS = {
    "sanctions_check": 0.35,
    "ubo_sanctions_check": 0.15,
    "director_sanctions_check": 0.10,
    "pep_check": 0.10,
    "registration_format_check": 0.05,
    "country_risk": 0.10,
    "aml_questionnaire_score": 0.10,
    "website_review": 0.10,
}

# AWS Bedrock Agent IDs
KYC_AGENT_ID = "NWXLUU7K4F"
DOC_ANALYST_AGENT_ID = "O7LECAXOR2"
AML_EXPERT_AGENT_ID = "R2M9IFL9QD"
AGENT_ALIAS_ID = "TSTALIASID"  # Default test alias

bedrock_runtime = boto3.client('bedrock-agent-runtime', region_name=os.getenv("AWS_REGION", "us-east-1"))

def invoke_bedrock_agent(agent_id, alias_id, session_id, prompt):
    """Helper to call Bedrock Agent and parse the resulting JSON string."""
    try:
        response = bedrock_runtime.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId=session_id,
            inputText=prompt
        )
        
        event_stream = response['completion']
        full_response = ""
        for event in event_stream:
            if 'chunk' in event:
                full_response += event['chunk']['bytes'].decode('utf-8')
        
        # Bedrock often wraps JSON in code blocks or adds conversational filler
        # Clean it up to get just the JSON
        json_start = full_response.find('{')
        json_end = full_response.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            return json.loads(full_response[json_start:json_end])
        
        # If no JSON object found, return as text if needed, or error
        return {"ai_summary": full_response, "decision_logic": full_response}
    except Exception as e:
        error_msg = f"Bedrock invocation failed: {str(e)}"
        logger.error(f"Error invoking agent {agent_id}: {e}", exc_info=True)
        return {"error": error_msg, "risk_level": "HIGH", "ai_summary": error_msg}

def _find_key(data: dict, keys: list, default=None):
    """Robustly find a value in a dict regardless of exact key casing or underscores."""
    if not isinstance(data, dict):
        return default
    
    # Try exact matches first
    for k in keys:
        if k in data:
            return data[k]
            
    # Try normalized matches
    norm_data = {k.lower().replace("_", "").replace("-", ""): v for k, v in data.items()}
    for k in keys:
        norm_k = k.lower().replace("_", "").replace("-", "")
        if norm_k in norm_data:
            return norm_data[norm_k]
            
    return default

_RISK_SCORE_MAP = {"LOW": 0, "MEDIUM": 50, "HIGH": 75, "CRITICAL": 100}


def _composite_risk(check_results: list) -> tuple[str, int]:
    """Compute weighted composite risk from check results."""
    total_score = 0
    total_weight = 0
    for r in check_results:
        name = r.get("check_name", "")
        weight = _RISK_WEIGHTS.get(name, 0.05)
        score = _RISK_SCORE_MAP.get(r.get("risk_level", "LOW"), 0)
        total_score += weight * score
        total_weight += weight

    composite = int(total_score / total_weight) if total_weight else 0

    if composite >= 76:
        return "CRITICAL", composite
    elif composite >= 51:
        return "HIGH", composite
    elif composite >= 26:
        return "MEDIUM", composite
    else:
        return "LOW", composite


def _get_onboarding_data(onboarding_id: str) -> dict | None:
    """Fetch full onboarding record with UBOs and directors."""
    conn = get_connection()
    if not conn:
        return None
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT id, company_name, email, lei_identifier, entity_type,
                       registration_number, incorporation_date, ownership_type,
                       business_activity, source_of_funds, source_of_wealth,
                       expected_volume, countries_operation, tax_residency_country,
                       pep_declaration, adverse_media_consent, correspondent_bank,
                       aml_program_description, aml_questions, status,
                       dba_name, ein_number, routing_number, account_number, bank_name, mcc_code
                FROM client_onboarding.onboarding_details
                WHERE id = %s
            """, (onboarding_id,))
            row = cursor.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cursor.description]
            data = dict(zip(cols, row))

            # Parse aml_questions
            if data.get("aml_questions") and isinstance(data["aml_questions"], str):
                try:
                    data["aml_questions"] = json.loads(data["aml_questions"])
                except Exception:
                    data["aml_questions"] = {}

            # Parse countries_operation TEXT[]
            if isinstance(data.get("countries_operation"), list):
                pass
            elif isinstance(data.get("countries_operation"), str):
                data["countries_operation"] = [c.strip() for c in data["countries_operation"].split(",") if c.strip()]
            else:
                data["countries_operation"] = []

            # UBOs
            cursor.execute(
                "SELECT full_name, stake_percent, nationality, country_of_residence, date_of_birth, is_pep, tax_id FROM client_onboarding.onboarding_ubos WHERE onboarding_id = %s",
                (onboarding_id,)
            )
            ubo_cols = [d[0] for d in cursor.description]
            data["ubos"] = [dict(zip(ubo_cols, r)) for r in cursor.fetchall()]

            # Directors  
            cursor.execute(
                "SELECT full_name, role, nationality, country_of_residence FROM client_onboarding.onboarding_directors WHERE onboarding_id = %s",
                (onboarding_id,)
            )
            dir_cols = [d[0] for d in cursor.description]
            data["directors"] = [dict(zip(dir_cols, r)) for r in cursor.fetchall()]

            # S3 URIs
            cursor.execute(
                """SELECT bod_list_s3_uri, financials_s3_uri, ownership_s3_uri, 
                          incorporation_doc_s3_uri, bank_statement_s3_uri, 
                          ein_certificate_s3_uri, ubo_id_s3_uri 
                   FROM client_onboarding.onboarding_details WHERE id = %s""",
                (onboarding_id,)
            )
            s3_row = cursor.fetchone()
            if s3_row:
                data["bod_s3"] = s3_row[0]
                data["fin_s3"] = s3_row[1]
                data["own_s3"] = s3_row[2]
                data["inc_s3"] = s3_row[3]
                data["bank_s3"] = s3_row[4]
                data["ein_s3"] = s3_row[5]
                data["ubo_doc_s3"] = s3_row[6]

            return data
    except Exception as e:
        logger.error(f"Failed to fetch onboarding data for {onboarding_id}: {e}", exc_info=True)
        return None
    finally:
        release_connection(conn)


def _update_risk_level(onboarding_id: str, risk_level: str):
    """Update ai_risk_level column in onboarding_details."""
    conn = get_connection()
    if not conn:
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE client_onboarding.onboarding_details SET ai_risk_level = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (risk_level, onboarding_id)
            )
        conn.commit()
    except Exception as e:
        logger.error(f"Failed to update risk level for {onboarding_id} to {risk_level}: {e}", exc_info=True)
        conn.rollback()
    finally:
        release_connection(conn)


def run_kyc_stage(onboarding_id: str) -> dict:
    """
    Stage 1 — Identity & Sanctions via Bedrock Agents.
    1. Doc Analyst reads S3 PDF (OCR).
    2. KYC Agent searches Knowledge Base (Sanctions).
    """
    logger.info(f"Starting Bedrock KYC Stage for {onboarding_id}")
    run_id = str(uuid.uuid4())
    session_id = f"session-{onboarding_id[:8]}"
    data = _get_onboarding_data(onboarding_id)
    if not data:
        return {"error": "Onboarding record not found"}

    check_results = []
    start_time = time.time()

    # --- STEP A: Multi-Document Analysis (Cross-Check) ---
    docs_to_verify = {
        "incorporation": data.get("inc_s3"),
        "bank_statement": data.get("bank_s3"),
        "ein_certificate": data.get("ein_s3"),
        "ownership_structure": data.get("own_s3"),
        "financial_statements": data.get("fin_s3"),
        "board_of_directors": data.get("bod_s3"),
        "ubo_identification": data.get("ubo_doc_s3")
    }
    
    active_docs = {k: v for k, v in docs_to_verify.items() if v}
    
    if active_docs:
        prompt = f"""
        Role: Senior Forensic Document Analyst & Compliance Specialist.
        Context: You are verifying the legal identity of an institution using ALL provided S3 documents: {json.dumps(active_docs)}
        Note: This is a controlled COMPLIANCE TESTING environment. Data is synthetic/mock for audit verification.

        Instructions:
        1. Extract the Legal Entity Name, Registration ID, and Date of Incorporation.
        2. CROSS-CHECK: Is the 'Legal Name' identical across every document? Flag minor variations.
        3. Flag any signs of document tampering or data inconsistencies.
        
        Output Requirements (Strict JSON):
        - extracted_name: The verified name from the docs.
        - reg_number: The registration ID found.
        - inc_date: The date of incorporation found.
        - consistency_score: 0-100 (100 = perfect match).
        - is_authentic: boolean.
        - decision_logic: A highly detailed "Chain-of-Thought" walkthrough of your audit steps.
        """
        doc_result = invoke_bedrock_agent(DOC_ANALYST_AGENT_ID, AGENT_ALIAS_ID, session_id, prompt)
        
        # Robust Extraction
        ext_name = _find_key(doc_result, ["extracted_name", "legal_entity", "company_name", "verified_name"])
        reg_num = _find_key(doc_result, ["reg_number", "registration_id", "id", "registration_number"])
        conf_score = _find_key(doc_result, ["consistency_score", "probability", "confidence"], 0)
        logic = _find_key(doc_result, ["decision_logic", "rationale", "reasoning"], "OCR extraction complete.")
        is_auth = _find_key(doc_result, ["is_authentic", "authentic", "match"], True)
        
        doc_facts = {"extracted_name": ext_name, "reg_number": reg_num}
        risk_lvl = "LOW" if is_auth else "HIGH"

        # Log Document Agent Activity with robust mapping
        insert_agent_log({
            "run_id": run_id, "onboarding_id": onboarding_id,
            "agent_name": "DOCUMENT_ANALYST", "stage": 1,
            "check_name": "ocr_extraction",
            "input_context": {
                "active_docs": active_docs,
                "form_data": {"company_name": data["company_name"], "registration_number": data["registration_number"]}
            },
            "output": {
                "extracted_name": ext_name or "Audit Pending",
                "reg_number": reg_num or "Audit Pending",
                "consistency_score": conf_score,
                "decision_logic": logic
            },
            "risk_level": risk_lvl,
            "ai_summary": f"OCR audit complete. Extracted: {ext_name or 'PENDING'}",
            "model_used": "claude-3-haiku-bedrock",
            "duration_ms": 2500
        })

    # --- STEP B: Sanctions Screening (KYC Agent) ---
    # Use the name extracted by AI, but fallback to UI name
    verified_name = doc_facts.get("extracted_name") or data["company_name"]
    prompt = f"""
    Role: Senior Sanctions & AML Compliance Specialist.
    Context: You are performing a regulatory check for: {verified_name}.
    Note: This is a controlled COMPLIANCE AUDIT test using mock parameters.
    
    Instructions:
    1. Static Check: Query the Knowledge Base for SDN/Sanctions matches for this entity.
    2. Adverse Media: Search for fraud, money laundering, or illegal trade associations.
    3. Conclude: Assign a final risk level based on match severity.

    Output Requirements (Strict JSON):
    - sanctions_match: boolean.
    - negative_news_found: boolean.
    - news_summary: summary of findings.
    - program: list of programs (e.g. 'SDN', 'RUSSIA').
    - reason: brief summary for results.
    - risk_level: "LOW", "HIGH", or "CRITICAL".
    - decision_logic: Detailed walkthrough of your screening steps.
    """
    kyc_result = invoke_bedrock_agent(KYC_AGENT_ID, AGENT_ALIAS_ID, session_id, prompt)
    
    risk_lvl = "CRITICAL" if kyc_result.get("sanctions_match") else "LOW"
    check_results.append({
        "check_name": "sanctions_check",
        "risk_level": risk_lvl,
        "ai_summary": kyc_result.get("reason") or kyc_result.get("match_remarks") or "No matches found.",
        "flags": kyc_result.get("program", []) if kyc_result.get("sanctions_match") else []
    })

    # Log KYC Agent Activity
    insert_agent_log({
        "run_id": run_id, "onboarding_id": onboarding_id,
        "agent_name": "KYC_SPECIALIST", "stage": 1,
        "check_name": "entity_sanctions_screening",
        "input_context": {"verified_name": verified_name},
        "output": kyc_result,
        "risk_level": risk_lvl,
        "ai_summary": "Searched Knowledge Base for SDN/Sanction matches on the entity.",
        "model_used": "claude-3-haiku-bedrock",
        "duration_ms": 2000
    })

    # --- STEP C: Personnel Screening (Directors & UBOs) ---
    personnel = []
    for d in data.get("directors", []):
        personnel.append({"name": d["full_name"], "type": "DIRECTOR"})
    for u in data.get("ubos", []):
        personnel.append({"name": u["full_name"], "type": "UBO"})

    for person in personnel:
        p_name = person["name"]
        p_type = person["type"]
        print(f"[Orchestrator] Screening {p_type}: {p_name}")
        
        # 1. Sanctions Check
        p_prompt = f"Role: Individual Screening Specialist. Context: Regulatory audit for {p_name} ({p_type}). Search KB for sanctions matches. Output JSON: sanctions_match, match_remarks, decision_logic."
        p_kyc_result = invoke_bedrock_agent(KYC_AGENT_ID, AGENT_ALIAS_ID, session_id, p_prompt)
        p_risk = "CRITICAL" if p_kyc_result.get("sanctions_match") else "LOW"
        check_results.append({
            "check_name": f"personnel_sanctions_{p_name}",
            "risk_level": p_risk,
            "ai_summary": f"{p_type} screening: {p_kyc_result.get('match_remarks', 'No matches found.')}"
        })

        # 2. Adverse Media / News Check (Search Tool)
        print(f"[Orchestrator] Adverse Media Check for {p_name}")
        news_prompt = f"Role: News Auditor. Context: Search for adverse news, fraud, or legal issues for {p_name}. Output JSON: negative_news_found, news_summary, decision_logic."
        news_result = invoke_bedrock_agent(KYC_AGENT_ID, AGENT_ALIAS_ID, session_id, news_prompt)
        
        n_risk = "HIGH" if news_result.get("negative_news_found") else "LOW"
        check_results.append({
            "check_name": f"adverse_media_{p_name}",
            "risk_level": n_risk,
            "ai_summary": f"Adverse Media for {p_name}: {news_result.get('news_summary', 'Clean record.')}"
        })

        # Log Personnel Sanctions log
        insert_agent_log({
            "run_id": run_id, "onboarding_id": onboarding_id,
            "agent_name": "KYC_SPECIALIST", "stage": 1,
            "check_name": f"personnel_sanctions_{p_name}",
            "input_context": {"person_name": p_name, "person_type": p_type},
            "output": p_kyc_result,
            "risk_level": p_risk,
            "ai_summary": f"{p_type} screening: {p_kyc_result.get('match_remarks', 'No matches found.')}",
            "model_used": "claude-3-haiku-bedrock",
            "duration_ms": 1500
        })

        # Log Personnel Adverse Media
        insert_agent_log({
            "run_id": run_id, "onboarding_id": onboarding_id,
            "agent_name": "KYC_SPECIALIST", "stage": 1,
            "check_name": f"adverse_media_{p_name}",
            "input_context": {"person_name": p_name, "person_type": p_type},
            "output": news_result,
            "risk_level": n_risk,
            "ai_summary": f"Adverse Media for {p_name}: {news_result.get('news_summary', 'Clean record.')}",
            "model_used": "claude-3-haiku-bedrock",
            "duration_ms": 1500
        })

    # --- STEP D: Entity Adverse Media ---
    print(f"[Orchestrator] Adverse Media Check for Entity: {verified_name}")
    ent_news_prompt = f"Use your search tool to query recent news, fraud, or legal issues regarding the company: {verified_name}"
    ent_news_result = invoke_bedrock_agent(KYC_AGENT_ID, AGENT_ALIAS_ID, session_id, ent_news_prompt)
    
    ent_n_risk = "HIGH" if ent_news_result.get("negative_news_found") else "LOW"
    check_results.append({
        "check_name": "entity_adverse_media",
        "risk_level": ent_n_risk,
        "ai_summary": f"Entity News: {ent_news_result.get('news_summary', 'No significant adverse media found.')}"
    })

    # Log Entity Adverse Media log
    insert_agent_log({
        "run_id": run_id, "onboarding_id": onboarding_id,
        "agent_name": "KYC_SPECIALIST", "stage": 1,
        "check_name": "entity_adverse_media",
        "input_context": {"verified_name": verified_name},
        "output": ent_news_result,
        "risk_level": ent_n_risk,
        "ai_summary": f"Entity News: {ent_news_result.get('news_summary', 'No significant adverse media found.')}",
        "model_used": "claude-3-haiku-bedrock",
        "duration_ms": 2000
    })

    # Compute composite risk
    composite_risk, composite_score = _composite_risk(check_results)
    
    _update_risk_level(onboarding_id, composite_risk)
    update_onboarding_status(
        onboarding_id, "KYC_COMPLETE",
        action_by="BEDROCK_AGENT",
        remarks=f"Bedrock KYC Phase 1 Complete. Risk: {composite_risk}. Score: {composite_score}/100"
    )

    return {
        "run_id": run_id,
        "composite_risk": composite_risk,
        "composite_score": composite_score,
        "check_results": check_results
    }


def run_aml_risk_stage(onboarding_id: str) -> dict:
    """
    Stage 2 — Final AML Risk Rating via Bedrock Agent.
    """
    print(f"[Orchestrator] Starting Bedrock AML Risk Stage for {onboarding_id}")
    run_id = str(uuid.uuid4())
    session_id = f"session-aml-{onboarding_id[:8]}"
    data = _get_onboarding_data(onboarding_id)
    if not data:
        return {"error": "Onboarding record not found"}

    # Gather facts for the expert
    facts = {
        "application_data": {
            "country": data.get("country"),
            "business_activity": data.get("business_activity"),
            "expected_volume": data.get("expected_volume"),
            "ownership_type": data.get("ownership_type"),
            "pep_declaration": data.get("pep_declaration")
        },
        "previous_checks": {
            "onboarding_id": onboarding_id,
            "kyc_verification": "Performed via Knowledge Base"
        }
    }

    facts_json = json.dumps(facts)
    prompt = f"""
    Role: Chief Risk Officer (AML Expert).
    Task: Assign the final numeric risk score (1-100) and rating for this institution.
    
    Inputs: {facts_json}
    
    Scoring Rules:
    - Sanctions Match (CRITICAL) = 100
    - Adverse Media Confirmed (HIGH) = 80-100
    - Multi-document Name Mismatch (MEDIUM) = 60-79
    - High-Risk Country/Activity = +20 to base score.
    
    Output Requirements (Strict JSON):
    - risk_rating: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL".
    - final_risk_score: 1-100.
    - rationale: A concise executive summary of the risk.
    - required_next_steps: list of actions (e.g., 'Enhanced Due Diligence').
    - decision_logic: A step-by-step breakdown of how you applied the scoring rules to the specific data points provided.
    """
    expert_result = invoke_bedrock_agent(AML_EXPERT_AGENT_ID, AGENT_ALIAS_ID, session_id, prompt)
    
    risk_lvl = expert_result.get("risk_rating", "MEDIUM")
    
    # Writing final log
    insert_agent_log({
        "run_id": run_id, "onboarding_id": onboarding_id,
        "agent_name": "AML_RISK_EXPERT", "stage": 2,
        "check_name": "final_risk_score",
        "input_context": facts,
        "output": expert_result,
        "risk_level": risk_lvl,
        "recommendation": expert_result.get("required_next_steps", ["Standard Review"]),
        "ai_summary": expert_result.get("rationale") or "Final risk assessment complete.",
        "model_used": "claude-3-haiku-bedrock",
        "duration_ms": 3000
    })

    _update_risk_level(onboarding_id, risk_lvl)
    update_onboarding_status(
        onboarding_id, "AML_COMPLETE",
        action_by="AML_RISK_AGENT",
        remarks=f"Bedrock AML Phase 2 Complete. Final Rating: {risk_lvl}."
    )

    return {
        "run_id": run_id,
        "final_rating": risk_lvl,
        "rationale": expert_result.get("rationale")
    }
