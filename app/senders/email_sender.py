"""
Enhanced Email Sender v4 - Mailgun API Integration
High-performance email delivery system with Mailgun REST API
"""
import requests
import time
import random
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import uuid

from ..core.config import config
from ..core.database import db

# Configure logging
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
logger = logging.getLogger(__name__)

class EmailSender:
    """Enhanced email sender using Mailgun REST API"""
    
    def __init__(self):
        # Mailgun Configuration
        self.api_key = config.MAILGUN_API_KEY
        self.domain = config.MAILGUN_DOMAIN
        self.from_email = config.MAILGUN_FROM_EMAIL
        
        # Determine API base URL based on region
        if config.MAILGUN_REGION.upper() == 'EU':
            self.base_url = f"https://api.eu.mailgun.net/v3/{self.domain}"
        else:
            self.base_url = f"https://api.mailgun.net/v3/{self.domain}"
        
        # Email templates
        self.default_template = self.get_default_template()
        
        # Optimized settings for Mailgun
        self.min_delay = config.EMAIL_DELAY_MIN  # 5 seconds
        self.max_delay = config.EMAIL_DELAY_MAX  # 15 seconds
        self.cooldown_days = config.COOLDOWN_DAYS  # 1 day
        
        # API timeout and retry settings
        self.api_timeout = config.MAILGUN_API_TIMEOUT
        self.max_retries = 3
        
        # Session for connection pooling
        self.session = requests.Session()
        self.session.auth = ("api", self.api_key)
        
        logger.info(f"📧 Mailgun Email Sender initialized - Domain: {self.domain}")
    
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
    
    def create_email_data(self, lead: Dict[str, Any], template: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Create email data for Mailgun API"""
        template = template or self.default_template
        
        # Personalize email body
        body = template['body'].format(
            business_name=lead.get('business_name', 'Business Owner'),
            address=lead.get('address', ''),
            phone=lead.get('phone', ''),
            website=lead.get('website', ''),
            affiliate_link=config.FIVERR_AFFILIATE_LINK
        )
        
        # Create email data for Mailgun API
        email_data = {
            'from': self.from_email,
            'to': lead['email_address'],
            'subject': template['subject'],
            'html': body.replace('\n', '<br>\n'),  # Convert to HTML
            'text': body  # Plain text version
        }
        
        # Add tracking if enabled
        if config.MAILGUN_ENABLE_TRACKING:
            email_data['o:tracking'] = 'yes'
        
        if config.MAILGUN_TRACK_CLICKS:
            email_data['o:tracking-clicks'] = 'yes'
            
        if config.MAILGUN_TRACK_OPENS:
            email_data['o:tracking-opens'] = 'yes'
        
        # Add custom variables for tracking
        email_data['v:lead_id'] = str(lead['id'])
        email_data['v:business_name'] = lead.get('business_name', '')
        
        return email_data
    
    def send_via_mailgun_api(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send email via Mailgun REST API with retry logic"""
        url = f"{self.base_url}/messages"
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.post(
                    url,
                    data=email_data,
                    timeout=self.api_timeout
                )
                
                # Parse response
                response_data = response.json() if response.content else {}
                
                if response.status_code == 200:
                    logger.debug(f"✅ Mailgun API success: {response_data}")
                    return {
                        'success': True,
                        'message_id': response_data.get('id', ''),
                        'message': response_data.get('message', 'Queued'),
                        'status_code': response.status_code
                    }
                else:
                    logger.warning(f"⚠️ Mailgun API error {response.status_code}: {response_data}")
                    return {
                        'success': False,
                        'error': response_data.get('message', f'HTTP {response.status_code}'),
                        'status_code': response.status_code
                    }
                    
            except requests.exceptions.Timeout:
                logger.warning(f"⏱️ Mailgun API timeout (attempt {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return {
                    'success': False,
                    'error': f'API timeout after {self.max_retries} attempts',
                    'status_code': 0
                }
                
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Mailgun API request error: {e}")
                return {
                    'success': False,
                    'error': f'Request error: {str(e)}',
                    'status_code': 0
                }
        
        return {
            'success': False,
            'error': f'Failed after {self.max_retries} attempts',
            'status_code': 0
        }
    
    def send_single_email(self, lead: Dict[str, Any], template: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Send email to a single lead via Mailgun API"""
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
            
            # Create email data
            email_data = self.create_email_data(lead, template)
            
            # Send via Mailgun API
            api_result = self.send_via_mailgun_api(email_data)
            
            if api_result['success']:
                # Log successful send
                send_data = {
                    'lead_id': lead['id'],
                    'email_address': lead['email_address'],
                    'subject': email_data['subject'],
                    'sent_date': datetime.now(),
                    'status': 'sent',
                    'response_code': str(api_result['status_code']),
                    'campaign_id': campaign_id,
                    'message_id': api_result.get('message_id', '')
                }
                
                db.insert_email_send(send_data)
                
                logger.info(f"✅ Email sent to {lead['business_name']} ({lead['email_address']}) - ID: {api_result.get('message_id', 'N/A')}")
                
                return {
                    'status': 'sent',
                    'lead_id': lead['id'],
                    'campaign_id': campaign_id,
                    'email_address': lead['email_address'],
                    'message_id': api_result.get('message_id', '')
                }
            else:
                # Log failed send
                error_msg = api_result.get('error', 'Unknown API error')
                
                send_data = {
                    'lead_id': lead['id'],
                    'email_address': lead['email_address'],
                    'subject': email_data['subject'],
                    'sent_date': datetime.now(),
                    'status': 'failed',
                    'error_message': error_msg,
                    'response_code': str(api_result.get('status_code', 0)),
                    'campaign_id': campaign_id
                }
                
                db.insert_email_send(send_data)
                
                logger.error(f"❌ Failed to send to {lead['business_name']}: {error_msg}")
                
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
        """Apply intelligent delay between emails (much shorter for Mailgun)"""
        base_delay = random.uniform(self.min_delay, self.max_delay)
        
        # Slight increase for higher volumes (less aggressive than Gmail)
        if email_count > 50:
            base_delay *= 1.2
        elif email_count > 100:
            base_delay *= 1.5
        
        # Add random variation (±10%)
        variation = base_delay * 0.1
        delay = base_delay + random.uniform(-variation, variation)
        
        logger.debug(f"Waiting {delay:.1f} seconds before next email...")
        time.sleep(delay)
    
    def send_batch_emails(self, limit: Optional[int] = None, template: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Send emails to multiple leads with optimized Mailgun performance"""
        limit = limit or config.MAX_EMAILS_PER_RUN
        logger.info(f"📧 Starting Mailgun email batch (limit: {limit})...")
        
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
                'mailgun_sender',
                f'Mailgun email batch completed: {total_sent}/{total_processed} emails sent',
                f'Sent: {total_sent}, Skipped: {total_skipped}, Failed: {total_failed}, Success rate: {success_rate}%'
            )
            
            logger.info(f"✅ Mailgun batch complete: {total_sent}/{total_processed} emails sent in {duration}")
            return summary
            
        except Exception as e:
            error_msg = f"Mailgun batch sending failed: {str(e)}"
            logger.error(error_msg)
            
            db.log_system_event('ERROR', 'mailgun_sender', error_msg, None)
            
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
        """Send notification email via Mailgun"""
        recipient = recipient or config.NOTIFICATION_EMAIL
        
        try:
            if not recipient:
                logger.error("No notification recipient configured")
                return False
            
            notification_data = {
                'from': self.from_email,
                'to': recipient,
                'subject': f"[HVAC Automation] {subject}",
                'html': f"""
                <h2>HVAC Email Automation System Notification</h2>
                <p>{message}</p>
                <hr>
                <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Server:</strong> Production Environment</p>
                <p><strong>Email Service:</strong> Mailgun API</p>
                <hr>
                <p><em>This is an automated notification from your HVAC Email Automation system.</em></p>
                """,
                'text': f"""HVAC Email Automation System Notification

{message}

Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Server: Production Environment
Email Service: Mailgun API

---
This is an automated notification from your HVAC Email Automation system.
"""
            }
            
            api_result = self.send_via_mailgun_api(notification_data)
            
            if api_result['success']:
                logger.info(f"📬 Notification sent via Mailgun: {subject}")
                return True
            else:
                logger.error(f"❌ Failed to send notification: {api_result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Notification error: {e}")
            return False
    
    def get_email_stats(self) -> Dict[str, Any]:
        """Get email sending statistics"""
        try:
            # This could be extended to query Mailgun's stats API
            # For now, return basic stats from our database
            return {
                'service': 'Mailgun API',
                'domain': self.domain,
                'from_email': self.from_email,
                'daily_limit': config.MAX_EMAILS_PER_DAY,
                'run_limit': config.MAX_EMAILS_PER_RUN,
                'cooldown_days': self.cooldown_days,
                'tracking_enabled': config.MAILGUN_ENABLE_TRACKING
            }
        except Exception as e:
            logger.error(f"Error getting email stats: {e}")
            return {}
    
    def __del__(self):
        """Cleanup session on destruction"""
        if hasattr(self, 'session'):
            self.session.close()

def main():
    """Main function for standalone execution"""
    try:
        sender = EmailSender()
        results = sender.send_batch_emails()
        
        print(f"\n📧 Mailgun Email Sending Results:")
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
