"""
generate_mock_data.py
Generates mock PDF documents for "North Star Asset Management" (Singapore)
and submits a test signup to the Kinetix backend API.

Run: python generate_mock_data.py
"""

import os
import requests
from fpdf import FPDF

# ── Config ────────────────────────────────────────────────────────────────────
OUTPUT_DIR = r"d:\learning\aml\mock_docs\north_star"
API_URL    = "http://localhost:8000/signup"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ── PDF helper ─────────────────────────────────────────────────────────────────
def make_pdf(title, sections: dict, filename: str):
    """Creates a clean, professional-looking PDF."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(20, 20, 20)

    # Header bar
    pdf.set_fill_color(27, 94, 32)      # Kinetix green
    pdf.rect(0, 0, 210, 30, "F")
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(0, 8)
    pdf.cell(210, 14, "KINETIX  |  Institutional Onboarding", align="C")

    # Document title
    pdf.set_xy(20, 38)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(27, 94, 32)
    pdf.cell(0, 10, title)

    # Divider
    pdf.set_draw_color(27, 94, 32)
    pdf.set_line_width(0.5)
    pdf.line(20, 50, 190, 50)

    y = 56
    for section_title, rows in sections.items():
        # Section heading
        pdf.set_xy(20, y)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(50, 50, 50)
        pdf.cell(0, 8, section_title)
        y += 10

        for label, value in rows:
            pdf.set_xy(20, y)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(100, 100, 100)
            pdf.cell(60, 7, label)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(30, 30, 30)
            pdf.cell(110, 7, str(value))
            y += 8

        y += 6  # extra spacing between sections

    # Footer
    pdf.set_xy(0, 277)
    pdf.set_fill_color(245, 245, 245)
    pdf.rect(0, 270, 210, 27, "F")
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(210, 27, "CONFIDENTIAL - Kinetix Strategic Onboarding | Generated for compliance testing only", align="C")

    pdf.output(filename)
    print(f"  ✓ Created: {filename}")


# ── 1. Board of Directors List ──────────────────────────────────────────────
make_pdf(
    "Board of Directors List",
    {
        "Entity Details": [
            ("Company",   "North Star Asset Management Pte. Ltd."),
            ("LEI",       "5493002KJY7UW9K67890"),
            ("Country",   "Singapore"),
            ("As of Date","2025-01-01"),
        ],
        "Board Members": [
            ("Director 1", "Mr. Wei Liang Tan - Chairman, Non-Executive"),
            ("Director 2", "Ms. Priya Nair - CEO & Executive Director"),
            ("Director 3", "Mr. James F. Sullivan - Independent Director (UK)"),
            ("Director 4", "Dr. Aiko Yamamoto - Independent Director"),
            ("Director 5", "Mr. Ravi Krishnan - COO & Executive Director"),
        ],
        "Compliance Officer": [
            ("Name",   "Ms. Clara Hoffmann"),
            ("Email",  "c.hoffmann@northstaram.sg"),
            ("Phone",  "+65 6123 4500"),
        ],
    },
    os.path.join(OUTPUT_DIR, "bod_list.pdf")
)

# ── 2. Audited Financials ────────────────────────────────────────────────────
make_pdf(
    "Audited Financial Statements - FY 2024",
    {
        "Fund Summary": [
            ("Fund Name",     "North Star Asia Growth Fund"),
            ("Fund Type",     "Closed-End Hedge Fund"),
            ("Base Currency", "USD"),
            ("AUM (FY2024)",  "USD 2.4 Billion"),
            ("Fund Vintage",  "2011"),
        ],
        "Income Statement (USD M)": [
            ("Total Revenue",             "$312.5 M"),
            ("Management Fees",           "$48.0 M"),
            ("Performance Fees",          "$62.5 M"),
            ("Operating Expenses",        "$28.3 M"),
            ("Net Income Before Tax",     "$284.2 M"),
            ("Tax Provision",             "$14.2 M"),
            ("Net Income After Tax",      "$270.0 M"),
        ],
        "Balance Sheet Highlights (USD M)": [
            ("Total Assets",              "$2,450.0 M"),
            ("Total Liabilities",         "$120.0 M"),
            ("Net Asset Value (NAV)",     "$2,330.0 M"),
            ("Cash & Equivalents",        "$185.0 M"),
        ],
        "Audit Certification": [
            ("Auditor",     "PricewaterhouseCoopers LLP, Singapore"),
            ("Audit Date",  "March 15, 2025"),
            ("Opinion",     "Unqualified (Clean)"),
        ],
    },
    os.path.join(OUTPUT_DIR, "financials.pdf")
)

# ── 3. Ownership Structure ───────────────────────────────────────────────────
make_pdf(
    "Ownership Structure & UBO Declaration",
    {
        "Entity Details": [
            ("Legal Name",      "North Star Asset Management Pte. Ltd."),
            ("Incorporation",   "Singapore, 2011"),
            ("Reg. Number",     "REG-67890-SG"),
            ("Ownership Type",  "Privately Held"),
        ],
        "Ultimate Beneficial Owners (UBO > 10%)": [
            ("UBO 1 - Name",        "Wei Liang Tan"),
            ("UBO 1 - Stake",       "35.0%"),
            ("UBO 1 - Nationality", "Singaporean"),
            ("UBO 2 - Name",        "Meridian Capital Partners LP"),
            ("UBO 2 - Stake",       "40.0%"),
            ("UBO 2 - Registered",  "Cayman Islands"),
            ("UBO 3 - Name",        "Public Market Float (SGX Listed)"),
            ("UBO 3 - Stake",       "25.0%"),
        ],
        "Sanctions & PEP Declaration": [
            ("Sanctions Exposure",  "None declared"),
            ("PEP Affiliated",      "No"),
            ("Adverse Media",       "None identified"),
            ("Declaration Date",    "February 2025"),
        ],
    },
    os.path.join(OUTPUT_DIR, "ownership_structure.pdf")
)

# ── Submit Signup via API ─────────────────────────────────────────────────────
print("\n── Submitting signup to API ──────────────────────────────────────")

def read_pdf(path):
    with open(path, "rb") as f:
        return f.read()

files = {
    "bod_list":           ("bod_list.pdf",          read_pdf(os.path.join(OUTPUT_DIR, "bod_list.pdf")),           "application/pdf"),
    "financials":         ("financials.pdf",         read_pdf(os.path.join(OUTPUT_DIR, "financials.pdf")),         "application/pdf"),
    "ownership_structure":("ownership_structure.pdf",read_pdf(os.path.join(OUTPUT_DIR, "ownership_structure.pdf")),"application/pdf"),
}

data = {
    # Personal
    "first_name":           "Priya",
    "last_name":            "Nair",
    "email":                "priya.nair@northstaram.sg",
    # Company
    "company_name":         "North Star Asset Management",
    "company_address":      "10 Collyer Quay, Ocean Financial Centre, #40-01",
    "city":                 "Singapore",
    "state":                "",
    "country":              "Singapore",
    "zip":                  "049315",
    "phone":                "+6561234500",
    "lei":                  "5493002KJY7UW9K67890",
    "entity_type":          "Fund",
    "product_interest":     "Compliance API",
    # AML
    "business_activity":    "Asset Management",
    "source_of_funds":      "Investment Returns",
    "expected_volume":      "$100M+",
    "countries_operation":  "SG, US, UK, HK, JP",
    "aml_questions": '{"sanctions_exposure": "No", "aml_program": "Yes", "registration_number": "REG-67890-SG", "ownership_type": "Privately Held"}',
}

try:
    response = requests.post(API_URL, data=data, files=files, timeout=30)
    result = response.json()
    print(f"\n  Status   : {response.status_code}")
    print(f"  Response : {result}")
    if response.ok:
        print(f"\n  ✅ Signup successful!")
        print(f"  Tracking ID : {result.get('tracking_id')}")
        print(f"  Check email : priya.nair@northstaram.sg for temp password")
    else:
        print(f"\n  ❌ Signup failed: {result.get('detail')}")
except requests.exceptions.ConnectionError:
    print("\n  ⚠️  Could not connect to backend. Is the server running on localhost:8000?")
except Exception as e:
    print(f"\n  ❌ Error: {e}")
