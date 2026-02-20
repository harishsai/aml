-- KINETIX PLATFORM: Aurora PostgreSQL Schema
-- Targets PostgreSQL v15+ compatibility

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
    email VARCHAR(255),
    company_name VARCHAR(255),
    company_address TEXT,
    city VARCHAR(100),
    state VARCHAR(100),
    country VARCHAR(100),
    zip_code VARCHAR(20),
    phone_number VARCHAR(50),
    lei_identifier VARCHAR(100), -- Legal Entity Identifier
    entity_type VARCHAR(50),      -- Bank, Broker-Dealer, Fund, etc.
    bod_list_content BYTEA,      -- Binary storage for Board of Directors PDF
    financials_content BYTEA,    -- Binary storage for Audited Balance Sheet PDF
    ownership_content BYTEA,     -- Binary storage for Ownership structure PDF
    business_activity VARCHAR(100),
    source_of_funds VARCHAR(100),
    expected_volume VARCHAR(100),
    countries_operation TEXT,
    business_need TEXT,
    -- Step 2: AML Questionnaire Data stored as JSONB for flexibility
    aml_questions JSONB,
    status VARCHAR(50) DEFAULT 'PENDING_REVIEW', -- PENDING_REVIEW, APPROVED, REJECTED, CANCELLED, CLARIFICATION_REQUIRED
    tracking_id VARCHAR(50) UNIQUE,
    current_step INTEGER DEFAULT 1,
    submitted_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. AUDIT & TRACKING
CREATE TABLE client_onboarding.onboarding_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    onboarding_id UUID REFERENCES client_onboarding.onboarding_details(id) ON DELETE CASCADE,
    old_status VARCHAR(50),
    new_status VARCHAR(50),
    action_by UUID REFERENCES client_onboarding.users(id), -- Null for system/initial submission
    action_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    workstation_info TEXT, -- User Agent or Hostname
    remarks TEXT
);

-- 4. SESSION MANAGEMENT
CREATE TABLE client_onboarding.sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES client_onboarding.users(id) ON DELETE CASCADE,
    session_token TEXT UNIQUE NOT NULL,
    user_agent TEXT,
    ip_address VARCHAR(45),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_users_email ON client_onboarding.users(email);
CREATE INDEX idx_onboarding_user_id ON client_onboarding.onboarding_details(user_id);
CREATE INDEX idx_sessions_token ON client_onboarding.sessions(session_token);
CREATE INDEX idx_sessions_expiry ON client_onboarding.sessions(expires_at);

-- ============================================================
-- SEED DATA: Roles & Default Admin Account
-- ============================================================

-- Initial Roles
INSERT INTO client_onboarding.roles (name, description) VALUES 
('ADMIN', 'Full system access and member vetting'),
('PARTICIPANT', 'Standard institution onboarding and gateway access');

-- Default Admin User
-- Email: admin@kinetix.com | Password: Kinetix$67#
INSERT INTO client_onboarding.users (email, password_hash, full_name, is_active, must_change_password)
VALUES (
    'admin@kinetix.com',
    '$2b$12$YCkJ8jhKCb6o6Pz1.RTD1uHagvqVpoexI9rUXt0E4VI97qSGitQHW',
    'Kinetix Admin',
    TRUE,
    FALSE
);

-- Link Admin to Role
INSERT INTO client_onboarding.user_roles (user_id, role_id)
SELECT u.id, r.id
FROM client_onboarding.users u, client_onboarding.roles r
WHERE u.email = 'admin@kinetix.com' AND r.name = 'ADMIN';
