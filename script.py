import requests
import os
import json
import time

API_URL = "https://api.microlink.io/"
TARGET_URL = "https://patnahighcourt.gov.in/causelist/auin/view/4079/0/CLIST"

CACHE_DIR = "cache"
CACHE_META = os.path.join(CACHE_DIR, "meta.json")
SCREENSHOT_FILE = os.path.join(CACHE_DIR, "screenshot.png")

TTL_SECONDS = 1 * 60 * 60  # 1 hour

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


if cache_is_valid():
    print("✅ Loaded screenshot from cache")
else:
    print("🌐 Cache expired or missing — fetching")

    response = requests.get(API_URL, params={
        "url": TARGET_URL,
        "screenshot.fullPage": "true",
        "screenshot.type": "png"
    })

    data = response.json()
    screenshot_url = data["data"]["screenshot"]["url"]

    image = requests.get(screenshot_url).content
    save_cache(data, image)

    print("📸 Screenshot fetched & cached")

print("📁 Cached file:", SCREENSHOT_FILE)
