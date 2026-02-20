"""
make_pdfs.py - Generates 3 mock compliance PDFs for North Star Asset Management.
Header shows the company name only (no Kinetix branding).
Run: python make_pdfs.py
"""
import os
from fpdf import FPDF

OUTPUT_DIR = r"d:\learning\aml\mock_docs\north_star"
os.makedirs(OUTPUT_DIR, exist_ok=True)

COMPANY     = "North Star Asset Management Pte. Ltd."
ADDR        = "10 Collyer Quay, Ocean Financial Centre, Singapore 049315"
HEADER_COLOR = (15, 52, 96)   # Navy blue

def make_pdf(company_name, doc_type, sections, filename):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_margins(20, 20, 20)

    # ── Company header (company name only)
    pdf.set_fill_color(*HEADER_COLOR)
    pdf.rect(0, 0, 210, 34, "F")
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(0, 7)
    pdf.cell(210, 10, company_name, align="C")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(190, 210, 240)
    pdf.set_xy(0, 19)
    pdf.cell(210, 10, doc_type, align="C")

    # ── Divider line
    pdf.set_draw_color(*HEADER_COLOR)
    pdf.set_line_width(0.5)
    pdf.line(20, 38, 190, 38)

    y = 44
    for section_title, rows in sections.items():
        if y > 255:
            pdf.add_page()
            y = 20
        pdf.set_xy(20, y)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*HEADER_COLOR)
        pdf.cell(0, 8, section_title)
        y += 9
        for label, value in rows:
            if y > 260:
                pdf.add_page()
                y = 20
            pdf.set_xy(22, y)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(90, 90, 90)
            pdf.cell(65, 7, label)
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(20, 20, 20)
            pdf.cell(110, 7, str(value))
            y += 7
        y += 5

    # ── Footer
    pdf.set_fill_color(240, 240, 240)
    pdf.rect(0, 270, 210, 27, "F")
    pdf.set_font("Helvetica", "I", 8)
    pdf.set_text_color(130, 130, 130)
    pdf.set_xy(0, 275)
    pdf.cell(210, 10, "CONFIDENTIAL - For Regulatory and Compliance Review Only", align="C")
    pdf.set_xy(0, 283)
    pdf.cell(210, 10, ADDR, align="C")

    pdf.output(filename)
    print(f"  OK  {filename}")


# ── 1. Board of Directors
make_pdf(
    COMPANY, "Board of Directors List",
    {
        "Entity Details": [
            ("Company",        COMPANY),
            ("LEI",            "5493002KJY7UW9K67890"),
            ("Country",        "Singapore"),
            ("Document Date",  "January 01, 2025"),
        ],
        "Board of Directors": [
            ("Director 1", "Mr. Wei Liang Tan - Chairman, Non-Executive"),
            ("Director 2", "Ms. Priya Nair - CEO and Executive Director"),
            ("Director 3", "Mr. James F. Sullivan - Independent Director"),
            ("Director 4", "Dr. Aiko Yamamoto - Independent Director"),
            ("Director 5", "Mr. Ravi Krishnan - COO and Executive Director"),
        ],
        "Compliance / MLRO Contact": [
            ("MLRO Name",  "Ms. Clara Hoffmann"),
            ("MLRO Email", "c.hoffmann@northstaram.sg"),
            ("MLRO Phone", "+65 6123 4500"),
        ],
    },
    os.path.join(OUTPUT_DIR, "bod_list.pdf"),
)

# ── 2. Financials
make_pdf(
    COMPANY, "Audited Financial Statements - FY 2024",
    {
        "Fund Overview": [
            ("Fund Name",      "North Star Asia Growth Fund"),
            ("Fund Type",      "Closed-End Hedge Fund"),
            ("Base Currency",  "USD"),
            ("AUM (FY2024)",   "USD 2.4 Billion"),
            ("Fund Vintage",   "2011"),
            ("Auditor",        "PricewaterhouseCoopers LLP, Singapore"),
            ("Audit Opinion",  "Unqualified (Clean)"),
            ("Audit Date",     "March 15, 2025"),
        ],
        "Income Statement (USD Millions)": [
            ("Total Revenue",         "312.5"),
            ("Management Fees",       " 48.0"),
            ("Performance Fees",      " 62.5"),
            ("Operating Expenses",    " 28.3"),
            ("Net Income Before Tax", "284.2"),
            ("Tax Provision",         " 14.2"),
            ("Net Income After Tax",  "270.0"),
        ],
        "Balance Sheet Summary (USD Millions)": [
            ("Total Assets",          "2,450.0"),
            ("Total Liabilities",     "  120.0"),
            ("Net Asset Value (NAV)", "2,330.0"),
            ("Cash and Equivalents",  "  185.0"),
        ],
    },
    os.path.join(OUTPUT_DIR, "financials.pdf"),
)

# ── 3. Ownership Structure
make_pdf(
    COMPANY, "Ownership Structure and UBO Declaration",
    {
        "Company Registration": [
            ("Legal Name",      COMPANY),
            ("Reg. Number",     "REG-67890-SG"),
            ("Incorporated",    "Singapore, 2011"),
            ("Ownership Type",  "Privately Held"),
        ],
        "Ultimate Beneficial Owners (Stake > 10%)": [
            ("UBO 1 - Name",    "Wei Liang Tan"),
            ("UBO 1 - Stake",   "35.0%"),
            ("UBO 1 - Nationality", "Singaporean"),
            ("UBO 2 - Name",    "Meridian Capital Partners LP"),
            ("UBO 2 - Stake",   "40.0%"),
            ("UBO 2 - Domicile","Cayman Islands"),
            ("UBO 3 - Name",    "Public Market Float (SGX-listed)"),
            ("UBO 3 - Stake",   "25.0%"),
        ],
        "Sanctions and PEP Declaration": [
            ("Sanctions Exposure", "None declared"),
            ("PEP Affiliation",    "No"),
            ("Adverse Media",      "None identified"),
            ("AML Program",        "Yes - MAS compliant program in place"),
            ("Declaration Date",   "February 2025"),
        ],
    },
    os.path.join(OUTPUT_DIR, "ownership_structure.pdf"),
)

print(f"\nAll PDFs saved to: {OUTPUT_DIR}")
