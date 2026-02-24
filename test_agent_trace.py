import os
import boto3
import json
from dotenv import load_dotenv

load_dotenv('.dbenv')

def get_bedrock_client(client_type='bedrock-agent-runtime'):
    return boto3.client(
        client_type,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
        region_name=os.getenv("AWS_REGION", "us-west-2")
    )

def test_trace_capture():
    print("\n--- CAPTURING TRACE: KYC AGENT ---")
    client = get_bedrock_client()
    
    # Very direct prompt, no meta-references
    prompt = "Screen Evergreen Financial Group for sanctions and news. Output JSON."
    
    try:
        response = client.invoke_agent(
            agentId="UCW81NPRUR",
            agentAliasId="TSTALIASID",
            sessionId='trace-test-session',
            inputText=prompt,
            enableTrace=True
        )
        
        completion = ""
        for event in response['completion']:
            if 'chunk' in event:
                completion += event['chunk']['bytes'].decode('utf-8')
            if 'trace' in event:
                trace = event['trace']
                if 'orchestrationTrace' in trace:
                    orch = trace['orchestrationTrace']
                    if 'modelInvocationInput' in orch:
                        print("\n[INPUT SENT TO MODEL]")
                        # print(orch['modelInvocationInput'].get('text', ''))
                    if 'modelInvocationOutput' in orch:
                        print("\n[MODEL RESPONSE]")
                        # print(orch['modelInvocationOutput'].get('rawResponse', {}).get('content', ''))
                    if 'observation' in orch:
                        print(f"\n[ORCHESTRATION STEP]: {orch['observation'].get('type')}")
                    if 'rationale' in orch:
                        print(f"\n[RATIONALE]: {orch['rationale'].get('text')}")

        print(f"\nFINAL RESULT: {completion}")
        
    except Exception as e:
        print(f"FAILED: {str(e)}")

if __name__ == "__main__":
    test_trace_capture()
