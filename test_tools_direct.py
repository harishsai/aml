import os
import boto3
from dotenv import load_dotenv

load_dotenv('.dbenv')

KB_ID = "MADM3WXUBU"

client_runtime = boto3.client('bedrock-agent-runtime', region_name='us-west-2')

def test_kb_direct(name):
    print(f"\n--- TESTING DIRECT KB ({KB_ID}) FOR '{name}' ---")
    try:
        response = client_runtime.retrieve(
            knowledgeBaseId=KB_ID,
            retrievalQuery={'text': name}
        )
        results = response.get('results', [])
        print(f"Results Count: {len(results)}")
        for r in results:
            print(f"Snippet: {r.get('content', {}).get('text')[:300]}...")
    except Exception as e:
        print(f"KB FAILED: {str(e)}")

if __name__ == "__main__":
    test_kb_direct("VTB Bank PJSC")
