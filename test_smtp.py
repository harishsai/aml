import smtplib
import os
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def test_smtp_strict():
    # Force reload from .dbenv
    load_dotenv('.dbenv', override=True)
    
    SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp-relay.brevo.com")
    SMTP_PORT = 587
    SMTP_USER = os.getenv("SMTP_USER")
    SMTP_PASS = os.getenv("SMTP_PASS")
    SMTP_SENDER = os.getenv("SMTP_SENDER", "dbacloudora@gmail.com")
    
    recipient = "harishsai@gmail.com"
    subject = "Strict SMTP Port 587 Test"
    
    print(f"--- Strict Port 587 Test ---")
    print(f"Server: {SMTP_SERVER}")
    print(f"User  : {SMTP_USER}")
    print(f"Sender: {SMTP_SENDER}")
    
    msg = MIMEMultipart()
    msg['From'] = SMTP_SENDER
    msg['To'] = recipient
    msg['Subject'] = subject
    msg.attach(MIMEText("Strict Port 587 test successful.", 'plain'))
    
    try:
        print(f"Connecting to {SMTP_SERVER} on Port {SMTP_PORT}...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15)
        server.set_debuglevel(1)
        print("Starting TLS...")
        server.starttls()
        
        print(f"Attempting login as {SMTP_USER}...")
        server.login(SMTP_USER, SMTP_PASS)
        
        print("Sending message...")
        server.send_message(msg)
        server.quit()
        print("\n✅ SUCCESS: Email sent successfully via Port 587.")
    except Exception as e:
        print(f"\n❌ FAILED: {e}")

if __name__ == "__main__":
    test_smtp_strict()
