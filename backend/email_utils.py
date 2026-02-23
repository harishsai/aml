import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.dbenv'))

# SMTP Settings
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp-relay.brevo.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "your_app_password")
SMTP_SENDER = os.getenv("SMTP_SENDER", SMTP_USER)

def send_confirmation_email(recipient_email, first_name, tracking_id=None, temp_password=None):
    """
    Sends a confirmation email with the tracking ID and temporary login credentials.
    """
    subject = "Application Received & Portal Access — Kinetix Strategic Onboarding"

    html_content = f"""
    <html>
    <body style="font-family: 'Inter', sans-serif; line-height: 1.6; color: #333; background: #f8f9fa;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.08);">
                <div style="background: #1B5E20; padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0; letter-spacing: 3px; font-size: 1.8rem;">KINETIX</h1>
                    <p style="color: rgba(255,255,255,0.8); margin: 5px 0 0 0; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 1px;">Institutional Excellence</p>
                </div>

                <div style="padding: 35px;">
                    <p>Dear <strong>{first_name}</strong>,</p>
                    <p>Thank you for submitting your institutional onboarding application with <strong>Kinetix</strong>. Your application has been received and is currently <strong>under review</strong> by our Internal Operations team.</p>

                    {'<div style="background: #f1f8e9; border: 1px solid #c8e6c9; border-radius: 8px; padding: 20px; margin: 25px 0;">' +
                    '<p style="margin: 0 0 15px 0; font-weight: 700; color: #1B5E20; font-size: 1rem;">📋 Your Application Reference</p>' +
                    '<table style="width: 100%; border-collapse: collapse;">' +
                    '<tr><td style="padding: 8px 0; color: #666; font-size: 0.9rem;">Tracking ID</td>' +
                    f'<td style="padding: 8px 0; font-weight: 700; font-family: monospace; font-size: 1rem; color: #1B5E20;">{tracking_id}</td></tr>' +
                    '</table></div>' if tracking_id else ''}

                    {'<div style="background: #fff8e1; border: 1px solid #ffe082; border-radius: 8px; padding: 20px; margin: 25px 0;">' +
                    '<p style="margin: 0 0 15px 0; font-weight: 700; color: #F57C00; font-size: 1rem;">🔐 Your Temporary Portal Access</p>' +
                    '<p style="margin: 0 0 10px 0; font-size: 0.9rem; color: #555;">Use these credentials to log in and track your application status:</p>' +
                    '<table style="width: 100%; border-collapse: collapse;">' +
                    f'<tr><td style="padding: 8px 0; color: #666; font-size: 0.9rem; width: 120px;">Username</td>' +
                    f'<td style="padding: 8px 0; font-weight: 600; font-family: monospace;">{recipient_email}</td></tr>' +
                    f'<tr><td style="padding: 8px 0; color: #666; font-size: 0.9rem;">Temp Password</td>' +
                    f'<td style="padding: 8px 0; font-weight: 700; font-family: monospace; font-size: 1.1rem; color: #E65100; letter-spacing: 1px;">{temp_password}</td></tr>' +
                    '</table>' +
                    '<p style="margin: 15px 0 0 0; font-size: 0.8rem; color: #888;">⚠️ You will be required to set a new password on your first login. This temporary password expires in 7 days.</p>' +
                    '</div>' if temp_password else ''}

                    <div style="background: #F8F9FA; padding: 15px; border-left: 4px solid #2E7D32; margin: 20px 0; border-radius: 0 6px 6px 0;">
                        <p style="margin: 0 0 8px 0; font-weight: 600;">What Happens Next:</p>
                        <ul style="margin: 0; padding-left: 20px; color: #555;">
                            <li>Our team will perform a detailed Sanctions and AML assessment.</li>
                            <li>You will receive a status update once the review is complete.</li>
                            <li>If additional information is required, an analyst will contact you.</li>
                        </ul>
                    </div>

                    <p style="margin-top: 25px;">Regards,<br>
                    <strong>Kinetix Strategic Onboarding Team</strong><br>
                    <span style="font-size: 0.8rem; color: #999;">This is an automated message. Please do not reply.</span></p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    msg = MIMEMultipart()
    msg['From'] = f"Kinetix Onboarding <{SMTP_SENDER}>"
    msg['To'] = recipient_email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        if SMTP_PASS == "your_app_password":
            print(f"DEBUG: Mock Send -> {recipient_email} (Please set SMTP_PASS in .dbenv for real mail)")
            return True

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        print(f"SUCCESS: Real Email sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"ERROR: Failed to send email: {e}")
        return False

def send_status_update_email(recipient_email, tracking_id, new_status, remarks=None):
    """
    Sends a status update notification to the participant.
    """
    subject = f"Update: Your Kinetix Application [{tracking_id}]"
    
    status_display = new_status.replace('_', ' ').upper()
    
    status_colors = {
        'APPROVED': '#1B5E20',
        'REJECTED': '#C62828',
        'PENDING_REVIEW': '#F57C00',
        'CLARIFICATION_REQUIRED': '#1565C0',
        'CANCELLED': '#616161'
    }
    
    color = status_colors.get(new_status, '#333')
    
    html_content = f"""
    <html>
    <body style="font-family: 'Inter', sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #eee; border-radius: 10px;">
            <div style="text-align: center; margin-bottom: 30px;">
                <h1 style="color: #1B5E20; letter-spacing: 2px;">KINETIX</h1>
            </div>
            
            <p>Dear Participant,</p>
            
            <p>The status of your institutional onboarding application has been updated.</p>
            
            <div style="background-color: #F8F9FA; padding: 20px; border-radius: 8px; border-left: 5px solid {color}; margin: 20px 0;">
                <p style="margin: 0; font-size: 0.9rem; color: #666;">Tracking ID: <strong>{tracking_id}</strong></p>
                <p style="margin: 10px 0 0 0; font-size: 1.2rem; font-weight: 700; color: {color};">
                    Current Status: {status_display}
                </p>
            </div>
            
            {f'<div style="margin: 20px 0; padding: 15px; background: #e3f2fd; border-radius: 5px;"><p style="margin:0; font-weight:600;">Message from Operations:</p><p style="margin:10px 0 0 0;">{remarks}</p></div>' if remarks else ''}
            
            <p>If you have any questions, please contact your dedicated relationship manager or reply to this email.</p>
            
            <p>Regards,<br>
            <strong>Kinetix Strategic Onboarding Team</strong></p>
        </div>
    </body>
    </html>
    """
    
    msg = MIMEMultipart()
    msg['From'] = f"Kinetix Onboarding <{SMTP_SENDER}>"
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        if SMTP_PASS == "your_app_password":
            print(f"DEBUG: Mock Status Update -> {recipient_email} [{new_status}] (Set SMTP_PASS in .dbenv for real mail)")
            return True

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        print(f"SUCCESS: Real Status Update sent to {recipient_email}")
        return True
    except Exception as e:
        print(f"ERROR: Email failure: {e}")
        return False


def _send_email(recipient_email: str, subject: str, html_content: str) -> bool:
    """Shared SMTP sender."""
    msg = MIMEMultipart()
    msg['From'] = f"Kinetix Onboarding <{SMTP_SENDER}>"
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(html_content, 'html'))
    try:
        if SMTP_PASS == "your_app_password":
            print(f"DEBUG: Mock Email → {recipient_email} | {subject}")
            return True
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"ERROR: Email failed: {e}")
        return False


def send_kyc_complete_email(recipient_email: str, tracking_id: str, risk_level: str) -> bool:
    """Sent when KYC Stage 1 agent check completes automatically after signup."""
    risk_color = {
        "LOW": "#1B5E20", "MEDIUM": "#F57C00",
        "HIGH": "#C62828", "CRITICAL": "#B71C1C"
    }.get(risk_level, "#333")
    risk_icon = {
        "LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴", "CRITICAL": "⛔"
    }.get(risk_level, "⚪")

    subject = f"KYC Review Complete — [{tracking_id}] | Kinetix"
    html = f"""
    <html><body style="font-family:Inter,sans-serif;line-height:1.6;color:#333;background:#f8f9fa;">
    <div style="max-width:600px;margin:0 auto;padding:20px;">
    <div style="background:white;border-radius:10px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.08);">
        <div style="background:#1B5E20;padding:25px;text-align:center;">
            <h1 style="color:white;margin:0;letter-spacing:3px;">KINETIX</h1>
            <p style="color:rgba(255,255,255,0.8);margin:5px 0 0 0;font-size:0.85rem;">Compliance Update</p>
        </div>
        <div style="padding:30px;">
            <p>Dear Applicant,</p>
            <p>Your application (<strong>{tracking_id}</strong>) has completed our automated <strong>KYC (Know Your Customer)</strong> screening — Stage 1 of the compliance review process.</p>
            <div style="background:#f1f8e9;border:1px solid #c8e6c9;border-radius:8px;padding:20px;margin:20px 0;">
                <p style="margin:0 0 10px;font-weight:700;color: #1B5E20;">Stage 1 — KYC Result</p>
                <p style="margin:0;font-size:1.1rem; color: #1B5E20; font-weight: 600;">✅ Assessment Complete</p>
                <p style="margin:5px 0 0 0; font-size: 0.85rem; color: #666;">Our automated identity and verification checks have been finalized.</p>
            </div>
            <div style="background:#F8F9FA;padding:15px;border-left:4px solid #2E7D32;border-radius:0 6px 6px 0;margin:20px 0;">
                <p style="margin:0 0 8px;font-weight:600;">What Happens Next:</p>
                <ul style="margin:0;padding-left:20px;color:#555;">
                    <li>Our Compliance team is reviewing the KYC findings.</li>
                    <li>Subject to their review, your application will proceed to <strong>AML Risk Assessment (Stage 2)</strong>.</li>
                    <li>You will receive another update once Stage 2 is complete.</li>
                </ul>
            </div>
            <p>You can log in to your <strong>Participant Portal</strong> to track real-time status.</p>
            <p>Regards,<br><strong>Kinetix Compliance Team</strong><br>
            <span style="font-size:0.8rem;color:#999;">This is an automated message. Please do not reply.</span></p>
        </div>
    </div></div></body></html>"""
    return _send_email(recipient_email, subject, html)


def send_aml_stage_complete_email(recipient_email: str, tracking_id: str, risk_level: str) -> bool:
    """Sent when AML Risk Stage 2 agent check completes."""
    risk_color = {
        "LOW": "#1B5E20", "MEDIUM": "#F57C00",
        "HIGH": "#C62828", "CRITICAL": "#B71C1C"
    }.get(risk_level, "#333")
    risk_icon = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴", "CRITICAL": "⛔"}.get(risk_level, "⚪")

    subject = f"AML Assessment Complete — [{tracking_id}] | Kinetix"
    html = f"""
    <html><body style="font-family:Inter,sans-serif;line-height:1.6;color:#333;background:#f8f9fa;">
    <div style="max-width:600px;margin:0 auto;padding:20px;">
    <div style="background:white;border-radius:10px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.08);">
        <div style="background:#1B5E20;padding:25px;text-align:center;">
            <h1 style="color:white;margin:0;letter-spacing:3px;">KINETIX</h1>
            <p style="color:rgba(255,255,255,0.8);margin:5px 0 0 0;font-size:0.85rem;">Compliance Update</p>
        </div>
        <div style="padding:30px;">
            <p>Dear Applicant,</p>
            <p>Stage 2 of your application review (<strong>{tracking_id}</strong>) — the <strong>AML (Anti-Money Laundering) Risk Assessment</strong> — has been completed by our compliance systems.</p>
            <div style="background:#f1f8e9;border:1px solid #c8e6c9;border-radius:8px;padding:20px;margin:20px 0;">
                <p style="margin:0 0 10px;font-weight:700;color:#1B5E20;">Stage 2 — AML Risk Assessment</p>
                <p style="margin:0;font-size:1.1rem; color: #1B5E20; font-weight: 600;">✅ Analysis Finalized</p>
                <p style="margin:5px 0 0 0; font-size: 0.85rem; color: #666;">Our deep-scrutiny screening and risk profiling is complete.</p>
            </div>
            <p>Our Compliance Officers are now conducting their final review. A decision on your application will be communicated shortly.</p>
            <p>Regards,<br><strong>Kinetix Compliance Team</strong><br>
            <span style="font-size:0.8rem;color:#999;">This is an automated message. Please do not reply.</span></p>
        </div>
    </div></div></body></html>"""
    return _send_email(recipient_email, subject, html)


def send_kyc_rejected_email(recipient_email: str, tracking_id: str, remarks: str = "") -> bool:
    """Sent when admin rejects an application at the KYC stage."""
    subject = f"Application Update — [{tracking_id}] | Kinetix"
    html = f"""
    <html><body style="font-family:Inter,sans-serif;line-height:1.6;color:#333;background:#f8f9fa;">
    <div style="max-width:600px;margin:0 auto;padding:20px;">
    <div style="background:white;border-radius:10px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.08);">
        <div style="background:#B71C1C;padding:25px;text-align:center;">
            <h1 style="color:white;margin:0;letter-spacing:3px;">KINETIX</h1>
            <p style="color:rgba(255,255,255,0.8);margin:5px 0 0 0;font-size:0.85rem;">Compliance Decision</p>
        </div>
        <div style="padding:30px;">
            <p>Dear Applicant,</p>
            <p>We regret to inform you that your institutional onboarding application (<strong>{tracking_id}</strong>) has not passed our <strong>KYC (Know Your Customer)</strong> review.</p>
            <div style="background:#ffebee;border:1px solid #ef9a9a;border-radius:8px;padding:20px;margin:20px 0;">
                <p style="margin:0 0 10px;font-weight:700;color:#B71C1C;">Status: ⛔ Not Approved at KYC Stage</p>
                {f'<p style="margin:0;color:#555;font-size:0.9rem;"><strong>Reason:</strong> {remarks}</p>' if remarks else ''}
            </div>
            <p>If you believe this decision was made in error, or wish to provide additional information, please contact our compliance team.</p>
            <p>Regards,<br><strong>Kinetix Compliance Team</strong><br>
            <span style="font-size:0.8rem;color:#999;">This is an automated message.</span></p>
        </div>
    </div></div></body></html>"""
    return _send_email(recipient_email, subject, html)
