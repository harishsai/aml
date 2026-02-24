import boto3
import os
from dotenv import load_dotenv

load_dotenv('.dbenv')

client = boto3.client('bedrock-agent', region_name='us-west-2')

try:
    print("Fetching Details for Agent NWXLUU7K4F (KYC Agent)...")
    response = client.get_agent(agentId='NWXLUU7K4F')
    agent = response['agent']
    print(f"Name: {agent.get('agentName')}")
    print(f"Instruction: {agent.get('instruction')}")
    print(f"Foundation Model: {agent.get('foundationModel')}")
    
    # Check for Action Groups or Knowledge Bases
    print("\nChecking Action Groups...")
    ags = client.list_agent_action_groups(agentId='NWXLUU7K4F', agentVersion='DRAFT')
    for ag in ags.get('actionGroupSummaries', []):
        print(f" - Action Group: {ag.get('actionGroupName')} ({ag.get('actionGroupState')})")
        
    print("\nChecking Knowledge Bases...")
    kbs = client.list_agent_knowledge_bases(agentId='NWXLUU7K4F', agentVersion='DRAFT')
    for kb in kbs.get('knowledgeBaseSummaries', []):
        print(f" - Knowledge Base: {kb.get('knowledgeBaseId')} ({kb.get('knowledgeBaseState')})")

except Exception as e:
    print(f"FAILED: {str(e)}")
