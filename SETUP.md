# QADS - Local Setup & Deployment Guide

## 📋 Quick Start (Local Development)

### Prerequisites
- **Python 3.9+**
- **Git**
- **API Keys**: Cohere, Groq, Pinecone, SerpAPI

---

## 🚀 Option 1: Quick Local Setup (5 minutes)

### Step 1: Clone & Navigate
```bash
git clone https://github.com/priyankakadirvel/QADS-Chatbot.git
cd QADS-Chatbot
```

### Step 2: Setup Backend

**Windows:**
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**macOS/Linux:**
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables

Create `.env` file in `backend/` folder:
```
COHERE_API_KEY=your_cohere_api_key_here
GROQ_API_KEY=your_groq_api_key_here
PINECONE_API_KEY=your_pinecone_api_key_here
PINECONE_INDEX_NAME=qads
PINECONE_ENVIRONMENT=us-east-1
SERP_API_KEY=your_serpapi_key_here
```

**Get API Keys:**
- Cohere: https://cohere.com/
- Groq: https://groq.com/
- Pinecone: https://pinecone.io/
- SerpAPI: https://serpapi.com/

### Step 4: Add Knowledge Base (Optional)
```bash
# Copy your PDF textbooks to backend/books_pdfs/
cp your_textbooks/*.pdf backend/books_pdfs/
```

### Step 5: Run Backend
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Starting QADS server...
INFO:     Ingestion complete. Vector DB ready.
```

### Step 6: Run Frontend (New Terminal)
```bash
cd frontend
python -m http.server 8080
```

### Step 7: Access Application
Open browser and go to:
```
http://localhost:8080/index.html
```

**Login with test credentials:**
- Username: `priyanka.k@msds.christuniversity.in`
- Password: `password`

---

## 🐳 Option 2: Docker Setup (Recommended for Deployment)

### Step 1: Install Docker
- **Windows/Mac**: https://www.docker.com/products/docker-desktop
- **Linux**: `apt-get install docker.io`

### Step 2: Create Dockerfile
File: `Dockerfile` (in project root)

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Copy backend files
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy application files
COPY backend/ ./backend/
COPY frontend/ ./frontend/

# Create data directories
RUN mkdir -p backend/data/history backend/books_pdfs

# Set environment
ENV PYTHONUNBUFFERED=1

# Expose ports
EXPOSE 8000 8080

# Start both backend and frontend
CMD sh -c "cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 & cd frontend && python -m http.server 8080"
```

### Step 3: Create Docker Compose
File: `docker-compose.yml`

```yaml
version: '3.8'

services:
  qads-app:
    build: .
    container_name: qads-chatbot
    ports:
      - "8000:8000"
      - "8080:8080"
    environment:
      - COHERE_API_KEY=${COHERE_API_KEY}
      - GROQ_API_KEY=${GROQ_API_KEY}
      - PINECONE_API_KEY=${PINECONE_API_KEY}
      - PINECONE_INDEX_NAME=qads
      - SERP_API_KEY=${SERP_API_KEY}
    volumes:
      - ./backend/books_pdfs:/app/backend/books_pdfs
      - ./backend/data:/app/backend/data
    restart: always
```

### Step 4: Build & Run Docker
```bash
# Build image
docker build -t qads-chatbot .

# Run container
docker run -p 8000:8000 -p 8080:8080 \
  -e COHERE_API_KEY=your_key \
  -e GROQ_API_KEY=your_key \
  -e PINECONE_API_KEY=your_key \
  -e SERP_API_KEY=your_key \
  qads-chatbot

# Or use Docker Compose
docker-compose up -d
```

---

## ☁️ Option 3: Cloud Deployment

### Option 3A: Deploy on Railway.app (Easiest)

**Step 1:** Go to https://railway.app/

**Step 2:** Click "New Project" → "Deploy from GitHub"

**Step 3:** Select your QADS repository

**Step 4:** Add Environment Variables
```
COHERE_API_KEY=your_key
GROQ_API_KEY=your_key
PINECONE_API_KEY=your_key
SERP_API_KEY=your_key
PINECONE_INDEX_NAME=qads
PINECONE_ENVIRONMENT=us-east-1
```

**Step 5:** Configure Service
- **Build Command:** `pip install -r backend/requirements.txt`
- **Start Command:** `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Port:** 8000

**Step 6:** Deploy
Railway automatically deploys on push. Your app will be live at:
```
https://your-app-name.railway.app
```

---

### Option 3B: Deploy on Heroku

**Step 1:** Install Heroku CLI
```bash
# Windows
choco install heroku-cli

# macOS
brew tap heroku/brew && brew install heroku

# Linux
curl https://cli-assets.heroku.com/install.sh | sh
```

**Step 2:** Create Procfile
File: `Procfile` (in project root)
```
web: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
```

**Step 3:** Create runtime.txt
File: `runtime.txt`
```
python-3.9.18
```

**Step 4:** Login & Deploy
```bash
heroku login
heroku create your-app-name
heroku config:set COHERE_API_KEY=your_key
heroku config:set GROQ_API_KEY=your_key
heroku config:set PINECONE_API_KEY=your_key
heroku config:set SERP_API_KEY=your_key
git push heroku main
```

**Step 5:** View App
```bash
heroku open
```

---

### Option 3C: Deploy on AWS (EC2)

**Step 1:** Launch EC2 Instance
- AMI: Ubuntu 20.04 LTS
- Instance Type: t2.medium (free tier: t2.micro)
- Security Group: Allow ports 8000, 8080

**Step 2:** SSH into Instance
```bash
ssh -i your-key.pem ubuntu@your-instance-ip
```

**Step 3:** Install Dependencies
```bash
sudo apt update
sudo apt install python3-pip python3-venv git

# Clone repo
git clone https://github.com/priyankakadirvel/QADS-Chatbot.git
cd QADS-Chatbot
```

**Step 4:** Setup Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Step 5:** Create .env File
```bash
nano .env
# Add your API keys
```

**Step 6:** Run with Supervisor (Background Service)
```bash
sudo apt install supervisor

sudo nano /etc/supervisor/conf.d/qads.conf
```

Add:
```ini
[program:qads]
directory=/home/ubuntu/QADS-Chatbot/backend
command=/home/ubuntu/QADS-Chatbot/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
autostart=true
autorestart=true
stderr_logfile=/var/log/qads.err.log
stdout_logfile=/var/log/qads.out.log
```

**Step 7:** Start Service
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start qads
```

**Step 8:** Access Application
```
http://your-instance-ip:8000/docs
```

---

### Option 3D: Deploy on Google Cloud Run (Serverless)

**Step 1:** Install Google Cloud SDK
```bash
# https://cloud.google.com/sdk/docs/install
```

**Step 2:** Authenticate
```bash
gcloud auth login
gcloud config set project your-project-id
```

**Step 3:** Create Dockerfile (same as Docker option)

**Step 4:** Build & Deploy
```bash
gcloud run deploy qads-chatbot \
  --source . \
  --platform managed \
  --region us-central1 \
  --port 8000 \
  --set-env-vars COHERE_API_KEY=your_key,GROQ_API_KEY=your_key,PINECONE_API_KEY=your_key,SERP_API_KEY=your_key
```

Your app will be live at the provided Cloud Run URL.

---

## 🔧 Production Configuration

### Using Gunicorn (Production Server)

**Step 1:** Install Gunicorn
```bash
pip install gunicorn
```

**Step 2:** Run with Gunicorn
```bash
cd backend
gunicorn -w 4 -b 0.0.0.0:8000 main:app
```

### Using Nginx Reverse Proxy

Create `/etc/nginx/sites-available/qads`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        root /var/www/qads-frontend;
        try_files $uri $uri/ /index.html;
    }
}
```

Enable and restart:
```bash
sudo ln -s /etc/nginx/sites-available/qads /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 📊 Monitoring & Logging

### View Logs
```bash
# Backend logs
journalctl -u qads -f

# Docker logs
docker logs -f qads-chatbot

# Heroku logs
heroku logs --tail
```

### Health Check Endpoint
```bash
curl http://localhost:8000/docs
```

---

## 🔐 Security Checklist

- [ ] API keys stored in `.env` (never commit)
- [ ] HTTPS enabled in production
- [ ] CORS configured properly
- [ ] Rate limiting enabled
- [ ] Input validation on all endpoints
- [ ] Database passwords hashed
- [ ] Logs monitored for errors

---

## 📝 Environment Variables Summary

| Variable | Required | Example |
|----------|----------|---------|
| `COHERE_API_KEY` | ✅ | `abc123...` |
| `GROQ_API_KEY` | ✅ | `gsk_...` |
| `PINECONE_API_KEY` | ✅ | `pcsk_...` |
| `PINECONE_INDEX_NAME` | ✅ | `qads` |
| `SERP_API_KEY` | ✅ | `...` |
| `PINECONE_ENVIRONMENT` | ⚠️ | `us-east-1` |
| `LOG_LEVEL` | ❌ | `INFO` |

---

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <pid> /F

# macOS/Linux
lsof -i :8000
kill -9 <PID>
```

### API Key Errors
```
RuntimeError: Groq API key not found
→ Check .env file exists in backend/
→ Check API key is correct
→ Restart server after updating .env
```

### Vector DB Connection Failed
```
pinecone.exceptions.PineconeException
→ Check PINECONE_API_KEY
→ Check PINECONE_INDEX_NAME
→ Check internet connection
```

### Frontend Cannot Connect to Backend
```
CORS Error
→ Check backend is running on 8000
→ Check frontend is accessing http://localhost:8000
→ Check CORS is enabled in main.py
```

---

## 📞 Support

- **Issues**: https://github.com/priyankakadirvel/QADS-Chatbot/issues
- **Documentation**: See README.md
- **Quick Start**: See this file

---

## ✨ Next Steps

1. ✅ Local development setup
2. ✅ Get API keys
3. ✅ Test with sample queries
4. ✅ Deploy to cloud
5. ✅ Configure custom domain
6. ✅ Setup monitoring & alerts

---

**Happy Building! 🚀**
