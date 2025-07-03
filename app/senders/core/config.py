"""
HVAC Email Automation v3.0 - Configuration
Production configuration with credentials.txt file support
"""
import os
from typing import List, Dict

def load_credentials_from_file(file_path: str = "credentials.txt") -> Dict[str, str]:
    """Load credentials from text file"""
    credentials = {}
    
    # Try to find credentials file
    possible_paths = [
        file_path,
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), file_path),
        os.path.join(os.getcwd(), file_path)
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            credentials[key.strip()] = value.strip()
                break
            except Exception as e:
                print(f"Warning: Could not read credentials file {path}: {e}")
                continue
    
    return credentials

# Load credentials from file
_credentials = load_credentials_from_file()

def get_credential(key: str, default: str = '') -> str:
    """Get credential value with fallback to environment variable"""
    return _credentials.get(key, os.getenv(key, default))

class Config:
    """Application configuration loaded from credentials.txt file"""
    
    # Server Configuration
    SERVER_IP = get_credential('SERVER_IP', 'localhost')  # SECURITY: Removed hardcoded IP
    LOG_LEVEL = get_credential('LOG_LEVEL', 'INFO')
    
    # API Keys - Loaded from credentials.txt file
    GOOGLE_PLACES_API_KEY = get_credential('GOOGLE_PLACES_API_KEY', '')
    HUNTER_API_KEY = get_credential('HUNTER_API_KEY', '')
    
    # Gmail Configuration - Loaded from credentials.txt file
    GMAIL_USER = get_credential('GMAIL_USER', '')
    GMAIL_APP_PASSWORD = get_credential('GMAIL_APP_PASSWORD', '')
    
    # Search Configuration - Handle potential None values
    CITIES = [city.strip() for city in get_credential('CITIES', 'Houston,Dallas,Austin,San Antonio,Fort Worth').split(',')]
    SEARCH_KEYWORDS = [keyword.strip() for keyword in get_credential('SEARCH_KEYWORDS', 'HVAC,air conditioning,heating,cooling,HVAC contractor').split(',')]
    
    # Affiliate Configuration - Loaded from credentials.txt file
    FIVERR_AFFILIATE_LINK = get_credential('FIVERR_AFFILIATE_LINK', '')
    
    # Rate Limiting (Anti-Spam Measures) - Load from credentials.txt with defaults
    MAX_EMAILS_PER_DAY = int(get_credential('MAX_EMAILS_PER_DAY', '50'))
    MAX_EMAILS_PER_RUN = int(get_credential('MAX_EMAILS_PER_RUN', '25'))
    EMAIL_DELAY_SECONDS = int(get_credential('EMAIL_DELAY_SECONDS', '30'))
    EMAIL_DELAY_MIN = int(get_credential('EMAIL_DELAY_MIN', '120'))  # 2 minutes
    EMAIL_DELAY_MAX = int(get_credential('EMAIL_DELAY_MAX', '300'))  # 5 minutes  
    MAX_HUNTER_REQUESTS_PER_DAY = int(get_credential('MAX_HUNTER_REQUESTS_PER_DAY', '100'))
    EMAIL_COOLDOWN_HOURS = int(get_credential('EMAIL_COOLDOWN_HOURS', '72'))
    COOLDOWN_DAYS = int(get_credential('COOLDOWN_DAYS', '7'))  # 7 days default
    THROTTLE_DELAY = int(get_credential('THROTTLE_DELAY', '2'))
    
    # Database
    DATABASE_PATH = get_credential('DATABASE_PATH', 'hvac_automation.db')
    BACKUP_DIR = get_credential('BACKUP_DIR', 'backups')
    BACKUP_RETENTION_DAYS = int(get_credential('BACKUP_RETENTION_DAYS', '30'))
    
    # Notifications
    NOTIFICATION_EMAIL = get_credential('NOTIFICATION_EMAIL', '')
    
    # Monitoring and Dashboard
    ENABLE_MONITORING = get_credential('ENABLE_MONITORING', 'true').lower() == 'true'
    ENABLE_WEB_DASHBOARD = get_credential('ENABLE_WEB_DASHBOARD', 'true').lower() == 'true'
    DASHBOARD_PORT = int(get_credential('DASHBOARD_PORT', '8080'))
    
    # Email Templates - Match what email_sender.py expects
    EMAIL_SUBJECT_TEMPLATE = "Boost Your HVAC Business with Professional Marketing"
    EMAIL_TEMPLATE = """Hi {business_name},

I hope this message finds you well. I came across your HVAC business and wanted to share an opportunity that could significantly boost your customer acquisition.

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
This message was sent to help grow your business. If you'd prefer not to receive similar opportunities, simply reply with "REMOVE" and I'll respect your preference immediately."""
    
    # Validation method
    @classmethod
    def validate(cls) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        if not cls.GOOGLE_PLACES_API_KEY.strip():
            errors.append("Google Places API key is required")
        
        if not cls.HUNTER_API_KEY.strip():
            errors.append("Hunter.io API key is required")
        
        if not cls.GMAIL_USER.strip():
            errors.append("Gmail user is required")
        
        if not cls.GMAIL_APP_PASSWORD.strip():
            errors.append("Gmail app password is required")
        
        if not cls.FIVERR_AFFILIATE_LINK.strip():
            errors.append("Fiverr affiliate link is required")
        
        if not cls.CITIES:
            errors.append("At least one city must be configured")
        
        if not cls.SEARCH_KEYWORDS:
            errors.append("At least one search keyword must be configured")
        
        return errors
    
    @classmethod
    def is_configured(cls) -> bool:
        """Check if basic configuration is complete"""
        return len(cls.validate()) == 0
    
    @classmethod
    def get_database_path(cls) -> str:
        """Get the full database path"""
        return os.path.abspath(cls.DATABASE_PATH)
    
    @classmethod
    def get_backup_path(cls) -> str:
        """Get the backup directory path"""
        backup_dir = os.path.abspath(cls.BACKUP_DIR)
        os.makedirs(backup_dir, exist_ok=True)
        return backup_dir

# Create config instance
config = Config()
