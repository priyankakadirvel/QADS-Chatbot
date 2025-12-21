# 🚂 Railway Deployment Guide (Simple)

Deploy QADS on Railway without Docker!

---

## 📋 **Prerequisites**

1. **GitHub Account** - Repository already set up ✅
2. **Railway Account** - https://railway.app/
3. **API Keys** - Cohere, Groq, Pinecone, SerpAPI

---

## 🚀 **Step-by-Step Deployment**

### **Step 1: Go to Railway**

Open: https://railway.app/

Click **"Login"** → Select **"GitHub"** → Authorize

---

### **Step 2: Create New Project**

1. Click **"+ New Project"**
2. Select **"Deploy from GitHub repo"**
3. Search for: **`QADS-Chatbot`**
4. Click on your repo
5. Click **"Deploy Now"**

---

### **Step 3: Wait for Initial Build**

Railway will:
- ✅ Detect Python project
- ✅ Read `Procfile`
- ✅ Install dependencies
- ✅ Build application

This takes **2-5 minutes**

---

### **Step 4: Add Environment Variables** ⚠️ IMPORTANT

While building, add your API keys:

**In Railway Dashboard:**

1. Click on your service/project
2. Go to **"Variables"** tab
3. Add each variable:

```
COHERE_API_KEY = [your_cohere_key]
GROQ_API_KEY = [your_groq_key]
PINECONE_API_KEY = [your_pinecone_key]
PINECONE_INDEX_NAME = qads
PINECONE_ENVIRONMENT = us-east-1
SERP_API_KEY = [your_serpapi_key]
```

**⚠️ Important:** Add variables BEFORE deployment completes!

---

### **Step 5: Trigger Deployment**

If already building:
- Variables take effect automatically

If build already finished:
1. Click **"Deployments"** tab
2. Click the **3-dot menu**
3. Select **"Redeploy"**

---

### **Step 6: Check Deployment Status**

Go to **"Deployments"** tab:

- ✅ **Building** - Environment being set up
- ✅ **Deploying** - App starting
- ✅ **Success** - App is live! 🎉

---

### **Step 7: Get Your Live URL**

In Railway Dashboard:

Look for your deployment URL:
```
https://your-app-name.railway.app
```

**✅ Your app is live!**

---

## 🧪 **Test Your Deployed App**

Open your Railway URL in browser:
```
https://your-app-name.railway.app
```

**Login:**
- Username: `priyanka.k@msds.christuniversity.in`
- Password: `password`

**Try a query:**
- "What is machine learning?"
- "Explain random forest algorithm"
- "Write Python code for data normalization"

---

## 🔍 **Monitor & Troubleshoot**

### **View Logs**

1. Go to **"Logs"** tab
2. See real-time output
3. Check for errors

### **Common Issues**

**Issue:** `ModuleNotFoundError: No module named 'xxx'`
- **Fix:** Add to `backend/requirements.txt` and redeploy

**Issue:** `API key not found`
- **Fix:** Check Variables are set correctly, redeploy

**Issue:** `Build failed`
- **Fix:** Check Build logs, verify requirements.txt is valid

### **Restart App**

1. Go to **"Deployments"**
2. Click **3-dot menu**
3. Select **"Redeploy"**

---

## 📊 **How Railway Works**

```
GitHub Push
    ↓
Railway detects change
    ↓
Reads Procfile
    ↓
Installs requirements.txt
    ↓
Runs: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
    ↓
App is live! 🎉
```

---

## 🔑 **API Keys - Where to Get Them**

### **Cohere**
- https://cohere.com/
- Sign up (free)
- Go to "API Keys"
- Copy key

### **Groq**
- https://groq.com/
- Sign in with GitHub
- Go to "API Keys"
- Create new key, copy

### **Pinecone**
- https://pinecone.io/
- Sign up (free tier)
- Create index: `qads`
- Go to "API Keys"
- Copy key

### **SerpAPI**
- https://serpapi.com/
- Free signup (100 requests/month free)
- Dashboard → "API Key"
- Copy key

---

## 📝 **Files Railway Uses**

```
QADS_Chatbot/
├── Procfile              ← Railway reads this
├── backend/
│   ├── requirements.txt  ← Installs these
│   ├── main.py          ← Starts this
│   ├── config/
│   ├── models/
│   └── utils/
├── frontend/            ← Static files
├── README.md
└── SETUP.md
```

**Procfile tells Railway:**
```
web: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT
```

---

## ✅ **Deployment Checklist**

- [ ] GitHub repo is public
- [ ] Authorized Railway with GitHub
- [ ] Created new project from repo
- [ ] All 6 environment variables added
- [ ] Build completed successfully
- [ ] App is running (green status)
- [ ] Tested login works
- [ ] Tested queries work
- [ ] Share live URL!

---

## 🎯 **Next Steps After Deployment**

1. **Share your app:**
   ```
   https://your-app-name.railway.app
   ```

2. **Monitor:**
   - Check logs regularly
   - Watch for errors

3. **Update code:**
   ```bash
   git push origin main
   ```
   Railway automatically redeploys!

4. **Troubleshoot:**
   - Check Railway logs
   - Verify environment variables
   - Check requirements.txt

---

## 💡 **Tips**

- **Free tier:** Limited resources, but works fine for testing
- **Custom domain:** Go to Settings → Domain to add your own domain
- **Environment:** Railway automatically detects Python/FastAPI
- **Auto-redeploy:** Every `git push` triggers new deployment
- **Logs:** Always check logs if something goes wrong

---

## 🆘 **Need Help?**

**Check logs first:**
1. Railway Dashboard → Logs tab
2. Look for error messages
3. Search for specific error

**Common fixes:**
- Missing environment variable → Add to Variables
- Module not found → Add to requirements.txt
- Port conflict → Railway handles this automatically
- API timeout → Check internet connection on Railway

---

## 🚀 **You're Deployed!**

Your QADS app is now live on the internet! 🎉

Share the URL and let people use your AI chatbot!

---

**Questions?** Check the logs or refer to SETUP.md for more details.
