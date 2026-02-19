# Product Requirements Document (PRD)

**Product:** Agentic AI-Assisted Client Onboarding (Framework-agnostic)  
**Audience:** Product + Engineering (Kira / Amazon Q Developer input)  
**Version:** 0.1 (Draft)  
**Date:** 2026-02-18  

---

## 1. Summary
Client onboarding in fintech is a long-running, multi-stakeholder workflow that is slow and expensive due to manual document collection/validation, complex regulatory compliance (KYC/AML/tax), limited real-time visibility, heavy human dependency, and siloed systems (e.g. CRM/BPM).  

This product introduces a **stage-gated onboarding platform with Agentic AI as a decision-support layer** to accelerate onboarding, reduce rework, and provide end-to-end transparency—without replacing accountable human approvals.

---

## 2. Problem Statement (What we're solving)

### 2.1 Current pain
1. **Manual document collection and validation** increases cycle time and error rate.
2. **Complex regulatory compliance** workflows (KYC, AML, tax) require repeatable evidence handling and escalation.
3. **High effort at early milestones** causes frequent stalls and rework later.
4. **Limited real-time visibility** into progress and blockers drives excessive follow-ups.
5. **High human dependency and scalability limits** make throughput proportional to headcount.
6. **Siloed systems and multiple platforms** fragment state and audit trails.

### 2.2 Desired outcome
- Reduce onboarding turnaround time while **improving consistency and auditability**.
- Provide a single, real-time view of onboarding state.
- Automate repetitive work while ensuring **rule-based gating** and **human-in-loop approvals** for regulated decisions.

---

## 3. Goals / Non-Goals

### 3.1 Goals
- **Speed:** Reduce cycle time by minimizing manual back-and-forth and automating validation and summarization.
- **Quality:** Increase completeness and reduce rework via deterministic validation and consistency checks.
- **Transparency:** Real-time stage status, blockers, and SLA timers.
- **Compliance:** End-to-end evidence and audit logs.
- **Scalability:** Route only exceptions to humans.

### 3.2 Non-Goals
- Fully autonomous onboarding without human approvals.
- Replacing compliance/legal/risk ownership.
- Encoding all policies directly inside the UI.

---

## 4. Users & Personas
1. **Client User (External):** submits data/documents; responds to requests for information.
2. **Client Onboarding Ops (Internal):** coordinates onboarding; monitors progress; ensures completion.
3. **Compliance (KYC/AML/Tax):** reviews escalations and high-risk cases; signs off.
4. **Risk & Legal:** performs/approves risk and contract decisions.
5. **Technology / Ops Enablement:** provisions connectivity, entitlements, data delivery; validates conformance.

---

## 5. End-to-End Workflow (Stage-Gated State Machine)
Onboarding proceeds in four stages (each with entry/exit criteria and artifacts):
1. **Vetting** (Needs assessment; Go/No-Go/Clarify)
2. **Application** (Evidence-based KYC/AML/Tax + Risk/Legal review)
3. **Operational Readiness** (Setup, connectivity, data delivery, conformance testing)
4. **Activation** (Training, final sign-offs, stage→prod, go-live)

### 5.1 Design principle
- **Vetting is a cheap decision gate** (qualify + scope) before expensive checks.
- Later stages are progressively more expensive and must be more deterministic and auditable.

---

## 6. Agentic AI Strategy (No frameworks; system behavior)

### 6.1 Core rule
- **Rules decide "must/shall."** (hard gates: required fields/docs, thresholds, dependencies)
- **AI decides "sufficiency/consistency."** (interpret docs, detect mismatches, summarize evidence, draft messages)

### 6.2 Agent roles (decision support)
Agents are defined by the **decisions they support**, not the tasks they perform.

- **Vetting Decision Assistant:**
  - Determines completeness for vetting; identifies missing info.
  - Suggests onboarding path/template based on client intent.
  - Outputs Go/No-Go/Clarify recommendation with rationale.

- **Compliance Evidence Assistant (Application):**
  - Classifies documents, extracts key fields, compares with declared data.
  - Flags sanctions/PEP and high-risk indicators for human review.
  - Produces an "evidence packet" for reviewer.

- **Risk & Legal Review Assistant:**
  - Summarizes risk signals (credit/cyber) and contract deltas.
  - Prepares approval packet; suggests next actions.

- **Operational Readiness Assistant:**
  - Validates configuration completeness (connectivity, entitlements, data feeds).
  - Summarizes test results; identifies blockers.

- **Activation Readiness Assistant:**
  - Verifies prerequisites across stages; compiles final go-live checklist.

### 6.3 Standard agent output contract
All assistants return a constrained, auditable response:

```json
{
  "decision": "PROCEED | REQUEST_INFO | ESCALATE | BLOCK",
  "missing_items": ["..."],
  "risk_flags": [{"type": "...", "severity": "low|med|high", "evidence": "doc_ref"}],
  "evidence_refs": ["doc_ref_1", "check_ref_2"],
  "summary": "short human-readable rationale",
  "next_actions": ["..."],
  "confidence": 0.0
}
```

### 6.4 Human-in-the-loop (first-class)
(Ensure manual intervention points are clearly defined for each regulated decision.)

---

## 7. Functional Operations

### 7.5 Exception Handling
- Generate "Request Info" tasks with client-ready messages.
- Escalation queues for compliance/risk/legal/ops.
- Evidence packets for reviewers:
  - Trigger reason
  - Extracted fields
  - Declared vs extracted diff
  - Relevant document links

### 7.6 Notifications
- Notify client/internal users on:
  - Missing info
  - Stage completed
  - Escalations assigned
  - SLA breaches

---

## 8. UI Requirements (Screens)

1. **Onboarding Dashboard**
   - Stage progress bar, SLA timers, blockers, next actions
2. **Stage Form Screen**
   - Structured sections, validation messages, submit gating
3. **Document Center**
   - Upload, classification, extraction preview, expiry warnings
4. **Checks & Evidence**
   - Rule outcomes + AI findings + evidence links
5. **Approvals & Queues**
   - Review UI with evidence packet; approve/reject + reason
6. **Audit Timeline**
   - Immutable event history

---

## 9. Data Model (Minimum)
- **ClientEntity** (entity master)
- **OnboardingCase** (workflow instance)
- **StageInstance** (state per stage)
- **Task** (review/approval/request-info/provisioning)
- **Document** (file ref + metadata + extracted_fields)
- **CheckResult** (rule evaluation outcomes)
- **DecisionRecord** (agent/human decisions)
- **AuditEvent** (append-only log)

---

## 10. Validation Strategy (How requirements stay maintainable)

### 10.1 Policy as configuration
Policies must be versioned and editable without redeploying UI.

**Policy types:**
- Required Field Rules
- Required Document Rules
- Dependency Rules
- Threshold Rules (route to human)

### 10.2 Example rules (illustrative)
- If `stage=Application` and `entity_type=Private` -> require UBO list >= 1
- If `connectivity=SFTP` -> require host/port/folder + PGP key
- If any uploaded doc expired -> BLOCK stage completion
- If `country` in high-risk list -> add Enhanced Due Diligence checklist + ESCALATE

---

## 11. Non-Functional Requirements
- **Security:** encryption at rest/in transit; least privilege; data residency controls.
- **Auditability:** immutable logs; policy version attached to decisions; evidence retention.
- **Reliability:** resumable workflows; idempotent stage transitions.
- **Performance:** responsive UI; async processing for OCR/extraction.
- **Explainability:** show "why blocked/why escalated" with evidence.

---

## 12. Risks & Mitigations
- **LLM hallucination:** deterministic rules for gates; constrained outputs; human review for high-risk.
- **Data privacy:** PII controls; access segregation; redact in prompts when possible.
- **Policy drift:** versioned policies; regression tests on rule sets.
- **Integration complexity:** keep integrations behind adapters; avoid coupling policies to systems.

---

## 13. MVP Scope

### Must-have
- Stage-gated case state machine
- Document upload + classification + extraction preview
- Deterministic validations + checks screen
- Request-info and escalation queues
- Audit timeline

### Nice-to-have
- SLA analytics dashboard
- Auto-generated client communication templates
- Reviewer diff view (declared vs extracted)

---

*Include milestones, open questions, and glossary.*
*Structure as a formal PRD with numbered sections, clear goals/non-goals, user personas, and implementation considerations.*
