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
   uv run playwright install --with-deps firefox
   ```

3. **Configure environment variables**
   
   Create a `.env` file in the project root:
   ```env
   PHONE_NUMBER_ID=your_whatsapp_phone_number_id
   ACCESS_TOKEN=your_whatsapp_access_token
   RECIPIENT_NUMBER=917XXXXXXXXX
   ```

   For multiple recipients, separate with commas:
   ```env
   RECIPIENT_NUMBER=917XXXXXXXXX,917YYYYYYYYY,917ZZZZZZZZZ
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

## Docker Deployment

### Build and Run

```bash
# Build the image (Downloads Camoufox browser (~700MB) once into the image)
docker compose build

# Run in background
docker compose up -d

# View logs
docker compose logs -f

# Stop
docker compose down
```

### Docker Features

| Feature | Value |
|---------|-------|
| Base Image | `python:3.12-slim-bookworm` (Debian) |
| Browser | Camoufox (Stealth Firefox) |
| Memory Limit | 1024MB (Required for browser) |
| CPU Limit | 1.0 cores |
| Auto-restart | Yes (unless-stopped) |
| Log Rotation | 10MB x 3 files |

---

## Project Structure

```
PHC_Cause_List_Whatsapp_Notifier/
├── main.py              # Main application logic
├── Dockerfile           # Production container definition
├── docker-compose.yml   # Orchestration for services
├── pyproject.toml       # Python dependencies (uv)
├── uv.lock              # Deterministic lock file
├── .env                 # Secrets (Ignored by git)
├── .gitignore           # File exclusion rules
├── README.md            # This documentation
├── LICENSE              # Project license
└── cache/               # Local data (Ignored by git)
    ├── screenshot.png   # Temporary image buffer
    └── sent_today.txt   # Duplicate prevention marker
```

---

## Configuration

### Time Window

The scheduler is active between **8:00 PM** and **11:30 PM**. To modify, edit the `is_within_time_window()` function in `main.py`:

```python
def is_within_time_window(start_hour=20, start_minute=0, end_hour=23, end_minute=30):
```

### Check Interval

Default is **10 minutes**. To modify, edit in `run_scheduler()`:

```python
CHECK_INTERVAL_SECONDS = 10 * 60  # 10 minutes
```

### Target URL

Default URL monitors cause list for advocate code 4079. To change, modify in `send_cause_list()`:

```python
TARGET_URL = "https://patnahighcourt.gov.in/causelist/auin/view/4079/0/CLIST"
```

### Screenshot Quality

You can adjust the resolution and quality of the screenshot by setting the `SCREENSHOT_QUALITY` environment variable in your `.env` or `docker-compose.yml`.

| Value | Resolution | Scale Factor | Description |
|-------|------------|--------------|-------------|
| `HIGH` (Default) | 1920x1080 | 2x | **Best Quality**. Retina-sharp text. Larger file size (~800KB). |
| `MEDIUM` | 1280x720 | 1x | Good balance. Standard HD. (~400KB) |
| `LOW` | 800x600 | 1x | Lowest file size (~250KB). Good for slow connections. |

Example in `.env`:
```env
SCREENSHOT_QUALITY=HIGH
```

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
