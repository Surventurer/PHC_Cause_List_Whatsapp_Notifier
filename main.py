import requests
import os
import time
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from bs4 import BeautifulSoup


# Define India Standard Time
IST = ZoneInfo("Asia/Kolkata")


class ScreenshotManager:
    """Manages screenshot fetching operations"""
    
    def __init__(self, target_url, cache_dir="cache"):
        """
        Initialize ScreenshotManager.
        
        Args:
            target_url: URL to screenshot
            cache_dir: Directory to save screenshot temporarily
        """
        self.target_url = target_url
        self.api_url = "https://api.microlink.io/"
        
        # File path for screenshot
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.screenshot_path = os.path.join(self.cache_dir, "screenshot.png")
    
    def fetch_screenshot(self):
        """Fetch screenshot from API and save to cache folder"""
        try:
            print("[INFO] Fetching screenshot from API...")
            response = requests.get(self.api_url, params={
                "url": self.target_url,
                "screenshot.fullPage": "true",
                # "screenshot.type": "png"
            })
            response.raise_for_status()
            
            data = response.json()
            screenshot_url = data["data"]["screenshot"]["url"]
            
            # Download and save the screenshot
            image_bytes = requests.get(screenshot_url).content
            with open(self.screenshot_path, "wb") as f:
                f.write(image_bytes)
            
            print(f"[OK] Screenshot saved to: {self.screenshot_path} ({len(image_bytes)} bytes)")
            return True
        except Exception as e:
            print(f"[ERROR] Failed to fetch screenshot: {e}")
            return False
    
    def get_screenshot(self):
        """Fetch new screenshot and return the file path"""
        if self.fetch_screenshot():
            return self.screenshot_path
        return None
    
    def extract_date_from_webpage(self):
        """Extract cause list date from the webpage content"""
        try:
            print("[INFO] Fetching webpage to extract cause list date...")
            response = requests.get(self.target_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # First, try to find the specific element with ID that contains the cause list date
            # The Patna High Court page has: <span id="ctl00_MainContent_lblHeader">Cause List for DD-MM-YYYY</span>
            header_element = soup.find(id='ctl00_MainContent_lblHeader')
            if header_element:
                header_text = header_element.get_text(strip=True)
                print(f"[INFO] Found header element: {header_text}")
                
                # Extract date from "Cause List for DD-MM-YYYY" format
                date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})', header_text)
                if date_match:
                    date_str = date_match.group(1)
                    for date_format in ['%d-%m-%Y', '%d/%m/%Y']:
                        try:
                            extracted_date = datetime.strptime(date_str, date_format)
                            print(f"[OK] Extracted date from header: {extracted_date.strftime('%d-%m-%Y')}")
                            return extracted_date
                        except ValueError:
                            continue
            
            # Fallback: Look for date in general text content
            text_content = soup.get_text()
            
            # Pattern: DD-MM-YYYY or DD/MM/YYYY
            date_patterns = [
                r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b',  # DD-MM-YYYY or DD/MM/YYYY
                r'\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})\b',  # DD Month YYYY
            ]
            
            for pattern in date_patterns:
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                if matches:
                    for match in matches:
                        # Try to parse the date
                        for date_format in ['%d-%m-%Y', '%d/%m/%Y', '%d %B %Y', '%d %b %Y']:
                            try:
                                extracted_date = datetime.strptime(match, date_format)
                                # Return dates within a reasonable range (60 days past to 30 days future)
                                # Use .date() for comparison to avoid timezone issues
                                days_diff = (extracted_date.date() - datetime.now(IST).date()).days
                                if -60 <= days_diff <= 30:
                                    print(f"[OK] Extracted date from webpage: {extracted_date.strftime('%d-%m-%Y')}")
                                    return extracted_date
                            except ValueError:
                                continue
            
            # If no date found in standard formats, look in specific HTML elements
            date_elements = soup.find_all(['h1', 'h2', 'h3', 'h4', 'div', 'span', 'td'], 
                                         string=re.compile(r'\d{1,2}[-/]\d{1,2}[-/]\d{4}'))
            
            for element in date_elements:
                element_text = element.get_text(strip=True)
                matches = re.findall(r'\d{1,2}[-/]\d{1,2}[-/]\d{4}', element_text)
                if matches:
                    for match in matches:
                        for date_format in ['%d-%m-%Y', '%d/%m/%Y']:
                            try:
                                extracted_date = datetime.strptime(match, date_format)
                                days_diff = (extracted_date.date() - datetime.now(IST).date()).days
                                if -60 <= days_diff <= 30:
                                    print(f"[OK] Extracted date from webpage element: {extracted_date.strftime('%d-%m-%Y')}")
                                    return extracted_date
                            except ValueError:
                                continue
            
            print("[WARN] Could not extract date from webpage")
            return None
            
        except Exception as e:
            print(f"[WARN] Failed to extract date from webpage: {e}")
            return None



class WhatsAppManager:
    """Manages WhatsApp Business Cloud API operations"""
    
    def __init__(self, phone_number_id, access_token):
        self.phone_number_id = phone_number_id
        self.access_token = access_token
        self.api_base_url = "https://graph.facebook.com/v21.0"
    
    def upload_media(self, image_path):
        """Upload media to WhatsApp Cloud API and get media ID"""
        url = f"{self.api_base_url}/{self.phone_number_id}/media"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }
        
        files = {
            "file": ("screenshot.png", open(image_path, "rb"), "image/png")
        }
        
        data = {
            "messaging_product": "whatsapp"
        }
        
        try:
            response = requests.post(url, headers=headers, data=data, files=files)
            response.raise_for_status()
            
            media_id = response.json().get("id")
            print(f"[OK] Media uploaded successfully! Media ID: {media_id}")
            return media_id
            
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Media upload failed: {e}")
            if hasattr(e.response, 'text'):
                print(f"Error details: {e.response.text}")
            return None
    
    def send_image(self, recipient_number, media_id, caption=""):
        """Send image message via WhatsApp Business Cloud API"""
        url = f"{self.api_base_url}/{self.phone_number_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_number,
            "type": "image",
            "image": {
                "id": media_id,
                "caption": caption
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            message_id = result.get("messages", [{}])[0].get("id")
            print(f"[OK] WhatsApp message sent successfully! Message ID: {message_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to send WhatsApp message: {e}")
            if hasattr(e.response, 'text'):
                print(f"Error details: {e.response.text}")
            return False
    
    def send_text(self, recipient_number, message):
        """Send text message via WhatsApp Business Cloud API"""
        url = f"{self.api_base_url}/{self.phone_number_id}/messages"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient_number,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message
            }
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            print(f"[OK] Text message sent successfully!")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Failed to send text message: {e}")
            if hasattr(e.response, 'text'):
                print(f"Error details: {e.response.text}")
            return False
    
    def send_screenshot(self, image_path, recipient_number, caption="Court Cause List Screenshot"):
        """Complete workflow: Upload media and send via WhatsApp"""
        print("[INFO] Uploading image to WhatsApp...")
        media_id = self.upload_media(image_path)
        
        if not media_id:
            return False
        
        print(f"[INFO] Sending to WhatsApp number: {recipient_number}")
        return self.send_image(recipient_number, media_id, caption)
    
    def send_to_multiple(self, image_path, recipient_numbers, caption="", delay_seconds=2):
        """Send screenshot to multiple recipients with delay between sends"""
        successful_sends = 0
        failed_sends = 0
        
        for idx, recipient in enumerate(recipient_numbers, 1):
            print(f"\n[{idx}/{len(recipient_numbers)}] Sending to {recipient}...")
            success = self.send_screenshot(image_path, recipient, caption=caption)
            
            if success:
                successful_sends += 1
            else:
                failed_sends += 1
            
            # Add delay between sends to avoid rate limiting
            if idx < len(recipient_numbers):
                time.sleep(delay_seconds)
        
        return successful_sends, failed_sends


def is_within_time_window(start_hour=20, start_minute=0, end_hour=23, end_minute=30):
    """Check if current time is within the specified time window (8:00 PM to 11:30 PM IST)"""
    now = datetime.now(IST)
    current_minutes = now.hour * 60 + now.minute
    start_minutes = start_hour * 60 + start_minute
    end_minutes = end_hour * 60 + end_minute
    return start_minutes <= current_minutes <= end_minutes


def get_sent_marker_file():
    """Get the path to the marker file that tracks if message was sent today"""
    cache_dir = "cache"
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, "sent_today.txt")


def was_message_sent_today():
    """Check if message was already sent today"""
    marker_file = get_sent_marker_file()
    if os.path.exists(marker_file):
        with open(marker_file, 'r') as f:
            sent_date = f.read().strip()
            today_str = datetime.now(IST).strftime('%Y-%m-%d')
            return sent_date == today_str
    return False


def mark_message_sent():
    """Mark that message was sent today"""
    marker_file = get_sent_marker_file()
    with open(marker_file, 'w') as f:
        f.write(datetime.now(IST).strftime('%Y-%m-%d'))
    print("[INFO] Marked message as sent for today")


def send_cause_list():
    """Send cause list screenshot via WhatsApp - returns True if sent successfully"""
    # Load environment variables
    load_dotenv()
    
    today = datetime.now(IST)
    
    # Configuration
    TARGET_URL = "https://patnahighcourt.gov.in/causelist/auin/view/4079/0/CLIST"
    PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
    ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
    RECIPIENT_NUMBERS_STR = os.getenv("RECIPIENT_NUMBER")
    
    # Validate environment variables
    if not PHONE_NUMBER_ID or not ACCESS_TOKEN or not RECIPIENT_NUMBERS_STR:
        raise ValueError("[ERROR] Missing required environment variables. Please check your .env file.")
    
    # Parse multiple recipient numbers (comma-separated)
    recipient_numbers = [num.strip() for num in RECIPIENT_NUMBERS_STR.split(',')]
    
    # Initialize screenshot manager
    screenshot_manager = ScreenshotManager(
        target_url=TARGET_URL,
        cache_dir="cache"
    )
    
    # Extract cause list date from webpage automatically
    cause_list_date = screenshot_manager.extract_date_from_webpage()
    
    # If no date found, skip
    if not cause_list_date:
        print("[ERROR] Could not determine cause list date")
        return False
    
    # Check if cause list date is greater than today
    if cause_list_date.date() <= today.date():
        print(f"[SKIP] Cause list date ({cause_list_date.strftime('%d-%m-%Y')}) is not greater than today ({today.strftime('%d-%m-%Y')})")
        return False
    
    print("=" * 50)
    print("Court Cause List Screenshot to WhatsApp")
    print(f"Today: {today.strftime('%A, %d-%m-%Y')}")
    print(f"Cause List Date: {cause_list_date.strftime('%A, %d-%m-%Y')}")
    print("=" * 50)
    
    # Initialize WhatsApp manager
    whatsapp_manager = WhatsAppManager(
        phone_number_id=PHONE_NUMBER_ID,
        access_token=ACCESS_TOKEN
    )
    
    # Get screenshot
    screenshot_path = screenshot_manager.get_screenshot()
    if not screenshot_path:
        print("[ERROR] Failed to get screenshot")
        return False
    
    print(f"[INFO] Cached file: {screenshot_path}")
    
    # Send via WhatsApp
    print("\n" + "=" * 50)
    print(f"[INFO] Sending to {len(recipient_numbers)} recipient(s)...")
    print("=" * 50)
    
    caption = f"Patna High Court Cause List\n{cause_list_date.strftime('%d-%m-%Y')}"
    
    successful_sends, failed_sends = whatsapp_manager.send_to_multiple(
        screenshot_path,
        recipient_numbers,
        caption=caption,
        delay_seconds=2
    )
    
    # Clean up temp file after sending
    if os.path.exists(screenshot_path):
        os.remove(screenshot_path)
        print(f"[INFO] Temp file deleted: {screenshot_path}")
    
    print("\n" + "=" * 50)
    print(f"[OK] Successfully sent: {successful_sends}/{len(recipient_numbers)}")
    if failed_sends > 0:
        print(f"[ERROR] Failed sends: {failed_sends}/{len(recipient_numbers)}")
    print("=" * 50)
    
    return successful_sends > 0


def run_scheduler():
    """
    Run the scheduler that checks every 10 minutes between 9:30 PM and 11:30 PM.
    Sends WhatsApp message when cause list date is greater than today.
    """
    print("=" * 50)
    print("Cause List Scheduler Started")
    print("Active window: 8:00 PM - 11:30 PM IST")
    print("Check interval: Every 10 minutes")
    print("=" * 50)
    
    CHECK_INTERVAL_SECONDS = 10 * 60  # 10 minutes
    
    
    while True:
        now = datetime.now(IST)
        
        # Check if within time window (8:00 PM to 11:30 PM IST)
        if not is_within_time_window():
            print(f"\n[{now.strftime('%H:%M:%S')}] [SKIP] Outside active window (8:00 PM - 11:30 PM IST)")
            print("[INFO] Waiting for next check...")
            time.sleep(CHECK_INTERVAL_SECONDS)
            continue
        
        # Check if message was already sent today
        if was_message_sent_today():
            print(f"\n[{now.strftime('%H:%M:%S')}] [OK] Message already sent today - Skipping")
            time.sleep(CHECK_INTERVAL_SECONDS)
            continue
        
        print(f"\n[{now.strftime('%H:%M:%S')}] [INFO] Checking cause list...")
        
        try:
            # Try to send cause list
            if send_cause_list():
                mark_message_sent()
                print("[OK] Message sent successfully! Will resume checking tomorrow.")
            else:
                print("[INFO] Cause list not ready yet. Will check again in 10 minutes.")
        except Exception as e:
            print(f"[ERROR] Error during execution: {e}")
        
        print(f"[INFO] Next check in 10 minutes...")
        time.sleep(CHECK_INTERVAL_SECONDS)


def main():
    """Main execution function - runs in scheduler mode"""
    import sys
    
    # Check for --once flag to run just once (for testing or cron)
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        print("[INFO] Running in single execution mode...")
        load_dotenv()
        
        if send_cause_list():
            print("[OK] Message sent successfully!")
        else:
            print("[ERROR] Failed to send message or conditions not met")
    else:
        # Run the scheduler
        run_scheduler()


if __name__ == "__main__":
    main()