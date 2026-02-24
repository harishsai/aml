import os
import boto3
from dotenv import load_dotenv

load_dotenv(".dbenv")

def add_permission():
    print("\n--- Adding Lambda Invoke Permissions for Bedrock ---")
    try:
        client = boto3.client(
            'lambda',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
            region_name="us-west-2"
        )
        
        # Add permission for Bedrock to invoke the function
        try:
            response = client.add_permission(
                FunctionName='web_search_news',
                StatementId='AllowBedrockInvoke-' + os.getenv("AWS_ACCESS_KEY_ID")[-4:],
                Action='lambda:InvokeFunction',
                Principal='bedrock.amazonaws.com'
            )
            print(f"SUCCESS: Permission added. Statement: {response['Statement']}")
        except client.exceptions.ResourceConflictException:
            print("INFO: Permission already exists (ResourceConflictException).")
            
    except Exception as e:
        print(f"FAILURE: {e}")

if __name__ == "__main__":
    add_permission()
