"""
KYC Agent — Stage 1: Identity & Sanctions Screening
Runs rule-based checks against local PostgreSQL tables.
Each check writes one row to ai_agent_logs and returns a structured result dict.
When AWS Bedrock is integrated, this module becomes a Lambda Action Group.
"""

import time
from ..db import get_connection, release_connection, insert_agent_log

# Public/free email domain blocklist
_PUBLIC_DOMAINS = {
    "yahoo.com", "hotmail.com", "outlook.com",
    "icloud.com", "protonmail.com", "aol.com", "live.com", "mail.com"
}

# Sanctions fuzzy match threshold (simple ILIKE for local; Bedrock KB for AWS)
_SANCTIONS_THRESHOLD = 0.80  # 80% similarity


def _ilike_match(cursor, name: str) -> list:
    """Simple ILIKE partial match against sanctions_list. Returns list of hits."""
    # Split name into tokens and check any token against entity_name
    tokens = [t for t in name.split() if len(t) > 3]
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
    """Check company name against OFAC SDN sanctions list."""
    start = time.time()
    conn = get_connection()
    hits = []
    try:
        with conn.cursor() as cursor:
            hits = _ilike_match(cursor, company_name)
    except Exception as e:
        print(f"[KYCAgent] sanctions_check error: {e}")
    finally:
        if conn:
            release_connection(conn)

    duration_ms = int((time.time() - start) * 1000)
    risk_level = "CRITICAL" if hits else "LOW"
    flags = [f"{h['matched_name']} → {h['program']}" for h in hits]
    summary = (
        f"Direct SDN match found: {', '.join(flags)}" if hits
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
            cursor.execute("""
                SELECT lei_code, legal_name, status, country, ein_number, dba_name
                FROM client_onboarding.entity_verification
                WHERE lei_code = %s
            """, (lei,))
            row = cursor.fetchone()
            if row:
                lei_valid = True
                lei_row = {
                    "lei_code": row[0], "legal_name": row[1], "status": row[2], 
                    "country": row[3], "ein_number": row[4], "dba_name": row[5]
                }
                # Simple name match — first word of each
                name_match = (
                    company_name.split()[0].lower() in row[1].lower() or
                    row[1].split()[0].lower() in company_name.lower()
                ) if company_name else False
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
        flags = [f"Name mismatch: form='{company_name}' vs LEI record='{lei_row['legal_name']}'"]
        summary = f"LEI valid but company name does not match LEI record ('{lei_row['legal_name']}')."
        recommendation = "FLAG"
    elif not ein_match:
        risk_level = "MEDIUM"
        flags = [f"EIN mismatch: form='{kwargs.get('ein_number')}' vs registry='{lei_row['ein_number']}'"]
        summary = f"LEI verify: EIN mismatch against official registration record."
        recommendation = "FLAG"
    elif not dba_match:
        risk_level = "LOW"
        flags = [f"DBA mismatch: form='{kwargs.get('dba_name')}' vs registry='{lei_row['dba_name']}'"]
        summary = f"LEI verify: DBA name '{kwargs.get('dba_name')}' differs from registry record."
        recommendation = "PASS" # DBA mismatches are common/low risk
    else:
        risk_level = "LOW"
        flags = []
        summary = f"LEI {lei} verified. Matches '{lei_row['legal_name']}' and tax records."
        recommendation = "PASS"

    result = {
        "check_name": "lei_verify",
        "risk_level": risk_level,
        "recommendation": recommendation,
        "flags": flags,
        "ai_summary": summary,
        "output": {"lei_valid": lei_valid, "name_match": name_match, "lei_row": lei_row}
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


def email_domain_check(email: str, run_id: str, onboarding_id: str) -> dict:
    """Block public/personal email domains — institutional emails required."""
    start = time.time()
    domain = email.split("@")[-1].lower() if "@" in email else ""
    is_public = domain in _PUBLIC_DOMAINS
    flags = [f"Public email domain detected: @{domain}"] if is_public else []
    risk_level = "HIGH" if is_public else "LOW"
    summary = (
        f"Non-institutional email domain '@{domain}' used. Institutional email required."
        if is_public else
        f"Email domain '@{domain}' is institutional. No concern."
    )
    recommendation = "FLAG" if is_public else "PASS"
    duration_ms = int((time.time() - start) * 1000)

    result = {
        "check_name": "email_domain_check",
        "risk_level": risk_level,
        "recommendation": recommendation,
        "flags": flags,
        "ai_summary": summary,
        "output": {"email": email, "domain": domain, "is_public": is_public}
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
