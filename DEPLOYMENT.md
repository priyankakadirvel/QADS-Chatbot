# QADS Deployment Guide

## Quick Deployment Options

### 1. **Railway.app** (Recommended - Easiest) ⭐
### 2. **Heroku** (Classic but paid)
### 3. **AWS EC2** (Full control)
### 4. **Google Cloud Run** (Serverless)
### 5. **DigitalOcean** (Simple VPS)

---

## 🚀 Railway.app (Recommended)

**Best for:** Quick deployment with minimal configuration

### Step 1: Prepare Repository
```bash
git add .
git commit -m "Add deployment files"
git push origin main
```

### Step 2: Sign Up on Railway
- Go to https://railway.app/
- Click "Login with GitHub"
- Authorize Railway to access your repositories

### Step 3: Create New Project
1. Click "New Project"
2. Select "Deploy from GitHub repo"
3. Find and select `QADS-Chatbot`
4. Click "Deploy Now"

### Step 4: Add Environment Variables
In Railway Dashboard → Variables:
```
COHERE_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
PINECONE_API_KEY=your_key_here
PINECONE_INDEX_NAME=qads
PINECONE_ENVIRONMENT=us-east-1
SERP_API_KEY=your_key_here
```

### Step 5: Configure Start Command
- Build Command: `pip install -r backend/requirements.txt`
- Start Command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`

### Step 6: Deploy
- Click "Deploy"
- Wait for completion (~2-5 minutes)
- Your app URL: `https://your-project-name.railway.app`

**Cost:** Free tier available (limited resources)

---

## 🔴 Heroku Deployment

**Best for:** Classic deployment with Git integration

### Step 1: Install Heroku CLI
```bash
# Windows
choco install heroku-cli

# macOS
brew tap heroku/brew && brew install heroku

# Linux
curl https://cli-assets.heroku.com/install.sh | sh
```

### Step 2: Login to Heroku
```bash
heroku login
```

### Step 3: Create Heroku App
```bash
heroku create qads-chatbot
```

### Step 4: Add Environment Variables
```bash
heroku config:set COHERE_API_KEY=your_key
heroku config:set GROQ_API_KEY=your_key
heroku config:set PINECONE_API_KEY=your_key
heroku config:set PINECONE_INDEX_NAME=qads
heroku config:set SERP_API_KEY=your_key
```

### Step 5: Update backend/requirements.txt
Add at the end:
```
gunicorn==20.1.0
```

### Step 6: Deploy
```bash
git push heroku main
```

### Step 7: Monitor
```bash
heroku logs --tail
heroku open
```

**Cost:** Starting at $7/month (free tier deprecated)

---

## ☁️ AWS EC2 Deployment

**Best for:** Full control and scalability

### Step 1: Launch EC2 Instance
1. Go to AWS Console → EC2
2. Click "Launch Instance"
3. Choose Ubuntu 20.04 LTS (Free Tier eligible)
4. Instance Type: `t2.micro` (free tier)
5. Configure Security Groups:
   - Allow HTTP (80)
   - Allow HTTPS (443)
   - Allow Custom TCP 8000 (backend)
   - Allow SSH (22)
6. Create/Select Key Pair
7. Launch Instance

### Step 2: Connect to Instance
```bash
chmod 400 your-key.pem
ssh -i your-key.pem ubuntu@your-instance-public-ip
```

### Step 3: Setup System
```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git curl nginx

# Clone repository
git clone https://github.com/yourusername/QADS-Chatbot.git
cd QADS-Chatbot
```

### Step 4: Setup Python Environment
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn
```

### Step 5: Create .env File
```bash
nano .env
# Add your API keys
```

### Step 6: Setup Supervisor (Background Service)
```bash
sudo apt install supervisor

sudo tee /etc/supervisor/conf.d/qads.conf > /dev/null <<EOF
[program:qads-backend]
directory=/home/ubuntu/QADS-Chatbot/backend
command=/home/ubuntu/QADS-Chatbot/backend/venv/bin/gunicorn -w 4 -b 127.0.0.1:8000 main:app
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/qads.log

[program:qads-frontend]
directory=/home/ubuntu/QADS-Chatbot/frontend
command=/home/ubuntu/QADS-Chatbot/frontend/venv/bin/python -m http.server 8080
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/qads-frontend.log
EOF
```

### Step 7: Start Services
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start qads-backend
sudo supervisorctl start qads-frontend
```

### Step 8: Setup Nginx Reverse Proxy
```bash
sudo tee /etc/nginx/sites-available/qads > /dev/null <<'EOF'
server {
    listen 80;
    server_name your-domain.com;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF
```

### Step 9: Enable Nginx
```bash
sudo ln -s /etc/nginx/sites-available/qads /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 10: Setup SSL (Let's Encrypt)
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

**Cost:** $5-20/month

---

## 🎯 Google Cloud Run (Serverless)

**Best for:** Automatic scaling, pay-per-use

### Step 1: Install Google Cloud SDK
```bash
# https://cloud.google.com/sdk/docs/install
gcloud init
gcloud auth login
gcloud config set project your-project-id
```

### Step 2: Enable Required APIs
```bash
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

### Step 3: Build and Deploy
```bash
gcloud run deploy qads-chatbot \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars=COHERE_API_KEY=your_key,GROQ_API_KEY=your_key,PINECONE_API_KEY=your_key,SERP_API_KEY=your_key
```

### Step 4: Get URL
```bash
gcloud run services describe qads-chatbot --platform managed --region us-central1 --format='value(status.url)'
```

**Cost:** Free tier up to 2 million requests/month

---

## 🌊 DigitalOcean App Platform

**Best for:** Developer-friendly, affordable

### Step 1: Sign Up
- Go to https://www.digitalocean.com/app-platform/
- Connect GitHub account

### Step 2: Create App
1. Click "Create App"
2. Select GitHub repository
3. Choose deployment source

### Step 3: Configure Services
Backend:
- Build: `pip install -r backend/requirements.txt`
- Start: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
- Port: 8080

### Step 4: Add Environment Variables
In Settings → Environment:
```
COHERE_API_KEY=your_key
GROQ_API_KEY=your_key
PINECONE_API_KEY=your_key
SERP_API_KEY=your_key
```

### Step 5: Deploy
Click "Deploy" and wait.

**Cost:** Starting at $12/month

---

## 📦 Docker Deployment (Any Platform)

### Build and Push to Docker Hub
```bash
# Build image
docker build -t yourusername/qads-chatbot .

# Login to Docker Hub
docker login

# Push image
docker push yourusername/qads-chatbot

# Run anywhere
docker run -p 8000:8000 -p 8080:8080 \
  -e COHERE_API_KEY=your_key \
  -e GROQ_API_KEY=your_key \
  -e PINECONE_API_KEY=your_key \
  -e SERP_API_KEY=your_key \
  yourusername/qads-chatbot
```

---

## 🔐 Security Checklist

Before deploying:

- [ ] .env file is in .gitignore
- [ ] Never commit API keys
- [ ] Use strong database passwords
- [ ] Enable HTTPS/SSL
- [ ] Setup firewall rules
- [ ] Enable rate limiting
- [ ] Monitor logs regularly
- [ ] Setup error alerting
- [ ] Regular backups configured
- [ ] Security headers configured

---

## 🚨 Troubleshooting

### Deployment Failed

**Railway:**
```bash
# Check logs in Dashboard → Deployments
# Click "View Build Logs"
```

**Heroku:**
```bash
heroku logs --tail
heroku logs --tail --source app
heroku logs --tail --source build
```

**AWS EC2:**
```bash
sudo supervisorctl status
sudo tail -f /var/log/qads.log
```

### Application Errors

**Port Already in Use:**
```bash
# Find process
lsof -i :8000

# Kill process
kill -9 <PID>
```

**API Key Not Found:**
- Check environment variables are set
- Restart application after adding .env
- Verify API key is correct

**Memory Issues:**
- Increase instance type
- Enable swap space
- Optimize code

---

## 📊 Monitoring

### Setup Monitoring
```bash
# AWS CloudWatch
# Railway: Built-in monitoring
# Heroku: Heroku Monitoring ($50/month)
# GCP: Cloud Monitoring (free)
```

### Health Checks
```bash
# Check backend
curl https://your-app.com/docs

# Check frontend  
curl https://your-app.com/index.html
```

---

## 💰 Cost Comparison

| Platform | Minimum Cost | Free Tier | Best For |
|----------|-------------|-----------|----------|
| Railway | Free | Yes (Limited) | Learning |
| Heroku | $7/month | Deprecated | Testing |
| AWS EC2 | $5/month | Yes (1yr) | Production |
| Google Cloud Run | Free | Yes (2M req) | Startups |
| DigitalOcean | $12/month | Yes | Small Projects |

---

## 🎓 Next Steps

1. Choose platform
2. Prepare environment variables
3. Follow deployment steps
4. Test application
5. Setup monitoring
6. Configure custom domain (optional)

---

**Happy Deploying! 🎉**
