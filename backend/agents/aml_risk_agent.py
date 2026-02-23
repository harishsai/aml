"""
AML Risk Agent — Stage 2: Risk Profiling
Runs weighted risk scoring checks against local PostgreSQL tables.
Each check writes one row to ai_agent_logs and returns a structured result dict.
When AWS Bedrock is integrated, this module becomes a Lambda Action Group.
"""

import time
from ..db import get_connection, release_connection, insert_agent_log

# SOF risk map
_SOF_RISK = {
    "Operating Revenues": "LOW",
    "Investment Returns": "LOW",
    "Shareholder Capital": "LOW",
    "Asset Sales": "MEDIUM",
    "Loans / Credit Facilities": "MEDIUM",
    "Grants / Subsidies": "MEDIUM",
    "Cash Deposits": "HIGH",
    "Other": "HIGH"
}

# Volume band to monthly USD approx
_VOLUME_BANDS = {
    "Under $100K": 100_000,
    "$100K – $500K": 500_000,
    "$500K – $1M": 1_000_000,
    "$1M – $5M": 5_000_000,
    "$5M – $10M": 10_000_000,
    "Over $10M": 50_000_000
}

# New entity threshold (months)
_NEW_ENTITY_MONTHS = 12


def country_risk(countries: list, run_id: str, onboarding_id: str) -> dict:
    """Check each country against FATF country_risk_reference table."""
    start = time.time()
    conn = get_connection()
    results = []
    highest_risk = "LOW"
    flags = []
    risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    try:
        with conn.cursor() as cursor:
            for country in countries:
                cursor.execute("""
                    SELECT country_name, fatf_status, risk_level
                    FROM client_onboarding.country_risk_reference
                    WHERE country_name ILIKE %s OR country_code = %s
                """, (f"%{country}%", country.upper()[:2]))
                row = cursor.fetchone()
                if row:
                    entry = {"country": country, "fatf_status": row[1], "risk_level": row[2]}
                    results.append(entry)
                    if risk_order.get(row[2], 0) > risk_order.get(highest_risk, 0):
                        highest_risk = row[2]
                    if row[2] in ("HIGH", "CRITICAL"):
                        flags.append(f"{row[0]}: FATF {row[1]} ({row[2]})")
                else:
                    results.append({"country": country, "fatf_status": "UNKNOWN", "risk_level": "MEDIUM"})
                    flags.append(f"{country}: not in FATF reference table")
    except Exception as e:
        print(f"[AMLRiskAgent] country_risk error: {e}")
    finally:
        if conn:
            release_connection(conn)

    duration_ms = int((time.time() - start) * 1000)
    summary = (
        f"Highest country risk: {highest_risk}. Flagged: {', '.join(flags)}" if flags
        else f"All {len(countries)} countries assessed as {highest_risk} risk."
    )
    recommendation = "REJECT" if highest_risk == "CRITICAL" else ("FLAG" if highest_risk == "HIGH" else "PASS")
    result = {
        "check_name": "country_risk",
        "risk_level": highest_risk,
        "recommendation": recommendation,
        "flags": flags,
        "ai_summary": summary,
        "output": {"countries": results, "highest_risk": highest_risk}
    }
    insert_agent_log({
        "run_id": run_id, "onboarding_id": onboarding_id,
        "agent_name": "AML_RISK_AGENT", "stage": 2,
        "check_name": "country_risk",
        "input_context": {"countries": countries},
        "output": result["output"],
        "flags": flags, "risk_level": highest_risk,
        "recommendation": recommendation,
        "ai_summary": summary,
        "model_used": "rule-based",
        "duration_ms": duration_ms
    })
    return result


def ubo_jurisdiction_risk(ubos: list, run_id: str, onboarding_id: str) -> dict:
    """Check UBO country of residence against FATF risk reference."""
    start = time.time()
    conn = get_connection()
    flags = []
    highest_risk = "LOW"
    risk_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    try:
        with conn.cursor() as cursor:
            for ubo in ubos:
                country = ubo.get("country_of_residence", "")
                if not country:
                    continue
                cursor.execute("""
                    SELECT country_name, fatf_status, risk_level
                    FROM client_onboarding.country_risk_reference
                    WHERE country_name ILIKE %s
                """, (f"%{country}%",))
                row = cursor.fetchone()
                if row and risk_order.get(row[2], 0) > 0:
                    if risk_order.get(row[2], 0) > risk_order.get(highest_risk, 0):
                        highest_risk = row[2]
                    flags.append(f"UBO '{ubo.get('full_name')}' domicile: {row[0]} [{row[1]}]")
    except Exception as e:
        print(f"[AMLRiskAgent] ubo_jurisdiction_risk error: {e}")
    finally:
        if conn:
            release_connection(conn)

    duration_ms = int((time.time() - start) * 1000)
    summary = (
        f"UBO jurisdiction risk: {highest_risk}. {', '.join(flags)}" if flags
        else f"All {len(ubos)} UBO domiciles assessed as low risk."
    )
    recommendation = "FLAG" if highest_risk in ("HIGH", "CRITICAL") else "PASS"
    result = {
        "check_name": "ubo_jurisdiction_risk",
        "risk_level": highest_risk,
        "recommendation": recommendation,
        "flags": flags,
        "ai_summary": summary,
        "output": {"highest_risk": highest_risk}
    }
    insert_agent_log({
        "run_id": run_id, "onboarding_id": onboarding_id,
        "agent_name": "AML_RISK_AGENT", "stage": 2,
        "check_name": "ubo_jurisdiction_risk",
        "input_context": {"ubo_count": len(ubos)},
        "output": result["output"],
        "flags": flags, "risk_level": highest_risk,
        "recommendation": recommendation,
        "ai_summary": summary,
        "model_used": "rule-based",
        "duration_ms": duration_ms
    })
    return result


def volume_check(expected_volume: str, entity_type: str, incorporation_date: str,
                 run_id: str, onboarding_id: str) -> dict:
    """Flag disproportionate transaction volume relative to entity age/type."""
    start = time.time()
    flags = []
    risk_level = "LOW"

    volume_usd = _VOLUME_BANDS.get(expected_volume, 0)

    # Check entity age
    is_new = False
    if incorporation_date:
        try:
            from datetime import date
            inc = date.fromisoformat(str(incorporation_date))
            months_old = (date.today().year - inc.year) * 12 + (date.today().month - inc.month)
            is_new = months_old < _NEW_ENTITY_MONTHS
        except Exception:
            pass

    if is_new and volume_usd > 1_000_000:
        flags.append(f"New entity (<{_NEW_ENTITY_MONTHS}mo) claiming volume {expected_volume}")
        risk_level = "HIGH"
    elif volume_usd > 10_000_000 and entity_type in ("Corporate", "Other"):
        flags.append(f"Very high volume {expected_volume} for {entity_type} entity")
        risk_level = "MEDIUM"

    duration_ms = int((time.time() - start) * 1000)
    summary = (
        f"Volume concern: {', '.join(flags)}" if flags
        else f"Expected volume {expected_volume} is proportionate to entity profile."
    )
    recommendation = "FLAG" if flags else "PASS"
    result = {
        "check_name": "volume_check",
        "risk_level": risk_level,
        "recommendation": recommendation,
        "flags": flags,
        "ai_summary": summary,
        "output": {"volume_band": expected_volume, "volume_usd": volume_usd, "is_new_entity": is_new}
    }
    insert_agent_log({
        "run_id": run_id, "onboarding_id": onboarding_id,
        "agent_name": "AML_RISK_AGENT", "stage": 2,
        "check_name": "volume_check",
        "input_context": {"expected_volume": expected_volume, "entity_type": entity_type, "incorporation_date": str(incorporation_date)},
        "output": result["output"],
        "flags": flags, "risk_level": risk_level,
        "recommendation": recommendation,
        "ai_summary": summary,
        "model_used": "rule-based",
        "duration_ms": duration_ms
    })
    return result


def aml_questionnaire_score(data: dict, run_id: str, onboarding_id: str) -> dict:
    """Weighted AML questionnaire scoring (0–100)."""
    start = time.time()
    score = 0
    flags = []

    # Source of Funds risk (weight 25)
    sof = data.get("source_of_funds", "")
    sof_risk = _SOF_RISK.get(sof, "MEDIUM")
    if sof_risk == "HIGH":
        score += 25
        flags.append(f"High-risk source of funds: {sof}")
    elif sof_risk == "MEDIUM":
        score += 13

    # AML program not confirmed (weight 20)
    aml_questions = data.get("aml_questions", {})
    if isinstance(aml_questions, str):
        import json
        try:
            aml_questions = json.loads(aml_questions)
        except Exception:
            aml_questions = {}
    aml_confirmed = aml_questions.get("aml_program_confirmed", "no")
    if aml_confirmed != "yes":
        score += 20
        flags.append("AML program not confirmed")
    elif not data.get("aml_program_description"):
        score += 10
        flags.append("AML program confirmed but no description provided")

    # Sanctions self-declared (weight 20)
    sanctions_exposure = aml_questions.get("sanctions_exposure", "no")
    if sanctions_exposure == "yes":
        score += 20
        flags.append("Applicant declared prior sanctions exposure")

    # PEP (weight 15)
    if data.get("pep_declaration"):
        score += 15
        flags.append("PEP declared")

    # Correspondent bank present (weight 10 if missing)
    if not data.get("correspondent_bank"):
        score += 10
        flags.append("No correspondent bank declared")

    # No adverse media consent (weight 10)
    if not data.get("adverse_media_consent"):
        score += 10
        flags.append("Adverse media consent not given")
        
    # Check for presence of settlement bank details (Industry Standard Requirement)
    bank_fields = ["bank_name", "routing_number", "account_number", "mcc_code"]
    missing_bank = [f for f in bank_fields if not data.get(f)]
    if missing_bank:
        score += 15
        flags.append(f"Missing settlement details: {', '.join(missing_bank)}")

    duration_ms = int((time.time() - start) * 1000)
    if score >= 75:
        risk_level = "CRITICAL"
        recommendation = "REJECT"
    elif score >= 50:
        risk_level = "HIGH"
        recommendation = "FLAG"
    elif score >= 25:
        risk_level = "MEDIUM"
        recommendation = "FLAG"
    else:
        risk_level = "LOW"
        recommendation = "PASS"

    summary = f"AML questionnaire score: {score}/100 → {risk_level}. Flags: {', '.join(flags) if flags else 'None'}."
    result = {
        "check_name": "aml_questionnaire_score",
        "risk_level": risk_level,
        "recommendation": recommendation,
        "flags": flags,
        "ai_summary": summary,
        "output": {"score": score, "max_score": 100}
    }
    insert_agent_log({
        "run_id": run_id, "onboarding_id": onboarding_id,
        "agent_name": "AML_RISK_AGENT", "stage": 2,
        "check_name": "aml_questionnaire_score",
        "input_context": {"source_of_funds": sof, "pep_declaration": data.get("pep_declaration")},
        "output": result["output"],
        "flags": flags, "risk_level": risk_level,
        "recommendation": recommendation,
        "ai_summary": summary,
        "model_used": "rule-based",
        "duration_ms": duration_ms
    })
    return result
