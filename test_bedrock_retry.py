import boto3
import json
import os
import uuid
from dotenv import load_dotenv

# Load env for AWS credentials/region
load_dotenv(".dbenv")

client = boto3.client('bedrock-agent-runtime', region_name=os.getenv("AWS_REGION", "us-west-2"))

KYC_AGENT_ID = "NWXLUU7K4F"
AML_EXPERT_AGENT_ID = "R2M9IFL9QD"
AGENT_ALIAS_ID = "TSTALIASID"

def test_agent(agent_id, alias_id, prompt):
    session_id = str(uuid.uuid4())
    print(f"\n--- Testing Agent: {agent_id} ---")
    print(f"Prompt: {prompt}")
    try:
        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=alias_id,
            sessionId=session_id,
            inputText=prompt
        )
        
        full_text = ""
        for event in response['completion']:
            if 'chunk' in event:
                full_text += event['chunk']['bytes'].decode('utf-8')
        
        print(f"Response: {full_text}")
        return full_text
    except Exception as e:
        print(f"Error invoking agent: {e}")
        return None

if __name__ == "__main__":
    # Test KYC Specialist (Sanctions)
    kyc_prompt = "Perform a sanctions check for Evergreen Financial Group. Use your tools and provide the results in strict JSON format including match_found and risk_level."
    test_agent(KYC_AGENT_ID, AGENT_ALIAS_ID, kyc_prompt)
    
    # Test AML Risk Expert (Risk Analysis)
    aml_prompt = "Analyze the AML risk for a bank in the US with expected volumes of $10M/month. Provide a numeric risk score (1-100) and rationale in strict JSON format."
    test_agent(AML_EXPERT_AGENT_ID, AGENT_ALIAS_ID, aml_prompt)
