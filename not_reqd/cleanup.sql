-- ============================================================
-- KINETIX: Test Data Cleanup Script
-- Usage: \i 'D:/learning/aml/mock_docs/cleanup.sql'
-- Safe to run repeatedly. Keeps ADMIN users + reference tables.
-- ORDER: child tables first (FK dependencies respected).
-- ============================================================

BEGIN;

-- 1. AI agent logs (child of onboarding_details)
TRUNCATE TABLE client_onboarding.ai_agent_logs RESTART IDENTITY CASCADE;

-- 2. Audit log (child of onboarding_details)
TRUNCATE TABLE client_onboarding.onboarding_audit_log RESTART IDENTITY CASCADE;

-- 3. UBOs (child of onboarding_details)
TRUNCATE TABLE client_onboarding.onboarding_ubos RESTART IDENTITY CASCADE;

-- 4. Directors (child of onboarding_details)
TRUNCATE TABLE client_onboarding.onboarding_directors RESTART IDENTITY CASCADE;

-- 5. User roles (child of users + roles; clears PARTICIPANT links)
DELETE FROM client_onboarding.user_roles
WHERE user_id IN (
    SELECT ur.user_id
    FROM client_onboarding.user_roles ur
    JOIN client_onboarding.roles r ON r.id = ur.role_id
    WHERE r.name = 'PARTICIPANT'
);

-- 6. Onboarding details (parent of audit/ubos/directors/logs)
TRUNCATE TABLE client_onboarding.onboarding_details RESTART IDENTITY CASCADE;

-- 7. Remove only PARTICIPANT users (keep ADMIN accounts intact)
DELETE FROM client_onboarding.users
WHERE id NOT IN (
    SELECT ur.user_id
    FROM client_onboarding.user_roles ur
    JOIN client_onboarding.roles r ON r.id = ur.role_id
    WHERE r.name = 'ADMIN'
);

-- Reference tables intentionally NOT touched:
--   client_onboarding.roles                  (ADMIN, PARTICIPANT)
--   client_onboarding.sanctions_list          (200 SDN records)
--   client_onboarding.entity_verification     (100 LEI records)
--   client_onboarding.country_risk_reference  (18 country risk entries)

COMMIT;

-- ---- Verification query ----
SELECT 'onboarding_details'        AS table_name, COUNT(*) AS row_count FROM client_onboarding.onboarding_details
UNION ALL
SELECT 'onboarding_ubos',                          COUNT(*) FROM client_onboarding.onboarding_ubos
UNION ALL
SELECT 'onboarding_directors',                     COUNT(*) FROM client_onboarding.onboarding_directors
UNION ALL
SELECT 'onboarding_audit_log',                     COUNT(*) FROM client_onboarding.onboarding_audit_log
UNION ALL
SELECT 'ai_agent_logs',                            COUNT(*) FROM client_onboarding.ai_agent_logs
UNION ALL
SELECT 'participant user_roles',                   COUNT(*)
    FROM client_onboarding.user_roles ur
    JOIN client_onboarding.roles r ON r.id = ur.role_id
    WHERE r.name = 'PARTICIPANT'
UNION ALL
SELECT 'participant users',                        COUNT(*)
    FROM client_onboarding.users
    WHERE id NOT IN (
        SELECT ur2.user_id FROM client_onboarding.user_roles ur2
        JOIN client_onboarding.roles r2 ON r2.id = ur2.role_id
        WHERE r2.name = 'ADMIN'
    )
ORDER BY table_name;
