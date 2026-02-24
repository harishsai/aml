-- Fix Audit Trail UUID Syntax Error
ALTER TABLE client_onboarding.onboarding_audit_log DROP CONSTRAINT IF EXISTS onboarding_audit_log_action_by_fkey;
ALTER TABLE client_onboarding.onboarding_audit_log ALTER COLUMN action_by TYPE VARCHAR(100);
