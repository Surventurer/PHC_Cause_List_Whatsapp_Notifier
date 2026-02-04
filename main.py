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
            
            # Wait for content to settle
            try:
                page.wait_for_selector('#ctl00_MainContent_lblHeader', timeout=30000)
            except:
                print("[WARN] lblHeader not found quickly, proceeding anyway...")
            
            time.sleep(5) 
            html_content = page.content()
            extracted_date = self._extract_date_from_page_content(html_content)
            
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
                <meta http-equiv="refresh" content="2">
                <style>
                    body { font-family: sans-serif; text-align: center; padding: 20px; background: #f0f2f5; margin: 0; }
                    .card { background: white; padding: 20px; border-radius: 12px; box-shadow: 0 8px 16px rgba(0,0,0,0.1); display: inline-block; max-width: 400px; margin-top: 50px; }
                    h1 { color: #128C7E; font-size: 24px; margin-bottom: 10px; }
                    .status { display: inline-block; padding: 5px 15px; background: #e7f3ff; color: #007bff; border-radius: 20px; font-weight: bold; margin-bottom: 20px; }
                    .qr-container { border: 2px solid #25d366; padding: 10px; border-radius: 10px; background: white; }
                    img { display: block; width: 100%; height: auto; border-radius: 5px; }
                    .steps { text-align: left; margin-top: 20px; color: #555; font-size: 14px; }
                    .steps ol { padding-left: 20px; }
                </style>
            </head>
            <body>
                <div class="card">
                    <h1>WhatsApp Login</h1>
                    <div class="status">Waiting for Scan...</div>
                    <div class="qr-container">
                        <img src="/whatsapp_qr.png?t=""" + str(int(time.time())) + """" alt="QR Code Loading..." />
                    </div>
                    <div class="steps">
                        <strong>Steps:</strong>
                        <ol>
                            <li>Open <b>WhatsApp</b> on your phone</li>
                            <li>Tap <b>Menu</b> or <b>Settings</b></li>
                            <li>Select <b>Linked Devices</b></li>
                            <li>Tap <b>Link a Device</b> and scan this code</li>
                        </ol>
                    </div>
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

    def _get_persistent_context(self, playwright):
        """
        Create a persistent browser context using WAHA's optimal configuration.
        Source: waha/src/core/engines/webjs/session.webjs.core.ts
        """
        # Ensure profile directory exists in the cache
        self.profile_dir = os.path.join(self.cache_dir, "whatsapp_profile")
        os.makedirs(self.profile_dir, exist_ok=True)
        
        print(f"[INFO] Using persistent profile: {self.profile_dir}")
        
        # WAHA Browser Arguments (Optimized for WhatsApp Web)
        waha_args = [
            '--disable-accelerated-2d-canvas',
            '--disable-application-cache',
            '--disable-client-side-phishing-detection',
            '--disable-component-update',
            '--disable-default-apps',
            '--disable-dev-shm-usage',
            '--disable-extensions',
            '--disable-metrics',
            '--disable-offer-store-unmasked-wallet-cards',
            '--disable-offline-load-stale-cache',
            '--disable-popup-blocking',
            '--disable-setuid-sandbox',
            '--disable-site-isolation-trials',
            '--disable-speech-api',
            '--disable-sync',
            '--disable-translate',
            '--disable-web-security',
            '--hide-scrollbars',
            '--ignore-certificate-errors',
            '--ignore-ssl-errors',
            '--metrics-recording-only',
            '--mute-audio',
            '--no-default-browser-check',
            '--no-first-run',
            '--no-pings',
            '--no-sandbox',
            '--no-zygote',
            '--password-store=basic',
            '--renderer-process-limit=2',
            '--safebrowsing-disable-auto-update',
            '--use-mock-keychain',
            '--window-size=1280,720',
            '--disable-blink-features=AutomationControlled',
            '--disk-cache-size=1073741824', 
        ]
        
        waha_user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
        
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=self.profile_dir,
            headless=False,
            args=waha_args,
            ignore_default_args=['--enable-automation'],
            viewport={'width': 1280, 'height': 720},
            user_agent=waha_user_agent,
            locale='en-US',
            timezone_id='Asia/Kolkata',
            permissions=['clipboard-read', 'clipboard-write'],  # Enable Clipboard for Copy/Paste
        )
        
        # Extended Stealth for WA Web
        stealth_js = """
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins', { 
            get: () => [{ description: "PDF", filename: "internal-pdf-viewer", name: "Chrome PDF Plugin" }] 
        });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
        window.chrome = { runtime: {} };
        """
        context.add_init_script(stealth_js)
        return context

    def start(self):
        """Start the session (Reference to WAHA: session.start())"""
        from playwright.sync_api import sync_playwright
        print("[INFO] Starting persistent session...")
        self._playwright = sync_playwright().start()
        self._context = self._get_persistent_context(self._playwright)
        return self._context

    def stop(self):
        """Stop the session (Reference to WAHA: session.stop())"""
        print("[INFO] Stopping session...")
        if hasattr(self, '_context'):
            self._context.close()
        if hasattr(self, '_playwright'):
            self._playwright.stop()
        print("[INFO] Session stopped.")

    def _get_context(self, browser):
        """Create a browser context, loading session if available [LEGACY]"""
        if os.path.exists(self.session_path):
            return browser.new_context(storage_state=self.session_path)
        return browser.new_context()

    def _ensure_loggedin(self, page):
        """
        Helper to ensure the session is authenticated.
        Navigates to root web.whatsapp.com and handles QR code if needed.
        Solved the 'unable to scan' problem by ensuring a clean entry point.
        """
        print("[INFO] Verifying authentication status...")
        if "web.whatsapp.com" not in page.url:
            page.goto("https://web.whatsapp.com/")
            
        try:
            # Wait for either QR code (canvas) or Main Chat List (pane-side)
            page.wait_for_selector('canvas, [data-icon="chat"], [data-icon="menu"], div[role="textbox"]', timeout=60000)
            time.sleep(2)
        except:
             # Just a warm-up check, sometimes it's slow
             pass
        
        # 1. Check if we are already logged in (Priority)
        # If the main UI is visible, we are logged in, even if a canvas is present (e.g. background/startup)
        # Added div[role="textbox"] back as it often appears as the search bar
        if page.locator('[data-icon="chat"], [data-icon="menu"], [data-icon="intro-md-beta-logo-dark"], [data-icon="intro-md-beta-logo-light"], div[role="textbox"]').count() > 0:
            print("[INFO] Already logged in.")
            return True

        # Check for loading screen
        if page.locator('progress').is_visible() or page.locator('[data-testid="progress-bar"]').is_visible():
            print("[INFO] WhatsApp is loading... waiting.")
            try:
                page.wait_for_selector('[data-icon="chat"], [data-icon="menu"]', timeout=30000)
                print("[INFO] Loading complete. Logged in.")
                return True
            except:
                print("[WARN] Timed out waiting for load.")

        # 2. Check for QR Code (Secondary)
        if page.locator('canvas').is_visible():
            print("[WARN] QR Code detected. Session not authenticated.")
            # Verify if we really have chat list (sometimes canvas exists in background?)
            # But usually canvas means scan needed.
        
            print("[WARN] Not logged in. Starting Live QR Dashboard...")
            self._save_debug_screenshot(page, "auth_qr_needed")
            self._start_qr_server()
            print(f"[ACTION REQUIRED] Open http://localhost:3000 to scan the QR code.")
            
            max_retries = 60 # 2 minutes to scan
            for i in range(max_retries):
                # Strict check for success
                if page.locator('[data-icon="chat"], [data-icon="menu"], div[role="textbox"]').count() > 0:
                    print("[INFO] Login detected!")
                    time.sleep(5)
                    self._save_debug_screenshot(page, "login_success")
                    return True
                
                # Snapshot for dashboard
                if page.locator('canvas').is_visible():
                    # Handle "Reload QR" button if it appears
                    reload_selectors = ['button:has-text("Click to reload QR")', '[data-icon="refresh-large"]', 'span[role="button"]:has-text("Reload")']
                    for sel in reload_selectors:
                        try:
                            btn = page.locator(sel).first
                            if btn.is_visible(timeout=1000):
                                print("[INFO] QR expired. Clicking reload button...")
                                btn.click()
                                time.sleep(2)
                                break
                        except: pass

                    try:
                        # Strategy 1: The official container
                        qr_container = page.locator('div[data-ref]').first
                        if qr_container.is_visible():
                            qr_container.screenshot(path=self.qr_path)
                        else:
                            # Strategy 2: The canvas itself
                            page.locator('canvas').first.screenshot(path=self.qr_path)
                    except:
                        # Fallback: Just the center of the page
                        page.screenshot(path=self.qr_path)
                
                time.sleep(2)
                if i % 10 == 0:
                    print(f"[INFO] Waiting for scan... ({i}/{max_retries})")
            
            print("[ERROR] Login timed out.")
            return False

        # Fallback: If we are here, we see neither a login screen nor a QR code
        print("[ERROR] Unknown state. Neither logged in nor QR code found.")
        self._save_debug_screenshot(page, "auth_failed_unknown_state")
        return False

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
                
    def _core_send_image(self, context, recipient_number, image_path, caption):
        """
        Core logic: Sends image using an ACTIVE Playwright context.
        """
        if not context: return False
        
        try:
            if context.pages:
                 page = context.pages[0]
            else:
                page = context.new_page()
            
            page.set_default_timeout(90000)
            
            # 1. Ensure we are logged in FIRST
            if not self._ensure_loggedin(page):
                print("[ERROR] Authentication failed. Cannot proceed.")
                return False
                
            # 2. Navigate to Specific Chat
            target_url = f"https://web.whatsapp.com/send?phone={recipient_number}"
            print(f"[INFO] Navigating directly to chat: {target_url}")
            page.goto(target_url)
            
            # 3. Wait for Chat Load (Handling Landing Pages)
            try:
                print("[INFO] Waiting for chat UI...")
                # Check for "Continue to Chat" landing page
                try:
                    landing_btn = page.locator('a[title="Share on WhatsApp"], button:has-text("Continue to Chat"), span:has-text("Continue to Chat")').first
                    if landing_btn.is_visible(timeout=5000):
                        print("[INFO] detected 'Continue to Chat' landing page. Clicking...")
                        landing_btn.click()
                        time.sleep(2)
                        
                        web_link = page.locator('a:has-text("use WhatsApp Web"), span:has-text("use WhatsApp Web")').first
                        if web_link.is_visible(timeout=5000):
                             print("[INFO] Clicking 'use WhatsApp Web'...")
                             web_link.click()
                except: pass

                # Wait for the chat input box specifically
                page.wait_for_selector('div[aria-placeholder="Type a message"]', timeout=60000)
                time.sleep(3) 
            except Exception as e:
                print(f"[ERROR] Chat failed to load: {e}")
                self._save_debug_screenshot(page, "chat_load_fail")
                return False

            # --- PHASE 2: UI-Driven File Upload ---
            print("[INFO] Chat loaded. Triggering 'Attach' menu...")
            
            try:
                # Click Attach (+)
                attach_button = page.locator('span[data-icon="plus"], [aria-label="Attach"]').first
                attach_button.click(force=True)
                time.sleep(2)
                
                # Photos & Videos menu item
                media_option = page.locator('li:has-text("Photos & videos"), [data-icon="attach-image"]').first
                
                if media_option.count() == 0:
                    print("[ERROR] Could not find 'Photos & videos' menu item.")
                    self._save_debug_screenshot(page, "error_menu_missing")
                    return False

                with page.expect_file_chooser() as fc_info:
                    media_option.click(force=True)
                
                file_chooser = fc_info.value
                file_chooser.set_files(image_path)
                time.sleep(5)
            except Exception as e:
                print(f"[ERROR] UI-driven upload failed: {e}")
                self._save_debug_screenshot(page, "error_upload")
                return False

            # --- PHASE 2.5: Pre-count Inputs (Snapshot) ---
            # SKIPPED: User requested simpler explicit delays instead of complex state diffing.
            
            # --- PHASE 3: Handle Preview Modal ---
            print("[INFO] Waiting for image preview modal...")
            try:
                # 1. Primary Wait: Use the user-confirmed text "Type a message" 
                # BUT we must ensure we don't just find the background one. 
                # We wait for the COUNT of "Type a message" inputs to increase or for a NEW one.
                
                # Wait for the modal container or just the presence of a NEW input
                # User Flow: Wait for fully loading
                time.sleep(5) # explicit heavy wait for modal load (User Request)
                
                caption_box = None
                
                # Find the caption box.
                # User provided exact selector: div[aria-placeholder="Type a message"][data-lexical-editor="true"]
                # There are TWO such elements: main chat + modal caption. Modal is the LAST one.
                print("[INFO] Finding caption box (aria-placeholder='Type a message')...")
                
                # Target the specific Lexical editor input
                caption_inputs = page.locator('div[aria-placeholder="Type a message"][data-lexical-editor="true"]')
                input_count = caption_inputs.count()
                print(f"[DEBUG] Found {input_count} matching caption inputs.")
                
                # Debug: Log bounding boxes of all found inputs
                for i in range(input_count):
                    inp = caption_inputs.nth(i)
                    try:
                        box = inp.bounding_box()
                        is_vis = inp.is_visible()
                        print(f"[DEBUG] Input {i}: visible={is_vis}, bbox={box}")
                    except Exception as e:
                        print(f"[DEBUG] Input {i}: error getting info: {e}")
                
                # Select the visible input with the SMALLEST y-coordinate (modal caption is higher up)
                # The modal caption appears ABOVE the main chat input in the preview
                best_candidate = None
                best_y = float('inf')
                
                for i in range(input_count):
                    inp = caption_inputs.nth(i)
                    if inp.is_visible():
                        box = inp.bounding_box()
                        # Modal caption should be on the RIGHT side (x > 300) AND have smaller y
                        if box and box.get('x', 0) > 300:
                            y = box.get('y', float('inf'))
                            if y < best_y:
                                best_y = y
                                best_candidate = inp
                                print(f"[DEBUG] Better candidate at index {i}: y={y}")
                
                if best_candidate:
                    caption_box = best_candidate
                    print(f"[INFO] Selected caption box with smallest y={best_y}")
                elif input_count > 0:
                    # Fallback: just take the first one
                    caption_box = caption_inputs.first
                    print("[WARN] Using fallback: first input")
                
                if caption_box:
                    print(f"[INFO] Caption box selected: {caption_box}")
                    # Highlight with VERY visible styling
                    try:
                        caption_box.evaluate("""el => {
                            el.style.outline = '5px solid red';
                            el.style.outlineOffset = '-2px';
                            el.style.backgroundColor = 'rgba(255, 0, 0, 0.1)';
                        }""")
                        self._save_debug_screenshot(page, "debug_caption_box_selected")
                        print("[DEBUG] Highlighted caption box with red outline")
                    except Exception as e:
                        print(f"[WARN] Could not highlight: {e}")
                else:
                    print("[ERROR] No caption box found.")
                    self._save_debug_screenshot(page, "error_no_caption_box")
                
                # Proceed to Typing/Sending...

                
                if caption and caption_box:
                    print(f"[INFO] Typing caption...")
                    
                    # Focus the caption box
                    caption_box.click(force=True)
                    time.sleep(1)
                    caption_box.focus()
                    
                    # TYPE: Use Playwright's type() for direct text input
                    # Split by newlines and handle them as Shift+Enter
                    lines = caption.split('\n')
                    for i, line in enumerate(lines):
                        if line:
                            caption_box.type(line, delay=10)  # 10ms delay between chars
                        if i < len(lines) - 1:  # Add newline except after last line
                            page.keyboard.press("Shift+Enter")
                    
                    time.sleep(1)
                    
                    print("[INFO] Caption typed.")

                time.sleep(2) # USER REQUEST: 1 sec explicit delay before send (made it 2s)
                
                print("[INFO] Sending message...")
                send_button_candidates = page.locator('span[data-icon="send"], [data-icon="send"], [aria-label="Send"]')
                send_button = None
                
                if send_button_candidates.count() > 0:
                     send_button = send_button_candidates.last # Modal button is usually last
                
                if send_button and send_button.is_visible():
                     send_button.click(force=True)
                else:
                     print("[WARN] Send button not found. Trying global search.")
                     page.locator('[data-icon="send"]').last.click(force=True)
                     
                time.sleep(5) # Wait for send animation
                
                # --- STEP 5: Verify Message Appears in DOM ---
                print("[INFO] Verifying message in DOM...")
                try:
                    # Wait for the image preview modal to close (it should disappear)
                    # The send button in modal should no longer be visible
                    time.sleep(3)
                    
                    # Check if our message appears in the chat
                    # Messages are typically in divs with class containing 'message-out'
                    # We'll look for the caption text in the chat area
                    if caption:
                        caption_snippet = caption[:20].strip()  # First 20 chars
                        message_check = page.locator(f'div.message-out:has-text("{caption_snippet}")')
                        if message_check.count() > 0:
                            print("[OK] Message verified in DOM!")
                        else:
                            print("[WARN] Could not verify message in DOM (may still have been sent).")
                    
                    self._save_debug_screenshot(page, "after_send_verification")
                except Exception as ve:
                    print(f"[WARN] DOM verification failed: {ve}")
                
                print("[OK] Message send process completed.")
                return True

            except Exception as e:
                print(f"[ERROR] Caption/Send failed: {e}")
                self._save_debug_screenshot(page, "error_send_flow")
                return False
        except Exception as e:
            print(f"[ERROR] Automation error: {e}")
            return False

    def send_image(self, recipient_number, image_path, caption="", browser=None):
        """Send a single image via WhatsApp Web"""
        print(f"[INFO] Sending single image to {recipient_number}...")
        
        if browser:
            # Legacy/Manual mode: use provided browser instance
            context = self._get_context(browser)
            return self._core_send_image(context, recipient_number, image_path, caption)
        else:
            # Persistent mode: use our internal WAHA context
            try:
                context = self.start()
                result = self._core_send_image(context, recipient_number, image_path, caption)
                time.sleep(2)
                self.stop()
                return result
            except Exception as e:
                print(f"[ERROR] Single send failed: {e}")
                self.stop()
                return False

    def send_to_multiple(self, image_path, recipient_numbers, caption="", delay_seconds=5, browser=None):
        """Batch sender with persistent session support"""
        successful_sends = 0
        failed_sends = 0
        
        def _loop(context_instance):
            nonlocal successful_sends, failed_sends
            for idx, recipient in enumerate(recipient_numbers, 1):
                print(f"\n[{idx}/{len(recipient_numbers)}] Sending to {recipient}...")
                
                # Add debug number to caption
                debug_caption = f"{caption}\n[Debug #{idx}]"
                
                if self._core_send_image(context_instance, recipient, image_path, debug_caption):
                    successful_sends += 1
                else:
                    failed_sends += 1
                
                if idx < len(recipient_numbers):
                    wait_time = delay_seconds + 5
                    print(f"[INFO] Waiting {wait_time}s...")
                    time.sleep(wait_time)
        
        if browser:
            # Legacy mode
            _loop(self._get_context(browser))
        else:
             # WAHA Persistent Mode (Effecient)
             print("[INFO] Batch Mode: Using persistent WAHA session...")
             try:
                 context = self.start()
                 _loop(context)
                 time.sleep(2)
                 self.stop()
             except Exception as e:
                 print(f"[ERROR] Batch send failed: {e}")
                 self.stop()
        
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