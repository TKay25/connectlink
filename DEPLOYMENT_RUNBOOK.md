# ConnectLink - Deployment & Operations Runbook

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Installation on Windows](#installation-windows)
3. [Installation on macOS/Linux](#installation-macos-linux)
4. [Installation on Production Server](#installation-production)
5. [Configuration & Setup](#configuration)
6. [Database Management](#database-management)
7. [Backup & Recovery](#backup-recovery)
8. [Monitoring & Maintenance](#monitoring)
9. [Troubleshooting](#troubleshooting)
10. [Upgrade Procedures](#upgrade)

---

## PRE-DEPLOYMENT CHECKLIST

### System Requirements
```
✓ Operating System: Windows 10+, macOS 10.14+, or Linux (Ubuntu 20.04+)
✓ Python: 3.8 or higher
✓ PostgreSQL: 12 or higher
✓ Server RAM: 2GB minimum (4GB recommended)
✓ Storage: 10GB minimum (20GB recommended)
✓ Internet: Required for API integrations
✓ Domain/IP: For public access
```

### Pre-Deployment Tasks
- [ ] Verify system meets requirements
- [ ] Check internet connectivity
- [ ] Install PostgreSQL
- [ ] Create PostgreSQL user account
- [ ] Create database `connectlinkdata`
- [ ] Obtain API keys:
  - Google Gemini API key
  - WhatsApp Business API token
  - (Optional) SendGrid email service key
- [ ] Reserve production domain/IP address
- [ ] Plan backup strategy
- [ ] Assign user roles and permissions
- [ ] Document configuration details

---

## INSTALLATION ON WINDOWS

### Step 1: Install Python 3.8+

**Download**:
1. Visit: https://www.python.org/downloads/
2. Download Python 3.11+ (latest stable)
3. Run installer
4. **IMPORTANT**: Check "Add Python to PATH"
5. Click "Install Now"

**Verify**:
```cmd
python --version
pip --version
```

### Step 2: Install Git

**Download**:
1. Visit: https://git-scm.com/download/win
2. Download Git for Windows
3. Run installer
4. Use default options

**Verify**:
```cmd
git --version
```

### Step 3: Install PostgreSQL

**Download**:
1. Visit: https://www.postgresql.org/download/windows/
2. Download PostgreSQL 12 or higher
3. Run installer
4. Set password for `postgres` user (save this!)
5. Use port 5432 (default)
6. Complete installation

**Verify**:
```cmd
psql --version
```

### Step 4: Create Database & User

**Open PostgreSQL Command Line**:
```cmd
psql -U postgres
```

**Create User**:
```sql
CREATE USER connectlink_user WITH PASSWORD 'your_secure_password';
ALTER ROLE connectlink_user WITH CREATEDB;
```

**Create Database**:
```sql
CREATE DATABASE connectlinkdata OWNER connectlink_user;
GRANT ALL PRIVILEGES ON DATABASE connectlinkdata TO connectlink_user;
```

**Verify**:
```sql
\l  -- List databases
\du -- List users
```

**Exit**:
```sql
\q
```

### Step 5: Clone ConnectLink Repository

**Choose Installation Directory**:
```cmd
cd Documents
```

**Clone Repository**:
```cmd
git clone https://github.com/yourusername/connectlink.git
cd connectlink
```

### Step 6: Create Virtual Environment

```cmd
python -m venv venv
venv\Scripts\activate
```

**Verify** (you should see `(venv)` in prompt):
```cmd
where python
```

### Step 7: Install Python Dependencies

```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

**Wait for completion** (2-5 minutes)

### Step 8: Create Environment Configuration

**Create `.env` file** (in connectlink folder):
```
# Database
DATABASE_URL=postgresql://connectlink_user:your_secure_password@localhost:5432/connectlinkdata

# Flask
FLASK_APP=ConnectLink.py
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your_super_secret_key_here_change_in_production

# API Keys
GEMINI_API_KEY=your_gemini_api_key_here
WHATSAPP_API_TOKEN=your_whatsapp_api_token_here
WHATSAPP_PHONE_ID=your_whatsapp_phone_id_here

# Email (Optional)
SENDGRID_API_KEY=your_sendgrid_api_key_here

# Application
APP_URL=http://localhost:5000
SESSION_TIMEOUT=3600
```

### Step 9: Initialize Database

**First Time Run**:
```cmd
python ConnectLink.py
```

**Wait for**:
- Database tables created
- System initialized
- Server starts on port 5000

**Expected Output**:
```
 * Running on http://127.0.0.1:5000
 * WARNING: This is a development server. Do not use it in production.
```

### Step 10: Access the Application

Open browser and go to:
```
http://localhost:5000
```

**Default Login** (create after first setup):
- Username: admin
- Password: (set during setup)

---

## INSTALLATION ON MACOS/LINUX

### Step 1: Install System Dependencies

**macOS**:
```bash
# Install Homebrew first if not installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.11
brew install postgresql
```

**Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv postgresql postgresql-contrib git
```

### Step 2: Verify Installations

```bash
python3.11 --version
psql --version
git --version
```

### Step 3: Start PostgreSQL Service

**macOS**:
```bash
brew services start postgresql
```

**Ubuntu/Debian**:
```bash
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### Step 4: Create Database User

```bash
# Connect to PostgreSQL
psql postgres

# In PostgreSQL:
CREATE USER connectlink_user WITH PASSWORD 'your_secure_password';
ALTER ROLE connectlink_user WITH CREATEDB;
CREATE DATABASE connectlinkdata OWNER connectlink_user;
GRANT ALL PRIVILEGES ON DATABASE connectlinkdata TO connectlink_user;
\q
```

### Step 5-10: Follow Windows Steps 5-10 Above

(Same process for cloning, virtual environment, dependencies, etc.)

---

## INSTALLATION ON PRODUCTION SERVER

### Pre-Production Considerations

- [ ] Use HTTPS (SSL certificate)
- [ ] Use strong SECRET_KEY
- [ ] Use environment-specific secrets
- [ ] Configure backup automation
- [ ] Set up monitoring
- [ ] Use production web server (Gunicorn)
- [ ] Configure reverse proxy (Nginx)
- [ ] Set up logging

### Production Setup

**1. Install Gunicorn**:
```bash
pip install gunicorn
```

**2. Create Gunicorn Configuration** (`gunicorn_config.py`):
```python
import multiprocessing

workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2
max_requests = 1000
max_requests_jitter = 50
bind = "127.0.0.1:8000"
accesslog = "/var/log/connectlink/access.log"
errorlog = "/var/log/connectlink/error.log"
loglevel = "info"
```

**3. Set Environment to Production**:
```bash
export FLASK_ENV=production
export FLASK_DEBUG=False
```

**4. Use Nginx as Reverse Proxy** (`/etc/nginx/sites-available/connectlink`):
```nginx
upstream connectlink {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/ssl/certs/yourdomain.crt;
    ssl_certificate_key /etc/ssl/private/yourdomain.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://connectlink;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/connectlink/static;
        expires 30d;
    }
}
```

**5. Enable Nginx Site**:
```bash
sudo ln -s /etc/nginx/sites-available/connectlink /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

**6. Create Systemd Service** (`/etc/systemd/system/connectlink.service`):
```ini
[Unit]
Description=ConnectLink Application
After=network.target postgresql.service

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/connectlink
Environment="PATH=/path/to/connectlink/venv/bin"
ExecStart=/path/to/connectlink/venv/bin/gunicorn --config gunicorn_config.py ConnectLink:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**7. Enable and Start Service**:
```bash
sudo systemctl daemon-reload
sudo systemctl enable connectlink
sudo systemctl start connectlink
sudo systemctl status connectlink
```

**8. Verify Application is Running**:
```bash
curl https://yourdomain.com
```

---

## CONFIGURATION

### Environment Variables

**Development** (`.env`):
```
FLASK_ENV=development
DEBUG=True
FLASK_DEBUG=True
SECRET_KEY=dev-key-only-for-development-not-secure
DATABASE_URL=postgresql://user:pass@localhost/connectlinkdata
```

**Production** (in CI/CD or server environment):
```
FLASK_ENV=production
DEBUG=False
FLASK_DEBUG=False
SECRET_KEY=<generate-with: python -c "import secrets; print(secrets.token_hex(32))">
DATABASE_URL=postgresql://user:pass@prod-db-server/connectlinkdata
GEMINI_API_KEY=<actual-api-key>
WHATSAPP_API_TOKEN=<actual-token>
```

### Generate Secure SECRET_KEY

```python
# Python
import secrets
print(secrets.token_hex(32))
```

### Configure Database Connection

**Connection String Format**:
```
postgresql://username:password@hostname:port/database_name
```

**Examples**:
```
# Local development
postgresql://connectlink_user:mypassword@localhost:5432/connectlinkdata

# Production
postgresql://prod_user:secure_password@db.prod.example.com:5432/connectlinkdata
```

### Configure API Keys

**1. Google Gemini API**:
   - Go to: https://makersuite.google.com/app/apikey
   - Create new API key
   - Copy to `.env` as `GEMINI_API_KEY`

**2. WhatsApp Business API**:
   - Register at: https://www.whatsapp.com/business/
   - Get API token
   - Get Phone ID
   - Copy to `.env`

**3. (Optional) SendGrid Email**:
   - Register at: https://sendgrid.com
   - Get API key
   - Copy to `.env`

---

## DATABASE MANAGEMENT

### Backup Database

**Full Backup**:
```bash
pg_dump -U connectlink_user connectlinkdata > backup_$(date +%Y%m%d_%H%M%S).sql
```

**Compressed Backup**:
```bash
pg_dump -U connectlink_user connectlinkdata | gzip > backup_$(date +%Y%m%d).sql.gz
```

**Scheduled Backup (Cron - Linux/macOS)**:
```bash
# Edit crontab
crontab -e

# Add this line (backup daily at 2 AM)
0 2 * * * pg_dump -U connectlink_user connectlinkdata | gzip > /backups/connectlink_$(date +\%Y\%m\%d).sql.gz
```

### Restore Database

**Full Restore**:
```bash
psql -U connectlink_user connectlinkdata < backup_20260415.sql
```

**From Compressed Backup**:
```bash
gunzip -c backup_20260415.sql.gz | psql -U connectlink_user connectlinkdata
```

### Database Optimization

**Analyze Tables** (improves query performance):
```bash
psql -U connectlink_user connectlinkdata -c "ANALYZE;"
```

**Vacuum Database** (removes dead tuples):
```bash
psql -U connectlink_user connectlinkdata -c "VACUUM ANALYZE;"
```

**Add Indexes** (speed up frequent queries):
```sql
CREATE INDEX idx_projects_status ON connectlinkdatabase(status);
CREATE INDEX idx_products_category ON connectlinkinventory(category);
CREATE INDEX idx_transactions_date ON connectlinktransactions(date);
CREATE INDEX idx_payments_status ON payments(status);
```

### Verify Database Health

```bash
# Check database size
psql -U connectlink_user connectlinkdata -c "SELECT pg_size_pretty(pg_database_size('connectlinkdata'));"

# List all tables
psql -U connectlink_user connectlinkdata -c "\dt"

# Check table sizes
psql -U connectlink_user connectlinkdata -c "SELECT table_name, pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) FROM information_schema.tables WHERE table_schema = 'public' ORDER BY pg_total_relation_size(quote_ident(table_name)) DESC;"
```

---

## BACKUP & RECOVERY

### Automated Backup Strategy

**Daily Backups**:
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backups/connectlink"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/connectlink_$TIMESTAMP.sql.gz"

# Create backup directory if not exists
mkdir -p $BACKUP_DIR

# Perform backup
pg_dump -U connectlink_user connectlinkdata | gzip > $BACKUP_FILE

# Keep only last 30 days of backups
find $BACKUP_DIR -name "connectlink_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE"
```

**Make executable**:
```bash
chmod +x backup.sh
```

**Add to crontab**:
```bash
# Daily at 2 AM
0 2 * * * /path/to/backup.sh >> /var/log/connectlink_backup.log 2>&1

# Multiple times per day (every 6 hours)
0 */6 * * * /path/to/backup.sh >> /var/log/connectlink_backup.log 2>&1
```

### Disaster Recovery Plan

**Step 1: Assessment**
- Identify what failed (database, app, server)
- Determine data loss tolerance
- Choose appropriate backup point

**Step 2: Restore from Backup**
```bash
# Stop application
sudo systemctl stop connectlink

# Restore database
psql -U connectlink_user connectlinkdata < /backups/connectlink_20260415_020000.sql

# Verify restore
psql -U connectlink_user connectlinkdata -c "SELECT COUNT(*) FROM connectlinkdatabase;"

# Restart application
sudo systemctl start connectlink
```

**Step 3: Verification**
- Test login
- Check recent data
- Verify all functionality
- Monitor logs for errors

**Step 4: Communication**
- Notify users of downtime
- Provide status updates
- Confirm service restoration

---

## MONITORING & MAINTENANCE

### Application Monitoring

**Check Application Status**:
```bash
# Systemd service status
sudo systemctl status connectlink

# Check if listening on port
sudo netstat -tulpn | grep 8000
# or
sudo ss -tulpn | grep 8000
```

**Monitor Application Logs**:
```bash
# View recent logs
sudo tail -100 /var/log/connectlink/error.log
sudo tail -100 /var/log/connectlink/access.log

# Follow logs in real-time
sudo tail -f /var/log/connectlink/error.log
```

### Database Monitoring

**Monitor Database Connections**:
```sql
SELECT datname, count(*) as connections FROM pg_stat_activity GROUP BY datname;
```

**Monitor Slow Queries** (enable slow query logging):
```sql
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries > 1000ms
SELECT pg_reload_conf();
```

**Check Database Activity**:
```sql
SELECT pid, usename, application_name, state, query FROM pg_stat_activity;
```

### System Monitoring

**CPU & Memory Usage**:
```bash
# Overall system
free -h
top -b -n 1

# PostgreSQL process
ps aux | grep postgres
```

**Disk Space**:
```bash
df -h
du -sh /path/to/connectlink

# PostgreSQL logs
du -sh /var/log/postgresql/
```

### Automated Health Checks

**Create Health Check Script** (`health_check.sh`):
```bash
#!/bin/bash

# Check application
if ! curl -s http://localhost:5000/health > /dev/null; then
    echo "Application is down!"
    sudo systemctl restart connectlink
fi

# Check database
if ! psql -U connectlink_user connectlinkdata -c "SELECT 1" > /dev/null 2>&1; then
    echo "Database is down!"
    sudo systemctl restart postgresql
fi

echo "Health check passed: $(date)"
```

**Run Hourly**:
```bash
# Add to crontab
0 * * * * /path/to/health_check.sh >> /var/log/health_check.log 2>&1
```

### Maintenance Schedule

**Daily**:
- [ ] Check error logs
- [ ] Monitor disk usage
- [ ] Verify backups completed
- [ ] Check database performance

**Weekly**:
- [ ] Review security updates
- [ ] Analyze slowest queries
- [ ] Test backup restoration
- [ ] Check application metrics

**Monthly**:
- [ ] Database optimization (VACUUM, ANALYZE)
- [ ] Security audit
- [ ] Performance tuning
- [ ] Update dependencies
- [ ] Plan capacity

**Quarterly**:
- [ ] Major updates/patches
- [ ] Security review
- [ ] Disaster recovery drill
- [ ] Documentation updates

---

## TROUBLESHOOTING

### Application Won't Start

**Error: "Address already in use"**
```bash
# Find process using port 5000
sudo lsof -i :5000
# or
sudo netstat -tulpn | grep 5000

# Kill the process
sudo kill -9 <PID>
```

**Error: "ModuleNotFoundError: No module named..."**
```bash
# Verify virtual environment is activated
which python
# Should show: /path/to/connectlink/venv/bin/python

# If not, activate it
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate  # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

**Error: "Database connection refused"**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Start PostgreSQL if stopped
sudo systemctl start postgresql

# Verify connection string in .env
# Format: postgresql://user:password@host:port/database
psql -U connectlink_user -h localhost -d connectlinkdata
```

### Database Issues

**Error: "Database does not exist"**
```bash
# Create database
psql -U postgres
CREATE DATABASE connectlinkdata OWNER connectlink_user;
\q

# Initialize tables
python ConnectLink.py  # Run application to create tables
```

**Error: "Permission denied for schema public"**
```sql
GRANT ALL PRIVILEGES ON SCHEMA public TO connectlink_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO connectlink_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO connectlink_user;
```

**Database Growing Too Large**
```sql
-- Check table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) FROM pg_tables ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Clean up old data
DELETE FROM transactions WHERE date < NOW() - INTERVAL '1 year';
VACUUM ANALYZE;
```

### API Integration Issues

**WhatsApp Messages Not Sending**
```python
# Test WhatsApp connection
from src.communication import WhatsAppService
service = WhatsAppService()
result = service.test_connection()
print(result)
```

**Gemini API Not Responding**
- Verify API key is correct
- Check quota limits
- Test API directly:
```bash
curl -X POST https://generativelanguage.googleapis.com/v1/models/gemini-pro:generateContent?key=YOUR_API_KEY \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
```

### Performance Issues

**Slow Queries**
```sql
-- Enable query logging
ALTER SYSTEM SET log_statement = 'all';
SELECT pg_reload_conf();

-- Check slow queries
SELECT query, calls, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;
```

**High Memory Usage**
```bash
# Restart application
sudo systemctl restart connectlink

# Check for memory leaks
ps aux | grep connectlink
# End process if >50% memory
sudo kill -9 <PID>
sudo systemctl start connectlink
```

---

## UPGRADE PROCEDURES

### Before Upgrade

- [ ] Backup database
- [ ] Backup configuration files
- [ ] Note current version
- [ ] Check upgrade warnings
- [ ] Schedule downtime if needed

### Upgrade Steps

**Step 1: Stop Application**
```bash
sudo systemctl stop connectlink
```

**Step 2: Backup Current Version**
```bash
cp -r /path/to/connectlink /path/to/connectlink_backup_v2.0
```

**Step 3: Pull Latest Code**
```bash
cd /path/to/connectlink
git fetch origin
git checkout main
git pull origin main
```

**Step 4: Update Dependencies**
```bash
source venv/bin/activate
pip install -r requirements.txt --upgrade
```

**Step 5: Run Database Migrations** (if any)
```bash
python manage.py db upgrade
```

**Step 6: Test Application Locally** (development)
```bash
python ConnectLink.py
# Test in browser at http://localhost:5000
```

**Step 7: Restart Service** (production)
```bash
sudo systemctl start connectlink
sudo systemctl status connectlink
```

**Step 8: Verify Upgrade**
```bash
# Check logs
sudo tail -50 /var/log/connectlink/error.log

# Test functionality
curl https://yourdomain.com
```

### Rollback Procedure (if needed)

**Step 1: Stop Application**
```bash
sudo systemctl stop connectlink
```

**Step 2: Restore Previous Version**
```bash
rm -rf /path/to/connectlink
cp -r /path/to/connectlink_backup_v2.0 /path/to/connectlink
```

**Step 3: Restore Virtual Environment**
```bash
rm -rf /path/to/connectlink/venv
python3 -m venv /path/to/connectlink/venv
source /path/to/connectlink/venv/bin/activate
pip install -r requirements.txt
```

**Step 4: Restart Service**
```bash
sudo systemctl start connectlink
```

---

## Version History

| Version | Release Date | Key Changes |
|---------|--------------|-------------|
| 2.0 | April 2026 | Full system release with all modules |
| 1.5 | January 2026 | Added AI classification, WhatsApp integration |
| 1.0 | October 2025 | Initial release |

---

## Support & Resources

- **Documentation**: See README_COMPLETE_SYSTEM.md
- **Quick Reference**: See QUICK_REFERENCE.md
- **Architecture**: See SYSTEM_ARCHITECTURE.md
- **Email Support**: support@connectlink.co.zw
- **Emergency Hotline**: +1234567890
- **Issue Tracker**: https://github.com/your/repo/issues

---

## Changelog

**v2.0.0 - April 2026**
- ✅ Full system release
- ✅ All modules functional
- ✅ Production-ready deployment
- ✅ Comprehensive documentation

**v1.5.0 - January 2026**
- ✅ AI product classification (98% accuracy)
- ✅ WhatsApp integration
- ✅ Enhanced reporting

**v1.0.0 - October 2025**
- ✅ Initial beta release
- ✅ Core modules
- ✅ Basic functionality
