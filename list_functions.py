import os
import boto3
from dotenv import load_dotenv

load_dotenv(".dbenv")

def list_functions():
    print("\n--- Listing Lambda Functions in us-west-2 ---")
    try:
        client = boto3.client(
            'lambda',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_session_token=os.getenv("AWS_SESSION_TOKEN"),
            region_name="us-west-2"
        )
        response = client.list_functions()
        functions = response.get('Functions', [])
        if not functions:
            print("No functions found.")
        for f in functions:
            print(f"- {f['FunctionName']}")
    except Exception as e:
        print(f"FAILURE: {e}")

if __name__ == "__main__":
    list_functions()
