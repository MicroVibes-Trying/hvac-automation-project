#!/usr/bin/env python3
"""
HVAC Email Automation - Enhanced Web Dashboard
Real-time monitoring dashboard with comprehensive system metrics and automation stats
"""
import os
import sys
import json
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify
import psutil

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

app = Flask(__name__)
DB_PATH = os.getenv('DATABASE_PATH', 'hvac_automation.db')

# If running from monitoring directory, adjust path to find database in parent directory
if not os.path.exists(DB_PATH):
    parent_db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'hvac_automation.db')
    if os.path.exists(parent_db_path):
        DB_PATH = parent_db_path

def get_dashboard_data():
    """Get comprehensive dashboard data with enhanced server analytics"""
    try:
        # System stats with enhanced metrics
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        network = psutil.net_io_counters()

        system_stats = {
            'cpu_percent': round(psutil.cpu_percent(interval=1), 1),
            'cpu_cores': psutil.cpu_count(),
            'memory_percent': round(memory.percent, 1),
            'memory_used_gb': round(memory.used / (1024**3), 2),
            'memory_total_gb': round(memory.total / (1024**3), 2),
            'disk_percent': round(disk.percent, 1),
            'disk_used_gb': round(disk.used / (1024**3), 2),
            'disk_total_gb': round(disk.total / (1024**3), 2),
            'network_sent_mb': round(network.bytes_sent / (1024**2), 2),
            'network_recv_mb': round(network.bytes_recv / (1024**2), 2),
            'uptime_hours': round((datetime.now().timestamp() - psutil.boot_time()) / 3600, 1),
            'load_avg': os.getloadavg() if hasattr(os, 'getloadavg') else [0, 0, 0]
        }

        # Database connection and automation stats
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check if database tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        if 'leads' not in tables:
            conn.close()
            return {'error': 'Database not initialized - leads table missing'}

        # Get comprehensive automation stats
        cursor.execute("SELECT COUNT(*) FROM leads")
        total_leads = cursor.fetchone()[0]

        # Check if email_enrichment table exists and get leads with emails
        if 'email_enrichment' in tables:
            cursor.execute("""
                SELECT COUNT(*) FROM leads l
                JOIN email_enrichment e ON l.id = e.lead_id
                WHERE e.email_address IS NOT NULL AND e.email_address != ''
            """)
            leads_with_emails = cursor.fetchone()[0]
        else:
            leads_with_emails = 0

        # Today's activity
        today = datetime.now().date()
        if 'email_sends' in tables:
            cursor.execute("SELECT COUNT(*) FROM email_sends WHERE DATE(sent_date) = ?", (today,))
            emails_sent_today = cursor.fetchone()[0]

            # This week's activity
            week_ago = today - timedelta(days=7)
            cursor.execute("SELECT COUNT(*) FROM email_sends WHERE DATE(sent_date) >= ?", (week_ago,))
            emails_sent_week = cursor.fetchone()[0]

            # Success rate calculation
            cursor.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) as successful
                FROM email_sends
                WHERE DATE(sent_date) >= ?
            """, (week_ago,))

            result = cursor.fetchone()
            success_rate = round((result[1] / result[0] * 100), 1) if result[0] > 0 else 0

            # Email trend data (last 7 days)
            cursor.execute("""
                SELECT
                    DATE(sent_date) as date,
                    COUNT(*) as total,
                    COUNT(CASE WHEN status = 'sent' THEN 1 END) as successful
                FROM email_sends
                WHERE sent_date >= datetime('now', '-7 days')
                GROUP BY DATE(sent_date)
                ORDER BY date
            """)
            email_trend = cursor.fetchall()
        else:
            emails_sent_today = 0
            emails_sent_week = 0
            success_rate = 0
            email_trend = []

        # Hunter credits used today
        if 'hunter_credits' in tables:
            cursor.execute("SELECT COALESCE(SUM(credits_used), 0) FROM hunter_credits WHERE date = ?", (today,))
            credits_used_today = cursor.fetchone()[0]
        else:
            credits_used_today = 0

        # Recent system logs
        if 'system_logs' in tables:
            cursor.execute("""
                SELECT level, module, message, timestamp
                FROM system_logs
                ORDER BY timestamp DESC
                LIMIT 10
            """)
            recent_logs = cursor.fetchall()
        else:
            recent_logs = []

        conn.close()

        automation_stats = {
            'total_leads': total_leads,
            'leads_with_emails': leads_with_emails,
            'emails_sent_today': emails_sent_today,
            'emails_sent_week': emails_sent_week,
            'credits_used_today': credits_used_today,
            'success_rate': success_rate,
            'leads_pending_enrichment': max(0, total_leads - leads_with_emails)
        }

        return {
            'system_stats': system_stats,
            'automation_stats': automation_stats,
            'email_trend': email_trend,
            'recent_logs': recent_logs,
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'database_tables': tables
        }

    except Exception as e:
        return {'error': f'Dashboard error: {str(e)}'}

@app.route('/')
def dashboard():
    """Enhanced dashboard page with comprehensive server and automation analytics"""
    return '''
<!DOCTYPE html>
<html>
<head>
    <title>HVAC Automation Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { background: rgba(255,255,255,0.95); color: #2c3e50; padding: 25px; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); }
        .section-title { color: #2c3e50; font-size: 1.4em; margin: 25px 0 15px 0; font-weight: 600; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 20px; margin-bottom: 25px; }
        .automation-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 25px; }
        .stat-card { background: rgba(255,255,255,0.95); padding: 25px; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); transition: transform 0.3s ease; }
        .stat-card:hover { transform: translateY(-5px); }
        .stat-value { font-size: 2.2em; font-weight: bold; color: #3498db; margin: 10px 0; }
        .stat-subtitle { font-size: 0.9em; color: #7f8c8d; margin-top: 5px; }
        .logs-box { background: rgba(255,255,255,0.95); padding: 25px; border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.1); margin-bottom: 25px; }
        .status-good { color: #27ae60; }
        .status-warning { color: #f39c12; }
        .status-danger { color: #e74c3c; }
        .refresh-btn { background: linear-gradient(45deg, #3498db, #2980b9); color: white; border: none; padding: 12px 24px; border-radius: 8px; cursor: pointer; font-weight: 600; transition: all 0.3s ease; }
        .refresh-btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(52, 152, 219, 0.4); }
        .progress-bar { width: 100%; height: 8px; background: #ecf0f1; border-radius: 4px; overflow: hidden; margin: 10px 0; }
        .progress-fill { height: 100%; transition: width 0.3s ease; }
        .log-entry { padding: 8px 0; border-bottom: 1px solid #ecf0f1; font-size: 0.9em; }
        .log-level { font-weight: bold; margin-right: 10px; }
        .log-info { color: #3498db; }
        .log-warning { color: #f39c12; }
        .log-error { color: #e74c3c; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 HVAC Email Automation Dashboard</h1>
            <p>Real-time system monitoring and automation analytics</p>
            <button class="refresh-btn" onclick="refreshData()">🔄 Refresh Data</button>
        </div>

        <div class="section-title">🖥️ Server Analytics</div>
        <div class="stats-grid" id="server-stats">
            <!-- Server stats will be loaded here -->
        </div>

        <div class="section-title">📊 Automation Performance</div>
        <div class="automation-grid" id="automation-stats">
            <!-- Automation stats will be loaded here -->
        </div>

        <div class="logs-box">
            <h3>📋 Recent System Activity</h3>
            <div id="system-logs">Loading...</div>
        </div>
    </div>

    <script>
        function refreshData() {
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    updateDashboard(data);
                })
                .catch(error => {
                    console.error('Error:', error);
                    document.getElementById('server-stats').innerHTML = '<div class="stat-card">❌ Connection Error: ' + error.message + '</div>';
                });
        }

        function updateDashboard(data) {
            if (data.error) {
                document.getElementById('server-stats').innerHTML = '<div class="stat-card">❌ Error: ' + data.error + '</div>';
                return;
            }

            const sys = data.system_stats;
            const auto = data.automation_stats;

            const statusClass = (value, warning, danger) => {
                if (value > danger) return 'status-danger';
                if (value > warning) return 'status-warning';
                return 'status-good';
            };

            const progressColor = (value, warning, danger) => {
                if (value > danger) return '#e74c3c';
                if (value > warning) return '#f39c12';
                return '#27ae60';
            };

            // Server Stats
            document.getElementById('server-stats').innerHTML = `
                <div class="stat-card">
                    <h3>💻 CPU Performance</h3>
                    <div class="stat-value ${statusClass(sys.cpu_percent, 70, 90)}">${sys.cpu_percent}%</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${sys.cpu_percent}%; background: ${progressColor(sys.cpu_percent, 70, 90)};"></div>
                    </div>
                    <div class="stat-subtitle">${sys.cpu_cores} cores • Load: ${sys.load_avg[0].toFixed(2)}</div>
                </div>
                <div class="stat-card">
                    <h3>🧠 Memory Usage</h3>
                    <div class="stat-value ${statusClass(sys.memory_percent, 70, 90)}">${sys.memory_percent}%</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${sys.memory_percent}%; background: ${progressColor(sys.memory_percent, 70, 90)};"></div>
                    </div>
                    <div class="stat-subtitle">${sys.memory_used_gb}GB / ${sys.memory_total_gb}GB</div>
                </div>
                <div class="stat-card">
                    <h3>💾 Disk Storage</h3>
                    <div class="stat-value ${statusClass(sys.disk_percent, 80, 95)}">${sys.disk_percent}%</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${sys.disk_percent}%; background: ${progressColor(sys.disk_percent, 80, 95)};"></div>
                    </div>
                    <div class="stat-subtitle">${sys.disk_used_gb}GB / ${sys.disk_total_gb}GB</div>
                </div>
                <div class="stat-card">
                    <h3>🌐 Network Activity</h3>
                    <div class="stat-value status-good">${sys.network_sent_mb}MB</div>
                    <div class="stat-subtitle">↑ Sent: ${sys.network_sent_mb}MB • ↓ Received: ${sys.network_recv_mb}MB</div>
                </div>
                <div class="stat-card">
                    <h3>⏰ System Uptime</h3>
                    <div class="stat-value status-good">${sys.uptime_hours}h</div>
                    <div class="stat-subtitle">Server running smoothly</div>
                </div>
            `;

            // Automation Stats
            document.getElementById('automation-stats').innerHTML = `
                <div class="stat-card">
                    <h3>🎯 Total Leads</h3>
                    <div class="stat-value status-good">${auto.total_leads.toLocaleString()}</div>
                    <div class="stat-subtitle">Businesses discovered</div>
                </div>
                <div class="stat-card">
                    <h3>📧 Leads with Emails</h3>
                    <div class="stat-value status-good">${auto.leads_with_emails.toLocaleString()}</div>
                    <div class="stat-subtitle">${auto.leads_pending_enrichment} pending enrichment</div>
                </div>
                <div class="stat-card">
                    <h3>📬 Emails Today</h3>
                    <div class="stat-value status-good">${auto.emails_sent_today}</div>
                    <div class="stat-subtitle">${auto.emails_sent_week} this week</div>
                </div>
                <div class="stat-card">
                    <h3>🎯 Success Rate</h3>
                    <div class="stat-value ${statusClass(100-auto.success_rate, 30, 50)}">${auto.success_rate}%</div>
                    <div class="stat-subtitle">Email delivery success</div>
                </div>
                <div class="stat-card">
                    <h3>🔍 Hunter Credits</h3>
                    <div class="stat-value status-good">${auto.credits_used_today}</div>
                    <div class="stat-subtitle">Used today</div>
                </div>
            `;

            // System Logs
            if (data.recent_logs && data.recent_logs.length > 0) {
                const formatLogMessage = (log) => {
                    const [level, module, message, timestamp] = log;
                    let formattedMessage = message;

                    // Format enricher messages
                    if (module === 'enricher' && message.includes('Email enrichment completed:')) {
                        const match = message.match(/Email enrichment completed: (\\d+\\/\\d+) emails found/);
                        if (match) {
                            formattedMessage = `Emails found and enriched: ${match[1]}`;
                        }
                    }

                    // Format database backup messages
                    if (module === 'database' && message.includes('Database backup created:')) {
                        const time = new Date(timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                        const period = new Date(timestamp).toLocaleTimeString([], {hour12: true}).split(' ')[1];
                        formattedMessage = `Backup created at: ${time} ${period.toLowerCase()}`;
                    }

                    // Format sender messages
                    if (module === 'sender' && message.includes('Email sending completed:')) {
                        const match = message.match(/Email sending completed: (\\d+\\/\\d+) emails sent/);
                        if (match) {
                            formattedMessage = `Email sending completed: ${match[1]} emails sent`;
                        }
                    }

                    // Format automation messages
                    if (module === 'automation' && message.includes('Full automation cycle completed')) {
                        const match = message.match(/Full automation cycle completed in (.+)/);
                        if (match) {
                            formattedMessage = `Automation cycle completed in ${match[1]}`;
                        }
                    }

                    // Format scraper messages
                    if (module === 'scraper' && message.includes('Scraping completed:')) {
                        const match = message.match(/Scraping completed: (\\d+) leads saved/);
                        if (match) {
                            formattedMessage = `Lead scraping completed: ${match[1]} leads saved`;
                        }
                    }

                    return formattedMessage;
                };

                const logsHtml = data.recent_logs.map(log => `
                    <div class="log-entry">
                        <span class="log-level log-${log[0].toLowerCase()}">${log[0]}</span>
                        <span>${formatLogMessage(log)}</span>
                        <span style="float: right; color: #bdc3c7; font-size: 0.8em;">${new Date(log[3]).toLocaleTimeString()}</span>
                    </div>
                `).join('');
                document.getElementById('system-logs').innerHTML = logsHtml;
            } else {
                document.getElementById('system-logs').innerHTML = '<div class="log-entry">No recent activity</div>';
            }

            // Update timestamp
            document.querySelector('.header p').innerHTML = `Last updated: ${data.last_updated} • Auto-refresh every 30 seconds`;
        }

        // Initial load
        refreshData();

        // Auto-refresh every 30 seconds
        setInterval(refreshData, 30000);
    </script>
</body>
</html>
    '''

@app.route('/api/data')
def api_data():
    """API endpoint for dashboard data"""
    return jsonify(get_dashboard_data())

if __name__ == '__main__':
    port = int(os.getenv('DASHBOARD_PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
