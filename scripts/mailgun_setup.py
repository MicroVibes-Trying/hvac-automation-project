#!/usr/bin/env python3
import os
import requests

MAILGUN_API_KEY = ""
MAILGUN_DOMAIN = ""

CREDENTIALS_FILE = "/home/hvacuser/projects/hvac_workspace/hvac_automation/credentials.txt"
LOG_FILE = "/home/hvacuser/projects/hvac_workspace/hvac_automation/system_audit/logs/task_execution.log"

def load_credentials():
    global MAILGUN_API_KEY, MAILGUN_DOMAIN
    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError("Missing credentials.txt")
    with open(CREDENTIALS_FILE, "r") as f:
        for line in f:
            if line.startswith("MAILGUN_API_KEY="):
                MAILGUN_API_KEY = line.strip().split("=", 1)[1]
            elif line.startswith("MAILGUN_DOMAIN="):
                MAILGUN_DOMAIN = line.strip().split("=", 1)[1]
    if not MAILGUN_API_KEY or not MAILGUN_DOMAIN:
        raise ValueError("Missing required Mailgun credentials")

def log(msg):
    timestamp = f"[{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"
    with open(LOG_FILE, "a") as logf:
        logf.write(f"{timestamp} [T001-Mailgun] {msg}\n")
    print(f"{timestamp} [T001-Mailgun] {msg}")

def verify_domain():
    url = f"https://api.mailgun.net/v3/domains/{MAILGUN_DOMAIN}"
    response = requests.get(url, auth=("api", MAILGUN_API_KEY))
    if response.status_code == 200:
        log("✅ Domain verified with Mailgun.")
    else:
        log(f"❌ Domain verification failed: {response.status_code} - {response.text}")
        raise Exception("Mailgun domain verification failed")

def main():
    log("🚀 Starting Mailgun setup")
    try:
        load_credentials()
        verify_domain()
        log("🎉 Mailgun setup completed successfully.")
    except Exception as e:
        log(f"💥 Mailgun setup failed: {str(e)}")
        raise

if __name__ == "__main__":
    main()
