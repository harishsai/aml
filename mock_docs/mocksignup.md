# KINETIX — Mock Signup Test Data (UI Ordered)
> **Goal:** Copy-paste data in the exact order it appears in the UI. All fields are now in sync with the backend.

## 🏆 RECORD 1: Alexander Great (Evergreen Financial Group)
**Profile:** Regulated US bank, pre-seeded LEI, designed to pass all checks.

### --- STEP 1: Entity Information ---
| Field In UI | Value to Enter |
| :--- | :--- |
| **First Name** | `Alexander` |
| **Last Name** | `Great` |
| **Professional Email** | `alexander.g@gmail.com` |
| **Phone Number** | `+12125550101` |
| **Legal Entity Name** | `Evergreen Financial Group` |
| **DBA Name** | `Evergreen Private Wealth` |
| **Company Website** | `https://www.evergreenfinancial.com` |
| **Registered Address** | `120 Wall Street, Suite 1800` |
| **Country (ISO)** | `US` |
| **State / Province** | `NY` |
| **City** | `New York City` |
| **Zip / Postal Code** | `10005` |
| **LEI (20 chars)** | `5493001KJY7UW9K12345` |
| **Registration No.** | `123456789` |
| **EIN / TIN** | `12-3456789` |
| **Incorporation Date** | `2004-03-15` |
| **Regulatory Status** | `Regulated` |
| **Regulatory Authority** | `NYDFS` |
| **Entity Type** | `Bank` |
| **Ownership Type** | `Publicly Traded` |

---

### --- STEP 2: Compliance Docs ---
*Note: Any PDF will work for testing.*

| Document Slot | Recommended Placeholder |
| :--- | :--- |
| **Board of Directors List** | `bod_list.pdf` |
| **Audited Financials** | `financials_2024.pdf` |
| **Ownership Structure** | `ownership_structure.pdf` |
| **Cert. of Incorporation** | `certificate_of_incorporation.pdf` |
| **Bank Statement** | `bank_statement.pdf` |
| **EIN Certificate** | `ein_certificate.pdf` |
| **UBO Identification** | `ubo_id.pdf` |

**Management (Add Director):**
- **Name:** `Alexander Great`
- **Role:** `CEO`
- **Nationality:** `American`
- **Residence:** `United States`

---

### --- STEP 3: Risk Profile ---
| Field In UI | Value to Select/Enter |
| :--- | :--- |
| **Product Interest** | `Payments & Settlements` |
| **Countries of Op.** | `US, UK, SG` |
| **Tax Residency** | `US` |
| **Sanctions Match?** | `No matches` |
| **PEP Status** | `No PEP involvement` |
| **AML/CFT Program?** | `Yes, we have a program` |
| **Program Description** | `Global AML/KYC policy updated annually.` |
| **Nature of Business** | `Retail Banking` |
| **Monthly Volume** | `$10M+ / Mo` |
| **Source of Funds** | `Operating Revenues` |
| **Source of Wealth** | `Shareholder Capital` |
| **Address Different?** | `No, same as registered` |
| **Correspondent Bank** | `Evergreen Ops Bank` |
| **Consent Checkbox** | `[Checked]` |

---

### --- STEP 4: Settlement ---
| Field In UI | Value to Enter |
| :--- | :--- |
| **Bank Name** | `Evergreen Ops Bank` |
| **Routing / SWIFT** | `021000021` |
| **Account Number** | `9988776655` |
| **MCC Code** | `6011` |
| **Terms Checkbox** | `[Checked]` |

---

## 🗑️ Cleanup Utility
```sql
BEGIN;
TRUNCATE TABLE client_onboarding.ai_agent_logs RESTART IDENTITY CASCADE;
TRUNCATE TABLE client_onboarding.onboarding_details RESTART IDENTITY CASCADE;
DELETE FROM client_onboarding.users WHERE id IN (
    SELECT user_id FROM client_onboarding.user_roles WHERE role_id = (SELECT id FROM client_onboarding.roles WHERE name = 'PARTICIPANT')
);
COMMIT;
```
