import requests
import os
import json
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

API_URL = "https://api.microlink.io/"
TARGET_URL = "https://patnahighcourt.gov.in/causelist/auin/view/4079/0/CLIST"

CACHE_DIR = "cache"
CACHE_META = os.path.join(CACHE_DIR, "meta.json")
SCREENSHOT_FILE = os.path.join(CACHE_DIR, "screenshot.png")

TTL_SECONDS = 1 * 60 * 60  # 1 hour

# WhatsApp Business Cloud API Configuration from .env
WHATSAPP_API_URL = "https://graph.facebook.com/v21.0"
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
WHATSAPP_BUSINESS_ACCOUNT_ID = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
RECIPIENT_NUMBERS_STR = os.getenv("RECIPIENT_NUMBER")

# Validate environment variables
if not PHONE_NUMBER_ID or not ACCESS_TOKEN or not RECIPIENT_NUMBERS_STR:
    raise ValueError("❌ Missing required environment variables. Please check your .env file.")

# Parse multiple recipient numbers (comma-separated)
RECIPIENT_NUMBERS = [num.strip() for num in RECIPIENT_NUMBERS_STR.split(',')]

os.makedirs(CACHE_DIR, exist_ok=True)


def cache_is_valid():
    if not os.path.exists(CACHE_META) or not os.path.exists(SCREENSHOT_FILE):
        return False

    with open(CACHE_META, "r") as f:
        meta = json.load(f)

    age = time.time() - meta["timestamp"]
    return age < meta["ttl"]


def save_cache(metadata, image_bytes):
    with open(SCREENSHOT_FILE, "wb") as f:
        f.write(image_bytes)

    with open(CACHE_META, "w") as f:
        json.dump({
            "timestamp": time.time(),
            "ttl": TTL_SECONDS,
            "source_url": TARGET_URL
        }, f)


def upload_media_to_whatsapp(image_path):
    """
    Upload media to WhatsApp Cloud API and get media ID
    """
    url = f"{WHATSAPP_API_URL}/{PHONE_NUMBER_ID}/media"
    
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}"
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


def send_whatsapp_image(recipient_number, media_id, caption=""):
    """
    Send image message via WhatsApp Business Cloud API
    """
    url = f"{WHATSAPP_API_URL}/{PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
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


def send_whatsapp_text(recipient_number, message):
    """
    Send text message via WhatsApp Business Cloud API
    """
    url = f"{WHATSAPP_API_URL}/{PHONE_NUMBER_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
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


def send_screenshot_via_whatsapp(image_path, recipient_number, caption="📋 Court Cause List Screenshot"):
    """
    Complete workflow: Upload media and send via WhatsApp
    """
    print("📤 Uploading image to WhatsApp...")
    media_id = upload_media_to_whatsapp(image_path)
    
    if not media_id:
        return False
    
    print(f"📱 Sending to WhatsApp number: {recipient_number}")
    return send_whatsapp_image(recipient_number, media_id, caption)


def main():
    """Main execution function"""
    print("=" * 50)
    print("📋 Court Cause List Screenshot to WhatsApp")
    print("=" * 50)
    
    # Check cache validity
    if cache_is_valid():
        print("✅ Loaded screenshot from cache")
    else:
        print("🌐 Cache expired or missing — fetching")

        try:
            response = requests.get(API_URL, params={
                "url": TARGET_URL,
                "screenshot.fullPage": "true",
                "screenshot.type": "png"
            })
            response.raise_for_status()

            data = response.json()
            screenshot_url = data["data"]["screenshot"]["url"]

            image = requests.get(screenshot_url).content
            save_cache(data, image)

            print("📸 Screenshot fetched & cached")
            
        except Exception as e:
            print(f"❌ Failed to fetch screenshot: {e}")
            return

    print("📁 Cached file:", SCREENSHOT_FILE)

    # Send via WhatsApp Business Cloud API
    print("\n" + "=" * 50)
    print(f"📱 Sending to {len(RECIPIENT_NUMBERS)} recipient(s)...")
    print("=" * 50)
    
    caption = f"Patna High Court Cause List\n{time.strftime('%d-%m-%Y')}"
    successful_sends = 0
    failed_sends = 0
    
    for idx, recipient in enumerate(RECIPIENT_NUMBERS, 1):
        print(f"\n[{idx}/{len(RECIPIENT_NUMBERS)}] Sending to {recipient}...")
        success = send_screenshot_via_whatsapp(
            SCREENSHOT_FILE, 
            recipient,
            caption=caption
        )
        
        if success:
            successful_sends += 1
        else:
            failed_sends += 1
        
        # Add small delay between sends to avoid rate limiting
        if idx < len(RECIPIENT_NUMBERS):
            time.sleep(2)
    
    print("\n" + "=" * 50)
    print(f"✅ Successfully sent: {successful_sends}/{len(RECIPIENT_NUMBERS)}")
    if failed_sends > 0:
        print(f"❌ Failed sends: {failed_sends}/{len(RECIPIENT_NUMBERS)}")
    print("=" * 50)


if __name__ == "__main__":
    main()