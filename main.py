import requests
import os
import time
import re
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from bs4 import BeautifulSoup
from camoufox.sync_api import Camoufox
import base64
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler


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
        
        # File path for screenshot
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.screenshot_path = os.path.join(self.cache_dir, "screenshot.png")
    
    def process_webpage(self, browser=None):
        """
        Unified method to check date and capture screenshot.
        Args:
            browser: Optional existing Camoufox browser instance.
        """
        print(f"[INFO] Launching Camoufox to check date and capture screenshot...")
        
        # Internal helper to run logic with a given browser
        def _run_with_browser(browser_instance):
            # Determine quality settings from environment variable
            quality_setting = os.getenv("SCREENSHOT_QUALITY", "HIGH").upper()
            
            if quality_setting == "LOW":
                viewport = {"width": 800, "height": 600}
                scale_factor = 1
                print("[INFO] Using LOW quality (800x600, 1x)")
            elif quality_setting == "MEDIUM":
                viewport = {"width": 1280, "height": 720}
                scale_factor = 1
                print("[INFO] Using MEDIUM quality (1280x720, 1x)")
            else: # Default to HIGH
                viewport = {"width": 1920, "height": 1080}
                scale_factor = 2
                print(f"[INFO] Using {quality_setting} quality (1920x1080, 2x)")

            page = browser_instance.new_page(
                viewport=viewport,
                device_scale_factor=scale_factor
            )
            page.set_default_timeout(60000)
            
            print(f"[INFO] Navigating to: {self.target_url}")
            page.goto(self.target_url)
            
            # Wait for content
            time.sleep(5)
            
            # --- 1. Extract Date ---
            extracted_date = self._extract_date_from_page_content(page.content())
            
            if not extracted_date:
                 print("[WARN] Could not extract date from webpage.")
                 page.close()
                 return None, None
            
            # --- 2. Take Screenshot ---
            # We take it now while the browser is open. 
            page.screenshot(path=self.screenshot_path, full_page=True)
            file_size = os.path.getsize(self.screenshot_path)
            print(f"[OK] Screenshot captured: {self.screenshot_path} ({file_size} bytes)")
            
            page.close()
            return extracted_date, self.screenshot_path

        try:
            if browser:
                return _run_with_browser(browser)
            else:
                with Camoufox(headless=True) as new_browser:
                    return _run_with_browser(new_browser)

        except Exception as e:
            print(f"[ERROR] Browser automation failed: {e}")
            return None, None

    def _extract_date_from_page_content(self, html_content):
        """Helper to parse date from HTML content (using BeautifulSoup)"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Strategy 1: Specific ID
            header_element = soup.find(id='ctl00_MainContent_lblHeader')
            if header_element:
                header_text = header_element.get_text(strip=True)
                print(f"[INFO] Found header element: {header_text}")
                
                date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})', header_text)
                if date_match:
                    try:
                        return datetime.strptime(date_match.group(1), '%d-%m-%Y')
                    except ValueError:
                        pass
            
            # Strategy 2: Regex in full text
            text_content = soup.get_text()
            matches = re.findall(r'\b(\d{1,2}[-/]\d{1,2}[-/]\d{4})\b', text_content)
            
            for match in matches:
                try:
                    d = datetime.strptime(match, '%d-%m-%Y')
                    # Sanity check: is date within reasonable range? (+/- 60 days)
                    if abs((d - datetime.now()).days) < 60:
                        print(f"[INFO] Extracted date from text: {match}")
                        return d
                except ValueError:
                    continue
            
            return None
            
        except Exception as e:
            print(f"[WARN] Date parsing failed: {e}")
            return None



import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler

class QRHandler(SimpleHTTPRequestHandler):
    """Custom handler to serve the QR dashboard"""
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>WhatsApp Web Login</title>
                <meta http-equiv="refresh" content="5">
                <style>
                    body { font-family: sans-serif; text-align: center; padding: 50px; background: #f0f2f5; }
                    .card { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); display: inline-block; }
                    h1 { color: #128C7E; }
                    img { border: 1px solid #ddd; margin-top: 20px; max-width: 100%; }
                    p { color: #666; }
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>Scan QR Code</h1>
                    <p>Open WhatsApp on your phone > Menu > Linked Devices > Link a Device</p>
                    <p>This page auto-refreshes every 5 seconds to show the latest code.</p>
                    <img src="/whatsapp_qr.png" alt="Waiting for QR Code..." />
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode())
        elif self.path == '/whatsapp_qr.png':
            # Serve the specific file from the cache directory
            # We map this request to the actual file path dynamically
            cache_dir = getattr(self.server, 'cache_dir', 'cache')
            qr_path = os.path.join(cache_dir, 'whatsapp_qr.png')
            
            try:
                with open(qr_path, 'rb') as f:
                    self.send_response(200)
                    self.send_header('Content-type', 'image/png')
                    self.end_headers()
                    self.wfile.write(f.read())
            except FileNotFoundError:
                self.send_error(404, f"QR Code not found yet in {qr_path}")
        else:
            self.send_error(404)

class WhatsAppWebClient:
    """
    Native Python WhatsApp Web Client using Camoufox/Playwright.
    Bypasses official API requirements and uses existing phone number.
    Offers Live QR Dashboard at http://localhost:3000
    """
    
    def __init__(self, cache_dir="cache"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.session_path = os.path.join(self.cache_dir, "whatsapp_session.json")
        self.qr_path = os.path.join(self.cache_dir, "whatsapp_qr.png")
        
    def _start_qr_server(self):
        """Starts a background HTTP server to serve the QR code"""
        try:
            server = HTTPServer(('0.0.0.0', 3000), QRHandler)
            # Inject cache directory so the handler knows where to look
            server.cache_dir = self.cache_dir
            
            thread = threading.Thread(target=server.serve_forever)
            thread.daemon = True
            thread.start()
            print("[INFO] Live QR Dashboard running at: http://localhost:3000")
            return server
        except Exception as e:
            print(f"[WARN] Failed to start QR server: {e}")
            return None

    def _save_debug_screenshot(self, page, name):
        """Helper to save debug screenshots with timestamp"""
        try:
            timestamp = datetime.now().strftime("%H%M%S")
            filename = f"debug_{timestamp}_{name}.png"
            path = os.path.join(self.cache_dir, filename)
            page.screenshot(path=path, full_page=True)
            print(f"[DEBUG] Saved screenshot: {filename}")
        except Exception as e:
            print(f"[WARN] Failed to save debug screenshot {name}: {e}")

    def _get_context(self, browser):
        """Create a browser context, loading session if available"""
        if os.path.exists(self.session_path):
            size = os.path.getsize(self.session_path)
            print(f"[INFO] Loading authenticated session... (Size: {size} bytes)")
            if size < 100:
                print("[WARN] Session file looks too small, might be invalid.")
            return browser.new_context(storage_state=self.session_path)
        else:
            print("[INFO] Starting new session (No previous session found)...")
            return browser.new_context()

    def _paste_file(self, page, file_path):
        """
        Simulates pasting OR dropping a file into the chat.
        Robust fallback that tries both Paste and Drag-and-Drop events.
        """
        print("[INFO] Simulating direct file injection (Paste/Drop)...")
        
        with open(file_path, "rb") as f:
            encoded_file = base64.b64encode(f.read()).decode('utf-8')
            
        filename = os.path.basename(file_path)
        mime = "image/png"
        
        js_script = """(args) => {
            const [data, filename, mime] = args;
            
            // 1. Convert base64 to File Object
            const byteCharacters = atob(data);
            const byteArrays = [];
            for (let offset = 0; offset < byteCharacters.length; offset += 512) {
                const slice = byteCharacters.slice(offset, offset + 512);
                const byteNumbers = new Array(slice.length);
                for (let i = 0; i < slice.length; i++) {
                    byteNumbers[i] = slice.charCodeAt(i);
                }
                const byteArray = new Uint8Array(byteNumbers);
                byteArrays.push(byteArray);
            }
            const blob = new Blob(byteArrays, {type: mime});
            const file = new File([blob], filename, { type: mime });
            
            // 2. Prepare DataTransfer
            const dt = new DataTransfer();
            dt.items.add(file);
            
            // 3. Find Target (Chat Input)
            const getTarget = () => {
                const selectors = [
                    'div[aria-placeholder="Type a message"]',
                    'div[data-tab="10"]', 
                    'footer div[contenteditable="true"]',
                    'div[role="textbox"][contenteditable="true"]'
                ];
                
                for (let s of selectors) {
                    const el = document.querySelector(s);
                    if (el) return el;
                }
                return document.querySelector('div[contenteditable="true"]') || document.body;
            };
            
            const target = getTarget();
            target.focus();
            
            // 4. Dispatch 'paste' event
            const pasteEvent = new ClipboardEvent('paste', {
                bubbles: true,
                cancelable: true,
                composed: true,
                clipboardData: dt
            });
            target.dispatchEvent(pasteEvent);
            
            // 5. Dispatch 'drop' event (Backup)
            const dropEvent = new DragEvent('drop', {
                bubbles: true,
                cancelable: true,
                composed: true,
                dataTransfer: dt
            });
            target.dispatchEvent(dropEvent);
        }"""
        
        page.evaluate(js_script, [encoded_file, filename, mime])
        print("[INFO] Injected file via JS (Paste + Drop events).")
                
    def send_image(self, recipient_number, image_path, caption="", browser=None):
        print(f"[INFO] WhatsApp Web: Sending to {recipient_number}...")
        
        # Internal logic helper to run with a specific browser instance
        def _send_logic(browser_instance):
            context = self._get_context(browser_instance)
            if not context: return False
            
            try:
                # Reuse existing page if available (efficiency) or create new one
                if context.pages:
                     page = context.pages[0]
                else:
                    page = context.new_page()
                    page.set_default_timeout(90000)
                    
                # --- PHASE 1: Navigate to Specific Chat ---
                target_url = f"https://web.whatsapp.com/send?phone={recipient_number}"
                print(f"[INFO] Navigating directly to chat: {target_url}")
                page.goto(target_url)
                time.sleep(5) # User requested 5s load time
                self._save_debug_screenshot(page, "1_navigated_direct")
                
                # --- Authentication & Page Load ---
                try:
                        print("[INFO] Waiting for page load...")
                        # Detect both logged-in state and login/logout screens
                        page.wait_for_selector(
                            'div[aria-placeholder="Type a message"], canvas, div[data-animate-modal-popup="true"], [data-icon="plus"], #initial_startup', 
                            timeout=90000
                        )
                        time.sleep(5) 
                        
                        # Check for logout redirect
                        if "post_logout=1" in page.url or page.locator('canvas').is_visible():
                             print("[WARN] Session expired or logged out. Re-authentication required.")
                             if os.path.exists(self.session_path):
                                 os.remove(self.session_path)
                                 print(f"[INFO] Cleared stale session: {self.session_path}")
                except Exception as e:
                        print(f"[ERROR] Timeout waiting for WhatsApp Web: {e}")
                        self._save_debug_screenshot(page, "error_timeout")
                        return False

                # Handle QR Code if visible
                if page.locator('canvas').is_visible() or "web.whatsapp.com" not in page.url or "post_logout=1" in page.url:
                    if "post_logout=1" in page.url:
                         print("[INFO] Re-navigating to main page for QR...")
                         page.goto("https://web.whatsapp.com/")
                         time.sleep(5)
                         
                    print("[WARN] Not logged in. Starting Live QR Dashboard...")
                    self._save_debug_screenshot(page, "2_needs_login")
                    
                    self._start_qr_server()
                    print(f"[ACTION REQUIRED] Open http://localhost:3000 to scan the QR code.")
                    
                    max_retries = 30
                    for i in range(max_retries):
                        if page.locator('div[role="textbox"]').count() > 0 or page.locator('div[aria-placeholder="Type a message"]').count() > 0:
                            print("[INFO] Login detected!")
                            time.sleep(5) # Wait for UI to settle after login
                            context.storage_state(path=self.session_path)
                            self._save_debug_screenshot(page, "3_login_success")
                            break
                        
                        if page.locator('canvas').is_visible():
                            try:
                                page.locator('div[data-ref]').first.screenshot(path=self.qr_path)
                            except:
                                page.screenshot(path=self.qr_path, full_page=True)
                        
                        time.sleep(2)
                        print(f"[INFO] Waiting for scan... ({i+1}/{max_retries})")
                        
                    else:
                            print("[ERROR] Login timed out.")
                            self._save_debug_screenshot(page, "error_login_timeout")
                            return False

                # --- PHASE 2: UI-Driven File Upload ---
                print("[INFO] Chat loaded. Triggering 'Attach' menu...")
                
                # 1. Verify Chat Input is ready
                chat_input = page.locator('div[aria-placeholder="Type a message"]')
                if chat_input.count() == 0:
                    print("[INFO] Chat input not found, re-navigating to target chat...")
                    page.goto(target_url)
                    time.sleep(5)
                    chat_input = page.locator('div[aria-placeholder="Type a message"]')

                try:
                    chat_input.wait_for(state="visible", timeout=30000)
                    time.sleep(5) 
                    self._save_debug_screenshot(page, "4_chat_ready")
                except:
                    if page.locator('div[data-animate-modal-popup="true"]').count() > 0:
                        print(f"[ERROR] Invalid Phone Number (Delayed): {recipient_number}")
                        return False
                    print("[ERROR] Chat input not found.")
                    self._save_debug_screenshot(page, "error_chat_input_not_found")
                    return False
                
                # 2. Click Attach (+) Button
                try:
                    print("[INFO] Clicking Attach button (+)...")
                    # Try to find the button and click it, forcing if necessary
                    attach_button = page.locator('span[data-icon="plus"], [aria-label="Attach"]').first
                    attach_button.click(force=True)
                    time.sleep(3)
                    self._save_debug_screenshot(page, "5_attach_menu_open")
                except Exception as e:
                    print(f"[ERROR] Failed to click Attach button: {e}")
                    self._save_debug_screenshot(page, "error_attach_click")
                    return False

                # 3. Click 'Photos & Videos' and Upload
                try:
                    print("[INFO] Selecting 'Photos & videos' option...")
                    # The menu might take a moment to animate
                    # We try multiple ways to find the 'Photos & videos' button
                    media_option_selectors = [
                        'li:has-text("Photos & videos")',
                        'div[aria-label="Photos & videos"]',
                        'span:has-text("Photos & videos")',
                        '[data-icon="attach-image"]'
                    ]
                    
                    target_option = None
                    for sel in media_option_selectors:
                        loc = page.locator(sel).first
                        if loc.count() > 0:
                            target_option = loc
                            break
                    
                    if not target_option:
                        print("[ERROR] Could not find 'Photos & videos' menu item.")
                        self._save_debug_screenshot(page, "error_menu_item_not_found")
                        return False

                    print(f"[INFO] Clicking option and handling file chooser...")
                    with page.expect_file_chooser() as fc_info:
                        # Use force=True because WA menus often have hidden overlays
                        target_option.click(force=True)
                    
                    file_chooser = fc_info.value
                    file_chooser.set_files(image_path)
                    
                    print("[INFO] Image uploaded via File Chooser.")
                    time.sleep(10) # Heavy wait for media generation
                    self._save_debug_screenshot(page, "6_file_set_via_chooser")
                except Exception as e:
                    print(f"[ERROR] UI-driven upload failed: {e}")
                    # Final fallback: look for the input that just appeared
                    print("[INFO] Attempting direct input fallback...")
                    try:
                        file_input = page.locator('input[type="file"][accept*="video/mp4"], input[type="file"][accept*="image/"]').first
                        file_input.set_input_files(image_path)
                        time.sleep(10)
                    except: pass
                    self._save_debug_screenshot(page, "error_ui_upload")

                # --- PHASE 3: Handle Preview Modal (Caption & Send) ---
                print("[INFO] Waiting for image preview modal...")
                try:
                    # Look for the media preview footer or the send button
                    send_selectors = [
                        'span[data-icon="send"]',
                        '[data-icon="send"]',
                        '[aria-label="Send"]'
                    ]
                    
                    send_button = None
                    print("[INFO] Searching for send button...")
                    # WA preview modal often has a 1-2s entry animation
                    time.sleep(5)
                    
                    for selector in send_selectors:
                        try:
                            # In the preview modal, the send button is usually the last one
                            btn = page.locator(selector).last
                            if btn.is_visible(timeout=10000):
                                send_button = btn
                                print(f"[INFO] Found send button: {selector}")
                                break
                        except: continue
                    
                    if not send_button:
                         print("[ERROR] Could not find send button in preview modal.")
                         self._save_debug_screenshot(page, "error_no_send_button")
                         return False

                    self._save_debug_screenshot(page, "7_preview_modal")
                    
                    if caption:
                        print(f"[INFO] Typing caption: {caption}")
                        # In the media editor, we want the caption box specifically.
                        # Using force click to bypass interception.
                        caption_box = page.locator('div[aria-placeholder="Add a caption"]').last
                        
                        if caption_box.count() == 0:
                             print("[WARN] aria-placeholder not found, searching for contenteditable in viewer footer...")
                             caption_box = page.locator('footer div[contenteditable="true"], .media-viewer-footer div[contenteditable="true"]').last
                        
                        if caption_box.count() == 0:
                             caption_box = page.locator('div[contenteditable="true"]').last
                        
                        # Use force=True to handle the "intercepted pointer events" error
                        caption_box.click(force=True)
                        time.sleep(2)
                        
                        # Use keyboard to type character by character
                        # First clear any placeholder
                        page.keyboard.press("Control+A")
                        page.keyboard.press("Backspace")
                        
                        # Type character by character to handle newlines correctly
                        # In WA Media Editor, plain \n sometimes sends or behaves weirdly.
                        # Shift+Enter is the standard for newline in captions.
                        for char in caption:
                            if char == '\n':
                                page.keyboard.press("Shift+Enter")
                            else:
                                page.keyboard.type(char)
                            time.sleep(0.02) # Subtle character delay
                            
                        time.sleep(3)
                        self._save_debug_screenshot(page, "8_caption_filled")

                    print("[INFO] Sending message...")
                    send_button.click(force=True)
                    
                    # Wait for message to actually send (modal closes)
                    time.sleep(10) 
                    
                    print("[OK] Message send process completed.")
                    self._save_debug_screenshot(page, "9_final")
                    context.storage_state(path=self.session_path)
                    return True
                except Exception as e:
                    print(f"[ERROR] Preview/Send failed: {e}")
                    self._save_debug_screenshot(page, "error_preview")
                    return False
            except Exception as e:
                print(f"[ERROR] WhatsApp Web automation error: {e}")
                return False

        # Support both Provided Browser and Creating New One
        if browser:
            return _send_logic(browser)
        else:
            try:
                with Camoufox(headless=True) as new_browser:
                    return _send_logic(new_browser)
            except Exception as e:
                print(f"[ERROR] Browser launch failed: {e}")
                return False

    def send_to_multiple(self, image_path, recipient_numbers, caption="", delay_seconds=5, browser=None):
        """Web version of bulk sender"""
        successful_sends = 0
        failed_sends = 0
        
        # Internal loop helper
        def _loop(browser_instance):
            nonlocal successful_sends, failed_sends
            for idx, recipient in enumerate(recipient_numbers, 1):
                print(f"\n[{idx}/{len(recipient_numbers)}] Sending to {recipient}...")
                
                if self.send_image(recipient, image_path, caption, browser=browser_instance):
                    successful_sends += 1
                else:
                    failed_sends += 1
                
                if idx < len(recipient_numbers):
                    wait_time = delay_seconds + 5 # Extra buffer
                    print(f"[INFO] Waiting {wait_time}s...")
                    time.sleep(wait_time)
        
        if browser:
             _loop(browser)
        else:
             try:
                 with Camoufox(headless=True) as new_browser:
                    _loop(new_browser)
             except Exception as e:
                 print(f"[ERROR] Bulk sender browser failed: {e}")
        
        return successful_sends, failed_sends



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
    
    # Unified step: Extract date AND take screenshot (if possible)
    cause_list_date, screenshot_path = screenshot_manager.process_webpage()
    
    # If no date found, skip
    if not cause_list_date:
        print("[ERROR] Could not determine cause list date")
        return False
    
    # Check if cause list date is greater than today
    if cause_list_date.date() <= today.date():
        print(f"[SKIP] Cause list date ({cause_list_date.strftime('%d-%m-%Y')}) is not greater than today ({today.strftime('%d-%m-%Y')})")
        # Optimization: Delete the screenshot taken if we don't need it
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                os.remove(screenshot_path)
            except:
                pass
        return False
    
    print("=" * 50)
    print("Court Cause List Screenshot to WhatsApp")
    print(f"Today: {today.strftime('%A, %d-%m-%Y')}")
    print(f"Cause List Date: {cause_list_date.strftime('%A, %d-%m-%Y')}")
    print("=" * 50)
    
    # ----------------------------------------------------
    # BACKEND SELECTION
    # ----------------------------------------------------
    # "OFFICIAL" -> WhatsApp Business Cloud API (Meta)
    # "WEB"      -> Native WhatsApp Web Automation (Camoufox)
    WHATSAPP_BACKEND = os.getenv("WHATSAPP_BACKEND", "OFFICIAL").upper()
    print(f"[INFO] Using WhatsApp Backend: {WHATSAPP_BACKEND}")
    
    caption = f"Patna High Court Cause List\n{cause_list_date.strftime('%d-%m-%Y')}"
    
    # In unified flow, screenshot_path is already returned
    if not screenshot_path or not os.path.exists(screenshot_path):
        print("[ERROR] Screenshot file missing despite successful date extraction")
        return False
        
    print(f"[INFO] Cached file: {screenshot_path}")
    print("\n" + "=" * 50)
    print(f"[INFO] Sending to {len(recipient_numbers)} recipient(s)...")
    print("=" * 50)
    
    successful_sends = 0
    failed_sends = 0

    if WHATSAPP_BACKEND == "WEB":
        # --- Native WhatsApp Web ---
        web_client = WhatsAppWebClient()
        successful_sends, failed_sends = web_client.send_to_multiple(
            screenshot_path, 
            recipient_numbers, 
            caption=caption
        )
        
    else:
        # --- Official Cloud API (Default) ---
        # Initialize WhatsApp manager
        whatsapp_manager = WhatsAppManager(
            phone_number_id=PHONE_NUMBER_ID,
            access_token=ACCESS_TOKEN
        )
        
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