-- KINETIX PLATFORM: Aurora PostgreSQL Schema
-- Targets PostgreSQL v15+ compatibility
-- Version: 2.0 — Updated with AML Blueprint Phase 1 fields

-- Enable extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Sequence for tracking IDs
CREATE SEQUENCE IF NOT EXISTS client_onboarding.onboarding_tracking_seq START 1001;

-- 1. AUTHENTICATION & AUTHORIZATION
CREATE TABLE client_onboarding.roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE client_onboarding.permissions (
    id SERIAL PRIMARY KEY,
    code VARCHAR(100) UNIQUE NOT NULL,
    description TEXT
);

CREATE TABLE client_onboarding.role_permissions (
    role_id INTEGER REFERENCES client_onboarding.roles(id) ON DELETE CASCADE,
    permission_id INTEGER REFERENCES client_onboarding.permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE client_onboarding.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    must_change_password BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE client_onboarding.user_roles (
    user_id UUID REFERENCES client_onboarding.users(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES client_onboarding.roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- 2. ONBOARDING & CORE DATA
CREATE TABLE client_onboarding.onboarding_details (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES client_onboarding.users(id) ON DELETE CASCADE,
    tracking_id VARCHAR(50) UNIQUE,
    status VARCHAR(50) DEFAULT 'PENDING_REVIEW',
    -- Status values: PENDING_REVIEW | APPROVED | REJECTED | CANCELLED | CLARIFICATION_REQUIRED
    -- AML pipeline: KYC_COMPLETE | AML_IN_PROGRESS | AML_COMPLETE | AML_REVIEW_READY

    -- 2a: Contact
    email VARCHAR(255),
    phone_number VARCHAR(50),

    -- 2b: Entity Identity (Step 1)
    company_name VARCHAR(255),
    lei_identifier VARCHAR(100),        -- Legal Entity Identifier (GLEIF)
    entity_type VARCHAR(50),            -- Bank | Broker-Dealer | Fund | Corporate | Other
    registration_number VARCHAR(100),   -- National company registration number
    incorporation_date DATE,            -- Entity formation date; flag if < 1 year old
    ownership_type VARCHAR(50),         -- Publicly Traded | Privately Held | Government Owned | Subsidiary | Other
    regulatory_status VARCHAR(50),      -- Regulated | Unregulated
    regulatory_authority VARCHAR(100),  -- Name of regulator (if regulated)
    business_need TEXT,                 -- Primary product / service interest (Step 1 dropdown)
    dba_name VARCHAR(255),              -- Doing Business As name
    ein_number VARCHAR(50),             -- Employer Identification Number (Federal Tax ID)

    -- 2c: Registered Address (Step 1)
    company_address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    zip_code VARCHAR(20),
    trading_address TEXT,               -- Only populated when different from registered

    -- 2d: Documents (Step 2)
    bod_list_s3_uri TEXT,               -- S3 URI for Board of Directors PDF
    financials_s3_uri TEXT,             -- S3 URI for Audited financial statements
    ownership_s3_uri TEXT,              -- S3 URI for Ownership structure / UBO declaration
    incorporation_doc_s3_uri TEXT,      -- S3 URI for Certificate of Incorporation (optional)
    bank_statement_s3_uri TEXT,         -- S3 URI for Bank Statement PDF
    ein_certificate_s3_uri TEXT,        -- S3 URI for EIN Certificate PDF
    ubo_id_s3_uri TEXT,                 -- S3 URI for UBO Identification PDF

    -- Legacy support / Fallback
    bod_list_content BYTEA,
    financials_content BYTEA,
    ownership_content BYTEA,
    incorporation_doc_content BYTEA,

    -- 2e: AML Questionnaire (Step 3)
    business_activity VARCHAR(100),     -- SIC / sector classification
    source_of_funds VARCHAR(100),       -- Dropdown: Operating Revenues | Shareholder Capital | etc.
    source_of_wealth TEXT,              -- Free-text: how initial capital was acquired
    expected_volume VARCHAR(100),       -- Monthly transaction volume band
    countries_operation TEXT[],         -- Array of main operating countries (queryable)
    tax_residency_country VARCHAR(100), -- FATCA/CRS classification country
    correspondent_bank VARCHAR(200),    -- Bank name + country for institutional clients
    aml_program_description TEXT,       -- Free-text description of existing AML program
    pep_declaration BOOLEAN DEFAULT FALSE,          -- Any director/UBO is a PEP
    adverse_media_consent BOOLEAN DEFAULT FALSE,    -- Consent to adverse media screening
    routing_number VARCHAR(50),         -- Bank routing number for settlement
    account_number VARCHAR(50),         -- Bank account number for settlement
    bank_name VARCHAR(255),              -- Recipient Bank Name
    mcc_code VARCHAR(10),               -- Risk classification code

    -- 2f: AML JSONB overflow — flags and classifications not deserving discrete columns
    -- Keys: sanctions_exposure (yes|no), aml_program_confirmed (yes|no), trading_address_different (yes|no)
    aml_questions JSONB,

    -- 2g: AI agent output
    ai_risk_level VARCHAR(20),          -- CLEARED | FLAGGED | HIGH_RISK | CRITICAL (set by AML agent)

    -- Metadata
    submitted_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. UBOs & DIRECTORS (Phase 1 — required for AML)
CREATE TABLE client_onboarding.onboarding_ubos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    onboarding_id UUID REFERENCES client_onboarding.onboarding_details(id) ON DELETE CASCADE,
    full_name VARCHAR(255) NOT NULL,
    stake_percent NUMERIC(5,2),          -- e.g. 35.00; all UBOs must sum to ≤ 100%
    nationality VARCHAR(100),
    country_of_residence VARCHAR(100),
    date_of_birth DATE,
    tax_id VARCHAR(50),                  -- SSN, Passport, or National ID
    is_pep BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE client_onboarding.onboarding_directors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    onboarding_id UUID REFERENCES client_onboarding.onboarding_details(id) ON DELETE CASCADE,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(100),                   -- CEO | CFO | COO | Chairman | Director | Other
    nationality VARCHAR(100),
    country_of_residence VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. AUDIT & TRACKING
CREATE TABLE client_onboarding.onboarding_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    onboarding_id UUID REFERENCES client_onboarding.onboarding_details(id) ON DELETE CASCADE,
    old_status VARCHAR(50),
    new_status VARCHAR(50),
    action_by UUID REFERENCES client_onboarding.users(id), -- NULL for system/initial submission
    action_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    workstation_info TEXT,
    remarks TEXT
);

-- 5. AML AGENT LOGS (Phase 1 — full per-check audit trail)
CREATE TABLE client_onboarding.ai_agent_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL,                -- Groups all checks for one AML run
    onboarding_id UUID REFERENCES client_onboarding.onboarding_details(id),
    agent_name VARCHAR(50),              -- ORCHESTRATOR | AML_AGENT | DOCUMENT_AGENT
    stage INTEGER,                       -- 1=Identity & Sanctions | 2=Risk Profile | 3=Documents
    check_name VARCHAR(100),             -- sanctions_check | lei_verification | pep_check | etc.
    input_context JSONB,
    output JSONB,
    flags TEXT[],
    risk_level VARCHAR(20),              -- LOW | MEDIUM | HIGH | CRITICAL
    recommendation VARCHAR(20),          -- PASS | FLAG | REJECT
    ai_summary TEXT,
    model_used VARCHAR(50),              -- rule-based | gemini-pro | gpt-4o | ocr
    duration_ms INTEGER,
    tokens_used INTEGER,
    status VARCHAR(20) DEFAULT 'COMPLETED',
    reviewed_by UUID REFERENCES client_onboarding.users(id),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    human_notes TEXT,
    human_decision VARCHAR(30),          -- ACCEPTED | OVERRIDDEN | ESCALATED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. REFERENCE DATA
CREATE TABLE client_onboarding.country_risk_reference (
    country_code CHAR(2) PRIMARY KEY,   -- ISO 3166-1 alpha-2
    country_name VARCHAR(100),
    fatf_status VARCHAR(30),            -- COMPLIANT | MONITORING | BLACKLIST
    risk_level VARCHAR(10),             -- LOW | MEDIUM | HIGH | CRITICAL
    last_updated DATE
);

-- 7. SESSION MANAGEMENT
CREATE TABLE client_onboarding.sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES client_onboarding.users(id) ON DELETE CASCADE,
    session_token TEXT UNIQUE NOT NULL,
    user_agent TEXT,
    ip_address VARCHAR(45),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX idx_users_email ON client_onboarding.users(email);
CREATE INDEX idx_onboarding_user_id ON client_onboarding.onboarding_details(user_id);
CREATE INDEX idx_onboarding_status ON client_onboarding.onboarding_details(status);
CREATE INDEX idx_onboarding_tracking ON client_onboarding.onboarding_details(tracking_id);
CREATE INDEX idx_sessions_token ON client_onboarding.sessions(session_token);
CREATE INDEX idx_sessions_expiry ON client_onboarding.sessions(expires_at);
CREATE INDEX idx_ubos_onboarding ON client_onboarding.onboarding_ubos(onboarding_id);
CREATE INDEX idx_directors_onboarding ON client_onboarding.onboarding_directors(onboarding_id);
CREATE INDEX idx_ai_logs_onboarding ON client_onboarding.ai_agent_logs(onboarding_id);
CREATE INDEX idx_ai_logs_run ON client_onboarding.ai_agent_logs(run_id);
-- GIN index on array column for fast ANY() queries
CREATE INDEX idx_countries_op ON client_onboarding.onboarding_details USING GIN(countries_operation);

-- ============================================================
-- SEED DATA
-- ============================================================

INSERT INTO client_onboarding.roles (name, description) VALUES
('ADMIN', 'Full system access and AML case review'),
('PARTICIPANT', 'Standard institution onboarding and gateway access');

-- Default Admin | Email: admin@kinetix.com | Password: Kinetix$67#
INSERT INTO client_onboarding.users (email, password_hash, full_name, is_active, must_change_password)
VALUES (
    'admin@kinetix.com',
    '$2b$12$YCkJ8jhKCb6o6Pz1.RTD1uHagvqVpoexI9rUXt0E4VI97qSGitQHW',
    'Kinetix Admin',
    TRUE,
    FALSE
);

INSERT INTO client_onboarding.user_roles (user_id, role_id)
SELECT u.id, r.id
FROM client_onboarding.users u, client_onboarding.roles r
WHERE u.email = 'admin@kinetix.com' AND r.name = 'ADMIN';

-- FATF Country Risk Reference (initial seed)
INSERT INTO client_onboarding.country_risk_reference (country_code, country_name, fatf_status, risk_level, last_updated)
VALUES
    ('IR', 'Iran', 'BLACKLIST', 'CRITICAL', CURRENT_DATE),
    ('KP', 'North Korea', 'BLACKLIST', 'CRITICAL', CURRENT_DATE),
    ('SY', 'Syria', 'BLACKLIST', 'CRITICAL', CURRENT_DATE),
    ('MM', 'Myanmar', 'BLACKLIST', 'CRITICAL', CURRENT_DATE),
    ('RU', 'Russia', 'MONITORING', 'HIGH', CURRENT_DATE),
    ('VE', 'Venezuela', 'MONITORING', 'HIGH', CURRENT_DATE),
    ('YE', 'Yemen', 'MONITORING', 'HIGH', CURRENT_DATE),
    ('LY', 'Libya', 'MONITORING', 'HIGH', CURRENT_DATE),
    ('SD', 'Sudan', 'MONITORING', 'HIGH', CURRENT_DATE),
    ('SO', 'Somalia', 'MONITORING', 'HIGH', CURRENT_DATE),
    ('PK', 'Pakistan', 'MONITORING', 'MEDIUM', CURRENT_DATE),
    ('NG', 'Nigeria', 'MONITORING', 'MEDIUM', CURRENT_DATE),
    ('PH', 'Philippines', 'MONITORING', 'MEDIUM', CURRENT_DATE),
    ('US', 'United States', 'COMPLIANT', 'LOW', CURRENT_DATE),
    ('GB', 'United Kingdom', 'COMPLIANT', 'LOW', CURRENT_DATE),
    ('SG', 'Singapore', 'COMPLIANT', 'LOW', CURRENT_DATE),
    ('IN', 'India', 'COMPLIANT', 'LOW', CURRENT_DATE),
    ('AE', 'United Arab Emirates', 'MONITORING', 'MEDIUM', CURRENT_DATE)
ON CONFLICT (country_code) DO NOTHING;
