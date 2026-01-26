import requests
import os
import json
import time
import re
from datetime import datetime, timedelta
from dotenv import load_dotenv
from bs4 import BeautifulSoup


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
            print("🌐 Fetching screenshot from API...")
            response = requests.get(self.api_url, params={
                "url": self.target_url,
                "screenshot.fullPage": "true",
                "screenshot.type": "png"
            })
            response.raise_for_status()
            
            data = response.json()
            screenshot_url = data["data"]["screenshot"]["url"]
            
            # Download and save the screenshot
            image_bytes = requests.get(screenshot_url).content
            with open(self.screenshot_path, "wb") as f:
                f.write(image_bytes)
            
            print(f"💾 Screenshot saved to: {self.screenshot_path} ({len(image_bytes)} bytes)")
            return True
        except Exception as e:
            print(f"❌ Failed to fetch screenshot: {e}")
            return False
    
    def get_screenshot(self):
        """Fetch new screenshot and return the file path"""
        if self.fetch_screenshot():
            return self.screenshot_path
        return None
    
    def extract_date_from_webpage(self):
        """Extract cause list date from the webpage content"""
        try:
            print("🔍 Fetching webpage to extract cause list date...")
            response = requests.get(self.target_url, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Common patterns to look for dates in cause list pages
            # Pattern 1: Look for date in text content
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
                                # Only return dates that are reasonable (within 30 days from now)
                                days_diff = (extracted_date - datetime.now()).days
                                if -7 <= days_diff <= 30:
                                    print(f"✅ Extracted date from webpage: {extracted_date.strftime('%d-%m-%Y')}")
                                    return extracted_date
                            except ValueError:
                                continue
            
            # If no date found in standard formats, look in specific HTML elements
            # Look for common class names or IDs that might contain dates
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
                                days_diff = (extracted_date - datetime.now()).days
                                if -7 <= days_diff <= 30:
                                    print(f"✅ Extracted date from webpage element: {extracted_date.strftime('%d-%m-%Y')}")
                                    return extracted_date
                            except ValueError:
                                continue
            
            print("⚠️  Could not extract date from webpage")
            return None
            
        except Exception as e:
            print(f"⚠️  Failed to extract date from webpage: {e}")
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
            print(f"✅ Media uploaded successfully! Media ID: {media_id}")
            return media_id
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Media upload failed: {e}")
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
            print(f"✅ WhatsApp message sent successfully! Message ID: {message_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to send WhatsApp message: {e}")
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
            print(f"✅ Text message sent successfully!")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to send text message: {e}")
            if hasattr(e.response, 'text'):
                print(f"Error details: {e.response.text}")
            return False
    
    def send_screenshot(self, image_path, recipient_number, caption="📋 Court Cause List Screenshot"):
        """Complete workflow: Upload media and send via WhatsApp"""
        print("📤 Uploading image to WhatsApp...")
        media_id = self.upload_media(image_path)
        
        if not media_id:
            return False
        
        print(f"📱 Sending to WhatsApp number: {recipient_number}")
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


def main():
    """Main execution function"""
    # Load environment variables
    load_dotenv()
    
    # Check if today is Sunday (weekday 6 = Sunday)
    today = datetime.now()
    if today.weekday() == 6:
        print("=" * 50)
        print("⏸️  Skipping execution - Today is Sunday")
        print("=" * 50)
        return
    
    # Configuration
    TARGET_URL = "https://patnahighcourt.gov.in/causelist/auin/view/4079/0/CLIST"
    PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
    ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
    RECIPIENT_NUMBERS_STR = os.getenv("RECIPIENT_NUMBER")
    #CAUSE_LIST_DATE_STR = os.getenv("CAUSE_LIST_DATE")  # Optional: manual override date in DD-MM-YYYY format
    
    # Validate environment variables
    if not PHONE_NUMBER_ID or not ACCESS_TOKEN or not RECIPIENT_NUMBERS_STR:
        raise ValueError("❌ Missing required environment variables. Please check your .env file.")
    
    # Parse multiple recipient numbers (comma-separated)
    recipient_numbers = [num.strip() for num in RECIPIENT_NUMBERS_STR.split(',')]
    
    # Initialize screenshot manager early to extract date
    screenshot_manager = ScreenshotManager(
        target_url=TARGET_URL,
        cache_dir="cache"
    )
    
    # Extract cause list date from webpage automatically
    cause_list_date = screenshot_manager.extract_date_from_webpage()
    
    # If no date found, skip execution
    if not cause_list_date:
        print("=" * 50)
        print("❌ Skipping execution - Could not determine cause list date")
        print("💡 The date should be automatically extracted from the webpage")
        print("💡 Or set CAUSE_LIST_DATE in .env file (format: DD-MM-YYYY)")
        print("=" * 50)
        return
    
    # Validate that cause list date is in the future
    if cause_list_date.date() <= today.date():
        print("=" * 50)
        print(f"⏸️  Skipping execution - Cause list date ({cause_list_date.strftime('%d-%m-%Y')}) is not in the future")
        print(f"📅 Today: {today.strftime('%d-%m-%Y')}")
        print("=" * 50)
        return
    
    print("=" * 50)
    print("📋 Court Cause List Screenshot to WhatsApp")
    print(f"� Today: {today.strftime('%A, %d-%m-%Y')}")
    if cause_list_date:
        print(f"📋 Cause List Date: {cause_list_date.strftime('%A, %d-%m-%Y')}")
    print("=" * 50)
    
    # Initialize WhatsApp manager
    whatsapp_manager = WhatsAppManager(
        phone_number_id=PHONE_NUMBER_ID,
        access_token=ACCESS_TOKEN
    )
    
    # Get screenshot
    screenshot_path = screenshot_manager.get_screenshot()
    if not screenshot_path:
        print("❌ Failed to get screenshot")
        return
    
    print(f"📁 Cached file: {screenshot_path}")
    
    # Send via WhatsApp
    print("\n" + "=" * 50)
    print(f"📱 Sending to {len(recipient_numbers)} recipient(s)...")
    print("=" * 50)
    
    # Prepare caption with appropriate date
    if cause_list_date:
        caption = f"Patna High Court Cause List\n{cause_list_date.strftime('%d-%m-%Y')}"
    else:
        caption = f"Patna High Court Cause List\n{time.strftime('%d-%m-%Y')}"
    
    successful_sends, failed_sends = whatsapp_manager.send_to_multiple(
        screenshot_path,
        recipient_numbers,
        caption=caption,
        delay_seconds=2
    )
    
    # Clean up temp file after sending
    if os.path.exists(screenshot_path):
        os.remove(screenshot_path)
        print(f"🗑️  Temp file deleted: {screenshot_path}")
    
    print("\n" + "=" * 50)
    print(f"✅ Successfully sent: {successful_sends}/{len(recipient_numbers)}")
    if failed_sends > 0:
        print(f"❌ Failed sends: {failed_sends}/{len(recipient_numbers)}")
    print("=" * 50)


if __name__ == "__main__":
    main()