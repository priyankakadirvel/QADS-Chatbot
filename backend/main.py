# main.py
import os
import sys
import json
import requests
import bcrypt
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Local imports
from config import config
from utils.pdf_processor import load_and_chunk_pdfs
from models.embeddings import get_clients, setup_vector_store, retrieve_context
from models.llm import get_groq_client, generate_llm_response

# ------------------ Setup ------------------
BOOKS_FOLDER_PATH = config.BOOKS_FOLDER_PATH
load_dotenv()
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")

# File paths
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
USERS_FILE = os.path.join(DATA_DIR, "users.json")
HISTORY_DIR = os.path.join(DATA_DIR, "history")
os.makedirs(HISTORY_DIR, exist_ok=True)

THREADS_FILE_TMPL = os.path.join(HISTORY_DIR, "threads_{username}.json")

INGEST_LOG = os.path.join(DATA_DIR, "ingested_files.json")
if not os.path.exists(INGEST_LOG):
    with open(INGEST_LOG, "w") as f:
        json.dump({}, f)

# FastAPI setup
app = FastAPI(title="QADS Chatbot API", version="2.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "../frontend")

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ Startup (Render-safe) ------------------
IS_RENDER = os.getenv("RENDER") == "true"

print(f"\n{'='*60}")
print("QADS Chatbot starting...")
print(f"Running on Render: {IS_RENDER}")
print(f"{'='*60}\n")

if not IS_RENDER:
    try:
        print(f"[LOG] Ingesting PDFs from {BOOKS_FOLDER_PATH}...")
        chunks = load_and_chunk_pdfs(BOOKS_FOLDER_PATH)
        print(f"[LOG] Generated {len(chunks)} chunks. Setting up vector store...")
        cohere_client, pinecone_client = get_clients()
        setup_vector_store(chunks, cohere_client, pinecone_client)
        print("[LOG] Vector store setup complete!")
    except Exception as e:
        print(f"[WARNING] Could not setup vector store: {e}")
else:
    print("[INFO] Skipping PDF ingestion on Render startup (free tier safe mode).")

# ==================== MODELS ====================

class ThreadCreate(BaseModel):
    username: str
    title: Optional[str] = "New Chat"

class ThreadUpdate(BaseModel):
    username: str
    title: str

class ThreadSync(BaseModel):
    username: str
    session_id: str
    messages: list

class User(BaseModel):
    username: str
    password: str

class ChatMessage(BaseModel):
    username: str
    query: str
    thread_id: Optional[str] = None

# ==================== HELPERS ====================

def get_threads_path(username):
    return THREADS_FILE_TMPL.format(username=username)

def load_threads(username):
    path = get_threads_path(username)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_threads(username, threads):
    path = get_threads_path(username)
    with open(path, "w") as f:
        json.dump(threads, f, indent=4)

# ==================== ROUTES ====================

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.post("/register")
async def register(user: User):
    users = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            users = json.load(f)

    if user.username in users:
        raise HTTPException(status_code=409, detail="User already exists")

    hashed_password = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode()
    users[user.username] = {"password": hashed_password}

    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

    return {"ok": True}

@app.post("/login")
async def login(user: User):
    if not os.path.exists(USERS_FILE):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    with open(USERS_FILE, "r") as f:
        users = json.load(f)

    if user.username not in users:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not bcrypt.checkpw(user.password.encode(), users[user.username]["password"].encode()):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return {"ok": True, "username": user.username}

@app.post("/api/chat")
async def chat_endpoint(message: ChatMessage):
    return {"ok": True, "response": "Backend is live 🎉", "thread_id": "demo"}

# ==================== RUN ====================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
