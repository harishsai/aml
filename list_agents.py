import os
import boto3
from dotenv import load_dotenv

# Load environment
load_dotenv(".dbenv")

def list_agents():
    print("\n--- Listing Bedrock Agents in us-west-2 ---")
    try:
        client = boto3.client(
            'bedrock-agent',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
            region_name="us-west-2"
        )
        response = client.list_agents()
        agents = response.get('agentSummaries', [])
        if not agents:
            print("No agents found in this account/region.")
        for agent in agents:
            print(f"ID: {agent['agentId']} | Name: {agent['agentName']} | Status: {agent['agentStatus']}")
            
            # Also list aliases for this agent
            try:
                aliases = client.list_agent_aliases(agentId=agent['agentId'])
                for alias in aliases.get('agentAliasSummaries', []):
                    print(f"  - Alias ID: {alias['agentAliasId']} | Name: {alias['agentAliasName']}")
            except Exception as e:
                print(f"  - Error listing aliases: {e}")
                
    except Exception as e:
        print(f"FAILURE: Could not list agents: {e}")

if __name__ == "__main__":
    list_agents()
