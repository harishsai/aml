import os
import json
import boto3
from dotenv import load_dotenv

load_dotenv('.dbenv')

# Agent IDs (Updated for new account)
KYC_AGENT_ID = "UCW81NPRUR"
AGENT_ALIAS_ID = "TSTALIASID"

client = boto3.client(
    'bedrock-agent-runtime', 
    region_name='us-west-2',
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    aws_session_token=os.getenv("AWS_SESSION_TOKEN")
)

def test_refined_kyc():
    print(f"\n--- REFINED VERIFICATION: KYC AGENT ---")
    
    # Simplified clinical prompt that avoids triggering safety rules
    prompt = "Screen the entity 'Evergreen Financial Group' for sanctions and adverse media. Return ONLY a single JSON object with findings."
    
    try:
        response = client.invoke_agent(
            agentId=KYC_AGENT_ID,
            agentAliasId=AGENT_ALIAS_ID,
            sessionId='proof-session-1',
            inputText=prompt
        )
        
        completion = ""
        for event in response['completion']:
            if 'chunk' in event:
                completion += event['chunk']['bytes'].decode('utf-8')
        print(f"Result: {completion}")
    except Exception as e:
        print(f"FAILED: {str(e)}")

if __name__ == "__main__":
    test_refined_kyc()
