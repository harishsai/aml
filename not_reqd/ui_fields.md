# UI Fields PRD — ui-fields.md

**Product**: Agentic AI-Assisted Client Onboarding UI  
**Document type**: UI Field Requirements (PRD)  
**Version**: 0.1  
**Date**: 2026-02-19  

---

## 1) Purpose
Define the **UI fields** required at each onboarding stage and the **validation logic** that governs stage submission for a fintech onboarding workflow: **Vetting → Application → Operational Readiness → Activation**.

---

## 2) Scope

### In scope
- Field inventory per stage (sections, field types, requiredness)
- Conditional requirements (if/then)
- Validation rules (format + business rules)
- Document upload "fields" (metadata requirements)

### Out of scope
- Country/product-specific policies beyond baseline examples (handled via policy configuration)
- Backend API contracts and storage schema (separate document)
- External system integrations (CRM/BPM, etc.) (separate design)

---

## 3) Global UI Requirements (applies to all stages)

### 3.1 Case header (always visible)
- **Case ID** (read-only)
- **Client Legal Name** (read-only after Vetting submit)
- **Current Stage** (read-only)
- **Stage Status** (Draft / In Review / Blocked / Complete)
- **Primary Stakeholders** (Relationship Manager, Onboarding Owner, Compliance Owner, Tech Owner)
- **SLA Timer** (read-only)
- **Blockers Summary** (read-only)

### 3.2 Standard actions
- **Save Draft**: Does not enforce hard validations.
- **Submit Stage**: Enforces hard validations.
- **Request Info**: Creates a structured "missing items" request.
- **Escalate**: Routes to internal queue with evidence.

### 3.3 Validation behavior
- **Hard errors**: Block stage submission.
- **Warnings**: Allow submission but require acknowledgement (tracked).
- **Waivers**: Allow bypass of specific hard errors only with role-based approval (tracked).

### 3.4 Document upload standard metadata (all stages)
Every uploaded document must capture (or infer) the following metadata:
- **Document Type** (dropdown)
- **Associated Party** (Entity / Director / Signatory / UBO / Other)
- **Issuer Country** (optional)
- **Issue Date** (optional)
- **Expiry Date** (required for time-bound IDs/certs)
- **Document Reference / ID** (optional)
- **Version / Upload timestamp** (auto)
- **Classification Confidence** (read-only if AI provides)
- **Extraction Preview** (read-only + editable corrections)

---

## 4) Stage 1 — Vetting (Needs Assessment / Qualification)

**Objective**: Qualify onboarding request, define scope, and decide **Go / No-Go / Clarify** before expensive downstream checks.

### 4.1 Section A — Client identity (minimum)
**Fields (Required):**
- `client.legal_name` (string)
- `client.entity_type` (enum: Bank | Broker-Dealer | Fund | Corporate | Other)
- `client.incorporation_country` (ISO country)
- `client.operating_countries` (multi-select ISO countries)
- `client.primary_contact.name` (string)
- `client.primary_contact.email` (email)
- `client.primary_contact.phone` (string)

**Fields (Optional):**
- `client.lei` (string)
- `client.website` (url)
- `client.registered_address` (structured)

### 4.2 Section B — Business intent & scope
**Fields (Required):**
- `scope.products_requested` (multi-select)
- `scope.onboarding_type` (enum: org-specific)
- `scope.target_go_live_window` (date or month)
- `scope.expected_volume_band` (enum or numeric range)
- `scope.primary_markets` (multi-select)

**Fields (Optional):**
- `scope.preferred_connectivity` (enum: API | SFTP | Portal | TBD)
- `scope.special_requirements` (free text)

### 4.3 Section C — Internal ownership / routing
**Fields (Required):**
- `owners.relationship_manager` (user)
- `owners.onboarding_owner` (user)
- `owners.business_sponsor` (team/user)

**Fields (Optional):**
- `owners.initial_risk_owner` (team/user)
- `owners.initial_legal_owner` (team/user)

### 4.4 Section D — Vetting outcome
**Fields (Required):**
- `vetting.outcome` (enum: GO | NO_GO | CLARIFY)
- `vetting.outcome_reason` (string: required if NO_GO)
- `vetting.missing_items` (list: required if CLARIFY)

### 4.5 Vetting validations

**Format validations**
- Email must be valid format
- Phone must match allowed character set and min length
- Legal name length >= 3
- If LEI present -> 20 characters, alphanumeric

**Business rule validations (hard gates on Submit Stage)**
- Must set `vetting.outcome`
- Must assign RM, onboarding owner, business sponsor
- Must set onboarding type and products requested
- If **NO_GO** -> outcome reason required
- If **CLARIFY** -> at least one missing item required

**Stage exit criteria**
- Vetting is **Complete** when all hard gates pass and outcome is set.

---

## 5) Stage 2 — Application (KYC / AML / Tax + Risk / Legal)

**Objective**: Collect evidence and complete regulated checks and reviews with auditable artifacts (KYC, AML, sanctions, tax), plus risk & legal review.

### 5.1 Section A — Entity registration details
**Fields (Required)**
- `application.registered_legal_name` (string)
- `application.registration_number` (string)
- `application.registered_address` (structured)
- `application.incorporation_country` (ISO country; default from Vetting)
- `application.incorporation_date` (date)
- `application.industry` (enum)
- `application.tax_residency_countries` (multi-select)

**Fields (Optional)**
- `application.other_identifiers` (list)
- `application.business_description` (free text)

### 5.2 Section B — Ownership & control
**Fields (Required):**
- `application.ownership_type` (enum: Public | Private | Subsidiary | Government | Other)
- `application.directors[]` (list; min 1)
- `application.signatories[]` (list; min 1)

**Conditional required:**
- `application.ubos[]` (list; min 1) **IF** `ownership_type` is Private (or non-public per policy)

**Person object fields (for directors/signatories/ubos):**
- `full_name` (string) — required
- `role` (enum) — required
- `country_of_residence` (country) — required
- `nationality` (country) — optional (policy)
- `date_of_birth` (date) — optional/conditional (policy)
- `id_document_type` (enum) — conditional (required when ID doc is required)
- `id_document_number` (string) — optional until doc is uploaded

### 5.3 Section C — Compliance declarations
**Fields (Required):**
- `compliance.sanctions_or_pep` (boolean)
- `compliance.aml_program_confirmed` (boolean)
- `compliance.fatca_classification` (enum)
- `compliance.crs_classification` (enum)
- `compliance.tax_form_type` (enum)

### 5.4 Section D — Risk inputs
**Fields (Required)**
- `risk.expected_exposure_band` (enum)
- `risk.cyber_questionnaire_status` (enum: NotStarted | InProgress | Complete)

**Fields (Optional)**
- `risk.credit_notes` (free text)
- `risk.cyber_notes` (free text)

### 5.5 Section E — Legal & contract
**Fields (Required)**
- `legal.agreement_type` (enum)
- `legal.contract_signatories[]` (list)
- `legal.data_privacy_consent` (boolean; must be true to proceed)

### 5.6 Section F — Documents (upload categories)
**Baseline required categories (policy-configurable)**
- Certificate of Incorporation / Registration proof
- Proof of Registered Address
- Board Resolution / Signing Authority proof
- ID documents for Directors/Signatories/UBOs (as required)
- Tax forms (FATCA/CRS/W-8/W-9 as applicable)
- AML policy (if required)
- Legal agreement / contract (when applicable)

### 5.7 Application validations

**Format validations**
- Incorporation date must not be in the future
- Address must include country and required locality fields
- Document file types limited to allowed list; enforce max size
- If expiry date present/required -> must be >= today

**Completeness validations (hard gates)**
- Must have >=1 director and >=1 signatory
- If ownership type requires UBOs -> UBO list must be populated
- Compliance declarations must be answered
- Required documents must be uploaded per policy
- `legal.data_privacy_consent` must be true

**Consistency validations (AI-assisted + rule-gated)**
- If extracted registered name/address differs from entered values beyond threshold ->
    - Require `application.mismatch_reason` OR
    - Escalate to Compliance/Legal queue (policy)
- If extraction confidence below threshold -> escalate for human review

**Routing rules**
- If `sanctions_or_pep=true` -> escalate to Compliance queue
- If incorporation/operating country in high-risk list -> add EDD checklist + escalate
- If exposure exceeds threshold -> escalate to Risk queue
- If cyber questionnaire not complete and policy requires completion -> block submission

**Stage exit criteria**
- Application is **Complete** when all hard gates pass or waivers are approved.

---

## 6) Stage 3 — Operational Readiness (Setup / Connectivity / Data / Testing)

**Objective**: Provision client setup and connectivity; configure data delivery; complete conformance testing and operational sign-off.

### 6.1 Section A — Client setup
**Fields (Required)**
- `ops.client_identifiers` (object; member code / external client id etc.)
- `ops.products_enabled` (multi-select; must be subset of vetted scope)
- `ops.entitlements` (multi-select)
- `ops.environments` (multi-select: UAT | Stage | Prod)

### 6.2 Section B — Connectivity
**Fields (Required)**
- `connectivity.type` (enum: API | SFTP | VPN | Other)
- `connectivity.technical_contact.name` (string)
- `connectivity.technical_contact.email` (email)

**Conditional required**
- **If API:**
    - `connectivity.api.callback_urls[]` (list)
    - `connectivity.api.auth_method` (enum: mTLS | OAuth | APIKey)
    - `connectivity.api.client_cert` (document upload)
- **If SFTP:**
    - `connectivity.sftp.host` (string)
    - `connectivity.sftp.port` (number)
    - `connectivity.sftp.folder_path` (string)
    - `connectivity.sftp.pgp_key` (document upload)
- **If VPN:**
    - `connectivity.vpn.allowed_ip_ranges[]` (list)
    - `connectivity.vpn.tunnel_params` (structured)

### 6.3 Section C — Data delivery setup
**Fields (Required)**
- `data.feeds[]` (multi-select)
- `data.delivery_schedule` (enum + optional custom)
- `data.format` (enum)
- `data.encryption_required` (boolean)

**Conditional required**
- If `encryption_required=true` -> `data.pgp_public_key` (document upload)

### 6.4 Section D — Testing & conformance
**Fields (Required)**
- `testing.test_plan_ref` (string/link)
- `testing.test_cases[]` (checklist)
- `testing.evidence_docs[]` (document uploads)
- `testing.ops_signoff.user` (user)
- `testing.ops_signoff.date` (date)

### 6.5 Operational readiness validations
**Hard gates**
- Application stage must be Complete (dependency)
- Products enabled must be subset of vetted scope
- Connectivity fields complete per selected type
- Certificates/keys not expiring within configured window (e.g., 30 days)
- Conformance tests must be marked passed OR waiver approved

**Stage exit criteria**
- Operational Readiness is **Complete** when provisioning + connectivity + testing gates pass.

---

## 7) Stage 4 — Activation (Training + Go-Live)

**Objective**: Complete training, collect final approvals, and safely transition to production go-live.

### 7.1 Section A — Training

**Fields (Required)**
- `training.modules[]` (checklist)
- `training.module_statuses[]` (enum per module)
- `training.attendees[]` (list of name/email)
- `training.evidence` (document upload or link)

### 7.2 Section B — Go-live readiness

**Fields (Required)**
- `golive.window_start` (datetime)
- `golive.window_end` (datetime)
- `golive.prod_enablement_ticket` (string)
- `approvals.ops.user` (user)
- `approvals.ops.date` (date)
- `approvals.risk.user` (user)
- `approvals.risk.date` (date)
- `approvals.legal.user` (user)
- `approvals.legal.date` (date)

**Conditional required**
- If any open exception with severity **High** -> block go-live unless waived by policy owner

### 7.3 Section C — Activation confirmation

**Fields (Required)**
- `activation.golive_completed` (boolean)
- `activation.golive_notes` (free text; required if issues occurred)

### 7.4 Activation validations

**Hard gates**
- All previous stages must be Complete (dependencies)
- All mandatory training modules must be Complete
- All required approvals must be present
- Go-live window must meet minimum lead time (policy)
- No open blockers above severity threshold

**Stage exit criteria**
- Activation is **Complete** when go-live is confirmed and all gates are satisfied.

---

## 8) Cross-Cutting Objects: Request Info & Escalations

These are UI components available in every stage.

### 8.1 Request Info

**Fields**
- `request_info.recipient` (client contact or internal contact)
- `request_info.missing_items[]` (structured list)
- `request_info.message` (free text; AI draft allowed; user editable)
- `request_info.due_date` (date)
- `request_info.status` (enum: Draft | Sent | Acknowledged | Fulfilled)

**Validations**
- Must have >=1 missing item
- Must have recipient and due date to send
