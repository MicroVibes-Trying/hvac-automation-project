"""
Database Management for HVAC Email Automation v3
SQLite database with comprehensive lead tracking and email management
"""
import sqlite3
import logging
import shutil
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from contextlib import contextmanager

from .config import config

# Configure logging
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Enhanced database manager with backup and recovery features"""
    
    def __init__(self):
        self.db_path = config.get_database_path()
        self.ensure_database_exists()
        self.create_tables()
    
    def ensure_database_exists(self):
        """Ensure database file and directory exist"""
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        
        if not db_file.exists():
            logger.info(f"Creating new database at {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        try:
            yield conn
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def create_tables(self):
        """Create all database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Leads table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    business_name TEXT NOT NULL,
                    address TEXT,
                    phone TEXT,
                    website TEXT,
                    domain TEXT,
                    google_maps_url TEXT,
                    category TEXT,
                    business_status TEXT DEFAULT 'OPERATIONAL',
                    scraped_date DATE NOT NULL,
                    status TEXT DEFAULT 'new',
                    quality_score INTEGER DEFAULT 0,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Email enrichment table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_enrichment (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id INTEGER NOT NULL,
                    email_address TEXT,
                    confidence_score INTEGER,
                    email_type TEXT,
                    sources_count INTEGER DEFAULT 0,
                    enriched_date DATE NOT NULL,
                    hunter_credits_used INTEGER DEFAULT 1,
                    status TEXT DEFAULT 'found',
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (lead_id) REFERENCES leads (id) ON DELETE CASCADE
                )
            """)
            
            # Email sends table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_sends (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lead_id INTEGER NOT NULL,
                    email_address TEXT NOT NULL,
                    subject TEXT,
                    sent_date DATETIME NOT NULL,
                    status TEXT NOT NULL,
                    response_code TEXT,
                    error_message TEXT,
                    next_eligible_date DATE,
                    campaign_id TEXT,
                    opened BOOLEAN DEFAULT FALSE,
                    clicked BOOLEAN DEFAULT FALSE,
                    bounced BOOLEAN DEFAULT FALSE,
                    complained BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (lead_id) REFERENCES leads (id) ON DELETE CASCADE
                )
            """)
            
            # System logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    level TEXT NOT NULL,
                    module TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details TEXT,
                    user_id TEXT,
                    ip_address TEXT
                )
            """)
            
            # Hunter.io credit tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hunter_credits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    credits_used INTEGER NOT NULL,
                    credits_remaining INTEGER,
                    operation_type TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Email templates table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # System settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_domain ON leads(domain)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_scraped_date ON leads(scraped_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_sends_sent_date ON email_sends(sent_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_email_sends_next_eligible ON email_sends(next_eligible_date)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp ON system_logs(timestamp)")
            
            conn.commit()
            logger.info("Database tables created/verified successfully")
    
    def insert_lead(self, lead_data: Dict[str, Any]) -> int:
        """Insert a new lead"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO leads (
                    business_name, address, phone, website, domain,
                    google_maps_url, category, business_status, scraped_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                lead_data.get('business_name'),
                lead_data.get('address'),
                lead_data.get('phone'),
                lead_data.get('website'),
                lead_data.get('domain'),
                lead_data.get('google_maps_url'),
                lead_data.get('category'),
                lead_data.get('business_status', 'OPERATIONAL'),
                lead_data.get('scraped_date', datetime.now().date())
            ))
            
            conn.commit()
            return cursor.lastrowid or 0
    
    def insert_email_enrichment(self, enrichment_data: Dict[str, Any]) -> int:
        """Insert email enrichment data"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO email_enrichment (
                    lead_id, email_address, confidence_score, email_type,
                    sources_count, enriched_date, hunter_credits_used, status, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                enrichment_data.get('lead_id'),
                enrichment_data.get('email_address'),
                enrichment_data.get('confidence_score'),
                enrichment_data.get('email_type'),
                enrichment_data.get('sources_count', 0),
                enrichment_data.get('enriched_date', datetime.now().date()),
                enrichment_data.get('hunter_credits_used', 1),
                enrichment_data.get('status', 'found'),
                enrichment_data.get('error_message')
            ))
            
            conn.commit()
            return cursor.lastrowid or 0
    
    def insert_email_send(self, send_data: Dict[str, Any]) -> int:
        """Insert email send record"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            next_eligible = datetime.now().date() + timedelta(days=config.COOLDOWN_DAYS)
            
            cursor.execute("""
                INSERT INTO email_sends (
                    lead_id, email_address, subject, sent_date, status,
                    response_code, error_message, next_eligible_date, campaign_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                send_data.get('lead_id'),
                send_data.get('email_address'),
                send_data.get('subject'),
                send_data.get('sent_date', datetime.now()),
                send_data.get('status'),
                send_data.get('response_code'),
                send_data.get('error_message'),
                next_eligible,
                send_data.get('campaign_id')
            ))
            
            conn.commit()
            return cursor.lastrowid or 0
    
    def get_leads_for_enrichment(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get leads that need email enrichment"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT l.* FROM leads l
                LEFT JOIN email_enrichment e ON l.id = e.lead_id
                WHERE l.website IS NOT NULL 
                AND l.website != ''
                AND l.domain IS NOT NULL
                AND e.id IS NULL
                AND l.status != 'excluded'
                ORDER BY l.quality_score DESC, l.scraped_date DESC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_leads_for_sending(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get leads ready for email sending (with cooldown check)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            today = datetime.now().date()
            
            cursor.execute("""
                SELECT l.*, e.email_address, e.confidence_score
                FROM leads l
                JOIN email_enrichment e ON l.id = e.lead_id
                LEFT JOIN email_sends es ON l.id = es.lead_id
                WHERE e.email_address IS NOT NULL
                AND e.status = 'found'
                AND l.status != 'excluded'
                AND (es.id IS NULL OR es.next_eligible_date <= ?)
                ORDER BY e.confidence_score DESC, l.quality_score DESC
                LIMIT ?
            """, (today, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def check_email_sent_recently(self, lead_id: int, days: Optional[int] = None) -> bool:
        """Check if email was sent to lead recently"""
        days = days or config.COOLDOWN_DAYS
        cutoff_date = datetime.now().date() - timedelta(days=days)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM email_sends
                WHERE lead_id = ? AND sent_date >= ?
            """, (lead_id, cutoff_date))
            
            result = cursor.fetchone()
            return (result[0] if result else 0) > 0
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Get statistics for dashboard"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total leads
            cursor.execute("SELECT COUNT(*) FROM leads")
            total_leads = cursor.fetchone()[0]
            
            # Leads with emails
            cursor.execute("""
                SELECT COUNT(*) FROM leads l
                JOIN email_enrichment e ON l.id = e.lead_id
                WHERE e.email_address IS NOT NULL
            """)
            leads_with_emails = cursor.fetchone()[0]
            
            # Emails sent today
            today = datetime.now().date()
            cursor.execute("""
                SELECT COUNT(*) FROM email_sends
                WHERE DATE(sent_date) = ?
            """, (today,))
            emails_sent_today = cursor.fetchone()[0]
            
            # Emails sent this week
            week_ago = today - timedelta(days=7)
            cursor.execute("""
                SELECT COUNT(*) FROM email_sends
                WHERE DATE(sent_date) >= ?
            """, (week_ago,))
            emails_sent_week = cursor.fetchone()[0]
            
            # Hunter credits used today
            cursor.execute("""
                SELECT COALESCE(SUM(credits_used), 0) FROM hunter_credits
                WHERE date = ?
            """, (today,))
            credits_used_today = cursor.fetchone()[0]
            
            # Success rate
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as successful
                FROM email_sends
                WHERE DATE(sent_date) >= ?
            """, (week_ago,))
            
            result = cursor.fetchone()
            success_rate = (result[1] / result[0] * 100) if result[0] > 0 else 0
            
            return {
                'total_leads': total_leads,
                'leads_with_emails': leads_with_emails,
                'emails_sent_today': emails_sent_today,
                'emails_sent_week': emails_sent_week,
                'credits_used_today': credits_used_today,
                'success_rate': round(success_rate, 1),
                'leads_pending_enrichment': total_leads - leads_with_emails
            }
    
    def log_system_event(self, level: str, module: str, message: str, details: Optional[str] = None):
        """Log system event"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO system_logs (level, module, message, details)
                VALUES (?, ?, ?, ?)
            """, (level, module, message, details))
            
            conn.commit()
    
    def backup_database(self) -> str:
        """Create database backup"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"automation_backup_{timestamp}.db"
        backup_dir = config.get_backup_path()
        backup_path = str(Path(backup_dir) / backup_filename)
        
        try:
            shutil.copy2(self.db_path, backup_path)
            logger.info(f"Database backed up to {backup_path}")
            
            # Log backup event
            self.log_system_event('INFO', 'database', f'Database backup created: {backup_filename}', None)
            
            return backup_path
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            raise
    
    def cleanup_old_backups(self):
        """Remove old backup files"""
        backup_dir = Path(config.BACKUP_DIR)
        cutoff_date = datetime.now() - timedelta(days=config.BACKUP_RETENTION_DAYS)
        
        for backup_file in backup_dir.glob("automation_backup_*.db"):
            if backup_file.stat().st_mtime < cutoff_date.timestamp():
                try:
                    backup_file.unlink()
                    logger.info(f"Removed old backup: {backup_file.name}")
                except Exception as e:
                    logger.error(f"Failed to remove old backup {backup_file.name}: {e}")
    
    def get_recent_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent system logs"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM system_logs
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]

# Global database instance
db = DatabaseManager()
