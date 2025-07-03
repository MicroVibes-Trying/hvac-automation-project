# 🧠 HVAC Automation System

An open-source, production-ready automation system built for discovering, enriching, and engaging HVAC businesses via email outreach. This project is designed to automate lead generation, personalize email delivery, and monitor performance — all with secure APIs and real-time dashboards.

## 🚀 Features

- **Lead Scraper**: Uses Google Places API to find HVAC companies by location
- **Email Enrichment**: Integrates with Hunter.io to discover and validate contact emails
- **Mailgun Integration**: Sends emails using a verified Mailgun domain (`mg.stxautomate.com`)
- **Task Autoloader**: JSON-driven task execution via cron every 10 minutes
- **Discord Alerts**: Instant error and event notifications sent to Discord via webhook
- **Web Dashboard**: Real-time metrics at `http://localhost:8080`
- **SQLite Logging**: Tracks lead lifecycle and email performance
- **Secure Credential Management**: No secrets stored in code

## 📁 Repo Structure
```
automation/github/hvac-automation-public/
├── app/                    # Core modules (scrapers, enrichers, senders)
├── scripts/                # Manual tools (e.g., generate task, send test email)
├── monitoring/             # Discord alerts + dashboard
├── automation_runner.py    # Main orchestrator
├── .env.example           # Template for configuration
├── README.md              # You are here
├── SECURITY_AUDIT_REPORT.md
├── credentials_template.txt
```

## 🔐 Configuration

Copy `.env.example` to `.env` and provide:
- `MAILGUN_API_KEY`
- `MAILGUN_DOMAIN`
- `DISCORD_WEBHOOK`
- `GOOGLE_PLACES_API_KEY`
- `HUNTER_API_KEY`

## 💬 Community

This project was built as part of a hands-on automation initiative using AI-led development, server orchestration, and real-world lead outreach. Contributions and forks are welcome.

## 📜 License

MIT
