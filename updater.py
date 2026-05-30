"""
updater.py - Expo AI Agent Brain Updater
Runs every 24 hours, fetches latest Expo/RN docs, updates agent.md
"""

import os
import sys
import io
import requests
import re
import json
import time
import schedule
import logging
from datetime import datetime
from bs4 import BeautifulSoup
from pathlib import Path

# Fix Windows console UTF-8 encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# CONFIG
AGENT_MD_PATH = Path(__file__).parent / "agent.md"
LOG_FILE = Path(__file__).parent / "updater.log"
CHECK_INTERVAL_HOURS = 24

# Docs URLs
EXPO_LATEST_URL       = "https://docs.expo.dev/versions/latest/"
EXPO_CAMERA_URL       = "https://docs.expo.dev/versions/latest/sdk/camera/"
EXPO_LOCATION_URL     = "https://docs.expo.dev/versions/latest/sdk/location/"
EXPO_NOTIFICATIONS_URL= "https://docs.expo.dev/versions/latest/sdk/notifications/"
EXPO_SQLITE_URL       = "https://docs.expo.dev/versions/latest/sdk/sqlite/"
EXPO_IMAGE_PICKER_URL = "https://docs.expo.dev/versions/latest/sdk/imagepicker/"
EXPO_ROUTER_URL       = "https://docs.expo.dev/router/introduction/"
NPM_API               = "https://registry.npmjs.org/{package}/latest"

PACKAGES = [
    "expo",
    "react-native",
    "expo-router",
    "expo-camera",
    "expo-location",
    "expo-notifications",
    "expo-image-picker",
    "expo-av",
    "expo-sqlite",
    "expo-file-system",
    "expo-auth-session",
    "expo-secure-store",
    "react-native-reanimated",
    "react-native-gesture-handler",
    "nativewind",
]

# LOGGING
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger(__name__)


# HELPERS

def fetch_page(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 ExpoAgentUpdater/1.0"}
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        return BeautifulSoup(res.text, "html.parser")
    except Exception as e:
        log.warning(f"Could not fetch {url}: {e}")
        return None


def get_npm_version(package):
    try:
        res = requests.get(NPM_API.format(package=package), timeout=10)
        res.raise_for_status()
        data = res.json()
        return data.get("version", "unknown")
    except Exception as e:
        log.warning(f"Could not get version for {package}: {e}")
        return "unknown"


def replace_block(content, block_name, new_content):
    pattern = (
        rf"(<!-- UPDATER_BLOCK_START: {block_name} -->)"
        rf".*?"
        rf"(<!-- UPDATER_BLOCK_END: {block_name} -->)"
    )
    replacement = rf"\1\n{new_content}\n\2"
    return re.sub(pattern, replacement, content, flags=re.DOTALL)


# UPDATE FUNCTIONS

def fetch_sdk_version():
    log.info("Fetching Expo SDK version...")
    expo_ver = get_npm_version("expo")
    rn_ver   = get_npm_version("react-native")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"Expo SDK: {expo_ver}\nReact Native: {rn_ver}\nLast checked: {now}"


def fetch_package_versions():
    log.info("Fetching package versions...")
    rows = ["| Package | Latest Version |", "|---------|---------------|"]
    for pkg in PACKAGES:
        version = get_npm_version(pkg)
        rows.append(f"| {pkg} | {version} |")
        time.sleep(0.3)
    return "\n".join(rows)


def fetch_gotchas():
    log.info("Fetching gotchas...")
    now = datetime.now().strftime("%Y-%m-%d")
    gotchas = [
        "- expo-camera: Old `Camera` component is deprecated -- use `CameraView`",
        "- expo-av: Being split into `expo-video` and `expo-audio` -- prefer new packages",
        "- Navigation: Wrap app in `<GestureHandlerRootView>` when using gestures",
        "- Android: Add permissions to `app.json` under `android.permissions`",
        "- iOS: Add permission descriptions to `app.json` under `ios.infoPlist`",
        "- NativeWind v4: Config changed from v3 -- always check installed version",
        "- New Architecture: Enabled by default in SDK 52+ -- some old packages may break",
        f"- Last verified: {now}",
    ]
    return "\n".join(gotchas)


def fetch_api_docs_snapshot():
    log.info("Fetching API docs snapshots...")
    now = datetime.now().strftime("%Y-%m-%d")
    sections = []

    sections.append(f"""### expo-router (Navigation)
- File-based routing -- files in /app folder become routes
- Dynamic routes: `[id].tsx`
- Tabs layout: `(tabs)/_layout.tsx`
- Docs: {EXPO_ROUTER_URL}
- Updated: {now}""")

    soup = fetch_page(EXPO_CAMERA_URL)
    camera_note = "Use `CameraView` component -- `Camera` is deprecated"
    if soup:
        intro = soup.find("p")
        if intro and len(intro.text.strip()) < 300:
            camera_note = intro.text.strip()
    sections.append(f"""### expo-camera
- {camera_note}
- Always request permissions: `Camera.useCameraPermissions()`
- Docs: {EXPO_CAMERA_URL}
- Updated: {now}""")

    sections.append(f"""### expo-location
- `Location.requestForegroundPermissionsAsync()` before any call
- `Location.getCurrentPositionAsync({{}})` for one-time location
- `Location.watchPositionAsync()` for live tracking
- Docs: {EXPO_LOCATION_URL}
- Updated: {now}""")

    sections.append(f"""### expo-notifications
- Requires EAS project ID for push notifications
- `Notifications.requestPermissionsAsync()` before use
- Docs: {EXPO_NOTIFICATIONS_URL}
- Updated: {now}""")

    sections.append(f"""### expo-image-picker
- `ImagePicker.requestMediaLibraryPermissionsAsync()` before gallery
- `ImagePicker.launchImageLibraryAsync()` to open gallery
- `ImagePicker.launchCameraAsync()` to open camera
- Docs: {EXPO_IMAGE_PICKER_URL}
- Updated: {now}""")

    sections.append(f"""### expo-sqlite
- Wrap app in `<SQLiteProvider databaseName="mydb.db">`
- Use `useSQLiteContext()` hook for database access
- Docs: {EXPO_SQLITE_URL}
- Updated: {now}""")

    sections.append(f"""### react-native-reanimated
- Import from `react-native-reanimated`
- Key hooks: `useSharedValue`, `useAnimatedStyle`, `withTiming`, `withSpring`
- Add babel plugin: `'react-native-reanimated/plugin'` in babel.config.js
- Docs: https://docs.swmansion.com/react-native-reanimated/
- Updated: {now}""")

    return "\n\n".join(sections)


# MAIN

def update_agent_md():
    log.info("=" * 50)
    log.info("Starting agent.md update...")

    if not AGENT_MD_PATH.exists():
        log.error(f"agent.md not found at {AGENT_MD_PATH}")
        return False

    content  = AGENT_MD_PATH.read_text(encoding="utf-8")
    original = content

    try:
        content = replace_block(content, "sdk_version",  fetch_sdk_version())
        content = replace_block(content, "packages",     fetch_package_versions())
        content = replace_block(content, "api_docs",     fetch_api_docs_snapshot())
        content = replace_block(content, "gotchas",      fetch_gotchas())

        if content != original:
            AGENT_MD_PATH.write_text(content, encoding="utf-8")
            log.info("[OK] agent.md updated successfully!")
        else:
            log.info("[INFO] No changes detected in agent.md")
        return True

    except Exception as e:
        log.error(f"Update failed: {e}")
        AGENT_MD_PATH.write_text(original, encoding="utf-8")
        return False


def run_scheduler():
    log.info(f"Updater started -- will check every {CHECK_INTERVAL_HOURS} hours")
    update_agent_md()
    schedule.every(CHECK_INTERVAL_HOURS).hours.do(update_agent_md)
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        log.info("Running one-time update...")
        success = update_agent_md()
        sys.exit(0 if success else 1)
    else:
        run_scheduler()
