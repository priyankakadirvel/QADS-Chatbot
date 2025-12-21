# 🚀 QADS - Quick Start Guide

Get QADS running in **5 minutes**!

---

## ⚡ Fastest Way (Windows Only)

**Double-click:** `run.bat`

That's it! ✅

---

## 📝 Manual Setup (All Platforms)

### Prerequisites
- Python 3.9+
- API Keys (Cohere, Groq, Pinecone, SerpAPI)

### 1️⃣ Setup Environment Variables

**Copy this file:** `.env.example` → `backend/.env`

```bash
cp .env.example backend/.env
```

**Edit `backend/.env` and add your API keys:**
```
COHERE_API_KEY=your_key_here
GROQ_API_KEY=your_key_here
PINECONE_API_KEY=your_key_here
PINECONE_INDEX_NAME=qads
SERP_API_KEY=your_key_here
```

**Get API Keys:**
- Cohere: https://cohere.com/ (Free)
- Groq: https://groq.com/ (Free)
- Pinecone: https://pinecone.io/ (Free tier: 1GB)
- SerpAPI: https://serpapi.com/ (Free: 100 requests/month)

### 2️⃣ Install Dependencies

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

### 3️⃣ Start Backend

**Windows:**
```bash
cd backend
venv\Scripts\activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**macOS/Linux:**
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

✅ **Expected output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Starting QADS server...
INFO:     Ingestion complete. Vector DB ready.
```

### 4️⃣ Start Frontend (New Terminal)

**Windows:**
```bash
cd frontend
python -m http.server 8080
```

**macOS/Linux:**
```bash
cd frontend
python3 -m http.server 8080
```

✅ **Expected output:**
```
Serving HTTP on 0.0.0.0 port 8080
```

### 5️⃣ Access Application

Open browser and go to:
```
http://localhost:8080/index.html
```

**Test Login:**
- **Username:** `priyanka.k@msds.christuniversity.in`
- **Password:** `password`

---

## 🐳 Docker Setup (Even Easier!)

### 1️⃣ Install Docker
- https://www.docker.com/products/docker-desktop

### 2️⃣ Create `.env` file
```bash
cp .env.example backend/.env
# Edit and add your API keys
```

### 3️⃣ Run Docker Compose
```bash
docker-compose up -d
```

### 4️⃣ Access Application
```
http://localhost:8080/index.html
```

### Check Logs
```bash
docker logs -f qads-chatbot
```

### Stop
```bash
docker-compose down
```

---

## 🎯 Test the Application

### Test Query Examples:
1. **"What is machine learning?"**
2. **"Explain random forest algorithm"**
3. **"How to handle missing data in pandas?"**
4. **"Write Python code for data normalization"**

### Check API Documentation:
```
http://localhost:8000/docs
```

---

## 🔧 Troubleshooting

### Issue: Port 8000 already in use
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <pid> /F

# macOS/Linux
lsof -i :8000
kill -9 <PID>
```

### Issue: API key not found error
```
✅ Check backend/.env file exists
✅ Verify API key is correct
✅ Restart backend after saving .env
```

### Issue: Frontend can't connect to backend
```
✅ Check backend is running on port 8000
✅ Check backend/.env has correct API keys
✅ Try http://localhost:8000/docs
```

### Issue: Virtual environment not working
```bash
# Delete and recreate
rm -rf backend/venv
python -m venv backend/venv
```

---

## 📁 Project Structure

```
QADS_Chatbot/
├── backend/           # Python FastAPI server
│   ├── main.py       # Entry point
│   ├── config/       # Configuration
│   ├── models/       # LLM & Embeddings
│   ├── utils/        # PDF & Web utilities
│   └── data/         # User data & history
├── frontend/         # HTML/CSS/JS UI
│   ├── index.html
│   ├── chat.html
│   ├── login.html
│   └── js/css/
├── Dockerfile        # Docker container
├── docker-compose.yml # Docker Compose
└── SETUP.md         # Detailed setup
```

---

## 📚 Documentation

- **SETUP.md** - Detailed setup for all platforms + Cloud deployment
- **DEPLOYMENT.md** - Deploy to Railway, Heroku, AWS, Google Cloud, etc.
- **README.md** - Project overview & architecture

---

## ✨ Features

✅ Domain-specific Q&A for Data Science
✅ Retrieval-Augmented Generation (RAG)
✅ Web search fallback
✅ Chat history & threads
✅ User authentication
✅ Code solutions (Python, SQL, R)

---

## 🚀 Next Steps

1. ✅ Get API keys
2. ✅ Setup `.env` file
3. ✅ Run backend & frontend
4. ✅ Test with sample queries
5. ✅ Deploy to cloud (SETUP.md → DEPLOYMENT.md)

---

## 📞 Need Help?

- **GitHub Issues**: https://github.com/priyankakadirvel/QADS-Chatbot/issues
- **Docs**: Read SETUP.md
- **API Docs**: http://localhost:8000/docs

---

## 💡 Tips

- Backend takes **20-30 seconds** to startup (PDF ingestion)
- First query takes **5-10 seconds** (embedding generation)
- Subsequent queries are **2-3 seconds**
- Test with queries about ML, statistics, data science

---

## 🎉 Happy Learning with QADS!

---

**Quick Command Reference:**

```bash
# Setup
python -m venv backend/venv
source backend/venv/bin/activate  # macOS/Linux
pip install -r backend/requirements.txt

# Run
uvicorn backend/main:app --reload --port 8000
python -m http.server 8080 --directory frontend

# Docker
docker-compose up -d
docker-compose down

# Test
curl http://localhost:8000/docs
open http://localhost:8080/index.html
```

---

**Version:** 2.0
**Last Updated:** December 2024
