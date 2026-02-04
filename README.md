# Patna High Court Cause List WhatsApp Notifier

An automated system that monitors the Patna High Court website for new cause lists and sends screenshots via WhatsApp Business Cloud API.

## Features

- **Automatic Date Detection** - Extracts cause list date directly from the court website
- **Anti-Bot Screenshot Capture** - Uses **Camoufox (Stealth Firefox)** to bypass bot protections (Cloudflare, etc.) and capture full-page screenshots
- **WhatsApp Integration** - Sends screenshots via WhatsApp Business Cloud API
- **Scheduled Execution** - Runs between 8:00 PM - 11:30 PM, checking every 10 minutes
- **Duplicate Prevention** - Tracks sent messages to avoid sending multiple times per day
- **Multiple Recipients** - Supports sending to multiple WhatsApp numbers

---

## Flow Diagram

```
                      +---------------------------------------+
                      |          SCHEDULER LOOP               |
                      |  (Runs continuously every 10 minutes) |
                      +---------------------------------------+
                                        |
                                        v
                      +---------------------------------------+
                      | Is current time between               |
                      | 8:00 PM and 11:30 PM?                 |
                      +---------------------------------------+
                              |                    |
                             NO                   YES
                              |                    |
                              v                    v
                      +---------------+   +------------------------+
                      | Sleep 10 mins |   | Was message already    |
                      | & retry       |   | sent today?            |
                      +---------------+   +------------------------+
                                                |            |
                                               YES          NO
                                                |            |
                                                v            v
                                      +----------+   +---------------------+
                                      | Skip -   |   | Fetch webpage from  |
                                      | already  |   | Patna High Court    |
                                      | sent     |   +---------------------+
                                      +----------+            |
                                                              v
                                                +---------------------------+
                                                | Extract cause list date   |
                                                | from lblHeader element    |
                                                +---------------------------+
                                                              |
                                                              v
                                                +---------------------------+
                                                | Is cause list date        |
                                                | greater than today?       |
                                                +---------------------------+
                                                        |           |
                                                       NO          YES
                                                        |           |
                                                        v           v
                                            +-----------+   +---------------------+
                                            | Cause list|   | Capture full-page   |
                                            | not ready |   | screenshot using    |
                                            | Sleep 10  |   | Camoufox (Stealth)  |
                                            | mins &    |   +---------------------+
                                            | retry     |            |
                                            +-----------+            v
                                                          +---------------------+
                                                          | Upload image to     |
                                                          | WhatsApp Cloud API  |
                                                          +---------------------+
                                                                     |
                                                                     v
                                                          +---------------------+
                                                          | Send to all         |
                                                          | recipients with     |
                                                          | caption             |
                                                          +---------------------+
                                                                     |
                                                                     v
                                                          +---------------------+
                                                          | Mark message as     |
                                                          | sent today          |
                                                          | (sent_today.txt)    |
                                                          +---------------------+
                                                                     |
                                                                     v
                                                          +---------------------+
                                                          | Delete temporary    |
                                                          | screenshot          |
                                                          | Success! Wait for   |
                                                          | next day            |
                                                          +---------------------+
```

---

## Installation

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- WhatsApp Business Cloud API access
- Docker (for production deployment)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Surventurer/PHC_Cause_List_Whatsapp_Notifier.git
   cd PHC_Cause_List_Whatsapp_Notifier
   ```

2. **Install dependencies**
   ```bash
   uv sync
   # Install browsers for Automation (Chromium) and Anti-Bot (Firefox) 
   uv run playwright install --with-deps chromium firefox
   ```

3. **Configure environment variables**
   
   Create a `.env` file in the project root:
   ```env
   # Backend Selection: "WEB" (Free/Headless) or "OFFICIAL" (Paid Cloud API)
   WHATSAPP_BACKEND=WEB
   
   # For WEB backend (Headless Automation)
   RECIPIENT_NUMBER=917XXXXXXXXX,917YYYYYYYYY
   SCREENSHOT_QUALITY=MEDIUM
   
   # For OFFICIAL backend (Meta Cloud API)
   # NOTE: These are IGNORED if WHATSAPP_BACKEND=WEB
   PHONE_NUMBER_ID=your_id
   ACCESS_TOKEN=your_token
   ```

---

## Usage

### Run Scheduler (Recommended)

Runs continuously, checking every 10 minutes between 8:00 PM - 11:30 PM:

```bash
uv run main.py
```

### Run Once (Testing/Manual)

Execute a single check immediately:

```bash
uv run main.py --once
```

---

## Web Automation (Headless Mode)

The system defaults to `WHATSAPP_BACKEND=WEB`, which uses robust headless browser automation to send messages via your existing phone number (Linked Device).

### First-Time Login (QR Code)
When running for the first time (or if the session expires), you need to link your device:

1.  Run the bot (`uv run main.py` or via Docker).
2.  The bot will detect it needs authentication.
3.  **Local Run**: A window might open, or check the terminal.
4.  **Headless/Docker Run**:
    - The bot starts a **Live QR Dashboard**.
    - Open **`http://localhost:3000`** in your browser.
    - Scan the QR code using WhatsApp on your phone (Menu > Linked Devices).
5.  **Session Saved**: Once scanned, the session is encrypted and saved to `cache/whatsapp_profile`. You won't need to scan again.

---

## Docker Deployment

### Build and Run

```bash
# Build the image (Downloads browsers ~700MB)
docker compose build

# Run in background (Ports 3000 mapped for QR)
docker compose up -d

# View logs to check for QR code prompt
docker compose logs -f
```

### Container Specs

| Feature | Value |
|---------|-------|
| Base Image | `python:3.12-slim-bookworm` |
| Browsers | Chromium (Automation), Camoufox (Stealth) |
| Memory Limit | 1024MB |
| Auto-Cleanup | Yes (Corrupted sessions auto-deleted) |

---


---

## How It Works

### 1. Unified Scraping & Screenshotting

To maximize efficiency and bypass anti-bot protections, the system uses a **unified Camoufox session**:
1.  **Launch**: A stealth Firefox instance (Camoufox) is launched.
2.  **Navigate**: It navigates to the Patna High Court cause list page.
3.  **Extract**: It parses the HTML content to find the cause list date (e.g., `ctl00_MainContent_lblHeader`).
4.  **Capture**: If the date is valid (a future date), it immediately takes a full-page screenshot using the configured quality settings.
5.  **Close**: The browser session is closed, ensuring minimal resource usage.

This unified approach ensures we only hit the court's servers once per check, reducing the chance of being flagged as a bot.

### 2. WhatsApp Integration

Uses WhatsApp Business Cloud API v21.0:
1.  **Upload**: The captured screenshot is uploaded to WhatsApp servers to get a `media_id`.
2.  **Send**: A message is sent to all configured recipients with the screenshot and a dynamic caption.

### 3. Duplicate Prevention

To avoid spamming, the system tracks successes in `cache/sent_today.txt`. Once a list is successfully sent for a specific date, it won't check again until the next day.

---

## Dependencies

| Package | Purpose |
|---------|---------|
| `camoufox` | Stealth browser automation (Anti-Bot) |
| `playwright` | Browser control engine |
| `requests` | HTTP calls to WhatsApp Business API |
| `beautifulsoup4` | HTML parsing for date extraction |
| `python-dotenv` | Configuration management |

---

## License

MIT License

---

## Author

Created for automated court cause list monitoring.
