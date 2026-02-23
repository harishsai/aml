-- KINETIX PLATFORM: Security & Role Setup
-- This script should be run by the 'db_master' or superuser

-- 1. Create the specialized application role
-- IMPORTANT: Change the password to something secure!
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'clientonboarding') THEN
        CREATE ROLE clientonboarding WITH LOGIN PASSWORD 'Kinetix_Onboard_Secure!';
    END IF;
END
$$;

-- FIX: Grant the new role to the current user (db_master) 
-- This allows the master user to create a schema owned by clientonboarding
GRANT clientonboarding TO CURRENT_USER;

-- 2. Create the core schema
CREATE SCHEMA IF NOT EXISTS client_onboarding AUTHORIZATION clientonboarding;

-- 3. Grant Permissions
-- Ensure the application user can use the schema
GRANT USAGE ON SCHEMA client_onboarding TO clientonboarding;

-- Grant permissions to create and manage objects in the schema
GRANT ALL PRIVILEGES ON SCHEMA client_onboarding TO clientonboarding;

-- Ensure future tables are also owned by the application role
ALTER DEFAULT PRIVILEGES IN SCHEMA client_onboarding GRANT ALL ON TABLES TO clientonboarding;
ALTER DEFAULT PRIVILEGES IN SCHEMA client_onboarding GRANT ALL ON SEQUENCES TO clientonboarding;

-- 4. Set Search Path (Optional but helpful)
ALTER ROLE clientonboarding SET search_path TO client_onboarding, public;

COMMENT ON SCHEMA client_onboarding IS 'Kinetix Institutional KYC/AML Onboarding Schema';
