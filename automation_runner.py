"""
HVAC Email Automation v3 - Main Automation Runner
Complete workflow orchestration with anti-spam measures and intelligent scheduling
"""
import sys
import os
import logging
import argparse
import traceback
from datetime import datetime
from typing import Dict, Any, Optional

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import config
from app.core.database import db
from app.scrapers.hvac_scraper import HVACLeadScraper
from app.enrichers.email_enricher import EmailEnricher
from app.senders.email_sender import EmailSender

# Import Discord Alert Utility with error handling
try:
    from scripts.discord_monitor_init import send_discord_alert
    DISCORD_AVAILABLE = True
    logger_temp = logging.getLogger(__name__)
    logger_temp.info("✅ Discord monitoring loaded successfully")
except ImportError as e:
    DISCORD_AVAILABLE = False
    def send_discord_alert(title, error_message, details="") -> bool:
        """Fallback function when Discord is not available"""
        print(f"⚠️ Discord not available - {title}: {error_message}")
        return False
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning(f"⚠️ Discord monitoring not available: {e}")

# Configure logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class AutomationRunner:
    """Main automation workflow orchestrator"""

    def __init__(self):
        self.scraper = HVACLeadScraper()
        self.enricher = EmailEnricher()
        self.sender = EmailSender()

        # Workflow settings
        self.run_scraping = True
        self.run_enrichment = True
        self.run_sending = True
        self.send_notifications = True

    def validate_configuration(self) -> bool:
        """Validate that all required configuration is present"""
        logger.info("🔍 Validating configuration...")

        errors = []

        # Check API keys
        if not config.GOOGLE_PLACES_API_KEY:
            errors.append("Google Places API key not configured")

        if not config.HUNTER_API_KEY:
            errors.append("Hunter.io API key not configured")

        # Check Gmail credentials
        if not config.GMAIL_USER:
            errors.append("Gmail user not configured")

        if not config.GMAIL_APP_PASSWORD:
            errors.append("Gmail app password not configured")

        # Check search configuration
        if not config.CITIES:
            errors.append("No cities configured for search")

        if not config.SEARCH_KEYWORDS:
            errors.append("No search keywords configured")

        # Check affiliate link
        if not config.FIVERR_AFFILIATE_LINK:
            errors.append("Fiverr affiliate link not configured")

        if errors:
            logger.error("❌ Configuration validation failed:")
            for error in errors:
                logger.error(f"   - {error}")

            # Send Discord alert for configuration errors
            if DISCORD_AVAILABLE:
                send_discord_alert(
                    "Configuration Validation Failed",
                    f"{len(errors)} configuration errors found",
                    "\n".join(errors)
                )

            return False

        logger.info("✅ Configuration validation passed")
        return True

    def run_lead_scraping(self) -> Dict[str, Any]:
        """Run lead scraping workflow"""
        logger.info("🔍 Starting lead scraping workflow...")

        try:
            results = self.scraper.scrape_leads()

            logger.info(f"✅ Lead scraping completed:")
            logger.info(f"   Found: {results['total_found']} leads")
            logger.info(f"   Saved: {results['total_saved']} new leads")
            logger.info(f"   Duplicates: {results['total_duplicates']}")
            logger.info(f"   Duration: {results['duration']}")

            if results['errors']:
                logger.warning(f"   Errors: {len(results['errors'])}")
                for error in results['errors'][:3]:
                    logger.warning(f"     - {error}")

                # Send Discord alert for scraping errors
                if DISCORD_AVAILABLE and len(results['errors']) > 5:
                    send_discord_alert(
                        "Lead Scraping Errors Detected",
                        f"{len(results['errors'])} errors during lead scraping",
                        "\n".join(results['errors'][:10])
                    )

            return results

        except Exception as e:
            logger.error(f"❌ Lead scraping failed: {e}")

            # Send Discord alert for scraping failure
            if DISCORD_AVAILABLE:
                send_discord_alert(
                    "Lead Scraping Failed",
                    str(e),
                    traceback.format_exc()
                )

            return {
                'total_found': 0,
                'total_saved': 0,
                'total_duplicates': 0,
                'duration': '0:00:00',
                'errors': [str(e)],
                'success': False
            }

    def run_email_enrichment(self) -> Dict[str, Any]:
        """Run email enrichment workflow"""
        logger.info("📧 Starting email enrichment workflow...")

        try:
            results = self.enricher.enrich_leads()

            logger.info(f"✅ Email enrichment completed:")
            logger.info(f"   Processed: {results['total_processed']} leads")
            logger.info(f"   Found: {results['total_found']} emails")
            logger.info(f"   Success Rate: {results['success_rate']}%")
            logger.info(f"   Credits Used: {results['total_credits_used']}")
            logger.info(f"   Duration: {results['duration']}")

            if results['errors']:
                logger.warning(f"   Errors: {len(results['errors'])}")
                for error in results['errors'][:3]:
                    logger.warning(f"     - {error}")

                # Send Discord alert for enrichment errors
                if DISCORD_AVAILABLE and len(results['errors']) > 5:
                    send_discord_alert(
                        "Email Enrichment Errors Detected",
                        f"{len(results['errors'])} errors during email enrichment",
                        "\n".join(results['errors'][:10])
                    )

            return results

        except Exception as e:
            logger.error(f"❌ Email enrichment failed: {e}")

            # Send Discord alert for enrichment failure
            if DISCORD_AVAILABLE:
                send_discord_alert(
                    "Email Enrichment Failed",
                    str(e),
                    traceback.format_exc()
                )

            return {
                'total_processed': 0,
                'total_found': 0,
                'total_credits_used': 0,
                'success_rate': 0,
                'duration': '0:00:00',
                'errors': [str(e)],
                'success': False
            }

    def run_email_sending(self) -> Dict[str, Any]:
        """Run email sending workflow"""
        logger.info("📬 Starting email sending workflow...")

        try:
            results = self.sender.send_batch_emails()

            logger.info(f"✅ Email sending completed:")
            logger.info(f"   Processed: {results['total_processed']} leads")
            logger.info(f"   Sent: {results['total_sent']} emails")
            logger.info(f"   Skipped: {results['total_skipped']} (cooldown)")
            logger.info(f"   Failed: {results['total_failed']}")
            logger.info(f"   Success Rate: {results['success_rate']}%")
            logger.info(f"   Duration: {results['duration']}")

            if results['errors']:
                logger.warning(f"   Errors: {len(results['errors'])}")
                for error in results['errors'][:3]:
                    logger.warning(f"     - {error}")

                # Send Discord alert for sending errors
                if DISCORD_AVAILABLE and len(results['errors']) > 5:
                    send_discord_alert(
                        "Email Sending Errors Detected",
                        f"{len(results['errors'])} errors during email sending",
                        "\n".join(results['errors'][:10])
                    )

            return results

        except Exception as e:
            logger.error(f"❌ Email sending failed: {e}")

            # Send Discord alert for sending failure
            if DISCORD_AVAILABLE:
                send_discord_alert(
                    "Email Sending Failed",
                    str(e),
                    traceback.format_exc()
                )

            return {
                'total_processed': 0,
                'total_sent': 0,
                'total_skipped': 0,
                'total_failed': 0,
                'success_rate': 0,
                'duration': '0:00:00',
                'errors': [str(e)],
                'success': False
            }

    def generate_report(self, scraping_results: Dict[str, Any],
                       enrichment_results: Dict[str, Any],
                       sending_results: Dict[str, Any]) -> str:
        """Generate comprehensive automation report"""

        # Get dashboard stats
        stats = db.get_dashboard_stats()

        report = f"""
🏠 HVAC EMAIL AUTOMATION REPORT

Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Discord Monitoring: {'✅ Active' if DISCORD_AVAILABLE else '⚠️ Disabled'}

📊 CURRENT STATISTICS
---------------------
Total Leads in Database: {stats['total_leads']:,}
Leads with Emails: {stats['leads_with_emails']:,}
Emails Sent Today: {stats['emails_sent_today']:,}
Emails Sent This Week: {stats['emails_sent_week']:,}
Hunter Credits Used Today: {stats['credits_used_today']:,}
Overall Success Rate: {stats['success_rate']}%

🔍 LEAD SCRAPING RESULTS
------------------------
Found: {scraping_results['total_found']} leads
Saved: {scraping_results['total_saved']} new leads
Duplicates: {scraping_results['total_duplicates']}
Duration: {scraping_results['duration']}
Success: {'✅' if scraping_results['success'] else '❌'}

📧 EMAIL ENRICHMENT RESULTS
---------------------------
Processed: {enrichment_results['total_processed']} leads
Found: {enrichment_results['total_found']} emails
Success Rate: {enrichment_results['success_rate']}%
Credits Used: {enrichment_results['total_credits_used']}
Duration: {enrichment_results['duration']}
Success: {'✅' if enrichment_results['success'] else '❌'}

📬 EMAIL SENDING RESULTS
------------------------
Processed: {sending_results['total_processed']} leads
Sent: {sending_results['total_sent']} emails
Skipped: {sending_results['total_skipped']} (cooldown)
Failed: {sending_results['total_failed']}
Success Rate: {sending_results['success_rate']}%
Duration: {sending_results['duration']}
Success: {'✅' if sending_results['success'] else '❌'}

⚠️ ERRORS SUMMARY
-----------------
"""

        all_errors = (scraping_results.get('errors', []) +
                     enrichment_results.get('errors', []) +
                     sending_results.get('errors', []))

        if all_errors:
            report += f"Total Errors: {len(all_errors)}\n"
            for i, error in enumerate(all_errors[:5], 1):
                report += f"{i}. {error}\n"
            if len(all_errors) > 5:
                report += f"... and {len(all_errors) - 5} more errors\n"
        else:
            report += "No errors encountered ✅\n"

        report += f"""
🚀 NEXT ACTIONS
---------------
- Leads pending enrichment: {stats['leads_pending_enrichment']:,}
- Next run recommended: Every 4-6 hours
- Monitor Hunter credits: {stats['credits_used_today']:,} used today

HVAC Email Automation v3.0
"""

        return report

    def send_completion_notification(self, report: str, success: bool):
        """Send completion notification email"""
        if not self.send_notifications:
            return

        try:
            subject = f"Automation {'Completed' if success else 'Failed'} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"

            self.sender.send_notification_email(subject, report)
            logger.info("✅ Completion notification sent")

        except Exception as e:
            logger.error(f"❌ Failed to send completion notification: {e}")

    def run_full_automation(self) -> bool:
        """Run complete automation workflow"""
        logger.info("🚀 Starting HVAC Email Automation v3.0...")
        start_time = datetime.now()

        try:
            # Validate configuration
            if not self.validate_configuration():
                return False

            # Create database backup
            try:
                backup_path = db.backup_database()
                logger.info(f"✅ Database backup created: {backup_path}")
            except Exception as e:
                logger.warning(f"⚠️ Database backup failed: {e}")

            # Initialize results
            scraping_results = {'total_found': 0, 'total_saved': 0, 'total_duplicates': 0, 'duration': '0:00:00', 'errors': [], 'success': True}
            enrichment_results = {'total_processed': 0, 'total_found': 0, 'total_credits_used': 0, 'success_rate': 0, 'duration': '0:00:00', 'errors': [], 'success': True}
            sending_results = {'total_processed': 0, 'total_sent': 0, 'total_skipped': 0, 'total_failed': 0, 'success_rate': 0, 'duration': '0:00:00', 'errors': [], 'success': True}

            # Run workflows
            if self.run_scraping:
                scraping_results = self.run_lead_scraping()

            if self.run_enrichment:
                enrichment_results = self.run_email_enrichment()

            if self.run_sending:
                sending_results = self.run_email_sending()

            # Generate and log report
            report = self.generate_report(scraping_results, enrichment_results, sending_results)
            logger.info(report)

            # Determine overall success
            overall_success = (scraping_results['success'] and enrichment_results['success'] and sending_results['success'])

            # Send completion notification
            self.send_completion_notification(report, overall_success)

            # Send Discord summary for successful runs
            if DISCORD_AVAILABLE and overall_success:
                stats = db.get_dashboard_stats()
                send_discord_alert(
                    "✅ Automation Completed Successfully",
                    f"Scraped: {scraping_results['total_saved']}, Enriched: {enrichment_results['total_found']}, Sent: {sending_results['total_sent']}",
                    f"Total leads: {stats['total_leads']:,}\nEmails sent today: {stats['emails_sent_today']:,}"
                )

            # Log completion
            duration = datetime.now() - start_time
            db.log_system_event(
                'INFO',
                'automation',
                f'Full automation cycle completed in {str(duration).split(".")[0]}',
                f'Scraped: {scraping_results["total_saved"]}, Enriched: {enrichment_results["total_found"]}, Sent: {sending_results["total_sent"]}'
            )

            # Cleanup old backups
            try:
                db.cleanup_old_backups()
            except Exception as e:
                logger.warning(f"⚠️ Backup cleanup failed: {e}")

            logger.info(f"🎉 Automation completed in {str(duration).split('.')[0]}")
            return overall_success

        except Exception as e:
            logger.error(f"❌ Automation failed: {e}")
            trace = traceback.format_exc()

            # Send Discord alert for critical failures
            if DISCORD_AVAILABLE:
                send_discord_alert("🚨 Critical Automation Failure", str(e), trace)

            # Log failure
            db.log_system_event('ERROR', 'automation', f'Automation failed: {str(e)}', None)

            # Send failure notification
            try:
                self.send_completion_notification(f"Automation failed: {str(e)}", False)
            except Exception:
                pass

            return False


def main():
    """Main entry point with command line arguments"""
    parser = argparse.ArgumentParser(description='HVAC Email Automation v3.0')
    parser.add_argument('--scrape-only', action='store_true', help='Run only lead scraping')
    parser.add_argument('--enrich-only', action='store_true', help='Run only email enrichment')
    parser.add_argument('--send-only', action='store_true', help='Run only email sending')
    parser.add_argument('--no-notifications', action='store_true', help='Disable email notifications')
    parser.add_argument('--stats', action='store_true', help='Show dashboard statistics only')

    args = parser.parse_args()

    try:
        # Show stats only
        if args.stats:
            stats = db.get_dashboard_stats()
            print(f"\n📊 HVAC Automation Dashboard Stats")
            print(f"   Total Leads: {stats['total_leads']:,}")
            print(f"   Leads with Emails: {stats['leads_with_emails']:,}")
            print(f"   Emails Sent Today: {stats['emails_sent_today']:,}")
            print(f"   Emails Sent This Week: {stats['emails_sent_week']:,}")
            print(f"   Hunter Credits Used Today: {stats['credits_used_today']:,}")
            print(f"   Success Rate: {stats['success_rate']}%")
            print(f"   Leads Pending Enrichment: {stats['leads_pending_enrichment']:,}")
            print(f"   Discord Monitoring: {'✅ Active' if DISCORD_AVAILABLE else '⚠️ Disabled'}")
            return 0

        # Initialize runner
        runner = AutomationRunner()

        # Configure runner based on arguments
        if args.scrape_only:
            runner.run_enrichment = False
            runner.run_sending = False
        elif args.enrich_only:
            runner.run_scraping = False
            runner.run_sending = False
        elif args.send_only:
            runner.run_scraping = False
            runner.run_enrichment = False

        if args.no_notifications:
            runner.send_notifications = False

        # Run automation
        success = runner.run_full_automation()
        return 0 if success else 1

    except KeyboardInterrupt:
        logger.info("🛑 Automation interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")

        # Send Discord alert for unexpected errors
        if DISCORD_AVAILABLE:
            send_discord_alert("🚨 Unexpected Automation Error", str(e), traceback.format_exc())

        return 1

if __name__ == "__main__":
    exit(main())
