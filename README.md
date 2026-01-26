# 📋 Patna High Court Cause List WhatsApp Notifier

An automated system that monitors the Patna High Court website for new cause lists and sends screenshots via WhatsApp Business Cloud API.

## ✨ Features

- 🔍 **Automatic Date Detection** - Extracts cause list date directly from the court website
- 📸 **Screenshot Capture** - Takes full-page screenshots using Microlink API
- 📱 **WhatsApp Integration** - Sends screenshots via WhatsApp Business Cloud API
- ⏰ **Scheduled Execution** - Runs between 9:30 PM - 11:30 PM, checking every 10 minutes
- 🚫 **Duplicate Prevention** - Tracks sent messages to avoid sending multiple times per day
- 👥 **Multiple Recipients** - Supports sending to multiple WhatsApp numbers

---

## 🔄 Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SCHEDULER LOOP                                     │
│                    (Runs continuously every 10 minutes)                      │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
                    ┌────────────────────────────────┐
                    │   Is current time between      │
                    │   9:30 PM and 11:30 PM?        │
                    └────────────────────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │ NO                              │ YES
                    ▼                                 ▼
        ┌───────────────────┐           ┌────────────────────────────┐
        │ 💤 Sleep 10 mins  │           │ Was message already sent   │
        │   & retry         │           │ today?                     │
        └───────────────────┘           └────────────────────────────┘
                                                     │
                                    ┌────────────────┴────────────────┐
                                    │ YES                             │ NO
                                    ▼                                 ▼
                        ┌───────────────────┐       ┌─────────────────────────────┐
                        │ ✅ Skip - already │       │ 🌐 Fetch webpage from       │
                        │   sent today      │       │ Patna High Court            │
                        └───────────────────┘       └─────────────────────────────┘
                                                                 │
                                                                 ▼
                                              ┌─────────────────────────────────────┐
                                              │ 🔍 Extract cause list date from     │
                                              │ <span id="ctl00_MainContent_       │
                                              │ lblHeader">                         │
                                              └─────────────────────────────────────┘
                                                                 │
                                                                 ▼
                                              ┌─────────────────────────────────────┐
                                              │ Is cause list date > today?         │
                                              └─────────────────────────────────────┘
                                                                 │
                                        ┌────────────────────────┴────────────────────────┐
                                        │ NO                                              │ YES
                                        ▼                                                 ▼
                        ┌───────────────────────────┐           ┌─────────────────────────────────┐
                        │ ⏳ Cause list not ready   │           │ 📸 Capture full-page screenshot │
                        │   Sleep 10 mins & retry   │           │ using Microlink API             │
                        └───────────────────────────┘           └─────────────────────────────────┘
                                                                             │
                                                                             ▼
                                                              ┌─────────────────────────────────┐
                                                              │ 📤 Upload image to WhatsApp     │
                                                              │ Cloud API                       │
                                                              └─────────────────────────────────┘
                                                                             │
                                                                             ▼
                                                              ┌─────────────────────────────────┐
                                                              │ 📱 Send to all recipients       │
                                                              │ with caption                    │
                                                              └─────────────────────────────────┘
                                                                             │
                                                                             ▼
                                                              ┌─────────────────────────────────┐
                                                              │ 📝 Mark message as sent today   │
                                                              │ (cache/sent_today.txt)          │
                                                              └─────────────────────────────────┘
                                                                             │
                                                                             ▼
                                                              ┌─────────────────────────────────┐
                                                              │ 🗑️ Delete temporary screenshot  │
                                                              │ 🎉 Success! Wait for next day   │
                                                              └─────────────────────────────────┘
```

---

## 🛠️ Installation

### Prerequisites

- Python 3.9+
- [uv](https://github.com/astral-sh/uv) package manager
- WhatsApp Business Cloud API access

### Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd screenshot_sending
   ```

2. **Install dependencies**
   ```bash
   uv sync
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

## 🚀 Usage

### Run Scheduler (Recommended)

Runs continuously, checking every 10 minutes between 9:30 PM - 11:30 PM:

```bash
uv run main.py
```

### Run Once (Testing/Manual)

Execute a single check immediately:

```bash
uv run main.py --once
```

---

## 🐳 Docker Deployment

### Build and Run

```bash
# Build the image
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
| Base Image | `python:3.12-alpine` (~50MB) |
| Memory Limit | 128MB |
| CPU Limit | 0.25 cores |
| Auto-restart | Yes (unless-stopped) |
| Log Rotation | 10MB × 3 files |

---

## 📁 Project Structure

```
screenshot_sending/
├── main.py              # Main application code
├── Dockerfile           # Docker image definition
├── docker-compose.yml   # Docker Compose configuration
├── .env                 # Environment variables (not in git)
├── .gitignore           # Git ignore rules
├── pyproject.toml       # Python project configuration
├── uv.lock              # Dependency lock file
├── README.md            # This file
└── cache/               # Temporary files
    ├── screenshot.png   # Cached screenshot (deleted after send)
    └── sent_today.txt   # Tracks if message was sent today
```

---

## ⚙️ Configuration

### Time Window

The scheduler is active between **9:30 PM** and **11:30 PM**. To modify, edit the `is_within_time_window()` function in `main.py`:

```python
def is_within_time_window(start_hour=21, start_minute=30, end_hour=23, end_minute=30):
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

---

## 🔧 How It Works

### 1. Date Extraction

The system fetches the court website and looks for the cause list date in:
```html
<span id="ctl00_MainContent_lblHeader">Cause List for DD-MM-YYYY</span>
```

### 2. Screenshot Capture

Uses [Microlink API](https://microlink.io/) to capture a full-page screenshot:
```
https://api.microlink.io/?url=<target_url>&screenshot.fullPage=true
```

### 3. WhatsApp Integration

Uses WhatsApp Business Cloud API v21.0:
1. Upload media to get `media_id`
2. Send image message with caption to recipients

### 4. Duplicate Prevention

After successful send, writes today's date to `cache/sent_today.txt`. On next check, skips if date matches.

---

## 📋 Dependencies

| Package | Purpose |
|---------|---------|
| `requests` | HTTP requests for API calls |
| `beautifulsoup4` | HTML parsing for date extraction |
| `python-dotenv` | Environment variable management |

---

## 🐛 Troubleshooting

### "Could not extract date from webpage"

- The webpage structure may have changed
- Check if `ctl00_MainContent_lblHeader` element exists
- Verify the URL is accessible

### "Cause list date is not greater than today"

- The cause list hasn't been updated yet
- Wait for the court to publish the next day's list

### WhatsApp errors

- Verify `ACCESS_TOKEN` is valid and not expired
- Check `PHONE_NUMBER_ID` is correct
- Ensure recipient numbers are in correct format (e.g., `917XXXXXXXXX`)

---

## 📜 License

MIT License

---

## 👤 Author

Created for automated court cause list monitoring.
