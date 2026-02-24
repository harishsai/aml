import os
import boto3
from dotenv import load_dotenv

PROFILE_NAME = "hackathon-participant-537998868531"
FILES_TO_UPDATE = [".dbenv", "cfg.txt"]

def refresh_creds():
    print(f"--- Refreshing AWS Credentials from Profile: {PROFILE_NAME} ---")
    try:
        session = boto3.Session(profile_name=PROFILE_NAME)
        credentials = session.get_credentials()
        
        if not credentials:
            print("ERROR: No credentials found for profile. Run 'aws sso login --profile " + PROFILE_NAME + "' first.")
            return

        frozen_creds = credentials.get_frozen_credentials()
        
        access_key = frozen_creds.access_key
        secret_key = frozen_creds.secret_key
        session_token = frozen_creds.token
        region = session.region_name or "us-west-2"

        print(f"SUCCESS: Fetched credentials (Access Key: {access_key[:10]}...)")
        
        for filename in FILES_TO_UPDATE:
            if not os.path.exists(filename):
                print(f"SKIPPING: {filename} does not exist.")
                continue
            
            with open(filename, 'r') as f:
                lines = f.readlines()
            
            new_lines = []
            found_token = False
            for line in lines:
                if line.startswith("AWS_ACCESS_KEY_ID="):
                    new_lines.append(f"AWS_ACCESS_KEY_ID={access_key}\n")
                elif line.startswith("AWS_SECRET_ACCESS_KEY="):
                    new_lines.append(f"AWS_SECRET_ACCESS_KEY={secret_key}\n")
                elif line.startswith("AWS_SESSION_TOKEN="):
                    new_lines.append(f"AWS_SESSION_TOKEN={session_token}\n")
                    found_token = True
                elif line.startswith("AWS_REGION="):
                    new_lines.append(f"AWS_REGION={region}\n")
                else:
                    new_lines.append(line)
            
            if not found_token:
                # Add it before AWS_REGION or at the end
                for i, line in enumerate(new_lines):
                    if line.startswith("AWS_REGION="):
                        new_lines.insert(i, f"AWS_SESSION_TOKEN={session_token}\n")
                        found_token = True
                        break
                if not found_token:
                    new_lines.append(f"AWS_SESSION_TOKEN={session_token}\n")
            
            with open(filename, 'w') as f:
                f.writelines(new_lines)
            print(f"UPDATED: {filename}")

    except Exception as e:
        print(f"FAILURE: Could not refresh credentials: {e}")
        print("Tip: Ensure you have run 'aws sso login --profile " + PROFILE_NAME + "'")

if __name__ == "__main__":
    refresh_creds()
