import boto3
import os
from dotenv import load_dotenv

load_dotenv('.dbenv')

def get_agent_meta(agent_id):
    print(f"\n--- Fetching Details for Agent {agent_id} ---")
    try:
        client = boto3.client(
            'bedrock-agent', 
            region_name='us-west-2',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_session_token=os.getenv("AWS_SESSION_TOKEN")
        )
        
        response = client.get_agent(agentId=agent_id)
        agent = response['agent']
        print(f"Name: {agent.get('agentName')}")
        print(f"Instruction: {agent.get('instruction')}")
        print(f"Foundation Model: {agent.get('foundationModel')}")
        
        guardrail = agent.get('guardrailConfiguration', {})
        if guardrail:
            print(f"Guardrail: {guardrail.get('guardrailIdentifier')} (Version: {guardrail.get('guardrailVersion')})")
        else:
            print("Guardrail: NONE")

        # Check for Action Groups or Knowledge Bases
        print("\nChecking Action Groups...")
        ags = client.list_agent_action_groups(agentId=agent_id, agentVersion='DRAFT')
        for ag in ags.get('actionGroupSummaries', []):
            print(f" - Action Group: {ag.get('actionGroupName')} ({ag.get('actionGroupState')})")
            
        print("\nChecking Knowledge Bases...")
        kbs = client.list_agent_knowledge_bases(agentId=agent_id, agentVersion='DRAFT')
        for kb in kbs.get('knowledgeBaseSummaries', []):
            print(f" - Knowledge Base: {kb.get('knowledgeBaseId')} ({kb.get('knowledgeBaseState')})")

    except Exception as e:
        print(f"FAILED: {str(e)}")

if __name__ == "__main__":
    # KYC Specialist Agent in the new account
    get_agent_meta('UCW81NPRUR')
