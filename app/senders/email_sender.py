"""
Enhanced Email Sender v3
Anti-spam email delivery system with 7-day cooldown and intelligent throttling
"""
import smtplib
import time
import random
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from email.mime.text import MIMEText as MimeText
from email.mime.multipart import MIMEMultipart as MimeMultipart
from email.mime.base import MIMEBase as MimeBase
from email import encoders
import uuid

from ..core.config import config
from ..core.database import db

# Configure logging
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
logger = logging.getLogger(__name__)

class EmailSender:
    """Enhanced email sender with anti-spam measures and cooldown tracking"""
    
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.username = config.GMAIL_USER
        self.password = config.GMAIL_APP_PASSWORD
        
        # Email templates
        self.default_template = self.get_default_template()
        
        # Anti-spam settings
        self.min_delay = config.EMAIL_DELAY_MIN  # 2 minutes
        self.max_delay = config.EMAIL_DELAY_MAX  # 5 minutes
        self.cooldown_days = config.COOLDOWN_DAYS  # 7 days
        
        # Session management
        self.smtp_connection = None
        self.emails_sent_in_session = 0
        self.max_emails_per_session = 10  # Reconnect after 10 emails
    
    def get_default_template(self) -> Dict[str, str]:
        """Get default email template"""
        return {
            'subject': 'Boost Your HVAC Business with Professional Marketing Solutions',
            'body': '''Hello {business_name},

I hope this message finds you well. I'm reaching out because I noticed your HVAC business and wanted to share an opportunity that could significantly boost your customer acquisition.

As a fellow business professional, I understand the challenges of finding quality leads in the competitive HVAC market. That's why I want to introduce you to a proven solution that's helping HVAC contractors nationwide:

🔥 **Professional HVAC Marketing Solutions**
- Custom landing pages designed specifically for HVAC contractors
- Lead generation systems that convert visitors into paying customers
- Professional sales funnels that work 24/7
- Proven strategies that increase customer engagement

Why am I sharing this with you? Because I believe in supporting local HVAC businesses, and I've seen these tools help contractors just like you increase their customer base by 40-60%.

**Special Offer:** You can explore these professional marketing solutions at a significant discount through this exclusive link:
{affiliate_link}

This isn't just another marketing tool - it's a complete system designed by experts who understand the HVAC industry inside and out.

Benefits you'll see:
✅ More qualified leads calling your business
✅ Professional online presence that builds trust
✅ Automated follow-up systems that convert prospects
✅ Mobile-optimized designs that capture leads 24/7

I'm not asking for anything in return - just paying it forward to help fellow business owners succeed. Take a look when you have a moment, and if it seems like a good fit, you can get started right away.

Best regards,
Marketing Partner

P.S. This special pricing is only available for a limited time, so I'd recommend checking it out soon if you're interested in growing your customer base.

---
This message was sent to help grow your business. If you'd prefer not to receive similar opportunities, simply reply with "REMOVE" and I'll respect your preference immediately.'''
        }
    
    def create_smtp_connection(self) -> bool:
        """Create and authenticate SMTP connection"""
        try:
            if self.smtp_connection:
                try:
                    # Test existing connection
                    self.smtp_connection.noop()
                    return True
                except Exception:
                    # Connection is dead, create new one
                    self.smtp_connection = None
            
            if not self.username or not self.password:
                logger.error("Gmail credentials not configured")
                return False
            
            logger.debug("Creating new SMTP connection...")
            self.smtp_connection = smtplib.SMTP(self.smtp_server, self.smtp_port)
            self.smtp_connection.starttls()
            self.smtp_connection.login(self.username, self.password)
            
            self.emails_sent_in_session = 0
            logger.debug("SMTP connection established successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create SMTP connection: {e}")
            self.smtp_connection = None
            return False
    
    def close_smtp_connection(self):
        """Close SMTP connection"""
        if self.smtp_connection:
            try:
                self.smtp_connection.quit()
                logger.debug("SMTP connection closed")
            except Exception as e:
                logger.warning(f"Error closing SMTP connection: {e}")
            finally:
                self.smtp_connection = None
                self.emails_sent_in_session = 0
    
    def create_email_message(self, lead: Dict[str, Any], template: Optional[Dict[str, str]] = None) -> MimeMultipart:
        """Create email message from template"""
        template = template or self.default_template
        
        # Create message
        msg = MimeMultipart()
        msg['From'] = self.username
        msg['To'] = lead['email_address']
        msg['Subject'] = template['subject']
        
        # Add custom headers for better deliverability
        msg['Reply-To'] = self.username
        msg['X-Mailer'] = 'HVAC-Automation/3.0'
        msg['Message-ID'] = f"<{uuid.uuid4()}@hvac-automation.local>"
        
        # Personalize email body
        body = template['body'].format(
            business_name=lead.get('business_name', 'Business Owner'),
            address=lead.get('address', ''),
            phone=lead.get('phone', ''),
            website=lead.get('website', ''),
            affiliate_link=config.FIVERR_AFFILIATE_LINK
        )
        
        # Attach body
        msg.attach(MimeText(body, 'plain'))
        
        return msg
    
    def send_single_email(self, lead: Dict[str, Any], template: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Send email to a single lead"""
        campaign_id = str(uuid.uuid4())[:8]
        
        try:
            # Check if email was sent recently (anti-spam)
            if db.check_email_sent_recently(lead['id'], self.cooldown_days):
                logger.debug(f"Skipping {lead['business_name']}: email sent within {self.cooldown_days} days")
                return {
                    'status': 'skipped',
                    'error': f'Email sent within {self.cooldown_days} days',
                    'lead_id': lead['id'],
                    'campaign_id': campaign_id
                }
            
            # Create SMTP connection if needed
            if not self.create_smtp_connection():
                return {
                    'status': 'failed',
                    'error': 'Failed to create SMTP connection',
                    'lead_id': lead['id'],
                    'campaign_id': campaign_id
                }
            
            # Create email message
            msg = self.create_email_message(lead, template)
            
            # Send email
            if self.smtp_connection:
                self.smtp_connection.send_message(msg)
            self.emails_sent_in_session += 1
            
            # Log successful send
            send_data = {
                'lead_id': lead['id'],
                'email_address': lead['email_address'],
                'subject': msg['Subject'],
                'sent_date': datetime.now(),
                'status': 'sent',
                'response_code': '250',
                'campaign_id': campaign_id
            }
            
            db.insert_email_send(send_data)
            
            logger.info(f"✅ Email sent to {lead['business_name']} ({lead['email_address']})")
            
            # Close connection if we've sent too many emails
            if self.emails_sent_in_session >= self.max_emails_per_session:
                self.close_smtp_connection()
            
            return {
                'status': 'sent',
                'lead_id': lead['id'],
                'campaign_id': campaign_id,
                'email_address': lead['email_address']
            }
            
        except smtplib.SMTPRecipientsRefused as e:
            error_msg = f"Recipient refused: {str(e)}"
            logger.warning(f"❌ {lead['business_name']}: {error_msg}")
            
            send_data = {
                'lead_id': lead['id'],
                'email_address': lead['email_address'],
                'subject': template['subject'] if template else self.default_template['subject'],
                'sent_date': datetime.now(),
                'status': 'failed',
                'error_message': error_msg,
                'campaign_id': campaign_id
            }
            
            db.insert_email_send(send_data)
            
            return {
                'status': 'failed',
                'error': error_msg,
                'lead_id': lead['id'],
                'campaign_id': campaign_id
            }
            
        except smtplib.SMTPException as e:
            error_msg = f"SMTP error: {str(e)}"
            logger.error(f"❌ {lead['business_name']}: {error_msg}")
            
            # Close connection on SMTP errors
            self.close_smtp_connection()
            
            send_data = {
                'lead_id': lead['id'],
                'email_address': lead['email_address'],
                'subject': template['subject'] if template else self.default_template['subject'],
                'sent_date': datetime.now(),
                'status': 'failed',
                'error_message': error_msg,
                'campaign_id': campaign_id
            }
            
            db.insert_email_send(send_data)
            
            return {
                'status': 'failed',
                'error': error_msg,
                'lead_id': lead['id'],
                'campaign_id': campaign_id
            }
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"❌ {lead['business_name']}: {error_msg}")
            
            send_data = {
                'lead_id': lead['id'],
                'email_address': lead['email_address'],
                'subject': template['subject'] if template else self.default_template['subject'],
                'sent_date': datetime.now(),
                'status': 'failed',
                'error_message': error_msg,
                'campaign_id': campaign_id
            }
            
            db.insert_email_send(send_data)
            
            return {
                'status': 'failed',
                'error': error_msg,
                'lead_id': lead['id'],
                'campaign_id': campaign_id
            }
    
    def intelligent_delay(self, email_count: int):
        """Apply intelligent delay between emails"""
        base_delay = random.uniform(self.min_delay, self.max_delay)
        
        # Increase delay as we send more emails
        if email_count > 10:
            base_delay *= 1.5
        elif email_count > 20:
            base_delay *= 2.0
        elif email_count > 30:
            base_delay *= 2.5
        
        # Add random variation (±20%)
        variation = base_delay * 0.2
        delay = base_delay + random.uniform(-variation, variation)
        
        logger.debug(f"Waiting {delay:.1f} seconds before next email...")
        time.sleep(delay)
    
    def send_batch_emails(self, limit: Optional[int] = None, template: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Send emails to multiple leads with anti-spam measures"""
        limit = limit or config.MAX_EMAILS_PER_RUN
        logger.info(f"📧 Starting email sending batch (limit: {limit})...")
        
        start_time = datetime.now()
        total_processed = 0
        total_sent = 0
        total_skipped = 0
        total_failed = 0
        errors = []
        
        try:
            # Get leads ready for sending
            leads = db.get_leads_for_sending(limit)
            logger.info(f"Found {len(leads)} leads ready for email sending")
            
            if not leads:
                return {
                    'total_processed': 0,
                    'total_sent': 0,
                    'total_skipped': 0,
                    'total_failed': 0,
                    'success_rate': 0,
                    'duration': '0:00:00',
                    'errors': ['No leads ready for sending'],
                    'success': False
                }
            
            for i, lead in enumerate(leads):
                try:
                    total_processed += 1
                    
                    logger.debug(f"Processing lead {total_processed}/{len(leads)}: {lead['business_name']}")
                    
                    # Send email
                    result = self.send_single_email(lead, template)
                    
                    if result['status'] == 'sent':
                        total_sent += 1
                    elif result['status'] == 'skipped':
                        total_skipped += 1
                    else:
                        total_failed += 1
                        if result.get('error'):
                            errors.append(f"{lead['business_name']}: {result['error']}")
                    
                    # Apply intelligent delay (except for last email)
                    if i < len(leads) - 1:
                        self.intelligent_delay(total_sent)
                    
                except Exception as e:
                    total_failed += 1
                    error_msg = f"Error processing {lead.get('business_name', 'unknown')}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # Close any remaining connections
            self.close_smtp_connection()
            
            # Calculate duration and success rate
            duration = datetime.now() - start_time
            success_rate = round((total_sent / total_processed * 100) if total_processed > 0 else 0, 1)
            
            # Prepare summary
            summary = {
                'total_processed': total_processed,
                'total_sent': total_sent,
                'total_skipped': total_skipped,
                'total_failed': total_failed,
                'success_rate': success_rate,
                'duration': str(duration).split('.')[0],
                'errors': errors,
                'success': total_sent > 0
            }
            
            # Log completion
            db.log_system_event(
                'INFO',
                'sender',
                f'Email sending completed: {total_sent}/{total_processed} emails sent',
                f'Sent: {total_sent}, Skipped: {total_skipped}, Failed: {total_failed}, Success rate: {success_rate}%'
            )
            
            logger.info(f"✅ Email sending complete: {total_sent}/{total_processed} emails sent")
            return summary
            
        except Exception as e:
            error_msg = f"Email sending batch failed: {str(e)}"
            logger.error(error_msg)
            
            # Ensure connection is closed
            self.close_smtp_connection()
            
            db.log_system_event('ERROR', 'sender', error_msg, None)
            
            return {
                'total_processed': total_processed,
                'total_sent': total_sent,
                'total_skipped': total_skipped,
                'total_failed': total_failed,
                'success_rate': 0,
                'duration': str(datetime.now() - start_time).split('.')[0],
                'errors': errors + [error_msg],
                'success': False
            }
    
    def send_notification_email(self, subject: str, message: str, recipient: Optional[str] = None):
        """Send notification email to admin"""
        recipient = recipient or config.NOTIFICATION_EMAIL
        
        try:
            if not self.create_smtp_connection() or not self.smtp_connection:
                logger.error("Failed to send notification: SMTP connection failed")
                return False
            
            if not recipient:
                logger.error("No notification recipient configured")
                return False
            
            msg = MimeMultipart()
            msg['From'] = self.username or ""
            msg['To'] = recipient
            msg['Subject'] = f"[HVAC Automation] {subject}"
            
            body = f"""HVAC Email Automation System Notification

{message}

Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Server: Production Environment

---
This is an automated notification from your HVAC Email Automation system.
"""
            
            msg.attach(MimeText(body, 'plain'))
            self.smtp_connection.send_message(msg)
            
            logger.info(f"Notification email sent: {subject}")
            self.close_smtp_connection()
            return True
            
        except Exception as e:
            logger.error(f"Failed to send notification email: {e}")
            self.close_smtp_connection()
            return False

def main():
    """Main function for standalone execution"""
    try:
        sender = EmailSender()
        results = sender.send_batch_emails()
        
        print(f"\n📧 Email Sending Results:")
        print(f"   Processed: {results['total_processed']} leads")
        print(f"   Sent: {results['total_sent']} emails")
        print(f"   Skipped: {results['total_skipped']} (cooldown)")
        print(f"   Failed: {results['total_failed']}")
        print(f"   Success Rate: {results['success_rate']}%")
        print(f"   Duration: {results['duration']}")
        
        if results['errors']:
            print(f"   Errors: {len(results['errors'])}")
            for error in results['errors'][:3]:  # Show first 3 errors
                print(f"     - {error}")
        
        return results['total_sent']
        
    except Exception as e:
        logger.error(f"Main execution failed: {e}")
        return 0

if __name__ == "__main__":
    sent_count = main()
    exit(0 if sent_count > 0 else 1)
