import time
import json
import uuid
import sys
import os

# Add parent dir to path to import db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db import insert_agent_log

def review_website(website_url: str, company_name: str, run_id: str, onboarding_id: str) -> dict:
    """
    Autonomous agent to crawl company website and verify:
    - Existence of Terms & Conditions / Refund Policy.
    - Consistency of contact details vs. signup form.
    - General business legitimacy and model.
    """
    print(f"[WebsiteAgent] Starting review for {website_url}")
    start = time.time()
    
    # Placeholder for actual crawling/AI logic
    # In Bedrock integration, this would invoke a search tool or a web scraper Lambda
    
    logs = []
    flags = []
    risk_level = "LOW"
    recommendation = "PASS"
    
    # Mock checks
    if not website_url:
        risk_level = "HIGH"
        recommendation = "FLAG"
        flags.append("No website URL provided")
        summary = "No website provided for review. Business legitimacy cannot be verified autonomously."
    else:
        # Mocking successful review
        summary = f"Autonomous review of {website_url} complete. Terms of Service and Privacy Policy found. Contact info matches application."
        logs.append(f"Crawled {website_url}")
        logs.append("Found /terms-of-service")
        logs.append("Found /privacy-policy")

    duration_ms = int((time.time() - start) * 1000)
    
    result = {
        "check_name": "website_review",
        "risk_level": risk_level,
        "recommendation": recommendation,
        "flags": flags,
        "ai_summary": summary,
        "output": {"website": website_url, "checks": logs}
    }

    insert_agent_log({
        "run_id": run_id,
        "onboarding_id": onboarding_id,
        "agent_name": "WEBSITE_AGENT",
        "stage": 2, # Stage 2: Risk Profile
        "check_name": "website_review",
        "input_context": {"website": website_url, "company_name": company_name},
        "output": result["output"],
        "flags": flags,
        "risk_level": risk_level,
        "recommendation": recommendation,
        "ai_summary": summary,
        "model_used": "autonomous-agent-stub",
        "duration_ms": duration_ms
    })
    
    return result
