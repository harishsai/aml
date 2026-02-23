-- ============================================================
-- KINETIX: DB Cleanup & Status Migration Script
-- Usage: \i 'D:/learning/aml/db/cleanup.sql'
-- Safe to run repeatedly. Keeps ADMIN users + reference tables.
-- ORDER: child tables first (FK dependencies respected).
-- ============================================================


-- ============================================================
-- SECTION A: Status value migration (runs automatically)
-- Migrates stale old-style names to the new semantic names.
-- Safe to run multiple times (no-op if already updated).
-- ============================================================

UPDATE client_onboarding.onboarding_details
SET status = 'KYC_COMPLETE', updated_at = CURRENT_TIMESTAMP
WHERE status = 'AML_STAGE1_COMPLETE';

UPDATE client_onboarding.onboarding_details
SET status = 'AML_IN_PROGRESS', updated_at = CURRENT_TIMESTAMP
WHERE status = 'AML_STAGE2_IN_PROGRESS';

UPDATE client_onboarding.onboarding_details
SET status = 'AML_COMPLETE', updated_at = CURRENT_TIMESTAMP
WHERE status = 'AML_STAGE2_COMPLETE';

-- Fix same stale names in audit log history
UPDATE client_onboarding.onboarding_audit_log
SET old_status = REPLACE(REPLACE(REPLACE(old_status,
    'AML_STAGE1_COMPLETE',   'KYC_COMPLETE'),
    'AML_STAGE2_IN_PROGRESS','AML_IN_PROGRESS'),
    'AML_STAGE2_COMPLETE',   'AML_COMPLETE')
WHERE old_status IN ('AML_STAGE1_COMPLETE','AML_STAGE2_IN_PROGRESS','AML_STAGE2_COMPLETE');

UPDATE client_onboarding.onboarding_audit_log
SET new_status = REPLACE(REPLACE(REPLACE(new_status,
    'AML_STAGE1_COMPLETE',   'KYC_COMPLETE'),
    'AML_STAGE2_IN_PROGRESS','AML_IN_PROGRESS'),
    'AML_STAGE2_COMPLETE',   'AML_COMPLETE')
WHERE new_status IN ('AML_STAGE1_COMPLETE','AML_STAGE2_IN_PROGRESS','AML_STAGE2_COMPLETE');

-- Update column comment
COMMENT ON COLUMN client_onboarding.onboarding_details.status IS
    'PENDING_REVIEW | APPROVED | REJECTED | CANCELLED | CLARIFICATION_REQUIRED | KYC_COMPLETE | AML_IN_PROGRESS | AML_COMPLETE | AML_REVIEW_READY';

DO $$ BEGIN RAISE NOTICE 'SECTION A complete: Status values migrated.'; END $$;


-- ============================================================
-- SECTION B: Full test data reset (DEV / DEMO use)
-- Wipes all onboarding data and participant users.
-- ADMIN accounts and reference tables are preserved.
-- Un-comment this block to run a full reset.
-- ============================================================

/*
BEGIN;

-- 1. AI agent logs (child of onboarding_details)
TRUNCATE TABLE client_onboarding.ai_agent_logs RESTART IDENTITY CASCADE;

-- 2. Audit log (child of onboarding_details)
TRUNCATE TABLE client_onboarding.onboarding_audit_log RESTART IDENTITY CASCADE;

-- 3. UBOs (child of onboarding_details)
TRUNCATE TABLE client_onboarding.onboarding_ubos RESTART IDENTITY CASCADE;

-- 4. Directors (child of onboarding_details)
TRUNCATE TABLE client_onboarding.onboarding_directors RESTART IDENTITY CASCADE;

-- 5. User roles — remove PARTICIPANT links only
DELETE FROM client_onboarding.user_roles
WHERE user_id IN (
    SELECT ur.user_id
    FROM client_onboarding.user_roles ur
    JOIN client_onboarding.roles r ON r.id = ur.role_id
    WHERE r.name = 'PARTICIPANT'
);

-- 6. Onboarding details (parent; cascades handle children already TRUNCATED above)
TRUNCATE TABLE client_onboarding.onboarding_details RESTART IDENTITY CASCADE;

-- 7. Remove PARTICIPANT users only (keep ADMIN accounts)
DELETE FROM client_onboarding.users
WHERE id NOT IN (
    SELECT ur.user_id
    FROM client_onboarding.user_roles ur
    JOIN client_onboarding.roles r ON r.id = ur.role_id
    WHERE r.name = 'ADMIN'
);

-- 8. Reset tracking ID sequence
ALTER SEQUENCE client_onboarding.onboarding_tracking_seq RESTART WITH 1001;

-- 9. Cleanup sessions (optional)
TRUNCATE TABLE client_onboarding.sessions RESTART IDENTITY CASCADE;

COMMIT;

DO $$ BEGIN RAISE NOTICE 'SECTION B complete: All test data wiped. Sequence reset to 1001.'; END $$;
*/


-- ============================================================
-- SECTION C: Wipe AI agent logs only (keep onboarding records)
-- Useful to re-run agents against existing applications.
-- Un-comment this block to run.
-- ============================================================

/*
TRUNCATE TABLE client_onboarding.ai_agent_logs;

UPDATE client_onboarding.onboarding_details
SET ai_risk_level = NULL, updated_at = CURRENT_TIMESTAMP
WHERE ai_risk_level IS NOT NULL;

DO $$ BEGIN RAISE NOTICE 'SECTION C complete: Agent logs cleared, risk levels reset.'; END $$;
*/


-- ============================================================
-- Reference tables intentionally NOT touched:
--   client_onboarding.roles                  (ADMIN, PARTICIPANT)
--   client_onboarding.sanctions_list          (200 SDN records)
--   client_onboarding.entity_verification     (LEI records)
--   client_onboarding.country_risk_reference  (18 FATF entries)
-- ============================================================


-- ============================================================
-- VERIFICATION — always runs; shows current state after script
-- ============================================================
SELECT 'onboarding_details'   AS table_name, COUNT(*) AS row_count FROM client_onboarding.onboarding_details
UNION ALL
SELECT 'onboarding_ubos',                    COUNT(*) FROM client_onboarding.onboarding_ubos
UNION ALL
SELECT 'onboarding_directors',               COUNT(*) FROM client_onboarding.onboarding_directors
UNION ALL
SELECT 'onboarding_audit_log',               COUNT(*) FROM client_onboarding.onboarding_audit_log
UNION ALL
SELECT 'ai_agent_logs',                      COUNT(*) FROM client_onboarding.ai_agent_logs
UNION ALL
SELECT 'participant user_roles',             COUNT(*)
    FROM client_onboarding.user_roles ur
    JOIN client_onboarding.roles r ON r.id = ur.role_id
    WHERE r.name = 'PARTICIPANT'
UNION ALL
SELECT 'participant users',                  COUNT(*)
    FROM client_onboarding.users
    WHERE id NOT IN (
        SELECT ur2.user_id FROM client_onboarding.user_roles ur2
        JOIN client_onboarding.roles r2 ON r2.id = ur2.role_id
        WHERE r2.name = 'ADMIN'
    )
ORDER BY table_name;

-- Status distribution check:
SELECT status, COUNT(*) AS count
FROM client_onboarding.onboarding_details
GROUP BY status
ORDER BY count DESC;
