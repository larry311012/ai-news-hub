"""
Email Service for Payment Notifications
========================================

Sends payment-related emails to users:
- Payment receipts
- Payment failure notifications
- Subscription cancellation confirmations
- Trial ending reminders

Uses the existing email utility with custom templates.
"""
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
from pathlib import Path

# Import existing email utility
import sys
sys.path.append(str(Path(__file__).parent.parent))
from utils.email import send_email, render_email_template

APP_URL = os.getenv("APP_URL", "http://localhost:3000")


async def send_payment_receipt(user_email: str, user_name: str, invoice_data: Dict[str, Any]) -> bool:
    """
    Send payment receipt email with invoice PDF link

    Args:
        user_email: User's email address
        user_name: User's full name
        invoice_data: Dictionary containing invoice information
            - amount_paid: Amount in cents
            - currency: Currency code (usd, etc.)
            - invoice_pdf: PDF download URL
            - hosted_invoice_url: Hosted invoice page URL
            - period_start: Billing period start date
            - period_end: Billing period end date
            - plan_name: Subscription plan name

    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        # Format amount
        amount_dollars = invoice_data.get("amount_paid", 0) / 100
        currency = invoice_data.get("currency", "usd").upper()
        amount_formatted = f"${amount_dollars:.2f}" if currency == "USD" else f"{amount_dollars:.2f} {currency}"

        # Format dates
        period_start = invoice_data.get("period_start")
        period_end = invoice_data.get("period_end")
        billing_period = ""
        if period_start and period_end:
            start_str = period_start.strftime("%B %d, %Y") if isinstance(period_start, datetime) else str(period_start)
            end_str = period_end.strftime("%B %d, %Y") if isinstance(period_end, datetime) else str(period_end)
            billing_period = f"{start_str} - {end_str}"

        # Build HTML content
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0;">Payment Receipt</h1>
            </div>

            <div style="padding: 30px; background-color: #f9f9f9;">
                <p style="font-size: 16px;">Hi {user_name},</p>

                <p style="font-size: 16px;">Thank you for your payment! Your subscription has been successfully renewed.</p>

                <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #667eea;">
                    <h3 style="margin-top: 0; color: #667eea;">Payment Details</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; border-bottom: 1px solid #eee;"><strong>Amount Paid:</strong></td>
                            <td style="padding: 8px 0; border-bottom: 1px solid #eee; text-align: right;">{amount_formatted}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; border-bottom: 1px solid #eee;"><strong>Plan:</strong></td>
                            <td style="padding: 8px 0; border-bottom: 1px solid #eee; text-align: right;">{invoice_data.get('plan_name', 'Pro Plan')}</td>
                        </tr>
                        {f'<tr><td style="padding: 8px 0; border-bottom: 1px solid #eee;"><strong>Billing Period:</strong></td><td style="padding: 8px 0; border-bottom: 1px solid #eee; text-align: right;">{billing_period}</td></tr>' if billing_period else ''}
                        <tr>
                            <td style="padding: 8px 0;"><strong>Payment Date:</strong></td>
                            <td style="padding: 8px 0; text-align: right;">{datetime.now().strftime('%B %d, %Y')}</td>
                        </tr>
                    </table>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    {f'<a href="{invoice_data.get("invoice_pdf")}" style="display: inline-block; background-color: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 5px;">Download PDF Receipt</a>' if invoice_data.get("invoice_pdf") else ''}
                    {f'<a href="{invoice_data.get("hosted_invoice_url")}" style="display: inline-block; background-color: #764ba2; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; margin: 5px;">View Invoice Online</a>' if invoice_data.get("hosted_invoice_url") else ''}
                </div>

                <p style="font-size: 14px; color: #666;">
                    Your subscription will continue until the end of your current billing period.
                    You can manage your subscription and payment methods in your
                    <a href="{APP_URL}/profile" style="color: #667eea; text-decoration: none;">account settings</a>.
                </p>

                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">

                <p style="font-size: 12px; color: #999; text-align: center;">
                    Questions? Contact us at support@example.com<br>
                    AI Post Generator - Automate Your Social Media
                </p>
            </div>
        </body>
        </html>
        """

        # Plain text version
        text_content = f"""
Payment Receipt
================

Hi {user_name},

Thank you for your payment! Your subscription has been successfully renewed.

Payment Details:
- Amount Paid: {amount_formatted}
- Plan: {invoice_data.get('plan_name', 'Pro Plan')}
{f'- Billing Period: {billing_period}' if billing_period else ''}
- Payment Date: {datetime.now().strftime('%B %d, %Y')}

{f'View Invoice: {invoice_data.get("hosted_invoice_url")}' if invoice_data.get("hosted_invoice_url") else ''}

Your subscription will continue until the end of your current billing period.
Manage your subscription at: {APP_URL}/profile

Questions? Contact us at support@example.com
        """

        success = send_email(
            to_email=user_email,
            subject=f"Payment Receipt - {amount_formatted}",
            html_content=html_content,
            text_content=text_content
        )

        if success:
            logger.info(f"Payment receipt sent to {user_email}")
        else:
            logger.error(f"Failed to send payment receipt to {user_email}")

        return success

    except Exception as e:
        logger.error(f"Error sending payment receipt: {str(e)}")
        return False


async def send_payment_failed_email(
    user_email: str,
    user_name: str,
    amount: int,
    currency: str = "usd",
    retry_url: Optional[str] = None
) -> bool:
    """
    Send payment failure notification with retry instructions

    Args:
        user_email: User's email address
        user_name: User's full name
        amount: Amount in cents that failed
        currency: Currency code
        retry_url: URL to update payment method and retry

    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        amount_dollars = amount / 100
        currency_upper = currency.upper()
        amount_formatted = f"${amount_dollars:.2f}" if currency_upper == "USD" else f"{amount_dollars:.2f} {currency_upper}"

        if not retry_url:
            retry_url = f"{APP_URL}/profile"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #ef4444; padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0;">Payment Failed</h1>
            </div>

            <div style="padding: 30px; background-color: #f9f9f9;">
                <p style="font-size: 16px;">Hi {user_name},</p>

                <p style="font-size: 16px;">
                    We were unable to process your payment of <strong>{amount_formatted}</strong> for your AI Post Generator subscription.
                </p>

                <div style="background-color: #fef2f2; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ef4444;">
                    <h3 style="margin-top: 0; color: #ef4444;">What This Means</h3>
                    <p style="margin: 0;">
                        Your subscription is still active for now, but if we cannot process payment soon,
                        your access may be limited or suspended.
                    </p>
                </div>

                <h3 style="color: #667eea;">How to Fix This</h3>
                <ol style="font-size: 15px; line-height: 1.8;">
                    <li>Check that your payment method has sufficient funds</li>
                    <li>Verify your card hasn't expired</li>
                    <li>Update your payment method in your account settings</li>
                    <li>We'll automatically retry the payment in a few days</li>
                </ol>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{retry_url}" style="display: inline-block; background-color: #667eea; color: white; padding: 14px 35px; text-decoration: none; border-radius: 5px; font-size: 16px; font-weight: bold;">
                        Update Payment Method
                    </a>
                </div>

                <p style="font-size: 14px; color: #666;">
                    If you continue to experience issues or have questions, please contact our support team
                    at support@example.com.
                </p>

                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">

                <p style="font-size: 12px; color: #999; text-align: center;">
                    AI Post Generator - Automate Your Social Media
                </p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
Payment Failed
==============

Hi {user_name},

We were unable to process your payment of {amount_formatted} for your AI Post Generator subscription.

What This Means:
Your subscription is still active for now, but if we cannot process payment soon, your access may be limited or suspended.

How to Fix This:
1. Check that your payment method has sufficient funds
2. Verify your card hasn't expired
3. Update your payment method: {retry_url}
4. We'll automatically retry the payment in a few days

If you have questions, contact: support@example.com
        """

        success = send_email(
            to_email=user_email,
            subject="Payment Failed - Action Required",
            html_content=html_content,
            text_content=text_content
        )

        if success:
            logger.info(f"Payment failed email sent to {user_email}")
        else:
            logger.error(f"Failed to send payment failed email to {user_email}")

        return success

    except Exception as e:
        logger.error(f"Error sending payment failed email: {str(e)}")
        return False


async def send_subscription_canceled_email(
    user_email: str,
    user_name: str,
    cancel_date: str,
    access_until: Optional[datetime] = None
) -> bool:
    """
    Send subscription cancellation confirmation

    Args:
        user_email: User's email address
        user_name: User's full name
        cancel_date: Date when cancellation was requested
        access_until: Date when access will end (for end-of-period cancellations)

    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        access_text = ""
        if access_until:
            access_date = access_until.strftime("%B %d, %Y") if isinstance(access_until, datetime) else str(access_until)
            access_text = f"You'll continue to have access to your Pro features until <strong>{access_date}</strong>."
        else:
            access_text = "Your access to Pro features has ended."

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #6b7280; padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0;">Subscription Canceled</h1>
            </div>

            <div style="padding: 30px; background-color: #f9f9f9;">
                <p style="font-size: 16px;">Hi {user_name},</p>

                <p style="font-size: 16px;">
                    We're sorry to see you go! Your AI Post Generator subscription has been canceled as of {cancel_date}.
                </p>

                <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #6b7280;">
                    <p style="margin: 0; font-size: 15px;">
                        {access_text}
                    </p>
                </div>

                <h3 style="color: #667eea;">What Happens Next?</h3>
                <ul style="font-size: 15px; line-height: 1.8;">
                    {f'<li>Your Pro features will remain active until {access_until.strftime("%B %d, %Y") if isinstance(access_until, datetime) else str(access_until)}</li>' if access_until else '<li>You now have access to our Free plan features</li>'}
                    <li>Your data and posts are safe and will be preserved</li>
                    <li>You can reactivate your subscription at any time</li>
                    <li>No further charges will be made to your payment method</li>
                </ul>

                <div style="background-color: #f0f9ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #0284c7;">We'd Love Your Feedback</h3>
                    <p style="margin-bottom: 15px;">
                        Help us improve! Let us know why you canceled so we can make AI Post Generator better.
                    </p>
                    <a href="{APP_URL}/feedback" style="display: inline-block; background-color: #0284c7; color: white; padding: 10px 25px; text-decoration: none; border-radius: 5px;">
                        Share Feedback
                    </a>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{APP_URL}/profile" style="display: inline-block; background-color: #667eea; color: white; padding: 14px 35px; text-decoration: none; border-radius: 5px; font-size: 16px; font-weight: bold;">
                        Reactivate Subscription
                    </a>
                </div>

                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">

                <p style="font-size: 12px; color: #999; text-align: center;">
                    Questions? Contact us at support@example.com<br>
                    AI Post Generator - Automate Your Social Media
                </p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
Subscription Canceled
=====================

Hi {user_name},

We're sorry to see you go! Your AI Post Generator subscription has been canceled as of {cancel_date}.

{access_text.replace('<strong>', '').replace('</strong>', '')}

What Happens Next:
{f'- Your Pro features will remain active until {access_until.strftime("%B %d, %Y") if isinstance(access_until, datetime) else str(access_until)}' if access_until else '- You now have access to our Free plan features'}
- Your data and posts are safe and will be preserved
- You can reactivate your subscription at any time
- No further charges will be made to your payment method

Reactivate your subscription: {APP_URL}/profile

Questions? Contact us at support@example.com
        """

        success = send_email(
            to_email=user_email,
            subject="Your Subscription Has Been Canceled",
            html_content=html_content,
            text_content=text_content
        )

        if success:
            logger.info(f"Subscription canceled email sent to {user_email}")
        else:
            logger.error(f"Failed to send subscription canceled email to {user_email}")

        return success

    except Exception as e:
        logger.error(f"Error sending subscription canceled email: {str(e)}")
        return False


async def send_trial_ending_email(
    user_email: str,
    user_name: str,
    trial_end_date: datetime,
    upgrade_url: Optional[str] = None
) -> bool:
    """
    Send trial ending reminder (3 days before trial ends)

    Args:
        user_email: User's email address
        user_name: User's full name
        trial_end_date: Date when trial ends
        upgrade_url: URL to upgrade subscription

    Returns:
        True if email sent successfully, False otherwise
    """
    try:
        if not upgrade_url:
            upgrade_url = f"{APP_URL}/profile"

        days_until_end = (trial_end_date - datetime.now()).days
        end_date_str = trial_end_date.strftime("%B %d, %Y")

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0;">Your Trial is Ending Soon</h1>
            </div>

            <div style="padding: 30px; background-color: #f9f9f9;">
                <p style="font-size: 16px;">Hi {user_name},</p>

                <p style="font-size: 16px;">
                    Your free trial of AI Post Generator Pro will end in <strong>{days_until_end} day{'s' if days_until_end != 1 else ''}</strong>
                    on <strong>{end_date_str}</strong>.
                </p>

                <div style="background-color: #fffbeb; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #f59e0b;">
                    <h3 style="margin-top: 0; color: #d97706;">Don't Lose Your Progress</h3>
                    <p style="margin: 0;">
                        Upgrade now to continue enjoying unlimited posts, premium AI models, and priority support.
                    </p>
                </div>

                <h3 style="color: #667eea;">What You've Accomplished During Your Trial</h3>
                <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p style="font-size: 15px; margin: 10px 0;">✨ Generated engaging social media content</p>
                    <p style="font-size: 15px; margin: 10px 0;">🚀 Saved hours of manual content creation</p>
                    <p style="font-size: 15px; margin: 10px 0;">📈 Improved your social media presence</p>
                </div>

                <h3 style="color: #667eea;">Pro Plan Benefits</h3>
                <ul style="font-size: 15px; line-height: 1.8;">
                    <li><strong>Unlimited Posts</strong> - Generate as many posts as you need</li>
                    <li><strong>Premium AI Models</strong> - Access to GPT-4 and Claude</li>
                    <li><strong>Priority Support</strong> - Get help when you need it</li>
                    <li><strong>Advanced Analytics</strong> - Track your content performance</li>
                    <li><strong>All Platforms</strong> - Twitter, LinkedIn, Instagram, Threads</li>
                </ul>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{upgrade_url}" style="display: inline-block; background-color: #f59e0b; color: white; padding: 16px 40px; text-decoration: none; border-radius: 5px; font-size: 18px; font-weight: bold; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                        Upgrade to Pro - $9.99/month
                    </a>
                </div>

                <p style="font-size: 14px; color: #666; text-align: center;">
                    Cancel anytime. No questions asked. 30-day money-back guarantee.
                </p>

                <div style="background-color: #f3f4f6; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0; font-size: 13px; color: #6b7280; text-align: center;">
                        After your trial ends, you'll still have access to our Free plan with 5 posts per day.
                    </p>
                </div>

                <hr style="border: none; border-top: 1px solid #ddd; margin: 30px 0;">

                <p style="font-size: 12px; color: #999; text-align: center;">
                    Questions? Contact us at support@example.com<br>
                    AI Post Generator - Automate Your Social Media
                </p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
Your Trial is Ending Soon
==========================

Hi {user_name},

Your free trial of AI Post Generator Pro will end in {days_until_end} day{'s' if days_until_end != 1 else ''} on {end_date_str}.

Don't Lose Your Progress!
Upgrade now to continue enjoying unlimited posts, premium AI models, and priority support.

Pro Plan Benefits:
- Unlimited Posts - Generate as many posts as you need
- Premium AI Models - Access to GPT-4 and Claude
- Priority Support - Get help when you need it
- Advanced Analytics - Track your content performance
- All Platforms - Twitter, LinkedIn, Instagram, Threads

Upgrade to Pro - $9.99/month: {upgrade_url}

Cancel anytime. No questions asked. 30-day money-back guarantee.

After your trial ends, you'll still have access to our Free plan with 5 posts per day.

Questions? Contact us at support@example.com
        """

        success = send_email(
            to_email=user_email,
            subject=f"Your Trial Ends in {days_until_end} Day{'s' if days_until_end != 1 else ''}",
            html_content=html_content,
            text_content=text_content
        )

        if success:
            logger.info(f"Trial ending email sent to {user_email}")
        else:
            logger.error(f"Failed to send trial ending email to {user_email}")

        return success

    except Exception as e:
        logger.error(f"Error sending trial ending email: {str(e)}")
        return False
