from fpdf import FPDF
import os

def create_pdf(file_path, title, content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(40, 10, title)
    pdf.ln(20)
    pdf.set_font("Arial", "", 12)
    for line in content:
        pdf.multi_cell(0, 10, line)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    pdf.output(file_path)
    print(f"Created: {file_path}")

def generate_all_mock_docs():
    base_dir = r"d:\learning\aml\mock_docs\evergreen"
    
    entities = {
        "Evergreen_Financial_Group": {
            "name": "Evergreen Financial Group",
            "country": "United States",
            "reg_num": "NY-889900",
            "inc_date": "May 15, 2010",
            "directors": [
                "Michael S. Evergreen - CEO & Chairman",
                "Sarah Jenkins - Chief Compliance Officer"
            ],
            "ubos": [
                "Evergreen Family Trust (65% Stake)",
                "Michael S. Evergreen (35% Stake)"
            ]
        },
        "Wagner_Shield_Corp": {
            "name": "Wagner Shield Corp",
            "country": "Russia",
            "reg_num": "RU-WAG-1122",
            "inc_date": "March 01, 2014",
            "directors": [
                "Yevgeny Prigozhin - Strategic Advisor"
            ],
            "ubos": [
                "Mikhail Fridman (100% Stake)"
            ]
        },
        "North_Star_Asset_Management": {
            "name": "North Star Asset Management",
            "country": "Singapore",
            "reg_num": "5493002KJY7UW9K67890"
        },
        "Riverbank_Global_Trade": {
            "name": "Riverbank Global Trade",
            "country": "United Kingdom",
            "reg_num": "5493003KJY7UW9K11111"
        },
        "Indus_Valley_Ventures": {
            "name": "Indus Valley Ventures",
            "country": "India",
            "reg_num": "5493004KJY7UW9K22222"
        },
        "Desert_Oasis_Logistics": {
            "name": "Desert Oasis Logistics",
            "country": "United Arab Emirates",
            "reg_num": "5493005KJY7UW9K33333"
        },
        "Alfa_Bank": {
            "name": "Alfa-Bank",
            "country": "Russia",
            "reg_num": "RU-INN-7701101"
        },
        "Moscow_Red_Square_Bank": {
            "name": "Moscow Red Square Bank",
            "country": "Russia",
            "reg_num": "RU-INN-7705505"
        },
        "Persia_Cargo_Intl": {
            "name": "Persia Cargo International",
            "country": "Iran",
            "reg_num": "IR-REG-9900"
        },
        "Petroleo_Phoenix_SA": {
            "name": "Petroleo Phoenix SA",
            "country": "Mexico",
            "reg_num": "MX-12345-REG"
        },
        "Wagner_Shield_Corp": {
            "name": "Wagner Shield Corp",
            "country": "Russia",
            "reg_num": "RU-WAG-1122"
        }
    }

    for folder_name, info in entities.items():
        entity_path = os.path.join(base_dir, folder_name)
        
        # 1. Certificate of Incorporation
        create_pdf(
            os.path.join(entity_path, "certificate_of_incorporation.pdf"),
            "CERTIFICATE OF INCORPORATION",
            [
                f"Entity Name: {info['name']}",
                f"Registration Number: {info['reg_num']}",
                f"Jurisdiction: {info['country']}",
                "Date of Incorporation: January 15, 2018",
                "Status: ACTIVE / REGISTERED"
            ]
        )
        
        # 2. Board of Directors
        create_pdf(
            os.path.join(entity_path, "bod_list.pdf"),
            "BOARD OF DIRECTORS LIST",
            [
                f"Company: {info['name']}",
                *info.get('directors', ["1. James Sterling - Chairman", "2. Sarah Connor - Managing Director"])
            ]
        )
        
        # 3. Financials 2024
        create_pdf(
            os.path.join(entity_path, "financials_2024.pdf"),
            "ANNUAL FINANCIAL STATEMENT 2024",
            [
                f"Audit Report for: {info['name']}",
                "Total Assets: $250,000,000",
                "Net Income: $12,500,000",
                "Audit Status: UNQUALIFIED OPINION"
            ]
        )
        
        # 4. Ownership Structure
        create_pdf(
            os.path.join(entity_path, "ownership_structure.pdf"),
            "OWNERSHIP & UBO DECLARATION",
            [
                f"Ultimate Beneficial Ownership for: {info['name']}",
                *info.get('ubos', ["UBO 1: Alexander Great (35% Stake)", "UBO 2: Catherine Middle (25% Stake)", "Public Float: 40%"])
            ]
        )

        # 5. Bank Statement
        create_pdf(
            os.path.join(entity_path, "bank_statement.pdf"),
            "MONTHLY BANK STATEMENT",
            [
                f"Account Holder: {info['name']}",
                "Bank: Global Institutional Bank",
                "Period: Jan 2024 - Dec 2024",
                "Ending Balance: $1,450,000.00",
                "Currency: USD"
            ]
        )

        # 6. EIN Certificate / Tax ID
        create_pdf(
            os.path.join(entity_path, "ein_certificate.pdf"),
            "TAX IDENTIFICATION CERTIFICATE",
            [
                f"Legal Entity: {info['name']}",
                f"Tax ID / EIN: {info['reg_num']}-TAX",
                "Issuing Authority: Federal Tax Department",
                "Status: VALID"
            ]
        )

        # 7. UBO ID / Passport (Simulated)
        create_pdf(
            os.path.join(entity_path, "ubo_id.pdf"),
            "PERSON OF SIGNIFICANT CONTROL - IDENTITY",
            [
                f"Beneficial Owner for: {info['name']}",
                "Name: Alexander Great",
                "Nationality: Jurisdictional Resident",
                "Document Type: Passport / National ID",
                "Status: VERIFIED"
            ]
        )

if __name__ == "__main__":
    generate_all_mock_docs()
