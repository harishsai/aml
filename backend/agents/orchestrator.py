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
    logger.info(f"[Orchestrator] Invoking Agent {agent_id} with prompt: {prompt}")
    
    # Simplified clinical prompt to avoid safety refusals
    force_prompt = f"Screen the entity '{prompt}' for sanctions and adverse media. Return ONLY a single JSON object with findings."
    
    try:
        client = get_bedrock_client('bedrock-agent-runtime')
        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId=session_id,
            inputText=force_prompt,
            enableTrace=True
        )
        
        full_text = ""
        # For deep debugging, let's log the raw traces to a file
        with open("agent_trace.log", "a") as trace_log:
            trace_log.write(f"\n--- SESSION: {session_id} START ---\n")
            
            for event in response['completion']:
                trace_log.write(f"EVENT: {list(event.keys())}\n")
                
                # Capture JSON Chunks
                if 'chunk' in event:
                    full_text += event['chunk']['bytes'].decode('utf-8')
                
                # Capture Traces for real-time visibility
                if 'trace' in event:
                    trace_data = event['trace'].get('trace', {})
                    # Use default=str to handle datetime serialization
                    trace_log.write(f"TRACE_DEBUG: {json.dumps(trace_data, default=str)}\n")
                    
                    orch = trace_data.get('orchestrationTrace', {})
                    
                    # 1. Detection of Tool Calls (Inputs)
                    inv_input = orch.get('invocationInput', {})
                    if 'actionGroupInvocationInput' in inv_input:
                        ag = inv_input['actionGroupInvocationInput']
                        func_name = ag.get('function', 'unknown_tool')
                        params = ag.get('parameters', [])
                        logger.info(f"[AgentTrace] INVOKING: {func_name} | {params}")
                        
                        if onboarding_id:
                            insert_agent_log({
                                "run_id": str(uuid.uuid4()), 
                                "onboarding_id": onboarding_id, 
                                "agent_name": "KYC_SPECIALIST" if stage==1 else "AML_EXPERT",
                                "stage": stage,
                                "check_name": f"tool_use: {func_name}",
                                "output": {"parameters": params},
                                "risk_level": "LOW",
                                "ai_summary": f"Agent is executing internal tool: {func_name.replace('_', ' ')}",
                                "status": "RUNNING"
                            })

                    # 2. Detection of Tool Results (Observations)
                    observation = orch.get('observation', {})
                    if 'actionGroupInvocationOutput' in observation:
                        ao = observation['actionGroupInvocationOutput']
                        text_res = ao.get('text', '')
                        logger.info(f"[AgentTrace] OBSERVATION: {text_res[:200]}...")
                        
                        if onboarding_id:
                            insert_agent_log({
                                "run_id": str(uuid.uuid4()), 
                                "onboarding_id": onboarding_id, 
                                "agent_name": "KYC_SPECIALIST" if stage==1 else "AML_EXPERT",
                                "stage": stage,
                                "check_name": f"tool_result",
                                "output": {"raw_result": text_res},
                                "risk_level": "LOW",
                                "ai_summary": f"Agent received data from internal tool.",
                                "status": "COMPLETED"
                            })

        duration = int((time.time() - start_time) * 1000)
        logger.info(f"[Orchestrator] Agent {agent_id} finished in {duration}ms. Full Output: {full_text[:200]}...")
        
        # Robust JSON extraction
        json_start = full_text.find('{')
        json_end = full_text.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            try:
                res = json.loads(full_text[json_start:json_end])
                res["_duration_ms"] = duration
                return res
            except Exception as je: 
                logger.warning(f"JSON Parse failed: {je}")
            
        return {"error": "No JSON found", "ai_summary": full_text, "_duration_ms": duration}
    except Exception as e:
        logger.error(f"Agent invocation failed for {agent_id}: {e}", exc_info=True)
        return {"error": str(e), "_duration_ms": int((time.time() - start_time) * 1000)}

def invoke_bedrock_model_direct(prompt, system_role="Institutional Onboarding Analyst"):
    """Direct Nova Lite call for risk reasoning and JSON consolidation."""
    try:
        bedrock_runtime_rt = get_bedrock_client('bedrock-runtime')
        message = {"role": "user", "content": [{"text": prompt}]}
        response = bedrock_runtime_rt.converse(
            modelId="amazon.nova-lite-v1:0",
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
            bucket = s3_uri.split("/")[2]
            key = "/".join(s3_uri.split("/")[3:])
            content.append({
                "document": {
                    "name": doc_type[:20].replace("_", ""),
                    "format": "pdf",
                    "source": {"s3Location": {"bucket": bucket, "key": key}}
                }
            })
        message = {"role": "user", "content": content}
        response = bedrock_runtime_rt.converse(
            modelId="amazon.nova-lite-v1:0",
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
                SELECT id, company_name, registration_number, 
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

# --- MAIN STAGES ---

def run_kyc_stage(onboarding_id):
    logger.info(f"Starting Native KYC Orchestration for {onboarding_id}")
    run_id = str(uuid.uuid4())
    session_id = f"kyc-{onboarding_id[:8]}"
    data = _get_onboarding_data(onboarding_id)
    if not data: return {"error": "Not Found"}
    
    # 1. Invoke KYC Agent (it handles SQL Sanctions + News via Action Groups)
    prompt = f"Perform a sanctions and adverse media screening for {data['company_name']}."
    kyc_res = invoke_bedrock_agent(KYC_AGENT_ID, AGENT_ALIAS_ID, session_id, prompt, onboarding_id, stage=1)
    
    risk_lvl = kyc_res.get("risk_level", "LOW")
    duration = kyc_res.get("_duration_ms", 0)
    
    # Map Agent keys to orchestrator internal keys if needed
    findings = kyc_res.get("findings") or kyc_res.get("ai_summary", "Native Screening Complete.")
    risk_lvl = kyc_res.get("risk_level", "LOW")
    
    # Log it
    insert_agent_log({
        "run_id": run_id, "onboarding_id": onboarding_id, "agent_name": "KYC_SPECIALIST", "stage": 1,
        "check_name": "entity_screening", "output": kyc_res, "risk_level": risk_lvl, 
        "ai_summary": findings,
        "duration_ms": duration
    })
    
    # Update DB Status & Risk
    _update_risk_level(onboarding_id, risk_lvl)
    update_onboarding_status(onboarding_id, "KYC_COMPLETE", remarks=f"AI Identity Check Complete. {risk_lvl} Risk identified.")
    
    return {"composite_risk": risk_lvl, "composite_score": kyc_res.get("risk_score", 10)}

def run_aml_risk_stage(onboarding_id):
    logger.info(f"Starting Native AML Risk Orchestration for {onboarding_id}")
    run_id = str(uuid.uuid4())
    session_id = f"aml-{onboarding_id[:8]}"
    
    # Fetch KYC context to pass to the agent
    kyc_context = _get_latest_kyc_findings(onboarding_id)
    
    # 2. Invoke AML Expert Agent
    prompt = (
        f"Analyze institutional risk for onboarding ID: {onboarding_id}.\n"
        f"CONTEXT - KYC FINDINGS: {kyc_context}"
    )
    aml_res = invoke_bedrock_agent(AML_EXPERT_AGENT_ID, AGENT_ALIAS_ID, session_id, prompt, onboarding_id, stage=2)
    
    risk_lvl = aml_res.get("risk_rating", "LOW")
    duration = aml_res.get("_duration_ms", 0)
    _update_risk_level(onboarding_id, risk_lvl)
    
    # Log it
    insert_agent_log({
        "run_id": run_id, "onboarding_id": onboarding_id, "agent_name": "AML_EXPERT", "stage": 2,
        "check_name": "final_profiling", "output": aml_res, "risk_level": risk_lvl,
        "ai_summary": aml_res.get("rationale", "Native AML Risk Analysis Complete."),
        "duration_ms": duration
    })
    
    update_onboarding_status(onboarding_id, "AML_COMPLETE", remarks=f"AI AML Risk Profile Complete. Final Rating: {risk_lvl}")
    
    return {"risk_rating": risk_lvl, "final_risk_score": aml_res.get("final_risk_score", 10)}
