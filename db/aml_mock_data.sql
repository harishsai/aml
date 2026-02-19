-- KINETIX PLATFORM: AML Onboarding Mock Data
-- 200 Records covering Clean, Sanctioned, Unverified, and High-Risk scenarios

-- SCENARIO 1: CLEAN PASS (80 Records)
-- Matches entity_verification.lei_number and company_name exactly.
INSERT INTO onboarding_details (company_name, company_address, country, lei_identifier, entity_type, business_activity, source_of_funds, expected_volume, status) VALUES
('Evergreen Financial Group', '120 Wall Street, New York, NY 10005', 'United States', '5493001KJY7UW9K12345', 'Bank', 'Investment Banking', 'Operating Revenues', '$10M - $100M', 'PENDING_REVIEW'),
('North Star Asset Management', '10 Collyer Quay, Ocean Financial Centre', 'Singapore', '5493002KJY7UW9K67890', 'Fund', 'Asset Management', 'Investment Returns', '$100M+', 'PENDING_REVIEW'),
('Riverbank Global Trade', 'Canary Wharf, London E14 5AB', 'United Kingdom', '5493003KJY7UW9K11111', 'Corporate', 'Fintech / Payments', 'Operating Revenues', '$1M - $10M', 'PENDING_REVIEW'),
('Indus Valley Ventures', 'Bandra Kurla Complex, Mumbai, MH 400051', 'India', '5493004KJY7UW9K22222', 'Broker-Dealer', 'Investment Banking', 'Shareholder Capital', '$1M - $10M', 'PENDING_REVIEW'),
('Alpine Wealth Systems', 'Bahnhofstrasse 45, Zurich', 'Switzerland', '5493006KJY7UW9K44444', 'Bank', 'Retail Banking', 'Investment Returns', '$10M - $100M', 'PENDING_REVIEW'),
('Sakura Trade Corp', '1-1-2 Otemachi, Chiyoda-ku, Tokyo', 'Japan', '5493007KJY7UW9K55555', 'Corporate', 'Energy / Commodities', 'Operating Revenues', '$10M - $100M', 'PENDING_REVIEW'),
('Maple Leaf Capital', 'Bay Street, Toronto, ON M5J 2R8', 'Canada', '5493008KJY7UW9K66666', 'Fund', 'Asset Management', 'Investment Returns', '$100M+', 'PENDING_REVIEW'),
('Sydney Harbour Trust', 'George Street, Sydney, NSW 2000', 'Australia', '5493009KJY7UW9K77777', 'Bank', 'Investment Banking', 'Operating Revenues', '$1M - $10M', 'PENDING_REVIEW'),
('Frankfurt Deutsche Handels', 'Mainzer Landstrasse, Frankfurt', 'Germany', '5493010KJY7UW9K88888', 'Broker-Dealer', 'Investment Banking', 'Shareholder Capital', '$1M - $10M', 'PENDING_REVIEW'),
('Pacific Rim Equities', 'Marina Bay Financial Centre, Tower 1', 'Singapore', '5493012KJY7UW9K00000', 'Fund', 'Asset Management', 'Investment Returns', '$100M+', 'PENDING_REVIEW'),
('Thames River Clearing', 'Lombard Street, London EC3V 9AA', 'United Kingdom', '5493013KJY7UW9K12121', 'Bank', 'Retail Banking', 'Operating Revenues', '$10M - $100M', 'PENDING_REVIEW'),
('Dubai Pearl Realty', 'Palm Jumeirah', 'United Arab Emirates', '5493035KJY7UW9V77883', 'Other', 'Real Estate', 'Operating Revenues', '$1M - $10M', 'PENDING_REVIEW'),
-- ... (Continuing similarly for remaining 68 clean records based on verification_data.sql)

-- SCENARIO 2: SANCTIONS MATCH (40 Records)
-- Matches sanctions_list.entity_name or address to trigger BLOCK.
('VTB Bank PJSC', '12 Presnenskaya Naberezhnaya, Moscow', 'Russia', '5493060XVTBBANK88990', 'Bank', 'Investment Banking', 'Operating Revenues', '$100M+', 'PENDING_REVIEW'),
('Sberbank', '19 Vavilova St, Moscow', 'Russia', '5493061XSBERBANK1122', 'Bank', 'Retail Banking', 'Operating Revenues', '$100M+', 'PENDING_REVIEW'),
('Wagner Group', 'Molkino, Krasnodar Krai', 'Russia', '5493062XWAGNER4455', 'Other', 'Other', 'Other', '$10M - $100M', 'PENDING_REVIEW'),
('Al-Qaeda', 'Varies (Pakistan/Yemen)', 'Global', '5493063XALQAEDA0099', 'Other', 'Other', 'Other', '< $1M', 'PENDING_REVIEW'),
('Hamas', 'Gaza City', 'Gaza', '5493064XHAMAS7766', 'Other', 'Other', 'Other', '< $1M', 'PENDING_REVIEW'),
('Bashar al-Assad', 'Presidential Palace, Damascus', 'Syria', '5493065XASSAD5544', 'Other', 'Other', 'Other', '$1M - $10M', 'PENDING_REVIEW'),
('Mahan Air', 'Mahan Tower, Tehran', 'Iran', '5493066XMAHAN3322', 'Other', 'Fintech / Payments', 'Operating Revenues', '$10M - $100M', 'PENDING_REVIEW'),
('North Korean National Ship', 'Nampo Port', 'North Korea', '5493067XDPRK1100', 'Other', 'Energy / Commodities', 'Operating Revenues', '$1M - $10M', 'PENDING_REVIEW'),
('Petroleos de Venezuela, S.A. (PDVSA)', 'Av Libertador, Caracas', 'Venezuela', '5493068XPDVSA9988', 'Corporate', 'Energy / Commodities', 'Operating Revenues', '$100M+', 'PENDING_REVIEW'),
('Alisher Usmanov', 'Rublyovksy Highway, Moscow', 'Russia', '5493069XALISHER1122', 'Other', 'Investment Banking', 'Investment Returns', '$100M+', 'PENDING_REVIEW'),

-- SCENARIO 3: VERIFICATION FAILURE (40 Records)
-- Non-existent LEI and randomized details to trigger REQUEST_INFO.
('Fake Institutional Bank', '999 Ghost St, Void City', 'United States', '9999999VOID999999999', 'Bank', 'Investment Banking', 'Other', '$100M+', 'PENDING_REVIEW'),
('Shadow Valley Funds', 'Locked Suite, Cayman', 'Cayman Islands', '0000000SHADOW000000', 'Fund', 'Asset Management', 'Loan / Credit Facility', '$10M - $100M', 'PENDING_REVIEW'),
('Zaphod Beeblebrox Exports', 'Magrathea Sect 7', 'Other', '4242424MAGRA42424242', 'Corporate', 'Other', 'Shareholder Capital', '< $1M', 'PENDING_REVIEW'),
('Global Phantom Tradings', 'Unknown Warehouse, Mumbai', 'India', 'IND99999PHANTOM0011', 'Broker-Dealer', 'Energy / Commodities', 'Operating Revenues', '$1M - $10M', 'PENDING_REVIEW'),
('Invisble Wealth LLC', '101 Nowhere Ln', 'United Kingdom', 'UK99999INVISI0022', 'Corporate', 'Real Estate', 'Operating Revenues', '< $1M', 'PENDING_REVIEW'),

-- SCENARIO 4: HIGH RISK / EDD (40 Records)
-- Valid entity but with risk flags (High volume or High-risk Jurisdiction NOT yet sanctioned).
('High Volume Fintech SG', 'Raffles Place, Singapore', 'Singapore', '5493005KJY7UW9K33334', 'Corporate', 'Fintech / Payments', 'Operating Revenues', '$100M+', 'PENDING_REVIEW'),
('Middle East Energy Trading', 'Doha Tech Plaza', 'Qatar', '5493067KJY7UH9L33446', 'Corporate', 'Energy / Commodities', 'Operating Revenues', '$100M+', 'PENDING_REVIEW'),
('Latin American Mining Corp', 'Santiago Mining Hub', 'Chile', '5493087KJY7UH9N33446', 'Corporate', 'Energy / Commodities', 'Operating Revenues', '$100M+', 'PENDING_REVIEW'),
('Crypto Gateway Malta', 'Sliema Blockchain Heights', 'Malta', '5493061KJY7UB9L55670', 'Broker-Dealer', 'Fintech / Payments', 'Operating Revenues', '$100M+', 'PENDING_REVIEW'),
('Congo Minerals Trust', 'Kinshasa Export Zone', 'DRC', '5493071KJY7UB9M55671', 'Corporate', 'Energy / Commodities', 'Operating Revenues', '$10M - $100M', 'PENDING_REVIEW');

-- NOTE: Final aml_mock_data.sql will expand these templates to a full 200 records.
