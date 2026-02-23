-- ============================================================
-- AML BLUEPRINT MIGRATION — Phase 1 (v2)
-- Applies to existing DB with the original tables.sql schema
-- Run in psql: \i 'D:/learning/aml/db/aml_migration.sql'
-- ============================================================

-- ============================================================
-- PATCH 1: Drop orphaned current_step column (never written to;
-- signup navigation is handled entirely client-side in JS)
-- ============================================================
ALTER TABLE client_onboarding.onboarding_details
    DROP COLUMN IF EXISTS current_step;

-- ============================================================
-- PATCH 2: Change countries_operation from TEXT → TEXT[]
-- Wrapped in a DO block so it is safe to run multiple times:
-- if the column is already TEXT[], the conversion is skipped.
-- ============================================================
DO $$
DECLARE
    col_type TEXT;
BEGIN
    SELECT data_type INTO col_type
    FROM information_schema.columns
    WHERE table_schema = 'client_onboarding'
      AND table_name   = 'onboarding_details'
      AND column_name  = 'countries_operation';

    IF col_type = 'ARRAY' THEN
        RAISE NOTICE 'PATCH 2: countries_operation is already TEXT[] — skipping conversion.';
    ELSE
        ALTER TABLE client_onboarding.onboarding_details
            ALTER COLUMN countries_operation
            TYPE TEXT[]
            USING CASE
                WHEN countries_operation IS NULL OR trim(countries_operation::TEXT) = '' THEN NULL
                ELSE string_to_array(trim(countries_operation::TEXT), ',')
            END;
        RAISE NOTICE 'PATCH 2: countries_operation converted to TEXT[].';
    END IF;
END $$;

-- GIN index for fast ANY() country checks by the AML agent
CREATE INDEX IF NOT EXISTS idx_countries_op
    ON client_onboarding.onboarding_details USING GIN(countries_operation);

-- ============================================================
-- PATCH 3: business_need — already exists as TEXT; add comment
-- so intent is crystal clear: this is the product / service
-- interest dropdown from Step 1 of signup, NOT a free-text field.
-- Previously was being unused because the form product value
-- was only written into aml_questions JSONB as "product_interest".
-- Now it is written to the discrete column AND kept in JSONB.
-- ============================================================
COMMENT ON COLUMN client_onboarding.onboarding_details.business_need IS
    'Primary product/service interest selected at signup Step 1 (e.g. FX Settlement, Treasury Services). Written from the product dropdown.';

-- ============================================================
-- PATCH 4: Add all new AML Blueprint columns (idempotent)
-- pep_declaration is ONLY a discrete boolean — never stored
-- inside aml_questions JSONB to avoid dual-storage confusion.
-- ============================================================
ALTER TABLE client_onboarding.onboarding_details
    ADD COLUMN IF NOT EXISTS registration_number VARCHAR(100),
    ADD COLUMN IF NOT EXISTS incorporation_date DATE,
    ADD COLUMN IF NOT EXISTS ownership_type VARCHAR(50),
    ADD COLUMN IF NOT EXISTS regulatory_status VARCHAR(50),
    ADD COLUMN IF NOT EXISTS regulatory_authority VARCHAR(100),
    ADD COLUMN IF NOT EXISTS trading_address TEXT,
    ADD COLUMN IF NOT EXISTS tax_residency_country VARCHAR(100),
    ADD COLUMN IF NOT EXISTS source_of_wealth TEXT,
    ADD COLUMN IF NOT EXISTS pep_declaration BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS adverse_media_consent BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS correspondent_bank VARCHAR(200),
    ADD COLUMN IF NOT EXISTS aml_program_description TEXT,
    ADD COLUMN IF NOT EXISTS incorporation_doc_content BYTEA,
    ADD COLUMN IF NOT EXISTS ai_risk_level VARCHAR(20);

-- Additional useful indexes
CREATE INDEX IF NOT EXISTS idx_onboarding_status
    ON client_onboarding.onboarding_details(status);
CREATE INDEX IF NOT EXISTS idx_onboarding_tracking
    ON client_onboarding.onboarding_details(tracking_id);

-- ============================================================
-- PATCH 4b: Column comments for AML fields
-- ============================================================
COMMENT ON COLUMN client_onboarding.onboarding_details.status IS
    'PENDING_REVIEW | APPROVED | REJECTED | CANCELLED | CLARIFICATION_REQUIRED | KYC_COMPLETE | AML_IN_PROGRESS | AML_COMPLETE | AML_REVIEW_READY';

COMMENT ON COLUMN client_onboarding.onboarding_details.pep_declaration IS
    'TRUE if any director or UBO declared as Politically Exposed Person. Discrete boolean — do NOT store in aml_questions JSONB.';

COMMENT ON COLUMN client_onboarding.onboarding_details.countries_operation IS
    'Array of operating country names. Use ANY() for AML country-risk scoring. GIN-indexed.';

COMMENT ON COLUMN client_onboarding.onboarding_details.ai_risk_level IS
    'AML agent output: CLEARED | FLAGGED | HIGH_RISK | CRITICAL. NULL until agent has run.';

-- ============================================================
-- PATCH 5: UBOs table
-- ============================================================
CREATE TABLE IF NOT EXISTS client_onboarding.onboarding_ubos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    onboarding_id UUID REFERENCES client_onboarding.onboarding_details(id) ON DELETE CASCADE,
    full_name VARCHAR(255) NOT NULL,
    stake_percent NUMERIC(5,2),
    nationality VARCHAR(100),
    country_of_residence VARCHAR(100),
    date_of_birth DATE,
    is_pep BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- PATCH 6: Directors table
-- ============================================================
CREATE TABLE IF NOT EXISTS client_onboarding.onboarding_directors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    onboarding_id UUID REFERENCES client_onboarding.onboarding_details(id) ON DELETE CASCADE,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(100),
    nationality VARCHAR(100),
    country_of_residence VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- PATCH 7: AML Agent logs table
-- ============================================================
CREATE TABLE IF NOT EXISTS client_onboarding.ai_agent_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL,
    onboarding_id UUID REFERENCES client_onboarding.onboarding_details(id),
    agent_name VARCHAR(50),
    stage INTEGER,
    check_name VARCHAR(100),
    input_context JSONB,
    output JSONB,
    flags TEXT[],
    risk_level VARCHAR(20),
    recommendation VARCHAR(20),
    ai_summary TEXT,
    model_used VARCHAR(50),
    duration_ms INTEGER,
    tokens_used INTEGER,
    status VARCHAR(20) DEFAULT 'COMPLETED',
    reviewed_by UUID REFERENCES client_onboarding.users(id),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    human_notes TEXT,
    human_decision VARCHAR(30),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- PATCH 8: Country risk reference table + seed data
-- ============================================================
CREATE TABLE IF NOT EXISTS client_onboarding.country_risk_reference (
    country_code CHAR(2) PRIMARY KEY,
    country_name VARCHAR(100),
    fatf_status VARCHAR(30),
    risk_level VARCHAR(10),
    last_updated DATE
);

INSERT INTO client_onboarding.country_risk_reference
    (country_code, country_name, fatf_status, risk_level, last_updated)
VALUES
    ('IR', 'Iran',              'BLACKLIST',  'CRITICAL', CURRENT_DATE),
    ('KP', 'North Korea',       'BLACKLIST',  'CRITICAL', CURRENT_DATE),
    ('SY', 'Syria',             'BLACKLIST',  'CRITICAL', CURRENT_DATE),
    ('MM', 'Myanmar',           'BLACKLIST',  'CRITICAL', CURRENT_DATE),
    ('RU', 'Russia',            'MONITORING', 'HIGH',     CURRENT_DATE),
    ('VE', 'Venezuela',         'MONITORING', 'HIGH',     CURRENT_DATE),
    ('YE', 'Yemen',             'MONITORING', 'HIGH',     CURRENT_DATE),
    ('LY', 'Libya',             'MONITORING', 'HIGH',     CURRENT_DATE),
    ('SD', 'Sudan',             'MONITORING', 'HIGH',     CURRENT_DATE),
    ('SO', 'Somalia',           'MONITORING', 'HIGH',     CURRENT_DATE),
    ('PK', 'Pakistan',          'MONITORING', 'MEDIUM',   CURRENT_DATE),
    ('NG', 'Nigeria',           'MONITORING', 'MEDIUM',   CURRENT_DATE),
    ('PH', 'Philippines',       'MONITORING', 'MEDIUM',   CURRENT_DATE),
    ('AE', 'United Arab Emirates','MONITORING','MEDIUM',  CURRENT_DATE),
    ('US', 'United States',     'COMPLIANT',  'LOW',      CURRENT_DATE),
    ('GB', 'United Kingdom',    'COMPLIANT',  'LOW',      CURRENT_DATE),
    ('SG', 'Singapore',         'COMPLIANT',  'LOW',      CURRENT_DATE),
    ('IN', 'India',             'COMPLIANT',  'LOW',      CURRENT_DATE)
ON CONFLICT (country_code) DO NOTHING;

-- ============================================================
-- PATCH 9: Table indexes
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_ubos_onboarding
    ON client_onboarding.onboarding_ubos(onboarding_id);
CREATE INDEX IF NOT EXISTS idx_directors_onboarding
    ON client_onboarding.onboarding_directors(onboarding_id);
CREATE INDEX IF NOT EXISTS idx_ai_logs_onboarding
    ON client_onboarding.ai_agent_logs(onboarding_id);
CREATE INDEX IF NOT EXISTS idx_ai_logs_run
    ON client_onboarding.ai_agent_logs(run_id);

-- ============================================================
-- VERIFY (uncomment to check after running)
-- ============================================================
-- SELECT column_name, data_type FROM information_schema.columns
--   WHERE table_schema = 'client_onboarding' AND table_name = 'onboarding_details'
--   ORDER BY ordinal_position;
--
-- SELECT table_name FROM information_schema.tables
--   WHERE table_schema = 'client_onboarding' ORDER BY table_name;
--
-- -- Check countries_operation is now TEXT[]:
-- SELECT column_name, data_type, udt_name FROM information_schema.columns
--   WHERE table_schema = 'client_onboarding'
--     AND table_name = 'onboarding_details'
--     AND column_name = 'countries_operation';
