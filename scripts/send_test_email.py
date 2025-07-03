#!/usr/bin/env python3
import os
import requests

CREDENTIALS_FILE = "/home/hvacuser/projects/hvac_workspace/hvac_automation/credentials.txt"
LOG_FILE = "/home/hvacuser/projects/hvac_workspace/hvac_automation/system_audit/logs/task_execution.log"

MAILGUN_API_KEY = ""
MAILGUN_DOMAIN = ""

def load_credentials():
    global MAILGUN_API_KEY, MAILGUN_DOMAIN
    with open(CREDENTIALS_FILE, "r") as f:
        for line in f:
            if line.startswith("MAILGUN_API_KEY="):
                MAILGUN_API_KEY = line.strip().split("=", 1)[1]
            elif line.startswith("MAILGUN_DOMAIN="):
                MAILGUN_DOMAIN = line.strip().split("=", 1)[1]
    if not MAILGUN_API_KEY or not MAILGUN_DOMAIN:
        raise Exception("Missing Mailgun credentials.")

def log(msg):
    timestamp = f"[{__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"
    with open(LOG_FILE, "a") as f:
        f.write(f"{timestamp} [Mailgun-Test] {msg}\n")
    print(f"{timestamp} [Mailgun-Test] {msg}")

def send_test_email():
    to_email = input("Enter recipient email: ").strip()
    subject = "🚀 STXAutomate Mailgun Test"
    content = """<html>
    <body>
        <h2>Hello from STXAutomate!</h2>
        <p>This is a test email sent via Mailgun from your automation server.</p>
        <p>✅ Integration is working.</p>
    </body>
</html>"""

    response = requests.post(
        f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages",
        auth=("api", MAILGUN_API_KEY),
        data={
            "from": f"STXAutomate <noreply@{MAILGUN_DOMAIN}>",
            "to": to_email,
            "subject": subject,
            "html": content,
            "o:tracking": "yes",
            "o:tracking-clicks": "yes",
            "o:tracking-opens": "yes"
        }
    )

    if response.status_code == 200:
        log(f"✅ Test email sent to {to_email}")
    else:
        log(f"❌ Failed to send test email: {response.status_code} - {response.text}")
        print(response.text)

def main():
    try:
        load_credentials()
        send_test_email()
    except Exception as e:
        log(f"💥 Error: {str(e)}")

if __name__ == "__main__":
    main()
