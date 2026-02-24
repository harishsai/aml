import boto3
import json
import os
from dotenv import load_dotenv

load_dotenv('.dbenv')

# Data from User's Screenshot
tracking_id = "KTX-202602-01001"
bucket = "kinetix-onboarding-docs"
key = f"uploads/{tracking_id}/certificate_of_incorporation.pdf"

client = boto3.client('bedrock-runtime', region_name='us-west-2')

print(f"--- DIRECT MODEL TEST: NOVA LITE ---")
print(f"S3: s3://{bucket}/{key}")

# Nova Lite direct invocation with S3 document
message = {
    "role": "user",
    "content": [
        {
            "text": "Please extract the company name and registration ID from this document."
        },
        {
            "document": {
                "name": "incorporation_doc",
                "format": "pdf",
                "source": {
                    "s3Location": {
                        "uri": f"s3://{bucket}/{key}"
                    }
                }
            }
        }
    ]
}

try:
    response = client.converse(
        modelId="amazon.nova-lite-v1:0",
        messages=[message],
        inferenceConfig={"maxTokens": 500, "temperature": 0}
    )
    
    text_out = response['output']['message']['content'][0]['text']
    print("\n[SUCCESS] Direct Model Response:")
    print(text_out)

except Exception as e:
    print(f"\n[FAILED] Error: {str(e)}")
