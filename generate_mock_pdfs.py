from fpdf import FPDF
import os

class IndustryPDF(FPDF):
    def __init__(self, company_name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.company_name = company_name

    def header(self):
        self.set_font('helvetica', 'B', 10)
        self.cell(0, 10, f'{self.company_name.upper()} - STRICTLY CONFIDENTIAL', border=0, ln=1, align='L')
        self.set_draw_color(0, 100, 0) # Dark green
        self.line(10, 18, 200, 18)
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()} | {self.company_name} | Internal Use Only', 0, 0, 'C')

def create_bod_pdf(company):
    pdf = IndustryPDF(company)
    pdf.add_page()
    pdf.set_font("helvetica", "B", 18)
    pdf.cell(0, 10, "Board of Directors List", ln=True, align="C")
    pdf.ln(5)
    
    pdf.set_font("helvetica", "", 10)
    pdf.cell(0, 8, "Date: February 20, 2026", ln=True)
    pdf.cell(0, 8, f"Entity: {company}", ln=True)
    pdf.ln(10)
    
    # Table Header
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(60, 10, "Name", 1, 0, 'C', fill=True)
    pdf.cell(60, 10, "Position", 1, 0, 'C', fill=True)
    pdf.cell(70, 10, "Tenure", 1, 1, 'C', fill=True)
    
    # Table Body
    pdf.set_font("helvetica", "", 10)
    data = [
        ("John Doe", "Chairman / Independent Director", "8 Years"),
        ("Jane Smith", "Chief Executive Officer (CEO)", "5 Years"),
        ("Robert Brown", "Senior Independent Director", "10 Years"),
        ("Emily Davis", "Chief Financial Officer (CFO)", "4 Years"),
        ("Michael Wilson", "Non-Executive Director", "6 Years"),
        ("Sarah Jenkins", "Compliance & Risk Committee Chair", "3 Years")
    ]
    
    for name, pos, tenure in data:
        pdf.cell(60, 10, name, 1)
        pdf.cell(60, 10, pos, 1)
        pdf.cell(70, 10, tenure, 1, 1)
    
    pdf.output("mock_docs/bod_list.pdf")
    print("Regenerated bod_list.pdf")

def create_financials_pdf(company):
    pdf = IndustryPDF(company)
    pdf.add_page()
    pdf.set_font("helvetica", "B", 16)
    pdf.cell(0, 10, "6-Month Financial Performance Summary", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("helvetica", "I", 10)
    pdf.cell(0, 10, "Period: July 2025 - December 2025 | All figures in USD Millions", ln=True, align="C")
    pdf.ln(10)
    
    # Header Row
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("helvetica", "B", 8)
    pdf.cell(40, 10, "Metric", 1, 0, 'C', fill=True)
    months = ["Jul '25", "Aug '25", "Sep '25", "Oct '25", "Nov '25", "Dec '25"]
    for month in months:
        pdf.cell(25, 10, month, 1, 0, 'C', fill=True)
    pdf.ln(10)
    
    # Data Rows
    metrics = [
        ("Net Revenue", [850, 875, 910, 890, 930, 980]),
        ("Operating Expense", [420, 430, 440, 435, 450, 470]),
        ("Net Profit", [430, 445, 470, 455, 480, 510]),
        ("Total Assets", [60200, 60500, 61100, 61400, 61800, 62000]),
        ("Total Liabilities", [53000, 53200, 53800, 54000, 54400, 54800])
    ]
    
    pdf.set_font("helvetica", "", 8)
    for metric, values in metrics:
        pdf.cell(40, 8, metric, 1)
        for val in values:
            pdf.cell(25, 8, f"{val:,}", 1, 0, 'R')
        pdf.ln(8)
    
    pdf.ln(10)
    pdf.set_font("helvetica", "B", 10)
    pdf.multi_cell(0, 6, "Note: These figures represent unaudited monthly management accounts for internal review and partnership verification purposes within the Kinetix ecosystem.")
    
    pdf.output("mock_docs/financials.pdf")
    print("Regenerated financials.pdf")

def create_ownership_pdf(company):
    pdf = IndustryPDF(company)
    pdf.add_page()
    pdf.set_font("helvetica", "B", 18)
    pdf.cell(0, 10, "Ownership Structure & UBO Declaration", ln=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "1. Corporate Structure Overview", ln=True)
    pdf.set_font("helvetica", "", 10)
    pdf.multi_cell(0, 6, f"{company} (the 'Entity') is a publicly traded financial institution. This document contains proprietary information and is provided strictly for verification.")
    pdf.ln(5)
    
    # Shareholder Table
    pdf.set_font("helvetica", "B", 10)
    pdf.cell(100, 10, "Shareholder Name", 1, 0, 'C', fill=True)
    pdf.cell(40, 10, "Equity %", 1, 0, 'C', fill=True)
    pdf.cell(50, 10, "Type", 1, 1, 'C', fill=True)
    
    pdf.set_font("helvetica", "", 10)
    shareholders = [
        ("Global Institutional Holdings Ltd", "32.5%", "Corporate"),
        ("Strategic Capital Fund LP", "12.8%", "Fund"),
        ("Northern Asset Management", "8.2%", "Institutional"),
        ("Public Float (NYSE: EVER)", "46.5%", "Public")
    ]
    for name, pct, stype in shareholders:
        pdf.cell(100, 10, name, 1)
        pdf.cell(40, 10, pct, 1, 0, 'C')
        pdf.cell(50, 10, stype, 1, 1, 'C')
    
    pdf.ln(10)
    pdf.set_font("helvetica", "B", 12)
    pdf.cell(0, 10, "2. Ultimate Beneficial Ownership (UBO)", ln=True)
    pdf.set_font("helvetica", "", 10)
    pdf.multi_cell(0, 6, "As a publicly traded entity, the entity is exempt from certain UBO disclosure requirements; however, significant individual control is monitored through statutory filings.")

    pdf.output("mock_docs/ownership_structure.pdf")
    print("Regenerated ownership_structure.pdf")

if __name__ == "__main__":
    if not os.path.exists("mock_docs"):
        os.makedirs("mock_docs")
    company_name = "Evergreen Financial Group"
    create_bod_pdf(company_name)
    create_financials_pdf(company_name)
    create_ownership_pdf(company_name)
