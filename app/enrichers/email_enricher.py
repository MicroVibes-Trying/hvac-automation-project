"""
Enhanced Email Enricher v3
Hunter.io integration with credit optimization and intelligent email discovery
"""
import requests
import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..core.config import config
from ..core.database import db

# Configure logging
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
logger = logging.getLogger(__name__)

class EmailEnricher:
    """Enhanced email enricher with Hunter.io optimization"""

    def __init__(self):
        self.api_key = config.HUNTER_API_KEY
        self.base_url = "https://api.hunter.io/v2"

        # Configure session with retry strategy and connection pooling
        self.session = requests.Session()

        # Set up retry strategy for network resilience
        retry_strategy = Retry(
            total=3,  # Total number of retries
            backoff_factor=1,  # Wait 1, 2, 4 seconds between retries
            status_forcelist=[429, 500, 502, 503, 504],  # HTTP status codes to retry
            allowed_methods=["GET"],  # Only retry GET requests
        )

        # Configure HTTP adapter with retry strategy
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20
        )

        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set headers and timeouts
        self.session.headers.update({
            'User-Agent': 'HVAC-Automation/3.0',
            'Accept': 'application/json',
            'Connection': 'keep-alive'
        })

        # Timeout settings (connect_timeout, read_timeout)
        self.timeout = (10, 30)  # 10s to connect, 30s to read

        # Email patterns for validation
        self.email_patterns = [
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        ]

        # Common business email prefixes (in order of preference)
        self.preferred_prefixes = [
            'info', 'contact', 'sales', 'service', 'office',
            'admin', 'support', 'hello', 'mail', 'business'
        ]

    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        if not email or '@' not in email:
            return False

        for pattern in self.email_patterns:
            if re.match(pattern, email.lower()):
                return True

        return False

    def get_hunter_credits(self) -> Optional[int]:
        """Get remaining Hunter.io credits with enhanced error handling"""
        try:
            logger.debug("Checking Hunter.io credits...")
            response = self.session.get(
                f"{self.base_url}/account",
                params={'api_key': self.api_key},
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                return data.get('data', {}).get('requests', {}).get('searches', {}).get('available', 0)
            else:
                logger.warning(f"Failed to get Hunter credits: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"Error getting Hunter credits: {e}")
            return None

    def log_hunter_usage(self, credits_used: int, operation_type: str):
        """Log Hunter.io credit usage"""
        try:
            remaining_credits = self.get_hunter_credits()

            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO hunter_credits (date, credits_used, credits_remaining, operation_type)
                    VALUES (?, ?, ?, ?)
                """, (datetime.now().date(), credits_used, remaining_credits, operation_type))
                conn.commit()

        except Exception as e:
            logger.error(f"Error logging Hunter usage: {e}")

    def domain_search(self, domain: str) -> Tuple[List[Dict[str, Any]], int]:
        """Search for emails on a domain using Hunter.io with enhanced error handling"""
        try:
            logger.debug(f"Searching domain: {domain}")
            params = {
                'domain': domain,
                'api_key': self.api_key,
                'limit': 10,  # Limit to save credits
                'type': 'generic'  # Focus on generic emails
            }

            response = self.session.get(
                f"{self.base_url}/domain-search",
                params=params,
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                emails = data.get('data', {}).get('emails', [])

                # Log credit usage
                self.log_hunter_usage(1, 'domain_search')

                return emails, 1

            elif response.status_code == 429:
                logger.warning(f"Hunter.io rate limit hit for domain: {domain}")
                time.sleep(60)  # Wait 1 minute
                return [], 0

            else:
                logger.warning(f"Hunter domain search failed for {domain}: {response.status_code}")
                return [], 0

        except Exception as e:
            logger.error(f"Hunter domain search error for {domain}: {e}")
            return [], 0

    def email_finder(self, domain: str, first_name: Optional[str] = None, last_name: Optional[str] = None) -> Tuple[Optional[str], int, int]:
        """Find specific email using Hunter.io email finder with enhanced error handling"""
        try:
            logger.debug(f"Finding email for {first_name or 'generic'} at {domain}")
            params = {
                'domain': domain,
                'api_key': self.api_key
            }

            if first_name:
                params['first_name'] = first_name
            if last_name:
                params['last_name'] = last_name

            response = self.session.get(
                f"{self.base_url}/email-finder",
                params=params,
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                email_data = data.get('data', {})
                email = email_data.get('email')
                confidence = email_data.get('confidence', 0)

                # Log credit usage
                self.log_hunter_usage(1, 'email_finder')

                return email, confidence, 1

            elif response.status_code == 429:
                logger.warning(f"Hunter.io rate limit hit for email finder: {domain}")
                time.sleep(60)
                return None, 0, 0

            else:
                logger.warning(f"Hunter email finder failed for {domain}: {response.status_code}")
                return None, 0, 0

        except Exception as e:
            logger.error(f"Hunter email finder error for {domain}: {e}")
            return None, 0, 0

    def email_verifier(self, email: str) -> Tuple[bool, int, int]:
        """Verify email using Hunter.io with enhanced error handling"""
        try:
            logger.debug(f"Verifying email: {email}")
            params = {
                'email': email,
                'api_key': self.api_key
            }

            response = self.session.get(
                f"{self.base_url}/email-verifier",
                params=params,
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                result = data.get('data', {}).get('result', 'undeliverable')

                # Log credit usage
                self.log_hunter_usage(1, 'email_verifier')

                # Consider deliverable and risky as valid
                is_valid = result in ['deliverable', 'risky']
                confidence = 90 if result == 'deliverable' else 60 if result == 'risky' else 10

                return is_valid, confidence, 1

            else:
                logger.warning(f"Hunter email verifier failed for {email}: {response.status_code}")
                return False, 0, 0

        except Exception as e:
            logger.error(f"Hunter email verifier error for {email}: {e}")
            return False, 0, 0

    def generate_common_emails(self, domain: str, business_name: str) -> List[str]:
        """Generate common business email patterns"""
        emails = []

        # Clean business name for email generation
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', business_name.lower())
        words = clean_name.split()

        # Standard generic emails
        for prefix in self.preferred_prefixes:
            emails.append(f"{prefix}@{domain}")

        # Business name based emails
        if words:
            first_word = words[0][:10]  # Limit length
            emails.extend([
                f"{first_word}@{domain}",
                f"{first_word}info@{domain}",
                f"contact{first_word}@{domain}"
            ])

        return emails[:5]  # Limit to 5 attempts

    def find_best_email(self, lead_data: Dict[str, Any]) -> Tuple[Optional[str], int, str, int]:
        """Find the best email for a lead using multiple strategies"""
        domain = lead_data.get('domain')
        business_name = lead_data.get('business_name', '')
        credits_used = 0

        if not domain:
            return None, 0, 'no_domain', 0

        logger.debug(f"Finding email for {business_name} ({domain})")

        # Strategy 1: Domain search to find existing emails
        try:
            emails, used = self.domain_search(domain)
            credits_used += used

            if emails:
                # Sort by confidence and preference
                best_email = None
                best_confidence = 0

                for email_data in emails:
                    email = email_data.get('value', '').lower()
                    confidence = email_data.get('confidence', 0)
                    email_type = email_data.get('type', '')

                    if not self.validate_email(email):
                        continue

                    # Prefer generic emails over personal ones
                    if email_type == 'generic':
                        confidence += 10

                    # Prefer emails with preferred prefixes
                    email_prefix = email.split('@')[0]
                    if any(prefix in email_prefix for prefix in self.preferred_prefixes):
                        confidence += 15

                    if confidence > best_confidence:
                        best_email = email
                        best_confidence = confidence

                if best_email and best_confidence >= 50:
                    logger.debug(f"Found email via domain search: {best_email} (confidence: {best_confidence})")
                    return best_email, best_confidence, 'domain_search', credits_used

            # Strategy 2: Try common email patterns
            common_emails = self.generate_common_emails(domain, business_name)

            for email in common_emails:
                if credits_used >= 3:  # Limit credit usage per lead
                    break

                is_valid, confidence, used = self.email_verifier(email)
                credits_used += used

                if is_valid and confidence >= 60:
                    logger.debug(f"Found email via pattern: {email} (confidence: {confidence})")
                    return email, confidence, 'pattern_verified', credits_used

                # Small delay between verifications
                time.sleep(0.5)

            # Strategy 3: Email finder with common names
            if credits_used < 2:
                common_names = [
                    ('info', ''), ('contact', ''), ('sales', ''),
                    ('service', ''), ('admin', '')
                ]

                for first_name, last_name in common_names:
                    if credits_used >= 4:
                        break

                    email, confidence, used = self.email_finder(domain, first_name, last_name)
                    credits_used += used

                    if email and confidence >= 70:
                        logger.debug(f"Found email via finder: {email} (confidence: {confidence})")
                        return email, confidence, 'email_finder', credits_used

            return None, 0, 'not_found', credits_used

        except Exception as e:
            logger.error(f"Error finding email for {domain}: {e}")
            return None, 0, 'error', credits_used

    def enrich_leads(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """Main enrichment function"""
        limit = limit or config.MAX_EMAILS_PER_RUN
        logger.info(f"🔍 Starting email enrichment (limit: {limit})...")

        start_time = datetime.now()
        total_processed = 0
        total_found = 0
        total_credits_used = 0
        errors = []

        try:
            # Check Hunter credits first
            available_credits = self.get_hunter_credits()
            if available_credits is not None and available_credits < 10:
                logger.warning(f"Low Hunter.io credits: {available_credits}")

            # Get leads that need enrichment
            leads = db.get_leads_for_enrichment(limit)
            logger.info(f"Found {len(leads)} leads to enrich")

            for lead in leads:
                try:
                    total_processed += 1
                    lead_id = lead['id']

                    logger.debug(f"Processing lead {total_processed}/{len(leads)}: {lead['business_name']}")

                    # Find best email
                    email, confidence, method, credits_used = self.find_best_email(lead)
                    total_credits_used += credits_used

                    # Save enrichment result
                    enrichment_data = {
                        'lead_id': lead_id,
                        'email_address': email,
                        'confidence_score': confidence,
                        'email_type': 'generic' if email else None,
                        'sources_count': 1 if email else 0,
                        'enriched_date': datetime.now().date(),
                        'hunter_credits_used': credits_used,
                        'status': 'found' if email else 'not_found',
                        'error_message': None if email else f'No email found using {method}'
                    }

                    db.insert_email_enrichment(enrichment_data)

                    if email:
                        total_found += 1
                        logger.debug(f"✅ Found email: {email} (confidence: {confidence})")
                    else:
                        logger.debug(f"❌ No email found for {lead['business_name']}")

                    # Respectful delay between requests
                    time.sleep(config.THROTTLE_DELAY)

                    # Check if we're running low on credits
                    if total_credits_used >= 40:  # Conservative limit
                        logger.warning("Approaching Hunter.io credit limit, stopping enrichment")
                        break

                except Exception as e:
                    error_msg = f"Error processing lead {lead.get('business_name', 'unknown')}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            # Calculate duration
            duration = datetime.now() - start_time

            # Prepare summary
            summary = {
                'total_processed': total_processed,
                'total_found': total_found,
                'total_credits_used': total_credits_used,
                'success_rate': round((total_found / total_processed * 100) if total_processed > 0 else 0, 1),
                'duration': str(duration).split('.')[0],
                'errors': errors,
                'success': total_found > 0
            }

            # Log completion
            db.log_system_event(
                'INFO',
                'enricher',
                f'Email enrichment completed: {total_found}/{total_processed} emails found',
                f'Credits used: {total_credits_used}, Success rate: {summary["success_rate"]}%'
            )

            logger.info(f"✅ Enrichment complete: {total_found}/{total_processed} emails found")
            return summary

        except Exception as e:
            error_msg = f"Email enrichment failed: {str(e)}"
            logger.error(error_msg)

            db.log_system_event('ERROR', 'enricher', error_msg, None)

            return {
                'total_processed': total_processed,
                'total_found': total_found,
                'total_credits_used': total_credits_used,
                'success_rate': 0,
                'duration': str(datetime.now() - start_time).split('.')[0],
                'errors': errors + [error_msg],
                'success': False
            }

def main():
    """Main function for standalone execution"""
    try:
        enricher = EmailEnricher()
        results = enricher.enrich_leads()

        print(f"\n📧 Email Enrichment Results:")
        print(f"   Processed: {results['total_processed']} leads")
        print(f"   Found: {results['total_found']} emails")
        print(f"   Success Rate: {results['success_rate']}%")
        print(f"   Credits Used: {results['total_credits_used']}")
        print(f"   Duration: {results['duration']}")

        if results['errors']:
            print(f"   Errors: {len(results['errors'])}")
            for error in results['errors'][:3]:  # Show first 3 errors
                print(f"     - {error}")

        return results['total_found']

    except Exception as e:
        logger.error(f"Main execution failed: {e}")
        return 0

if __name__ == "__main__":
    found_count = main()
    exit(0 if found_count > 0 else 1)
