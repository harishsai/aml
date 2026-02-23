-- KINETIX PLATFORM: Industry Standard KYC Upgrade
-- Adds missing fields for EIN, DBA, Bank Account, and UBO Identification

ALTER TABLE client_onboarding.onboarding_details 
ADD COLUMN dba_name VARCHAR(255),
ADD COLUMN ein_number VARCHAR(50),
ADD COLUMN routing_number VARCHAR(50),
ADD COLUMN account_number VARCHAR(50),
ADD COLUMN mcc_code VARCHAR(10);

ALTER TABLE client_onboarding.onboarding_ubos
ADD COLUMN tax_id VARCHAR(50); -- SSN, Passport, or National ID

-- Log the migration in audit trail for any existing records (optional)
COMMENT ON COLUMN client_onboarding.onboarding_details.dba_name IS 'Doing Business As name';
COMMENT ON COLUMN client_onboarding.onboarding_details.ein_number IS 'Employer Identification Number (Federal Tax ID)';
COMMENT ON COLUMN client_onboarding.onboarding_details.routing_number IS 'Bank routing number for settlement';
COMMENT ON COLUMN client_onboarding.onboarding_details.account_number IS 'Bank account number for settlement';
COMMENT ON COLUMN client_onboarding.onboarding_ubos.tax_id IS 'UBO Personal identification number (SSN/Passport)';
