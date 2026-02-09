# main.py
import os
import sys
import json
import bcrypt
import threading
import time
from datetime import datetime
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
os.makedirs(DATA_DIR, exist_ok=True)
USERS_FILE = os.path.join(DATA_DIR, "users.json")
HISTORY_DIR = os.path.join(DATA_DIR, "history")
os.makedirs(HISTORY_DIR, exist_ok=True)
THREADS_FILE_TMPL = os.path.join(HISTORY_DIR, "threads_{username}.json")

app = FastAPI(title="QADS Chatbot API", version="2.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "../frontend")

# ------------------ Frontend Routes ------------------

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.head("/")
def head_index():
    return Response(status_code=200)

@app.get("/index.html")
def serve_index_alias():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

@app.get("/chat.html")
def serve_chat():
    return FileResponse(os.path.join(FRONTEND_DIR, "chat.html"))

@app.get("/login.html")
def serve_login():
    return FileResponse(os.path.join(FRONTEND_DIR, "login.html"))

@app.get("/instruction.html")
def serve_instruction():
    return FileResponse(os.path.join(FRONTEND_DIR, "instruction.html"))

# Serve static exactly as frontend expects: /static/js/*, /static/css/*
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# Favicon (supports both .ico and .svg)
@app.get("/favicon.ico")
def favicon():
    ico = os.path.join(FRONTEND_DIR, "favicon.ico")
    svg = os.path.join(FRONTEND_DIR, "favicon.svg")
    if os.path.exists(ico):
        return FileResponse(ico)
    if os.path.exists(svg):
        return FileResponse(svg)
    raise HTTPException(status_code=404)

# ------------------ Middleware ------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------ Vector Store (load ONCE) ------------------

VECTOR_READY = False

def background_ingest_once():
    global VECTOR_READY
    try:
        print(f"[LOG] Ingesting PDFs from {BOOKS_FOLDER_PATH} (startup only)...")
        chunks = load_and_chunk_pdfs(BOOKS_FOLDER_PATH)
        print(f"[LOG] Generated {len(chunks)} chunks. Setting up vector store...")
        cohere_client, pinecone_client = get_clients()
        setup_vector_store(chunks, cohere_client, pinecone_client)
        VECTOR_READY = True
        print("[LOG] Vector store ready ✅")
    except Exception as e:
        print(f"[WARNING] Vector store setup failed: {e}")
        VECTOR_READY = False

@app.on_event("startup")
def startup_event():
    threading.Thread(target=background_ingest_once, daemon=True).start()

# ------------------ Health ------------------

@app.get("/health")
async def health_check():
    return {"status": "ok", "vector_ready": VECTOR_READY}

# ==================== MODELS ====================

class ThreadCreate(BaseModel):
    username: str
    title: Optional[str] = "New Chat"

class ThreadSync(BaseModel):
    username: str
    messages: List[dict]

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

# ==================== AUTH ====================

@app.post("/register")
async def register(user: User):
    users = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            users = json.load(f)

    if user.username in users:
        raise HTTPException(status_code=409, detail="User already exists")

    hashed_password = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode()
    users[user.username] = {"password": hashed_password, "created_at": str(datetime.now())}

    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

    return {"ok": True, "username": user.username}

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

    return {"ok": True, "username": user.username, "token": user.username}

# ==================== CHAT (FAST PATH) ====================

@app.post("/api/chat")
@app.post("/chat")
async def chat_endpoint(message: ChatMessage):
    context = ""

    # Fast, non-blocking retrieval (skip if vector not ready)
    if VECTOR_READY:
        try:
            start = time.time()
            cohere_client, pinecone_client = get_clients()
            index = pinecone_client.Index(config.PINECONE_INDEX_NAME)
            ctx_list = retrieve_context(message.query, cohere_client, index)
            context = "\n\n".join(ctx_list) if ctx_list else ""
            print(f"[LOG] Context retrieval took {time.time() - start:.2f}s")
        except Exception as e:
            print(f"[WARNING] Vector retrieval failed: {e}")
            context = ""

    groq_client = get_groq_client()
    try:
        chunks = list(generate_llm_response(
            [{"role": "user", "content": message.query}],
            context,
            groq_client
        ))
        response = "".join(chunks).strip()
    except Exception as e:
        print(f"[ERROR] LLM failed: {e}")
        response = ""

    if not response:
        response = "The AI service is currently slow. Please try again in a few seconds."

    threads = load_threads(message.username)
    thread_id = message.thread_id or f"thread_{int(datetime.now().timestamp())}"

    threads.setdefault(thread_id, {
        "id": thread_id,
        "title": message.query[:30],
        "created_at": str(datetime.now()),
        "updated_at": str(datetime.now()),
        "messages": []
    })

    threads[thread_id]["messages"].extend([
        {"role": "user", "content": message.query, "ts": str(datetime.now())},
        {"role": "assistant", "content": response, "ts": str(datetime.now())}
    ])
    threads[thread_id]["updated_at"] = str(datetime.now())
    save_threads(message.username, threads)

    return {"ok": True, "response": response, "thread_id": thread_id}

# ==================== THREADS ====================

@app.get("/api/threads")
async def list_threads(username: str = Query(...)):
    return {"ok": True, "threads": list(load_threads(username).values())}

@app.get("/api/threads/{thread_id}")
async def get_thread(thread_id: str, username: str = Query(...)):
    threads = load_threads(username)
    if thread_id not in threads:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"ok": True, "thread": threads[thread_id]}

@app.post("/api/threads")
async def create_thread_api(payload: ThreadCreate):
    threads = load_threads(payload.username)
    tid = f"thread_{int(datetime.now().timestamp())}"
    threads[tid] = {
        "id": tid,
        "title": payload.title or "New Chat",
        "created_at": str(datetime.now()),
        "updated_at": str(datetime.now()),
        "messages": []
    }
    save_threads(payload.username, threads)
    return {"ok": True, "thread": threads[tid]}

@app.post("/api/threads/{thread_id}/sync")
async def sync_thread(thread_id: str, payload: ThreadSync, username: str = Query(...)):
    threads = load_threads(username)
    threads.setdefault(thread_id, {
        "id": thread_id,
        "title": "Synced Chat",
        "created_at": str(datetime.now()),
        "updated_at": str(datetime.now()),
        "messages": []
    })
    threads[thread_id]["messages"] = payload.messages
    threads[thread_id]["updated_at"] = str(datetime.now())
    save_threads(username, threads)
    return {"ok": True, "thread": threads[thread_id]}

@app.delete("/api/threads/{thread_id}")
async def delete_thread_api(thread_id: str, username: str = Query(...)):
    threads = load_threads(username)
    if thread_id in threads:
        del threads[thread_id]
        save_threads(username, threads)
        return {"ok": True}
    raise HTTPException(status_code=404, detail="Thread not found")

# ==================== RUN ====================

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
