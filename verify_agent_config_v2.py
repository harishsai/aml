import boto3
import os
import json
from dotenv import load_dotenv

load_dotenv('.dbenv')

client = boto3.client('bedrock-agent', region_name='us-west-2')

AGENTS = {
    "KYC_AGENT": "UCW81NPRUR"
}

def get_meta(label, agent_id):
    try:
        print(f"\n=== {label} ({agent_id}) ===")
        response = client.get_agent(agentId=agent_id)
        agent = response['agent']
        print(f"Name: {agent.get('agentName')}")
        
        # Check for Action Groups
        ags = client.list_agent_action_groups(agentId=agent_id, agentVersion='DRAFT')
        for ag in ags.get('actionGroupSummaries', []):
            print(f"\n - Action Group: {ag.get('actionGroupName')} ({ag.get('actionGroupState')})")
            ag_id = ag['actionGroupId']
            ag_detail = client.get_agent_action_group(agentId=agent_id, agentVersion='DRAFT', actionGroupId=ag_id)
            ag_obj = ag_detail['actionGroup']
            
            if 'apiSchema' in ag_obj:
                print(f"   API Schema: {ag_obj['apiSchema']}")
            if 'functionSchema' in ag_obj:
                functions = ag_obj['functionSchema'].get('functions', [])
                for f in functions:
                    print(f"   Function: {f['name']} - {f.get('description')}")
            if 'actionGroupExecutor' in ag_obj:
                print(f"   Executor: {ag_obj['actionGroupExecutor']}")
            
    except Exception as e:
        print(f"FAILED for {label}: {str(e)}")

if __name__ == "__main__":
    for label, aid in AGENTS.items():
        get_meta(label, aid)
