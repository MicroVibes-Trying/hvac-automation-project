"""
Enhanced HVAC Lead Scraper v3
Advanced lead scraping with quality scoring, deduplication, and database integration
"""
import requests
import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import re

from ..core.config import config
from ..core.database import db

# Configure logging
logging.basicConfig(level=getattr(logging, config.LOG_LEVEL))
logger = logging.getLogger(__name__)

class HVACLeadScraper:
    """Enhanced HVAC Lead Scraper with quality scoring and database integration"""
    
    def __init__(self):
        self.api_key = config.GOOGLE_PLACES_API_KEY
        self.base_url = "https://places.googleapis.com/v1/places:searchText"
        self.headers = {
            "Content-Type": "application/json",
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.nationalPhoneNumber,places.websiteUri,places.googleMapsUri,places.primaryTypeDisplayName,places.businessStatus,places.rating,places.userRatingCount,places.priceLevel"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Quality scoring weights
        self.quality_weights = {
            'has_website': 30,
            'has_phone': 20,
            'high_rating': 25,
            'many_reviews': 15,
            'complete_address': 10
        }
    
    def extract_domain(self, url: str) -> Optional[str]:
        """Extract clean domain from URL"""
        if not url:
            return None
        
        try:
            # Add protocol if missing
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Validate domain format
            if '.' not in domain or len(domain) < 4:
                return None
                
            return domain
        except Exception as e:
            logger.warning(f"Failed to extract domain from {url}: {e}")
            return None
    
    def calculate_quality_score(self, place_data: Dict[str, Any]) -> int:
        """Calculate quality score for a lead"""
        score = 0
        
        # Has website
        if place_data.get('website'):
            score += self.quality_weights['has_website']
        
        # Has phone
        if place_data.get('phone'):
            score += self.quality_weights['has_phone']
        
        # High rating (4.0+)
        rating = place_data.get('rating', 0)
        if rating >= 4.0:
            score += self.quality_weights['high_rating']
        elif rating >= 3.5:
            score += self.quality_weights['high_rating'] // 2
        
        # Many reviews (20+)
        review_count = place_data.get('user_rating_count', 0)
        if review_count >= 50:
            score += self.quality_weights['many_reviews']
        elif review_count >= 20:
            score += self.quality_weights['many_reviews'] // 2
        
        # Complete address
        address = place_data.get('address', '')
        if address and len(address.split(',')) >= 3:  # City, State, ZIP
            score += self.quality_weights['complete_address']
        
        return min(score, 100)  # Cap at 100
    
    def clean_phone_number(self, phone: str) -> Optional[str]:
        """Clean and validate phone number"""
        if not phone:
            return None
        
        # Remove all non-digit characters except + and -
        cleaned = re.sub(r'[^\d+\-\(\)\s]', '', phone)
        
        # Extract digits only for validation
        digits_only = re.sub(r'[^\d]', '', cleaned)
        
        # Validate US phone number (10 digits)
        if len(digits_only) == 10:
            return cleaned
        elif len(digits_only) == 11 and digits_only.startswith('1'):
            return cleaned
        
        return None
    
    def is_duplicate_lead(self, business_name: str, domain: Optional[str], phone: Optional[str]) -> bool:
        """Check if lead already exists in database"""
        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check by domain (most reliable)
                if domain:
                    cursor.execute("""
                        SELECT COUNT(*) FROM leads 
                        WHERE domain = ? AND status != 'excluded'
                    """, (domain,))
                    
                    if cursor.fetchone()[0] > 0:
                        return True
                
                # Check by business name and phone
                if business_name and phone:
                    cursor.execute("""
                        SELECT COUNT(*) FROM leads 
                        WHERE business_name = ? AND phone = ? AND status != 'excluded'
                    """, (business_name, phone))
                    
                    if cursor.fetchone()[0] > 0:
                        return True
                
                return False
                
        except Exception as e:
            logger.error(f"Error checking for duplicate lead: {e}")
            return False
    
    def make_api_request(self, query: str, location: str) -> List[Dict[str, Any]]:
        """Make API request to Google Places"""
        payload = {
            "textQuery": f"{query} in {location}",
            "maxResultCount": 20,
            "languageCode": "en"
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}?key={self.api_key}",
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                places = data.get("places", [])
                
                # Log API usage
                db.log_system_event(
                    'INFO', 
                    'scraper', 
                    f'Google Places API call successful: {query} in {location}',
                    f'Found {len(places)} places'
                )
                
                return places
                
            elif response.status_code == 429:
                logger.warning(f"Rate limit hit for '{query}' in '{location}'")
                time.sleep(60)  # Wait 1 minute
                return []
                
            else:
                logger.error(f"API request failed: {response.status_code} - {response.text}")
                return []
                
        except requests.exceptions.Timeout:
            logger.error(f"API request timeout for '{query}' in '{location}'")
            return []
        except Exception as e:
            logger.error(f"API request error for '{query}' in '{location}': {e}")
            return []
    
    def process_place(self, place: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single place from API response"""
        try:
            # Skip permanently closed businesses
            if place.get("businessStatus") == "CLOSED_PERMANENTLY":
                return None
            
            # Extract basic data
            business_name = place.get("displayName", {}).get("text", "").strip()
            if not business_name:
                return None
            
            address = place.get("formattedAddress", "").strip()
            phone = self.clean_phone_number(place.get("nationalPhoneNumber", ""))
            website = place.get("websiteUri", "").strip()
            domain = self.extract_domain(website) if website else None
            
            # Skip if no website (we need this for email enrichment)
            if not domain:
                return None
            
            # Check for duplicates
            if self.is_duplicate_lead(business_name, domain, phone):
                logger.debug(f"Skipping duplicate: {business_name}")
                return None
            
            # Build lead data
            lead_data = {
                'business_name': business_name,
                'address': address,
                'phone': phone,
                'website': website,
                'domain': domain,
                'google_maps_url': place.get("googleMapsUri", ""),
                'category': place.get("primaryTypeDisplayName", {}).get("text", ""),
                'business_status': place.get("businessStatus", "OPERATIONAL"),
                'rating': place.get("rating", 0),
                'user_rating_count': place.get("userRatingCount", 0),
                'scraped_date': datetime.now().date()
            }
            
            # Calculate quality score
            lead_data['quality_score'] = self.calculate_quality_score(lead_data)
            
            return lead_data
            
        except Exception as e:
            logger.error(f"Error processing place: {e}")
            return None
    
    def scrape_leads(self) -> Dict[str, Any]:
        """Main scraping function"""
        logger.info("🔍 Starting HVAC lead scraping...")
        
        start_time = datetime.now()
        total_found = 0
        total_saved = 0
        total_duplicates = 0
        errors = []
        
        try:
            total_requests = len(config.CITIES) * len(config.SEARCH_KEYWORDS)
            current_request = 0
            
            for city in config.CITIES:
                for keyword in config.SEARCH_KEYWORDS:
                    current_request += 1
                    logger.info(f"🔍 Searching: '{keyword}' in '{city}' ({current_request}/{total_requests})")
                    
                    try:
                        places = self.make_api_request(keyword, city)
                        total_found += len(places)
                        
                        for place in places:
                            lead_data = self.process_place(place)
                            
                            if lead_data:
                                try:
                                    lead_id = db.insert_lead(lead_data)
                                    if lead_id > 0:
                                        total_saved += 1
                                        logger.debug(f"✅ Saved: {lead_data['business_name']}")
                                    else:
                                        logger.warning(f"Failed to save: {lead_data['business_name']}")
                                except Exception as e:
                                    logger.error(f"Database error saving lead: {e}")
                                    errors.append(f"Database error: {str(e)}")
                            else:
                                total_duplicates += 1
                        
                        # Respectful delay between requests
                        time.sleep(config.THROTTLE_DELAY)
                        
                    except Exception as e:
                        error_msg = f"Error processing {keyword} in {city}: {str(e)}"
                        logger.error(error_msg)
                        errors.append(error_msg)
            
            # Calculate duration
            duration = datetime.now() - start_time
            
            # Prepare summary
            summary = {
                'total_found': total_found,
                'total_saved': total_saved,
                'total_duplicates': total_duplicates,
                'duration': str(duration).split('.')[0],  # Remove microseconds
                'errors': errors,
                'success': total_saved > 0
            }
            
            # Log completion
            db.log_system_event(
                'INFO',
                'scraper',
                f'Scraping completed: {total_saved} leads saved',
                f'Found: {total_found}, Saved: {total_saved}, Duplicates: {total_duplicates}'
            )
            
            logger.info(f"✅ Scraping complete: {total_saved} new leads saved")
            return summary
            
        except Exception as e:
            error_msg = f"Scraping failed: {str(e)}"
            logger.error(error_msg)
            
            db.log_system_event('ERROR', 'scraper', error_msg, None)
            
            return {
                'total_found': total_found,
                'total_saved': total_saved,
                'total_duplicates': total_duplicates,
                'duration': str(datetime.now() - start_time).split('.')[0],
                'errors': errors + [error_msg],
                'success': False
            }

def main():
    """Main function for standalone execution"""
    try:
        scraper = HVACLeadScraper()
        results = scraper.scrape_leads()
        
        print(f"\n📊 Scraping Results:")
        print(f"   Found: {results['total_found']} leads")
        print(f"   Saved: {results['total_saved']} new leads")
        print(f"   Duplicates: {results['total_duplicates']}")
        print(f"   Duration: {results['duration']}")
        
        if results['errors']:
            print(f"   Errors: {len(results['errors'])}")
            for error in results['errors'][:3]:  # Show first 3 errors
                print(f"     - {error}")
        
        return results['total_saved']
        
    except Exception as e:
        logger.error(f"Main execution failed: {e}")
        return 0

if __name__ == "__main__":
    saved_count = main()
    exit(0 if saved_count > 0 else 1)
