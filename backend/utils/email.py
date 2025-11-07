"""
Email utilities for sending verification and notification emails
"""
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Email configuration
EMAIL_MODE = os.getenv("EMAIL_MODE", "development")  # development, smtp, sendgrid
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "noreply@example.com")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "AI Post Generator")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
APP_URL = os.getenv("APP_URL", "http://localhost:3000")


def render_email_template(template_name: str, **kwargs) -> str:
    """
    Render email template with provided variables.

    Args:
        template_name: Name of the template file (without .html)
        **kwargs: Variables to replace in template

    Returns:
        Rendered HTML string
    """
    template_path = Path(__file__).parent.parent / "templates" / f"{template_name}.html"

    if not template_path.exists():
        logger.warning(f"Template not found: {template_path}, using fallback")
        return _get_fallback_template(template_name, **kwargs)

    with open(template_path, "r") as f:
        template = f.read()

    # Simple template variable replacement
    for key, value in kwargs.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))

    return template


def _get_fallback_template(template_name: str, **kwargs) -> str:
    """
    Generate fallback email template if file not found.

    Args:
        template_name: Name of the template
        **kwargs: Template variables

    Returns:
        Simple HTML email template
    """
    if template_name == "email_verification":
        verification_link = kwargs.get("verification_link", "#")
        full_name = kwargs.get("full_name", "User")
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2>Welcome to AI Post Generator!</h2>
                <p>Hi {full_name},</p>
                <p>Thank you for registering! Please verify your email address by clicking the button below:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{verification_link}" style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
                        Verify Email Address
                    </a>
                </div>
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #666;">{verification_link}</p>
                <p style="color: #999; font-size: 12px; margin-top: 30px;">
                    This link will expire in 24 hours. If you didn't create an account, please ignore this email.
                </p>
            </div>
        </body>
        </html>
        """
    elif template_name == "password_reset":
        reset_link = kwargs.get("reset_link", "#")
        full_name = kwargs.get("full_name", "User")
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2>Password Reset Request</h2>
                <p>Hi {full_name},</p>
                <p>We received a request to reset your password. Click the button below to create a new password:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{reset_link}" style="background-color: #2196F3; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
                        Reset Password
                    </a>
                </div>
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #666;">{reset_link}</p>
                <p style="color: #999; font-size: 12px; margin-top: 30px;">
                    This link will expire in 1 hour. If you didn't request a password reset, please ignore this email.
                </p>
            </div>
        </body>
        </html>
        """
    elif template_name == "welcome":
        full_name = kwargs.get("full_name", "User")
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2>Welcome to AI Post Generator!</h2>
                <p>Hi {full_name},</p>
                <p>Your email has been verified successfully. You can now access all features of AI Post Generator.</p>
                <p>Get started by:</p>
                <ul>
                    <li>Adding your API keys for AI services</li>
                    <li>Connecting your social media accounts</li>
                    <li>Creating your first post</li>
                </ul>
                <p>If you have any questions, feel free to reach out to our support team.</p>
                <p>Happy posting!</p>
            </div>
        </body>
        </html>
        """
    else:
        return "<html><body><p>Email content</p></body></html>"


def send_email_smtp(
    to_email: str, subject: str, html_content: str, text_content: Optional[str] = None
) -> bool:
    """
    Send email via SMTP.

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email content
        text_content: Plain text email content (optional)

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        # Create message
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        # Add text and HTML parts
        if text_content:
            part1 = MIMEText(text_content, "plain")
            msg.attach(part1)

        part2 = MIMEText(html_content, "html")
        msg.attach(part2)

        # Send email
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)

        logger.info(f"Email sent via SMTP to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Error sending email via SMTP: {str(e)}")
        return False


def send_email_sendgrid(
    to_email: str, subject: str, html_content: str, text_content: Optional[str] = None
) -> bool:
    """
    Send email via SendGrid API.

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email content
        text_content: Plain text email content (optional)

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail, Email, To, Content

        message = Mail(
            from_email=Email(SMTP_FROM_EMAIL, SMTP_FROM_NAME),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_content),
        )

        if text_content:
            message.plain_text_content = Content("text/plain", text_content)

        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)

        logger.info(f"Email sent via SendGrid to {to_email}, status: {response.status_code}")
        return True

    except Exception as e:
        logger.error(f"Error sending email via SendGrid: {str(e)}")
        return False


def send_email(
    to_email: str, subject: str, html_content: str, text_content: Optional[str] = None
) -> bool:
    """
    Send email using configured method (development, SMTP, or SendGrid).

    Args:
        to_email: Recipient email address
        subject: Email subject
        html_content: HTML email content
        text_content: Plain text email content (optional)

    Returns:
        True if sent successfully (always True in development mode)
    """
    if EMAIL_MODE == "development":
        # Log email to console instead of sending
        logger.info("=" * 80)
        logger.info("DEVELOPMENT MODE - Email not sent, logging to console:")
        logger.info(f"To: {to_email}")
        logger.info(f"Subject: {subject}")
        logger.info("-" * 80)
        if text_content:
            logger.info("Plain Text Content:")
            logger.info(text_content)
            logger.info("-" * 80)
        logger.info("HTML Content:")
        logger.info(html_content)
        logger.info("=" * 80)
        return True

    elif EMAIL_MODE == "smtp":
        return send_email_smtp(to_email, subject, html_content, text_content)

    elif EMAIL_MODE == "sendgrid":
        return send_email_sendgrid(to_email, subject, html_content, text_content)

    else:
        logger.error(f"Unknown EMAIL_MODE: {EMAIL_MODE}")
        return False


def send_verification_email(user, token: str) -> bool:
    """
    Send email verification email to user.

    Args:
        user: User object
        token: Verification token

    Returns:
        True if sent successfully
    """
    verification_link = f"{APP_URL}/verify-email/{token}"

    html_content = render_email_template(
        "email_verification",
        full_name=user.full_name,
        verification_link=verification_link,
        app_url=APP_URL,
    )

    text_content = f"""
Welcome to AI Post Generator!

Hi {user.full_name},

Thank you for registering! Please verify your email address by visiting:

{verification_link}

This link will expire in 24 hours.

If you didn't create an account, please ignore this email.
    """

    return send_email(
        to_email=user.email,
        subject="Verify Your Email Address",
        html_content=html_content,
        text_content=text_content,
    )


def send_password_reset_email(user, token: str) -> bool:
    """
    Send password reset email to user.

    Args:
        user: User object
        token: Password reset token

    Returns:
        True if sent successfully
    """
    reset_link = f"{APP_URL}/reset-password/{token}"

    html_content = render_email_template(
        "password_reset", full_name=user.full_name, reset_link=reset_link, app_url=APP_URL
    )

    text_content = f"""
Password Reset Request

Hi {user.full_name},

We received a request to reset your password. Visit this link to create a new password:

{reset_link}

This link will expire in 1 hour.

If you didn't request a password reset, please ignore this email.
    """

    return send_email(
        to_email=user.email,
        subject="Reset Your Password",
        html_content=html_content,
        text_content=text_content,
    )


def send_welcome_email(user) -> bool:
    """
    Send welcome email to user after verification.

    Args:
        user: User object

    Returns:
        True if sent successfully
    """
    html_content = render_email_template("welcome", full_name=user.full_name, app_url=APP_URL)

    text_content = f"""
Welcome to AI Post Generator!

Hi {user.full_name},

Your email has been verified successfully. You can now access all features of AI Post Generator.

Get started by:
- Adding your API keys for AI services
- Connecting your social media accounts
- Creating your first post

If you have any questions, feel free to reach out to our support team.

Happy posting!
    """

    return send_email(
        to_email=user.email,
        subject="Welcome to AI Post Generator!",
        html_content=html_content,
        text_content=text_content,
    )
