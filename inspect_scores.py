import json
import psycopg2
import os
from dotenv import load_dotenv

# Load env from .dbenv
load_dotenv(dotenv_path='.dbenv')

def inspect_scores():
    try:
        conn = psycopg2.connect(
            host=os.getenv("DB_HOST", "localhost"),
            database=os.getenv("DB_NAME", "aml_db"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "postgres"),
            port=os.getenv("DB_PORT", "5432")
        )
        with conn.cursor() as cur:
            cur.execute("""
                SELECT output, ai_summary, risk_level, created_at
                FROM client_onboarding.ai_agent_logs 
                WHERE agent_name = 'KYC_SPECIALIST' 
                ORDER BY created_at DESC LIMIT 1
            """)
            row = cur.fetchone()
            if row:
                output = row[0]
                summary = row[1]
                risk = row[2]
                print(f"Time: {row[3]}")
                print(f"Risk Level: {risk}")
                print(f"Risk Scores: {json.dumps(output.get('risk_scores'), indent=2)}")
                print(f"Findings: {output.get('findings')}")
                
                # Check for observations
                obs = output.get('_observations', [])
                print(f"Tool Observations Count: {len(obs)}")
                for o in obs:
                    if 'technical_check' not in o:
                        print(f"Agent Observation: {json.dumps(o, indent=2)}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals(): conn.close()

if __name__ == "__main__":
    inspect_scores()
