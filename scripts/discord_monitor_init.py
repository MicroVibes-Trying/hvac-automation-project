#!/usr/bin/env python3
import os
import requests
import traceback
from datetime import datetime

CREDENTIALS_FILE = "/home/hvacuser/projects/hvac_workspace/hvac_automation/credentials.txt"
DISCORD_WEBHOOK = ""

def load_webhook_url():
    """Load Discord webhook URL from credentials file"""
    global DISCORD_WEBHOOK
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(f"Missing credentials file: {CREDENTIALS_FILE}")

    with open(CREDENTIALS_FILE, "r") as f:
        for line in f:
            if line.startswith("DISCORD_WEBHOOK="):
                DISCORD_WEBHOOK = line.strip().split("=", 1)[1]
                break

    if not DISCORD_WEBHOOK:
        raise ValueError("DISCORD_WEBHOOK not found in credentials.txt")

    return DISCORD_WEBHOOK

def send_discord_alert(title, error_message, details=""):
    """Send alert to Discord webhook with error handling"""
    try:
        # Ensure webhook URL is loaded
        if not DISCORD_WEBHOOK:
            load_webhook_url()

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Truncate details to prevent message being too long
        truncated_details = details[:1500] if details else "No additional details"
        if len(details) > 1500:
            truncated_details += "\n... (truncated)"

        message = f"""🚨 **{title}**

**Time**: {timestamp}
**Server**: HVAC Automation Server
**Error**: {error_message}

**Details**:
```
{truncated_details}
```"""

        payload = {"content": message}

        # Send with timeout to prevent hanging
        response = requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)

        if response.status_code == 204:
            print("✅ Discord alert sent successfully")
            return True
        else:
            print(f"⚠️ Discord alert failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"❌ Failed to send Discord alert: {str(e)}")
        # Don't raise exception - we don't want Discord failures to break automation
        return False

# Initialize webhook URL when module is imported
try:
    print("🔄 Initializing Discord webhook...")
    load_webhook_url()
    print("✅ Discord webhook initialized")
except Exception as e:
    print(f"⚠️ Discord webhook initialization failed: {e}")
    # Continue without Discord - don't break the automation

def simulate_failure():
    # Simulated try/except block that fails
    try:
        raise RuntimeError("Simulated automation failure in test block")
    except Exception as e:
        err_trace = traceback.format_exc()
        send_discord_alert("Automation Failure (Test Trigger)", str(e), err_trace)

def main():
    try:
        load_webhook_url()
        simulate_failure()
    except Exception as e:
        print(f"💥 Failed to run Discord notifier: {str(e)}")

if __name__ == "__main__":
    main()
