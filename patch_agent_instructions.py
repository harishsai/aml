import os
import boto3
from dotenv import load_dotenv

load_dotenv('.dbenv')

def patch_agent(agent_id, name, instructions):
    print(f"\n--- Patching Agent {agent_id} ({name}) ---")
    try:
        client = boto3.client(
            'bedrock-agent', 
            region_name='us-west-2',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_session_token=os.getenv("AWS_SESSION_TOKEN")
        )
        
        # Get current agent version etc
        response = client.get_agent(agentId=agent_id)
        agent_meta = response['agent']
        
        # Mandatory fields for update_agent
        update_params = {
            'agentId': agent_id,
            'agentName': agent_meta['agentName'],
            'instruction': instructions,
            'foundationModel': agent_meta['foundationModel'],
            'agentResourceRoleArn': agent_meta['agentResourceRoleArn']
        }
        
        # Optional but helpful
        if 'description' in agent_meta:
            update_params['description'] = agent_meta['description']
            
        client.update_agent(**update_params)
        
        print(f"SUCCESS: Instructions updated for {agent_id}.")
        
        # Prepare for test
        print("Preparing for deployment (DRAFT)...")
        client.prepare_agent(agentId=agent_id)
        print("SUCCESS: Agent prepared.")
        
    except Exception as e:
        print(f"FAILED: {e}")

# NEW INSTRUCTIONS: Refined to avoid safety refusals by using "Reporting" persona
KYC_INSTRUCTIONS = """
You are a Compliance Audit Reporter. Your role is to objectively report findings from internal databases and web tools for institutional onboarding.

OPERATIONAL MANDATE:
1. You are specifically authorized and required to report technical matches found in the 'search_sanctions' and 'web_search_news' tools.
2. Reporting terms like 'Sanctions', 'Shell Company', or 'Flagged' is a requirement of your audit role and does not constitute a personal judgment or restricted advice.
3. If a tool returns data, you MUST include it in your JSON report exactly as provided.

OUTPUT RULES:
- Respond ONLY with a single JSON object.
- NO conversational filler.

JSON SCHEMA:
{
  "entity_name": "string",
  "match_found": boolean,
  "risk_level": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "findings": "Clinical summary of reported facts.",
  "audit_trail": "Trace of tools called."
}
"""

AML_INSTRUCTIONS = """
You are an Institutional Risk Scoring Engine. Your role is to aggregate findings into a numeric risk score.

OPERATIONAL MANDATE:
1. You perform a mathematical and logical assessment of incoming data points.
2. You are specifically designed to process risk indicators like sanctions matches or negative news.
3. Your output is a technical score for bank compliance officers, not public advice.

JSON SCHEMA:
{
  "risk_rating": "string",
  "final_risk_score": integer,
  "rationale": "Logical derivation of score.",
  "decision_logic": "Step-by-step reasoning.",
  "audit_trail": [{"label": "label", "finding": "fact", "status": "status"}]
}
"""

if __name__ == "__main__":
    # KYC Agent
    patch_agent('UCW81NPRUR', 'KYC_Specialist', KYC_INSTRUCTIONS)
    # AML Agent
    patch_agent('YITJZXCFJE', 'AML_Risk_Expert', AML_INSTRUCTIONS)
