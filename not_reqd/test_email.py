import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

# Load env from .dbenv
load_dotenv(dotenv_path='.dbenv')

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_SENDER = os.getenv("SMTP_SENDER", SMTP_USER)

def test_smtp():
    configs = [
        {"port": 587, "use_ssl": False, "desc": "Port 587 (STARTTLS)"},
        {"port": 465, "use_ssl": True, "desc": "Port 465 (SSL)"}
    ]

    for config in configs:
        port = config["port"]
        use_ssl = config["use_ssl"]
        print(f"\n--- Testing {config['desc']} ---")
        
        msg = MIMEMultipart()
        msg['From'] = f"Kinetix Diagnostic <{SMTP_SENDER}>"
        msg['To'] = SMTP_SENDER
        msg['Subject'] = f"Kinetix SMTP Test ({config['desc']})"
        msg.attach(MIMEText(f"This is a {config['desc']} test email.", 'plain'))

        try:
            if use_ssl:
                print(f"Connecting to {SMTP_SERVER}:{port} via SSL...")
                server = smtplib.SMTP_SSL(SMTP_SERVER, port, timeout=10)
            else:
                print(f"Connecting to {SMTP_SERVER}:{port}...")
                server = smtplib.SMTP(SMTP_SERVER, port, timeout=10)
                print("Starting TLS...")
                server.starttls()
            
            print("Attempting login...")
            server.login(SMTP_USER, SMTP_PASS)
            
            print("Sending test message...")
            server.send_message(msg)
            server.quit()
            print(f"SUCCESS: Email sent via {config['desc']}!")
            return # Exit if one succeeds
        except Exception as e:
            print(f"FAILED {config['desc']}: {str(e)}")

    print("\nALL ATTEMPTS FAILED.")
    print("TIP: Please verify your Brevo SMTP Master Password (API Key) and Username at: https://app.brevo.com/settings/keys/smtp")

if __name__ == "__main__":
    test_smtp()
