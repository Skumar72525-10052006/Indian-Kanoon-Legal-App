"""
Notification service for sending OTP via email and SMS.
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# Email Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)
FROM_NAME = os.getenv("FROM_NAME", "Indian Kanoon Legal App")

# SMS functionality removed - using email OTP only


async def send_email(to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
    """
    Send an email using SMTP.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        body: Plain text body
        html_body: Optional HTML body
    
    Returns:
        True if email sent successfully, False otherwise
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        print("Warning: SMTP credentials not configured. Email not sent.")
        print(f"Would send email to {to_email}: {subject}")
        print(f"Body: {body}")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{FROM_NAME} <{FROM_EMAIL}>"
        msg['To'] = to_email
        
        # Add plain text part
        text_part = MIMEText(body, 'plain')
        msg.attach(text_part)
        
        # Add HTML part if provided
        if html_body:
            html_part = MIMEText(html_body, 'html')
            msg.attach(html_part)
        
        # Send email
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"✓ Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"✗ Failed to send email to {to_email}: {e}")
        return False


# SMS functionality removed - using email OTP only


async def send_otp_email(to_email: str, otp: str, purpose: str = "verification") -> bool:
    """
    Send OTP via email.
    
    Args:
        to_email: Recipient email address
        otp: OTP code
        purpose: Purpose of OTP (verification, password reset, etc.)
    
    Returns:
        True if email sent successfully, False otherwise
    """
    subject = f"Your OTP for {purpose}"
    
    body = f"""
Hello,

Your OTP for {purpose} is: {otp}

This OTP is valid for 10 minutes.

If you did not request this OTP, please ignore this email.

Best regards,
Indian Kanoon Legal App Team
    """
    
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .otp-box {{ background-color: #f4f4f4; border: 2px solid #4CAF50; border-radius: 5px; padding: 20px; text-align: center; margin: 20px 0; }}
        .otp-code {{ font-size: 32px; font-weight: bold; color: #4CAF50; letter-spacing: 5px; }}
        .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>OTP Verification</h2>
        <p>Hello,</p>
        <p>Your OTP for <strong>{purpose}</strong> is:</p>
        <div class="otp-box">
            <div class="otp-code">{otp}</div>
        </div>
        <p>This OTP is valid for <strong>10 minutes</strong>.</p>
        <p>If you did not request this OTP, please ignore this email.</p>
        <div class="footer">
            <p>Best regards,<br>Indian Kanoon Legal App Team</p>
        </div>
    </div>
</body>
</html>
    """
    
    return await send_email(to_email, subject, body, html_body)


async def send_otp_notification(email: str, otp: str, purpose: str = "verification") -> dict:
    """
    Send OTP via email only.

    Args:
        email: Recipient email address
        otp: OTP code
        purpose: Purpose of OTP

    Returns:
        Dictionary with email status
    """
    email_sent = await send_otp_email(email, otp, purpose)

    return {
        "email_sent": email_sent,
        "success": email_sent
    }


async def send_welcome_email(to_email: str, full_name: str) -> bool:
    """Send welcome email to new user"""
    subject = "Welcome to Indian Kanoon Legal App!"
    
    body = f"""
Hello {full_name},

Welcome to Indian Kanoon Legal App!

Your account has been successfully created. You can now access AI-powered summaries of legal documents in English.

Thank you for joining us!

Best regards,
Indian Kanoon Legal App Team
    """
    
    html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px; }}
        .content {{ padding: 20px 0; }}
        .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to Indian Kanoon Legal App!</h1>
        </div>
        <div class="content">
            <p>Hello <strong>{full_name}</strong>,</p>
            <p>Your account has been successfully created. You can now access AI-powered summaries of legal documents in English.</p>
            <p>Thank you for joining us!</p>
        </div>
        <div class="footer">
            <p>Best regards,<br>Indian Kanoon Legal App Team</p>
        </div>
    </div>
</body>
</html>
    """
    
    return await send_email(to_email, subject, body, html_body)

