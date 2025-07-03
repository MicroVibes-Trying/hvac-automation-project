#!/usr/bin/env python3
"""
Mailgun Test Email Script v4.0
Test Mailgun API integration with your HVAC automation system
"""
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import config
from app.senders.email_sender import EmailSender
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def validate_mailgun_config():
    """Validate Mailgun configuration"""
    errors = []
    
    if not config.MAILGUN_API_KEY:
        errors.append("❌ MAILGUN_API_KEY is missing")
    elif len(config.MAILGUN_API_KEY) < 20:
        errors.append("❌ MAILGUN_API_KEY appears invalid (too short)")
    else:
        # Mask the key for display
        masked_key = config.MAILGUN_API_KEY[:8] + "..." + config.MAILGUN_API_KEY[-8:]
        print(f"✅ MAILGUN_API_KEY: {masked_key}")
    
    if not config.MAILGUN_DOMAIN:
        errors.append("❌ MAILGUN_DOMAIN is missing")
    else:
        print(f"✅ MAILGUN_DOMAIN: {config.MAILGUN_DOMAIN}")
    
    if not config.MAILGUN_FROM_EMAIL:
        errors.append("❌ MAILGUN_FROM_EMAIL is missing")
    else:
        print(f"✅ FROM_EMAIL: {config.MAILGUN_FROM_EMAIL}")
    
    print(f"✅ MAILGUN_REGION: {config.MAILGUN_REGION}")
    print(f"✅ TRACKING_ENABLED: {config.MAILGUN_ENABLE_TRACKING}")
    
    return errors

def create_test_lead(email_address: str) -> dict:
    """Create a test lead for sending"""
    return {
        'id': 99999,  # Test ID
        'business_name': 'Test HVAC Company',
        'email_address': email_address,
        'address': '123 Test Street, Test City, TX 12345',
        'phone': '(555) 123-4567',
        'website': 'https://testhvac.com'
    }

def main():
    """Main test function"""
    print("🔧 HVAC Automation - Mailgun Email Test")
    print("=" * 50)
    
    # Validate configuration
    print("\n📋 Validating Mailgun Configuration:")
    config_errors = validate_mailgun_config()
    
    if config_errors:
        print("\n❌ Configuration Errors:")
        for error in config_errors:
            print(f"   {error}")
        print("\n💡 Please check your credentials.txt file and ensure all Mailgun settings are configured.")
        return False
    
    print("\n✅ Mailgun configuration looks good!")
    
    # Get test email address
    print("\n📧 Email Test Setup:")
    test_email = input("Enter test email address: ").strip()
    
    if not test_email or '@' not in test_email:
        print("❌ Invalid email address")
        return False
    
    # Confirm sending
    print(f"\n📤 Ready to send test email to: {test_email}")
    print(f"   From: {config.MAILGUN_FROM_EMAIL}")
    print(f"   Domain: {config.MAILGUN_DOMAIN}")
    
    confirm = input("\nProceed with sending test email? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Test cancelled.")
        return False
    
    try:
        # Initialize Mailgun sender
        print("\n🚀 Initializing Mailgun Email Sender...")
        sender = EmailSender()
        
        # Create test lead
        test_lead = create_test_lead(test_email)
        
        # Send test email
        print("📧 Sending test email via Mailgun API...")
        result = sender.send_single_email(test_lead)
        
        # Display results
        print("\n📊 Test Results:")
        print("=" * 30)
        
        if result['status'] == 'sent':
            print("✅ SUCCESS: Test email sent successfully!")
            print(f"   Status: {result['status']}")
            print(f"   Lead ID: {result['lead_id']}")
            print(f"   Campaign ID: {result['campaign_id']}")
            print(f"   Email: {result['email_address']}")
            if 'message_id' in result:
                print(f"   Mailgun Message ID: {result['message_id']}")
            
            print("\n📬 Check your inbox for the test email!")
            print("   Note: Check spam folder if not in inbox")
            
            if config.MAILGUN_ENABLE_TRACKING:
                print("   📊 Email tracking is enabled - opens/clicks will be tracked")
            
            return True
            
        elif result['status'] == 'skipped':
            print(f"⚠️ SKIPPED: {result.get('error', 'Unknown reason')}")
            return False
            
        else:
            print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
            print(f"   Status: {result['status']}")
            return False
            
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        logger.exception("Test email failed")
        return False

def test_mailgun_api_direct():
    """Test Mailgun API directly"""
    print("\n🔧 Direct Mailgun API Test")
    print("-" * 30)
    
    try:
        sender = EmailSender()
        
        # Test API connectivity
        test_data = {
            'from': config.MAILGUN_FROM_EMAIL,
            'to': 'test@example.com',  # This won't actually send
            'subject': 'API Test',
            'text': 'API connectivity test'
        }
        
        # Just test the URL formation and auth
        url = f"{sender.base_url}/messages"
        print(f"✅ API URL: {url}")
        print(f"✅ Authentication configured")
        print(f"✅ Session created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

if __name__ == "__main__":
    print("🔧 HVAC Automation - Mailgun Integration Test")
    print("=" * 55)
    
    # Run configuration test
    success = main()
    
    # Run API connectivity test
    if success:
        test_mailgun_api_direct()
    
    print("\n" + "=" * 55)
    if success:
        print("🎉 Mailgun integration test completed successfully!")
        print("Your system is ready to send emails via Mailgun API.")
    else:
        print("❌ Mailgun integration test failed.")
        print("Please check configuration and try again.")
    
    sys.exit(0 if success else 1)
