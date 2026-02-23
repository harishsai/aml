AML Verification Blueprint — Kinetix Platform
Version: 2.0 | Date: 2026-02-20

Based on: FINRA Rule 3310, FATF Recommendations, EU AMLD, USA PATRIOT Act §326, LSEG, Dotfile, AML Network

Architecture Decision: No separate Vetting Agent. The AML Agent is the single intelligence layer. All KYB, entity identity, UBO, and document checks are part of the AML process. The signup form collects all raw data; the AML Agent processes it after submission.

Part 1: Current DB Field Audit vs AML Requirements
1a — What Is Already Collected (
onboarding_details
 table)
DB Column	Form Step	AML Purpose	Status
email
Step 1	Contact identity	✅ Present
company_name	Step 1	Entity name for sanctions match	✅ Present
company_address	Step 1	Registered address (unstructured)	⚠️ Unstructured
city	Step 1	Address part	✅ Present
state	Step 1	Address part	✅ Present
country	Step 1	Incorporation country risk	✅ Present
zip_code	Step 1	Address verification	✅ Present
phone_number	Step 1	Contact verification	✅ Present
lei_identifier	Step 1	GLEIF entity lookup	✅ Present
entity_type	Step 1	Risk classification	✅ Present
business_activity	Step 3 AML	Business activity risk	✅ Present
source_of_funds	Step 3 AML	AML risk indicator	✅ Present
expected_volume	Step 3 AML	Volume vs entity size check	✅ Present
countries_operation	Step 3 AML	Multi-country risk	✅ Present (plain text)
business_need	Step 1	Business intent	✅ Present
aml_questions	Step 3 AML	AML questionnaire (JSONB)	✅ Present
bod_list_content	Step 2	Director verification (PDF bytes)	✅ Present
financials_content	Step 2	Financial legitimacy (PDF bytes)	✅ Present
ownership_content	Step 2	UBO identification (PDF bytes)	✅ Present
1b — What Is MISSING from DB (AML Requirements)
Missing Field	AML Step	Why Critical	Storage Decision
registration_number	Step 1 CIP	Core KYB — different from LEI; validates legal existence	Aurora PostgreSQL
incorporation_date	Step 1 CIP	Flags shell companies (very young), validates entity age	Aurora PostgreSQL
ownership_type	Step 1	Public/Private/Subsidiary/Govt — drives UBO requirement logic	Aurora PostgreSQL
regulatory_status	Step 1	Is entity regulated? By which authority?	Aurora PostgreSQL
tax_residency_country	Step 3	FATCA/CRS classification	Aurora PostgreSQL
trading_address	Step 3	Address confirmation — may differ from registered address	Aurora PostgreSQL
source_of_wealth	Step 3 AML	Different from source of funds — origin of capital, not cash flows	Aurora PostgreSQL
pep_declaration	Step 3 AML	FATF R12: "Is any director/UBO a Politically Exposed Person?"	Aurora PostgreSQL
adverse_media_consent	Step 3 AML	User consent before running media checks	Aurora PostgreSQL
correspondent_bank	Step 3 AML	Bank name + jurisdiction for institutional clients	Aurora PostgreSQL
aml_program_description	Step 3 AML	Free text: describe existing AML program	Aurora PostgreSQL
UBO records	Step 4	Each UBO: name, stake %, nationality, DOB, country of residence	Aurora PostgreSQL (separate table)
Director records	Step 2	Each director: name, role, nationality, country of residence	Aurora PostgreSQL (separate table)
1c — What Is REDUNDANT / Needs Consolidation
Issue	Current State	Recommendation
countries_operation is plain text	Comma-separated string, hard to query	Change to TEXT[] array or JSON array
company_address is unstructured	Single text blob	Add registered_address_line2, trading_address structured fields
aml_questions JSONB catches everything	Sanctions + PEP + AML program all jammed into JSONB	Keep for flexibility but add discrete columns for key boolean fields (pep_declaration, aml_program_confirmed) for queryability
business_need vs business_activity	Overlapping intent	business_activity = SIC/type; business_need = free text description of why signing up
Part 2: Data Storage Strategy — Aurora PostgreSQL vs External Query
Stored in Aurora PostgreSQL (persistent, queryable)
Data Category	Table	Rationale
All onboarding form fields	
onboarding_details
Core application data
UBO records	onboarding_ubos (new)	Must be queryable per onboarding, retained 5 years
Director records	onboarding_directors (new)	Same retention requirement
OFAC / UN / EU sanctions list	sanctions_list (exists)	Snapshot loaded periodically, fast local query
Entity verification reference	entity_verification (exists)	LEI + entity data for local fuzzy matching
AML agent run logs	ai_agent_logs (new)	Full audit trail per regulatory requirement
AML findings per check	aml_agent_logs (new)	Every sub-check logged with input + output
Risk score per onboarding	Inside ai_agent_logs	Composite score, per-factor breakdown
Country risk reference	country_risk_reference (new)	FATF greylist, blacklist table — static, updated quarterly
Queried from External APIs (real-time, not persisted raw)
Data	API Source	When Called	What Is Stored
LEI entity details	GLEIF API	Stage 1 AML Agent	LEI match result + entity name + status stored in ai_agent_logs
Real-time sanctions updates	OFAC SDN API / EU API	Periodic sync job (not on signup)	Delta loaded into sanctions_list table
Adverse media	NewsAPI / Google News API	Stage 2 AML Agent	AI summary + sentiment score stored in ai_agent_logs
Address geocoding / validation	Google Maps API or postcodes.io	Optional — address confirmation	Only result (match/no-match) stored
Documents (Binary, in PostgreSQL)
Document	Column	AI Processing
Board of Directors PDF	bod_list_content BYTEA	OCR → extract director names
Financials PDF	financials_content BYTEA	OCR → extract AUM, revenue, auditor name
Ownership Structure PDF	ownership_content BYTEA	OCR → extract UBO names + stakes
Certificate of Incorporation	incorporation_doc_content BYTEA (new)	OCR → extract reg number, entity name, date
Part 3: New UI Fields Required — Step by Step
Step 1: Entity Information (Add to existing)
New Field	Type	Validation	Required
registration_number	Text	Non-empty, format check by country	✅ Yes
incorporation_date	Date	Cannot be in future; flag if < 1 year old	✅ Yes
ownership_type	Dropdown	Public / Private / Subsidiary / Government / Other	✅ Yes
regulatory_status	Dropdown	Regulated (specify authority) / Unregulated	✅ Yes
regulatory_authority	Text	Show if regulated selected	Conditional
website	URL	Valid URL format	Optional
Step 2: Documents (Add to existing 3 uploads)
New Upload	Doc Type	Required
Certificate of Incorporation	PDF/image	✅ Yes
Proof of Registered Address	PDF/image	✅ Yes
Director ID documents	PDF/image per director	Conditional (if Private)
UBO ID documents	PDF/image per UBO	Conditional (if Private + UBO declared)
Step 2b: UBO Declaration (New section — shown if ownership_type ≠ Public)
Repeatable section (add up to 5 UBOs):

Field	Type	Validation
ubo_full_name	Text	Required
ubo_stake_percent	Number	0–100, all UBOs must total ≤ 100%
ubo_nationality	Country dropdown	Required
ubo_country_of_residence	Country dropdown	Required
ubo_date_of_birth	Date	Required; must be adult (>18)
ubo_is_pep	Boolean	Required — "Is this person a Politically Exposed Person?"
Step 2c: Director Declaration (New section)
Repeatable section (add up to 10 directors):

Field	Type	Validation
director_full_name	Text	Required; at least 1 director
director_role	Dropdown	CEO / CFO / COO / Chairman / Director / Other
director_nationality	Country dropdown	Required
director_country_of_residence	Country dropdown	Required
Step 3: AML Questionnaire (Expand existing)
Field	Current?	Change
Registration Number	❌	Already added to Step 1 — remove from AML step (was redundant here)
Ownership Type	❌	Already added to Step 1 — remove from AML step
Primary Business Activity	✅	Keep
Source of Funds	✅	Keep
Source of Wealth	❌	Add: "How was the initial capital of this entity acquired?" (free text)
Expected Monthly Volume	✅	Keep
Main Countries of Operation	✅	Keep — change to multi-select dropdown
Sanctions Exposure	✅	Keep
Confirm AML Program	✅	Keep
AML Program Description	❌	Add: "Briefly describe your AML program" (textarea)
PEP Declaration	❌	Add: "Is any director or UBO a Politically Exposed Person?" (Yes/No)
Trading Address	❌	Add: "Is your trading address different from registered?" — if Yes, show address fields
Tax Residency Country	❌	Add: Multi-select country dropdown
Correspondent Bank	❌	Add: Bank name + country (for institutional clients)
Adverse Media Consent	❌	Add: Checkbox "I consent to adverse media screening"
Note: Registration Number and Ownership Type previously appeared in the AML step — these were redundant since they are entity identity fields that belong in Step 1. Moving them to Step 1 cleans up the AML questionnaire.

Part 4: Field-Level Validation Rules
Field	Rule	Type	Action on Failure
lei_identifier	Exactly 20 alphanumeric characters	Hard	Block submit
lei_identifier	Checksum validation (ISO 17442)	Hard	Block submit
lei_identifier	No duplicate in DB	Hard	Block submit
email
Valid email format	Hard	Block submit
email
Not a public domain (@gmail, @yahoo, @hotmail)	Warning	Require acknowledgement
email
No duplicate in DB	Hard	Block submit
phone_number	E.164 format	Hard	Block submit
registration_number	Non-empty	Hard	Block submit
incorporation_date	Not in future	Hard	Block submit
incorporation_date	If < 1 year old → flag	Warning	Flag in AI agent log
ownership_type	Required selection	Hard	Block submit
ubo_stake_percent	0 ≤ value ≤ 100	Hard	Block submit
All UBO stakes combined	Sum ≤ 100%	Hard	Block submit
UBO section	At least 1 UBO if ownership_type = Private	Hard	Block submit
Director section	At least 1 director required	Hard	Block submit
Document uploads	File type = PDF, JPG, PNG only; max 10MB	Hard	Block submit
Document expiry	Uploaded ID docs must not be expired	Warning	Flag in AI agent log
countries_operation	At least 1 country selected	Hard	Block submit
countries_operation	If includes FATF greylist country → EDD trigger	Warning	Flag for EDD review
pep_declaration	Required Yes/No	Hard	Block submit
adverse_media_consent	Must be checked	Hard	Block submit
expected_volume	Required selection	Hard	Block submit
expected_volume vs entity_type	High volume + startup entity → flag	Warning	Flag in AI agent log
Part 5: AML Agent — Full Architecture & Flow
End-to-End Flow
PARTICIPANT SUBMITS SIGNUP FORM
         │
         ▼
POST /signup → save_onboarding_details()
         │
         ├─ Creates user account (temp password)
         ├─ Saves onboarding record (status: PENDING_REVIEW)
         ├─ Sends confirmation email (tracking ID + temp password)
         └─ Enqueues: background_task → run_aml_orchestrator(onboarding_id)
         │
         ▼
OrchestratorAgent.run(onboarding_id)
         │
         ├── Loads full onboarding record from DB
         ├── Creates run_id (UUID groups all logs for this run)
         │
         ├── [STAGE 1] AMLAgent.identity_and_sanctions()
         │       │
         │       ├── lei_verification()
         │       │     Input:  lei_identifier, company_name
         │       │     Action: Query GLEIF API → compare entity name
         │       │     Output: {lei_valid, name_match_score, lei_status}
         │       │     Tech:   External API + fuzzy string match
         │       │
         │       ├── entity_name_sanctions_check()
         │       │     Input:  company_name
         │       │     Action: Fuzzy match vs sanctions_list table
         │       │     Output: {hit: bool, matched_name, program, confidence}
         │       │     Tech:   PostgreSQL + python-Levenshtein / rapidfuzz
         │       │
         │       ├── ubo_sanctions_check()
         │       │     Input:  ubos[].full_name for each UBO
         │       │     Action: Same fuzzy match for every declared UBO
         │       │     Output: [{ubo_name, hit, matched_name, confidence}]
         │       │     Tech:   Same as above, looped
         │       │
         │       ├── pep_check()
         │       │     Input:  pep_declaration, ubos[].is_pep, directors names
         │       │     Action: Check self-declared PEP + cross-reference flag list
         │       │     Output: {pep_flagged: bool, flagged_persons: []}
         │       │     Tech:   Rules + local PEP reference table (future: external API)
         │       │
         │       ├── email_domain_check()
         │       │     Input:  email
         │       │     Action: Check domain against public provider blocklist
         │       │     Output: {is_institutional: bool, domain}
         │       │     Tech:   Rules (hardcoded blocklist)
         │       │
         │       └── registration_format_check()
         │             Input:  registration_number, country
         │             Action: Validate format by country regex rules
         │             Output: {valid: bool}
         │             Tech:   Rules engine
         │
         │       → Writes 6 rows to ai_agent_logs (one per sub-check)
         │       → Sets stage_1_risk: LOW / MEDIUM / HIGH / CRITICAL
         │       → STATUS UPDATE: AML_STAGE1_COMPLETE
         │
         │       ⏸ HUMAN GATE 1 — Admin reviews Stage 1
         │       Admin sees: entity match result, any sanctions hits, PEP flags
         │       Admin action: CONTINUE | CLARIFICATION_REQUIRED | REJECT
         │
         ├── [STAGE 2] AMLAgent.risk_profiling()  ← only if admin chose CONTINUE
         │       │
         │       ├── country_risk_score()
         │       │     Input:  country, countries_operation[], tax_residency_country
         │       │     Action: Check each against FATF greylist/blacklist table
         │       │     Output: {countries: [{name, risk_level}], highest_risk}
         │       │     Tech:   Aurora PostgreSQL country_risk_reference table
         │       │
         │       ├── ubo_jurisdiction_risk()
         │       │     Input:  ubos[].country_of_residence
         │       │     Action: Flag offshore/sanctioned/high-risk UBO domiciles
         │       │     Output: {flagged_ubos: [], risk_level}
         │       │     Tech:   Rules + country_risk_reference table
         │       │
         │       ├── aml_questionnaire_score()
         │       │     Input:  source_of_funds, aml_program_confirmed, source_of_wealth
         │       │     Action: Rule-based score on answers (0-100)
         │       │     Output: {score: int, flags: []}
         │       │     Tech:   Rules engine (weighted rules)
         │       │
         │       ├── source_of_funds_classification()
         │       │     Input:  source_of_funds (dropdown value)
         │       │     Action: Classify risk of SOF: Investment Returns=LOW, Cash=HIGH
         │       │     Output: {sof_risk: LOW/MED/HIGH}
         │       │     Tech:   Rules with hardcoded risk map
         │       │
         │       └── volume_vs_entity_check()
         │             Input:  expected_volume, entity_type, incorporation_date
         │             Action: Flag if volume is disproportionate to entity size/age
         │             Output: {flagged: bool, reason}
         │             Tech:   Rules engine
         │
         │       → Writes 5 rows to ai_agent_logs
         │       → Sets stage_2_risk: LOW / MEDIUM / HIGH
         │       → STATUS UPDATE: AML_STAGE2_COMPLETE
         │
         │       ⏸ HUMAN GATE 2 — Admin reviews Stage 2
         │       Admin sees: country risk breakdown, AML score, volume flags
         │       Admin action: CONTINUE | CLARIFICATION_REQUIRED | REJECT
         │
         ├── [STAGE 3] DocumentAgent.ocr_and_verify()  ← Phase 2, only if CONTINUE
         │       │
         │       ├── ocr_extract(bod_list_content)
         │       │     Input:  PDF bytes
         │       │     Action: Extract director names from BOD list PDF
         │       │     Output: {directors_found: [names], confidence}
         │       │     Tech:   AWS Textract / Google Vision OCR
         │       │
         │       ├── ocr_extract(ownership_content)
         │       │     Input:  PDF bytes
         │       │     Action: Extract UBO names + percentage stakes
         │       │     Output: {ubos_found: [{name, stake}], confidence}
         │       │     Tech:   OCR + regex for percentage extraction
         │       │
         │       ├── ocr_extract(financials_content)
         │       │     Input:  PDF bytes
         │       │     Action: Extract AUM, revenue, auditor name
         │       │     Output: {aum, revenue, auditor, audit_opinion}
         │       │     Tech:   OCR + LLM key-value extraction
         │       │
         │       ├── cross_check_consistency()
         │       │     Input:  OCR results vs declared form values
         │       │     Action: Compare director names, UBO names/stakes, AUM vs expected volume
         │       │     Output: {mismatches: [], consistency_score: 0-100}
         │       │     Tech:   LLM (Gemini / GPT-4o) with structured comparison prompt
         │       │
         │       └── adverse_media_check()   ← conditional on consent
         │             Input:  company_name, UBO names
         │             Action: Query NewsAPI → LLM summarizes findings, scores sentiment
         │             Output: {adverse_found: bool, summary, articles_reviewed}
         │             Tech:   NewsAPI (external) + LLM + RAG
         │
         │       → Writes 5 rows to ai_agent_logs
         │       → Sets stage_3_risk: LOW / MEDIUM / HIGH
         │       → STATUS UPDATE: AML_STAGE3_COMPLETE
         │
         │       ⏸ HUMAN GATE 3 — Admin reviews Stage 3
         │       Admin sees: document consistency, red flags, adverse media summary
         │       Admin FINAL ACTION: APPROVE | REJECT | CLARIFICATION_REQUIRED | CANCEL
         │
         └── [FINAL] OrchestratorAgent.compile_report()
                 │
                 ├── composite_risk_score()   → weighted average across all stages
                 ├── generate_narrative()     → LLM writes plain-English summary
                 ├── write final row to ai_agent_logs (type: FINAL_REPORT)
                 └── status → AML_REVIEW_READY (admin dashboard notified)
Part 6: Risk Scoring Model
Composite Score Weights
Factor	Weight	Low (0)	Medium (50)	High (100)
Sanctions hit — entity	35%	No match	Indirect/partial	Direct hit
Sanctions hit — any UBO	15%	No match	Indirect	Direct hit
Country risk (highest)	20%	FATF compliant	FATF monitoring	FATF blacklist
UBO jurisdiction	10%	Major economy	Offshore centre	Sanctioned state
PEP flag	10%	No PEP	Self-declared (no hit)	PEP + verified
Source of funds risk	5%	Investment returns	Mixed	Cash/undisclosed
AML program	5%	Declared + described	Declared only	Not declared
Final Classification:

0–25 → 🟢 LOW — Standard Due Diligence
26–50 → 🟡 MEDIUM — Enhanced monitoring
51–75 → 🔴 HIGH — Enhanced Due Diligence (EDD) required
76–100 → ⛔ CRITICAL — Auto-escalate, likely reject
Part 7: New DB Tables Required
New Table: onboarding_ubos
sql
CREATE TABLE client_onboarding.onboarding_ubos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    onboarding_id UUID REFERENCES client_onboarding.onboarding_details(id) ON DELETE CASCADE,
    full_name VARCHAR(255) NOT NULL,
    stake_percent NUMERIC(5,2),          -- e.g. 35.00
    nationality VARCHAR(100),
    country_of_residence VARCHAR(100),
    date_of_birth DATE,
    is_pep BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
New Table: onboarding_directors
sql
CREATE TABLE client_onboarding.onboarding_directors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    onboarding_id UUID REFERENCES client_onboarding.onboarding_details(id) ON DELETE CASCADE,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(100),                   -- CEO, CFO, Chairman, Director
    nationality VARCHAR(100),
    country_of_residence VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
New Table: ai_agent_logs
sql
CREATE TABLE client_onboarding.ai_agent_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL,                -- groups all checks for one signup run
    onboarding_id UUID REFERENCES client_onboarding.onboarding_details(id),
    agent_name VARCHAR(50),              -- ORCHESTRATOR | AML_AGENT | DOCUMENT_AGENT
    stage INTEGER,                       -- 1, 2, 3
    check_name VARCHAR(100),             -- e.g. 'sanctions_check', 'lei_verification'
    input_context JSONB,                 -- inputs passed to this check
    output JSONB,                        -- structured findings
    flags TEXT[],                        -- array of human-readable flags
    risk_level VARCHAR(20),              -- LOW | MEDIUM | HIGH | CRITICAL
    recommendation VARCHAR(20),          -- PASS | FLAG | REJECT
    ai_summary TEXT,                     -- plain English explanation
    model_used VARCHAR(50),              -- rule-based | gemini-pro | gpt-4o | ocr
    duration_ms INTEGER,
    tokens_used INTEGER,
    status VARCHAR(20) DEFAULT 'COMPLETED',
    -- Human review tracking
    reviewed_by UUID REFERENCES client_onboarding.users(id),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    human_notes TEXT,
    human_decision VARCHAR(30),          -- ACCEPTED | OVERRIDDEN | ESCALATED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
New Table: country_risk_reference
sql
CREATE TABLE client_onboarding.country_risk_reference (
    country_code CHAR(2) PRIMARY KEY,    -- ISO 3166-1 alpha-2
    country_name VARCHAR(100),
    fatf_status VARCHAR(30),             -- COMPLIANT | MONITORING | BLACKLIST
    risk_level VARCHAR(10),              -- LOW | MEDIUM | HIGH | CRITICAL
    last_updated DATE
);
Additions to 
onboarding_details
sql
ALTER TABLE client_onboarding.onboarding_details
    ADD COLUMN registration_number VARCHAR(100),
    ADD COLUMN incorporation_date DATE,
    ADD COLUMN ownership_type VARCHAR(50),         -- Public | Private | Subsidiary | Government
    ADD COLUMN regulatory_status VARCHAR(50),
    ADD COLUMN regulatory_authority VARCHAR(100),
    ADD COLUMN trading_address TEXT,
    ADD COLUMN tax_residency_country VARCHAR(100),
    ADD COLUMN source_of_wealth TEXT,
    ADD COLUMN pep_declaration BOOLEAN,
    ADD COLUMN adverse_media_consent BOOLEAN DEFAULT FALSE,
    ADD COLUMN correspondent_bank VARCHAR(200),
    ADD COLUMN aml_program_description TEXT,
    ADD COLUMN incorporation_doc_content BYTEA;
Part 8: AI Technology Stack Per Step
AML Step	Check	Technology	Phase
1: CIP	Format validation	Rules Engine (Python)	Phase 1
1: CIP	Duplicate LEI/email	PostgreSQL query	Phase 1
2: KYB	LEI lookup	GLEIF REST API	Phase 1
2: KYB	Entity name match	rapidfuzz (Levenshtein)	Phase 1
2: KYB	Reg doc extraction	OCR (Tesseract/Textract)	Phase 2
3: Address	Address match	Rules + fuzzy	Phase 2
4: UBO	Ownership doc OCR	OCR + regex	Phase 2
4: UBO	UBO stake validation	Rules engine	Phase 1
5: Sanctions	Entity name screening	rapidfuzz (local DB)	Phase 1
5: Sanctions	UBO name screening	rapidfuzz (local DB)	Phase 1
5: PEP	PEP check	Rules + reference table	Phase 1
5: Adverse Media	News search + scoring	NewsAPI + LLM (RAG)	Phase 2
6: Risk Score	Weighted scoring	Rules engine	Phase 1
6: Risk Score	Narrative generation	LLM (Gemini Pro)	Phase 2
6: Consistency	Document vs form	LLM comparison prompt	Phase 2
7: Monitoring	Re-screening	Scheduler + rules	Phase 3
7: Monitoring	Anomaly detection	ML model	Phase 3
Part 9: Phased Implementation Plan
Phase 1 — Rules Engine (No LLM / No OCR)
 Add missing fields to 
onboarding_details
 (ALTER TABLE)
 Create onboarding_ubos, onboarding_directors, ai_agent_logs, country_risk_reference tables
 Update signup form: Step 1 fields, UBO section, Director section
 Update Step 3 AML Questionnaire: add PEP, source of wealth, trading address, correspondent bank
 Implement AMLAgent Stage 1: LEI (GLEIF API), sanctions fuzzy match, PEP, email domain
 Implement AMLAgent Stage 2: country risk, UBO jurisdiction, AML score, volume check
 Implement OrchestratorAgent: coordinate stages, write ai_agent_logs, set status
 Admin dashboard: Stage-by-stage findings panel with CONTINUE/REJECT/CLARIFY buttons
Phase 2 — LLM + OCR Layer
 LLM narrative generation (Gemini Pro) — final risk summary for admin
 OCR extraction from BOD, Ownership, Financials PDFs
 Adverse media check (NewsAPI + LLM RAG summarization)
 Document consistency cross-check (OCR vs form values)
 Certificate of Incorporation upload + OCR
Phase 3 — Ongoing Monitoring
 Sanctions list sync scheduler (weekly OFAC/EU pull)
 Re-screening trigger on UBO/director changes
 Transaction volume anomaly detection (ML)
Part 10: Regulatory Compliance Checklist
Requirement	Regulation	Phase 1	Phase 2
CIP — entity identity collection	FINRA 3310 / PATRIOT Act	✅	—
Document-based KYB	FATF R10	❌ → Add	✅ OCR
UBO identification ≥ 25%	FATF R24 / FinCEN	❌ → Add	—
Director identification	FINRA CIP	❌ → Add	—
Sanctions screening (OFAC, UN, EU)	All regulators	✅ (local DB)	✅ API sync
PEP screening	FATF R12	❌ → Add	✅
Country risk assessment	FATF R1	✅	—
Source of funds + wealth	FATF R10	❌ → Add	—
Adverse media check	Best practice	—	✅
Risk classification (LOW/MED/HIGH)	FATF R1	✅	—
EDD for high-risk	FATF R19	⚠️ Flagged only	✅
Full audit trail	All regulators	✅ ai_agent_logs	—
5-year record retention	FINRA CIP	⚠️ DB exists, policy needed	—
GDPR consent for media screening	EU GDPR	❌ → Add consent field	—

Comment
Ctrl+Alt+M
