import os
import boto3
from dotenv import load_dotenv

load_dotenv('.dbenv')

print(f"Testing AWS Key: {os.getenv('AWS_ACCESS_KEY_ID')[:8]}...")

client = boto3.client('bedrock-agent-runtime', region_name='us-west-2')

try:
    response = client.invoke_agent(
        agentId='NWXLUU7K4F',
        agentAliasId='TSTALIASID',
        sessionId='test-session-123',
        inputText='Hello, are you working?'
    )
    print("Invocation successful!")
    completion = ""
    for event in response['completion']:
        if 'chunk' in event:
            completion += event['chunk']['bytes'].decode('utf-8')
    print(f"Response: {completion}")
except Exception as e:
    print(f"FAILED: {str(e)}")
