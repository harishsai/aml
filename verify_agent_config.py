import boto3
import os
from dotenv import load_dotenv

load_dotenv('.dbenv')

client = boto3.client('bedrock-agent', region_name='us-west-2')

AGENTS = {
    "KYC_AGENT": "UCW81NPRUR",
    "AML_EXPERT_AGENT": "YITJZXCFJE"
}

def get_meta(label, agent_id):
    try:
        print(f"\n=== {label} ({agent_id}) ===")
        response = client.get_agent(agentId=agent_id)
        agent = response['agent']
        print(f"Name: {agent.get('agentName')}")
        print(f"Instruction: {agent.get('instruction')}")
        
        # Check for Action Groups
        ags = client.list_agent_action_groups(agentId=agent_id, agentVersion='DRAFT')
        for ag in ags.get('actionGroupSummaries', []):
            print(f" - Action Group: {ag.get('actionGroupName')} ({ag.get('actionGroupState')})")
            # Get details of the action group to see tools
            ag_detail = client.get_agent_action_group(agentId=agent_id, agentVersion='DRAFT', actionGroupId=ag['actionGroupId'])
            print(f"   Tools: {ag_detail['actionGroup'].get('apiSchema') or ag_detail['actionGroup'].get('functionSchema')}")
            
    except Exception as e:
        print(f"FAILED for {label}: {str(e)}")

if __name__ == "__main__":
    for label, aid in AGENTS.items():
        get_meta(label, aid)
