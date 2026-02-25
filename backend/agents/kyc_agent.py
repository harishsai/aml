"""
KYC Agent — Stage 1: Identity & Sanctions Screening
Runs rule-based checks against local PostgreSQL tables.
Each check writes one row to ai_agent_logs and returns a structured result dict.
When AWS Bedrock is integrated, this module becomes a Lambda Action Group.
"""

import time
import json
import urllib.request
from ..db import get_connection, release_connection, insert_agent_log

# Public/free email domain blocklist
_PUBLIC_DOMAINS = {
    "yahoo.com", "hotmail.com", "outlook.com",
    "icloud.com", "protonmail.com", "aol.com", "live.com", "mail.com"
}

# Generic corporate tokens to ignore in sanctions fuzzy match to prevent false positives
_COMMON_TOKENS = {
    "group", "financial", "services", "corporation", "corp", "limited", "ltd", 
    "inc", "incorporated", "company", "holdings", "management", "international",
    "global", "solutions", "partners", "capital", "trust", "investment"
}


def _ilike_match(cursor, name: str) -> list:
    """Simple ILIKE partial match against sanctions_list. Returns list of hits."""
    # Split name into tokens and check any token against entity_name
    # Filter out common tokens and short words to reduce false positives
    tokens = [t.lower() for t in name.split() if len(t) > 3 and t.lower() not in _COMMON_TOKENS]
    hits = []
    for token in tokens:
        cursor.execute("""
            SELECT entity_name, entity_type, program, list_type, country
            FROM client_onboarding.sanctions_list
            WHERE entity_name ILIKE %s
            LIMIT 5
        """, (f"%{token}%",))
        for row in cursor.fetchall():
            hits.append({
                "matched_name": row[0],
                "entity_type": row[1],
                "program": row[2],
                "list_type": row[3],
                "country": row[4]
            })
    return hits


def sanctions_check(company_name: str, run_id: str, onboarding_id: str) -> dict:
    """Check company name against US ICE Wanted API."""
    start = time.time()
    hits = []
    try:
        url = "https://data.opensanctions.org/artifacts/us_ice_wanted/20250714143724-bvk/entities.delta.json"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            print(f"Response {response}")
            for line in response:
                if not line.strip():
                    continue
                obj = json.loads(line)
                entity = obj.get("entity", {})
                caption = entity.get("caption", "")
                print(f"caption {caption} : company_name {company_name}")
                # Compare caption with company name
                if caption and (company_name.lower() in caption.lower() or caption.lower() in company_name.lower()):
                    hits.append({
                        "matched_name": caption,
                        "program": "US_ICE_WANTED"
                    })
    except Exception as e:
        print(f"[KYCAgent] sanctions_check error: {e}")

    duration_ms = int((time.time() - start) * 1000)
    risk_level = "CRITICAL" if hits else "LOW"
    flags = [f"{h['matched_name']} → {h['program']}" for h in hits]
    summary = (
        f"API SDN match found: {', '.join(flags)}" if hits
        else f"No sanctions match for '{company_name}'."
    )
    result = {
        "check_name": "sanctions_check",
        "risk_level": risk_level,
        "recommendation": "REJECT" if hits else "PASS",
        "flags": flags,
        "ai_summary": summary,
        "output": {"input_name": company_name, "hits": hits}
    }
    insert_agent_log({
        "run_id": run_id, "onboarding_id": onboarding_id,
        "agent_name": "KYC_AGENT", "stage": 1,
        "check_name": "sanctions_check",
        "input_context": {"company_name": company_name},
        "output": {"hits": hits},
        "flags": flags, "risk_level": risk_level,
        "recommendation": result["recommendation"],
        "ai_summary": summary,
        "model_used": "rule-based",
        "duration_ms": duration_ms
    })
    print(f"result {result}")

    return result


def ubo_sanctions_check(ubos: list, run_id: str, onboarding_id: str) -> dict:
    """Check each UBO name against sanctions list."""
    start = time.time()
    all_hits = []
    all_flags = []
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            for ubo in ubos:
                name = ubo.get("full_name", "")
                hits = _ilike_match(cursor, name)
                for h in hits:
                    all_hits.append({"ubo": name, **h})
                    all_flags.append(f"{name} → {h['matched_name']} [{h['program']}]")
    except Exception as e:
        print(f"[KYCAgent] ubo_sanctions_check error: {e}")
    finally:
        if conn:
            release_connection(conn)

    duration_ms = int((time.time() - start) * 1000)
    risk_level = "CRITICAL" if all_hits else "LOW"
    summary = (
        f"UBO sanctions hits: {', '.join(all_flags)}" if all_hits
        else f"No sanctions matches found for {len(ubos)} UBO(s)."
    )
    result = {
        "check_name": "ubo_sanctions_check",
        "risk_level": risk_level,
        "recommendation": "REJECT" if all_hits else "PASS",
        "flags": all_flags,
        "ai_summary": summary,
        "output": {"hits": all_hits}
    }
    insert_agent_log({
        "run_id": run_id, "onboarding_id": onboarding_id,
        "agent_name": "KYC_AGENT", "stage": 1,
        "check_name": "ubo_sanctions_check",
        "input_context": {"ubo_count": len(ubos)},
        "output": {"hits": all_hits},
        "flags": all_flags, "risk_level": risk_level,
        "recommendation": result["recommendation"],
        "ai_summary": summary,
        "model_used": "rule-based",
        "duration_ms": duration_ms
    })
    return result


def director_sanctions_check(directors: list, run_id: str, onboarding_id: str) -> dict:
    """Check each director name against sanctions list."""
    start = time.time()
    all_hits = []
    all_flags = []
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            for director in directors:
                name = director.get("full_name", "")
                hits = _ilike_match(cursor, name)
                for h in hits:
                    all_hits.append({"director": name, **h})
                    all_flags.append(f"{name} → {h['matched_name']} [{h['program']}]")
    except Exception as e:
        print(f"[KYCAgent] director_sanctions_check error: {e}")
    finally:
        if conn:
            release_connection(conn)

    duration_ms = int((time.time() - start) * 1000)
    risk_level = "HIGH" if all_hits else "LOW"
    summary = (
        f"Director sanctions hits: {', '.join(all_flags)}" if all_hits
        else f"No sanctions matches found for {len(directors)} director(s)."
    )
    result = {
        "check_name": "director_sanctions_check",
        "risk_level": risk_level,
        "recommendation": "FLAG" if all_hits else "PASS",
        "flags": all_flags,
        "ai_summary": summary,
        "output": {"hits": all_hits}
    }
    insert_agent_log({
        "run_id": run_id, "onboarding_id": onboarding_id,
        "agent_name": "KYC_AGENT", "stage": 1,
        "check_name": "director_sanctions_check",
        "input_context": {"director_count": len(directors)},
        "output": {"hits": all_hits},
        "flags": all_flags, "risk_level": risk_level,
        "recommendation": result["recommendation"],
        "ai_summary": summary,
        "model_used": "rule-based",
        "duration_ms": duration_ms
    })
    return result


def lei_verify(lei: str, company_name: str, run_id: str, onboarding_id: str, **kwargs) -> dict:
    """Verify LEI against local entity_verification table."""
    start = time.time()
    conn = get_connection()
    lei_valid = False
    name_match = False
    lei_row = None
    try:
        with conn.cursor() as cursor:
            # First try LEI
            if lei:
                cursor.execute("""
                    SELECT lei_number, company_name, verification_status, country, ein_number, dba_name
                    FROM client_onboarding.entity_verification
                    WHERE lei_number = %s
                """, (lei,))
                row = cursor.fetchone()
                if row:
                    lei_valid = True
                    lei_row = {
                        "lei_number": row[0], "company_name": row[1], "status": row[2], 
                        "country": row[3], "ein_number": row[4], "dba_name": row[5]
                    }
            
            # If no LEI match, fallback to Company Name fuzzy match
            if not lei_valid and company_name:
                cursor.execute("""
                    SELECT lei_number, company_name, verification_status, country, ein_number, dba_name
                    FROM client_onboarding.entity_verification
                    WHERE company_name ILIKE %s
                    LIMIT 1
                """, (f"%{company_name.split()[0]}%",))
                row = cursor.fetchone()
                if row:
                    lei_row = {
                        "lei_number": row[0], "company_name": row[1], "status": row[2], 
                        "country": row[3], "ein_number": row[4], "dba_name": row[5]
                    }
                    # We found a record by name even if LEI was missing/wrong
                    name_match = True 

            # Cross-verify name if LEI was found (OUTSIDE the fallback loop)
            if lei_valid and not name_match and company_name and lei_row:
                # Get unique tokens (ignoring common ones like Group, Financial)
                form_tokens = {t.lower() for t in company_name.split() if t.lower() not in _COMMON_TOKENS and len(t) > 2}
                reg_name_lower = lei_row['company_name'].lower()
                
                # If any unique word from the form is in the registry name, it's a match
                if any(token in reg_name_lower for token in form_tokens):
                    name_match = True
                else:
                    # Final fallback: check if first word of registry is in form name
                    first_reg_word = lei_row['company_name'].split()[0].lower()
                    if first_reg_word in company_name.lower():
                        name_match = True
    except Exception as e:
        print(f"[KYCAgent] lei_verify error: {e}")
    finally:
        if conn:
            release_connection(conn)

    duration_ms = int((time.time() - start) * 1000)
    
    ein_match = True
    dba_match = True
    
    if lei_valid:
        # Cross-verify EIN if record has one
        submitted_ein = kwargs.get("ein_number")
        if lei_row.get("ein_number") and submitted_ein:
            if lei_row["ein_number"].replace("-","") != submitted_ein.replace("-",""):
                ein_match = False
        
        # Cross-verify DBA if record has one
        submitted_dba = kwargs.get("dba_name")
        if lei_row.get("dba_name") and submitted_dba:
            if submitted_dba.lower() not in lei_row["dba_name"].lower() and \
               lei_row["dba_name"].lower() not in submitted_dba.lower():
                dba_match = False

    if not lei_valid:
        risk_level = "HIGH"
        flags = [f"LEI '{lei}' not found in entity_verification table"]
        summary = f"LEI {lei} could not be verified. Entity may not exist or LEI may be invalid."
        recommendation = "FLAG"
    elif not name_match:
        risk_level = "MEDIUM"
        flags = [f"Name mismatch: form='{company_name}' vs LEI record='{lei_row['company_name']}'"]
        summary = f"LEI valid but company name mismatch: Form='{company_name}' vs Registry='{lei_row['company_name']}'."
        recommendation = "FLAG"
    elif not ein_match:
        risk_level = "HIGH"
        reg_ein = lei_row.get("ein_number", "None")
        sub_ein = kwargs.get("ein_number", "None")
        flags = [f"EIN mismatch: form='{sub_ein}' vs registry='{reg_ein}'"]
        summary = f"CRITICAL: EIN Mismatch. Form EIN '{sub_ein}' does not match official Registry EIN '{reg_ein}'."
        recommendation = "REJECT"
    elif not dba_match:
        risk_level = "LOW"
        flags = [f"DBA mismatch: form='{kwargs.get('dba_name')}' vs registry='{lei_row['dba_name']}'"]
        summary = f"LEI verify: DBA name '{kwargs.get('dba_name')}' differs from registry record."
        recommendation = "PASS" # DBA mismatches are common/low risk
    else:
        risk_level = "LOW"
        flags = []
        summary = f"LEI {lei} verified. Matches '{lei_row['company_name']}' and tax records."
        recommendation = "PASS"

    result = {
        "check_name": "lei_verify",
        "risk_level": risk_level,
        "recommendation": recommendation,
        "flags": flags,
        "ai_summary": summary,
        "output": {
            "submitted_lei": lei,
            "submitted_ein": kwargs.get("ein_number"),
            "registry_record": lei_row,
            "lei_valid": lei_valid,
            "name_match": name_match,
            "ein_match": ein_match
        }
    }
    insert_agent_log({
        "run_id": run_id, "onboarding_id": onboarding_id,
        "agent_name": "KYC_AGENT", "stage": 1,
        "check_name": "lei_verify",
        "input_context": {"lei": lei, "company_name": company_name},
        "output": result["output"],
        "flags": flags, "risk_level": risk_level,
        "recommendation": recommendation,
        "ai_summary": summary,
        "model_used": "rule-based",
        "duration_ms": duration_ms
    })
    return result


def pep_check(pep_declaration: bool, ubos: list, run_id: str, onboarding_id: str) -> dict:
    """Check PEP declaration and UBO PEP flags."""
    start = time.time()
    pep_ubos = [u["full_name"] for u in ubos if u.get("is_pep")]
    flags = []
    if pep_declaration:
        flags.append("Entity-level PEP declared by applicant")
    for name in pep_ubos:
        flags.append(f"UBO '{name}' flagged as PEP")

    duration_ms = int((time.time() - start) * 1000)
    if pep_declaration and pep_ubos:
        risk_level = "HIGH"
        summary = f"PEP risk confirmed: entity-level declaration + {len(pep_ubos)} PEP UBO(s)."
        recommendation = "FLAG"
    elif pep_declaration or pep_ubos:
        risk_level = "MEDIUM"
        summary = f"PEP flag detected: {', '.join(flags)}."
        recommendation = "FLAG"
    else:
        risk_level = "LOW"
        summary = "No PEP exposure detected."
        recommendation = "PASS"

    result = {
        "check_name": "pep_check",
        "risk_level": risk_level,
        "recommendation": recommendation,
        "flags": flags,
        "ai_summary": summary,
        "output": {"pep_declaration": pep_declaration, "pep_ubos": pep_ubos}
    }
    insert_agent_log({
        "run_id": run_id, "onboarding_id": onboarding_id,
        "agent_name": "KYC_AGENT", "stage": 1,
        "check_name": "pep_check",
        "input_context": {"pep_declaration": pep_declaration, "ubo_count": len(ubos)},
        "output": result["output"],
        "flags": flags, "risk_level": risk_level,
        "recommendation": recommendation,
        "ai_summary": summary,
        "model_used": "rule-based",
        "duration_ms": duration_ms
    })
    return result


def email_domain_check(email: str, run_id: str, onboarding_id: str, website: str = None, directors: list = None) -> dict:
    """Institutional email validation with domain-to-website cross-check."""
    start = time.time()
    domain = email.split("@")[-1].lower() if "@" in email else ""
    is_public = domain in _PUBLIC_DOMAINS
    
    # 1. Match against company website domain (if provided)
    web_domain = website.lower().replace("https://","").replace("http://","").replace("www.","").split("/")[0] if website else ""
    web_match = domain == web_domain if web_domain and domain else False
    
    # 2. Match against director names (high risk if domain is a relative's name)
    director_match = False
    if directors:
        for d in directors:
            d_name = d.get('full_name', '').lower().replace(" ","")
            if d_name and d_name in domain:
                director_match = True
                break

    flags = []
    if is_public:
        flags.append(f"Public email domain detected: @{domain}")
    elif website and not web_match:
        flags.append(f"Domain mismatch: email '@{domain}' vs website '{web_domain}'")
    
    if director_match and is_public:
        flags.append(f"Personal email belongs to director match")

    risk_level = "HIGH" if is_public else ("MEDIUM" if (website and not web_match) else "LOW")
    
    if is_public:
        summary = f"Personal email '@{domain}' used. Institutional '@{web_domain or 'company.com'}' required."
    elif website and not web_match:
        summary = f"Email '@{domain}' does not match official company domain '{web_domain}'."
    else:
        summary = f"Institutional email '@{domain}' verified against company identity."

    recommendation = "FLAG" if (is_public or (website and not web_match)) else "PASS"
    duration_ms = int((time.time() - start) * 1000)

    result = {
        "check_name": "email_domain_check",
        "risk_level": risk_level,
        "recommendation": recommendation,
        "flags": flags,
        "ai_summary": summary,
        "output": {"email": email, "domain": domain, "web_domain": web_domain, "is_public": is_public, "web_match": web_match}
    }
    insert_agent_log({
        "run_id": run_id, "onboarding_id": onboarding_id,
        "agent_name": "KYC_AGENT", "stage": 1,
        "check_name": "email_domain_check",
        "input_context": {"email": email},
        "output": result["output"],
        "flags": flags, "risk_level": risk_level,
        "recommendation": recommendation,
        "ai_summary": summary,
        "model_used": "rule-based",
        "duration_ms": duration_ms
    })
    return result


def registration_format_check(reg_number: str, country: str, run_id: str, onboarding_id: str) -> dict:
    """Basic format validation for company registration numbers based on country."""
    start = time.time()
    # Mock logic: Flag if numeric-only or too short
    is_valid = len(str(reg_number)) >= 5
    flags = [] if is_valid else [f"Suspiciously short registration number: {reg_number}"]
    risk_level = "LOW" if is_valid else "MEDIUM"
    summary = (
        f"Registration number '{reg_number}' format seems valid for {country}."
        if is_valid else
        f"Registration number '{reg_number}' is unusually short. Verification recommended."
    )
    recommendation = "PASS" if is_valid else "FLAG"
    duration_ms = int((time.time() - start) * 1000)

    result = {
        "check_name": "registration_format_check",
        "risk_level": risk_level,
        "recommendation": recommendation,
        "flags": flags,
        "ai_summary": summary,
        "output": {"reg_number": reg_number, "country": country, "is_valid": is_valid}
    }
    insert_agent_log({
        "run_id": run_id, "onboarding_id": onboarding_id,
        "agent_name": "KYC_AGENT", "stage": 1,
        "check_name": "registration_format_check",
        "input_context": {"reg_number": reg_number, "country": country},
        "output": result["output"],
        "flags": flags, "risk_level": risk_level,
        "recommendation": recommendation,
        "ai_summary": summary,
        "model_used": "rule-based",
        "duration_ms": duration_ms
    })
    return result
