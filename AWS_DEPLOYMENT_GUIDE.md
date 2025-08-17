# Voice AI Agent - AWS Deployment Guide

## 🎯 Why We're Moving to AWS

### Current Problem
- **Agent running locally** cannot receive job dispatches from LiveKit Cloud
- **WebSocket connection unstable** - drops every 30-60 minutes
- **NAT/Firewall issues** - LiveKit Cloud cannot reach local agent
- **No database updates** - Agent never processes calls

### Solution: Cloud Deployment
- **Stable internet connection** with static IP
- **24/7 availability** for receiving calls
- **Direct connectivity** to LiveKit Cloud
- **Reliable database updates** for all call events

## 📊 Cost Analysis

### AWS Free Tier (12 months)
- EC2 t2.micro: **FREE** (750 hours/month)
- RDS PostgreSQL: **FREE** (750 hours/month)
- Data transfer: 15GB/month **FREE**

### Ongoing Costs (Pay-per-use)
- LiveKit Cloud: ~$0.0075/minute
- SIP Trunk (Twilio): ~$0.0085/minute
- **Total: ~$0.016/minute** (only for actual calls)

### Monthly Estimate
- 1000 calls × 5 minutes = 5000 minutes
- Cost: ~$80/month for calls
- Infrastructure: $0 (free tier) or $30-50 (after free tier)

## 🚀 AWS Setup Steps

### Step 1: AWS Account Setup ✅
- Created account with CISO approval
- Received EC2 instance details
- Got PEM key file for SSH access

### Step 2: Connect to EC2 Instance (Current Step)
```bash
# Fix PEM file permissions
chmod 400 ~/Downloads/your-key.pem

# Connect to instance
ssh -i ~/Downloads/your-key.pem ubuntu@YOUR_EC2_IP

# Common usernames to try:
# - ubuntu (for Ubuntu)
# - ec2-user (for Amazon Linux)
# - admin (for Debian)
```

### Step 3: Server Setup (Next Steps)
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install PostgreSQL client
sudo apt install postgresql-client -y

# Install git and other tools
sudo apt install git nginx supervisor -y
```

### Step 4: Deploy Application
```bash
# Clone repository
git clone https://github.com/your-repo/outbound-caller-python.git
cd outbound-caller-python

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Add your credentials
```

### Step 5: Database Setup
```bash
# Option 1: Use RDS (Managed)
# - Create RDS PostgreSQL instance
# - Update DATABASE_URL in .env

# Option 2: Install locally
sudo apt install postgresql -y
sudo -u postgres createdb voice_ai_db
sudo -u postgres createuser voice_ai_user
```

### Step 6: Create Systemd Services

#### Agent Service (/etc/systemd/system/voice-agent.service)
```ini
[Unit]
Description=Voice AI Agent
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/outbound-caller-python
Environment="PATH=/home/ubuntu/outbound-caller-python/venv/bin"
Environment="PYTHONPATH=/home/ubuntu/outbound-caller-python"
ExecStart=/home/ubuntu/outbound-caller-python/venv/bin/python agent.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### API Service (/etc/systemd/system/voice-api.service)
```ini
[Unit]
Description=Voice AI API Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/outbound-caller-python
Environment="PATH=/home/ubuntu/outbound-caller-python/venv/bin"
Environment="PYTHONPATH=/home/ubuntu/outbound-caller-python"
ExecStart=/home/ubuntu/outbound-caller-python/venv/bin/python api_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Step 7: Start Services
```bash
# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable voice-agent voice-api
sudo systemctl start voice-agent voice-api

# Check status
sudo systemctl status voice-agent
sudo systemctl status voice-api

# View logs
sudo journalctl -u voice-agent -f
sudo journalctl -u voice-api -f
```

### Step 8: Configure Nginx (Optional)
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

### Step 9: Security Setup
```bash
# Configure firewall
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp # HTTPS
sudo ufw allow 8000:8003/tcp # API ports
sudo ufw enable

# Security groups (AWS Console)
# Inbound rules:
# - SSH (22) from your IP only
# - HTTP (80) from anywhere
# - HTTPS (443) from anywhere
# - Custom TCP (8000-8003) from anywhere
```

### Step 10: Testing
```bash
# Test API server
curl http://localhost:8000/health

# Make test call
curl -X POST http://localhost:8000/call \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "user_dummy_1",
    "organization_id": "krim_ai_dummy_org",
    "phone_number": "+1234567890",
    "from_number": "+15076269649",
    "customer_info": {
      "customer_name": "Test User",
      "emi_amount": 1500,
      "emi_due_date": "2025-08-01"
    }
  }'

# Check agent logs
sudo journalctl -u voice-agent -f

# Check database
psql -U voice_ai_user -d voice_ai_db -c "SELECT * FROM interactions;"
```

## 🔍 Troubleshooting

### SSH Connection Issues
```bash
# Wrong username
ssh -i key.pem ec2-user@IP  # Try this for Amazon Linux
ssh -i key.pem admin@IP      # Try this for Debian

# Wrong key
# Ask CISO for correct PEM file

# Permissions issue
chmod 400 key.pem
```

### Agent Not Receiving Jobs
```bash
# Check WebSocket connection
sudo journalctl -u voice-agent | grep "registered worker"

# Check LiveKit credentials
grep LIVEKIT /home/ubuntu/outbound-caller-python/.env

# Test network connectivity
curl https://voice-ai-project-qxvy2kj1.livekit.cloud
```

### Database Connection Issues
```bash
# Test connection
psql $DATABASE_URL -c "SELECT 1;"

# Check credentials
grep DATABASE_URL /home/ubuntu/outbound-caller-python/.env
```

## 📈 Monitoring

### Basic Monitoring
```bash
# CPU and Memory
top
htop

# Disk usage
df -h

# Service status
systemctl status voice-agent voice-api

# Active connections
netstat -an | grep ESTABLISHED
```

### Advanced Monitoring (Optional)
- CloudWatch for metrics
- Datadog for APM
- Prometheus + Grafana

## 🎯 Success Criteria

1. ✅ Agent stays connected to LiveKit for hours
2. ✅ Receives job dispatch when call is made
3. ✅ Updates database with call progress
4. ✅ Saves transcripts and recordings
5. ✅ Runs 24/7 without manual intervention

## 📞 Next Steps After Deployment

1. **Test with real calls**
2. **Monitor logs for errors**
3. **Set up alerts for failures**
4. **Plan scaling strategy**
5. **Implement CI/CD pipeline**

## 🆘 Support

- LiveKit Docs: https://docs.livekit.io
- AWS Support: Through console
- Database: PostgreSQL docs
- Monitoring: CloudWatch/Datadog

---

**Current Status**: Setting up SSH connection to EC2 instance