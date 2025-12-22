# main.py
import os
import sys
import json
import requests
import bcrypt
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, Path, Body
from fastapi.staticfiles import StaticFiles
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

# Legacy single-history path (kept for migration)
LEGACY_HISTORY_FILE_TMPL = os.path.join(HISTORY_DIR, "history_{username}.json")

# New threads storage per user
THREADS_FILE_TMPL = os.path.join(HISTORY_DIR, "threads_{username}.json")

# Track which files were ingested already
INGEST_LOG = os.path.join(DATA_DIR, "ingested_files.json")
if not os.path.exists(INGEST_LOG):
    with open(INGEST_LOG, "w") as f:
        json.dump({}, f)

# FastAPI setup
app = FastAPI(title="QADS Chatbot API", version="2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Preload PDFs into vector store on startup
print(f"\n{'='*60}")
print(f"QADS Chatbot initialized!")
print(f"{'='*60}\n")

try:
    print(f"\n[LOG] Ingesting PDFs from {BOOKS_FOLDER_PATH}...")
    chunks = load_and_chunk_pdfs(BOOKS_FOLDER_PATH)
    
    print(f"[LOG] Generated {len(chunks)} chunks. Setting up vector store...")
    cohere_client, pinecone_client = get_clients()
    setup_vector_store(chunks, cohere_client, pinecone_client)
    print("[LOG] Vector store setup complete!")

except Exception as e:
    print(f"[WARNING] Could not setup vector store: {e}")


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

# ==================== HELPERS ====================

def get_threads_path(username):
    return THREADS_FILE_TMPL.format(username=username)

def load_threads(username):
    path = get_threads_path(username)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            data = json.load(f)
            # Migration check: if values are lists, convert to objects
            new_data = {}
            for tid, val in data.items():
                if isinstance(val, list):
                    new_data[tid] = {
                        "id": tid,
                        "title": "New Chat",
                        "created_at": str(datetime.now()),
                        "updated_at": str(datetime.now()),
                        "messages": val
                    }
                else:
                    new_data[tid] = val
            return new_data
    except Exception:
        return {}

def save_threads(username, threads):
    path = get_threads_path(username)
    with open(path, "w") as f:
        json.dump(threads, f, indent=4)


# ==================== API ENDPOINTS ====================

@app.get("/")
async def root():
    """Root endpoint - returns API info"""
    return {
        "message": "QADS Chatbot API",
        "version": "2.0",
        "endpoints": {
            "chat": "/chat",
            "register": "/register",
            "login": "/login"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok"}


# ==================== AUTHENTICATION ====================

class User(BaseModel):
    """User registration/login schema"""
    username: str
    password: str


@app.post("/register")
async def register(user: User):
    """Register a new user"""
    if not user.username or not user.password:
        raise HTTPException(status_code=400, detail="Username and password required")
    
    # Load existing users
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
    else:
        users = {}
    
    # Check if user exists
    if user.username in users:
        raise HTTPException(status_code=409, detail="User already exists")
    
    # Hash password
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt())
    
    # Save user
    users[user.username] = {"password": hashed_password.decode('utf-8'), "created_at": str(datetime.now())}
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)
    
    return {"message": "User registered successfully", "username": user.username}


@app.post("/login")
async def login(user: User):
    """Authenticate user"""
    if not os.path.exists(USERS_FILE):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    with open(USERS_FILE, "r") as f:
        users = json.load(f)
    
    if user.username not in users:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    stored_hash = users[user.username]["password"]
    
    if not bcrypt.checkpw(user.password.encode('utf-8'), stored_hash.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    return {
        "message": "Login successful",
        "username": user.username,
        "token": user.username  # Simplified token
    }


# ==================== CHAT ENDPOINTS ====================

class ChatMessage(BaseModel):
    """Chat message schema"""
    username: str
    query: str
    thread_id: Optional[str] = None


@app.post("/api/chat")
@app.post("/chat")
async def chat_endpoint(message: ChatMessage):
    """Chat endpoint - handles Q&A with context retrieval"""
    try:
        # Validate user exists
        if not os.path.exists(USERS_FILE):
            raise HTTPException(status_code=401, detail="User not found")
        
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
        
        if message.username not in users:
            raise HTTPException(status_code=401, detail="User not found")
        
        # Get context from vector store
        context = ""
        try:
            cohere_client, pinecone_client = get_clients()
            index = pinecone_client.Index(config.PINECONE_INDEX_NAME)
            context_list = retrieve_context(message.query, cohere_client, index)
            context = "\n\n".join(context_list) if context_list else ""
        except Exception as e:
            print(f"[WARNING] Vector store retrieval failed: {e}")
            context = ""
        
        # If no context from PDFs, use SerpAPI for web search
        if not context or context.strip() == "":
            print(f"[LOG] No context found in PDFs for query: {message.query}")
            print("[LOG] Attempting web search via SerpAPI...")
            try:
                from google_search_results import GoogleSearch
                params = {"q": message.query, "api_key": SERPAPI_API_KEY}
                search = GoogleSearch(params)
                results = search.get_dict()
                if "organic_results" in results:
                    context = " ".join([result.get("snippet", "") for result in results["organic_results"][:3]])
                    print(f"[LOG] Found web context: {context[:100]}...")
                else:
                    context = "No information found"
            except Exception as e:
                print(f"[LOG] Web search failed: {e}")
                context = "No information found"
        
        # Generate response using LLM
        groq_client = get_groq_client()
        chat_history = [{"role": "user", "content": message.query}]
        response_generator = generate_llm_response(chat_history, context, groq_client)
        
        response = ""
        for chunk in response_generator:
            response += chunk
        
        # Save chat to history
        threads = load_threads(message.username)
        thread_id = message.thread_id or f"thread_{int(datetime.now().timestamp())}"
        
        if thread_id not in threads:
            threads[thread_id] = {
                "id": thread_id,
                "title": message.query[:30],
                "created_at": str(datetime.now()),
                "updated_at": str(datetime.now()),
                "messages": []
            }
        
        # Append user message
        threads[thread_id]["messages"].append({
            "role": "user",
            "content": message.query,
            "ts": str(datetime.now())
        })
        
        # Append assistant message
        threads[thread_id]["messages"].append({
            "role": "assistant",
            "content": response,
            "ts": str(datetime.now()),
            "context_used": context[:200]
        })
        
        threads[thread_id]["updated_at"] = str(datetime.now())
        save_threads(message.username, threads)
        
        return {
            "ok": True,
            "response": response,
            "context_used": context[:200],
            "thread_id": thread_id,
            "timestamp": str(datetime.now())
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Chat error: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


# ==================== THREADS API ====================

@app.get("/api/threads")
async def list_threads(username: str):
    threads = load_threads(username)
    # Convert dict to list and sort by updated_at desc
    thread_list = list(threads.values())
    # thread_list.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return {"ok": True, "threads": thread_list}

@app.post("/api/threads")
async def create_thread_api(payload: ThreadCreate):
    threads = load_threads(payload.username)
    thread_id = f"thread_{int(datetime.now().timestamp())}"
    
    new_thread = {
        "id": thread_id,
        "title": payload.title,
        "created_at": str(datetime.now()),
        "updated_at": str(datetime.now()),
        "messages": []
    }
    
    threads[thread_id] = new_thread
    save_threads(payload.username, threads)
    
    return {"ok": True, "thread": new_thread}

@app.get("/api/threads/{thread_id}")
async def get_thread(thread_id: str, username: str):
    threads = load_threads(username)
    if thread_id not in threads:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"ok": True, "thread": threads[thread_id]}

@app.patch("/api/threads/{thread_id}")
async def rename_thread(thread_id: str, payload: ThreadUpdate):
    threads = load_threads(payload.username)
    if thread_id not in threads:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    threads[thread_id]["title"] = payload.title
    threads[thread_id]["updated_at"] = str(datetime.now())
    save_threads(payload.username, threads)
    
    return {"ok": True, "thread": threads[thread_id]}

@app.delete("/api/threads/{thread_id}")
async def delete_thread_api(thread_id: str, username: str):
    threads = load_threads(username)
    if thread_id in threads:
        del threads[thread_id]
        save_threads(username, threads)
    return {"ok": True}

@app.post("/api/threads/{thread_id}/sync")
async def sync_thread(thread_id: str, payload: ThreadSync):
    threads = load_threads(payload.username)
    if thread_id not in threads:
        threads[thread_id] = {
            "id": thread_id,
            "title": "Synced Chat",
            "created_at": str(datetime.now()),
            "updated_at": str(datetime.now()),
            "messages": []
        }
    
    # Sync messages from client
    new_msgs = []
    for m in payload.messages:
        role = "assistant" if m.get("role") == "bot" else "user"
        content = m.get("text")
        ts = m.get("ts")
        new_msgs.append({"role": role, "content": content, "ts": ts})
        
    threads[thread_id]["messages"] = new_msgs
    threads[thread_id]["updated_at"] = str(datetime.now())
    save_threads(payload.username, threads)
    
    return {"ok": True, "thread": threads[thread_id]}



@app.get("/pdfs")
async def get_pdf_list():
    """Get list of available PDFs"""
    pdf_paths = config.get_all_pdf_paths(BOOKS_FOLDER_PATH)
    pdf_names = [os.path.basename(path) for path in pdf_paths]
    return {"count": len(pdf_names), "pdfs": pdf_names}


# Mount frontend static files
# Go up one level from backend/ to find frontend/
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")

if os.path.exists(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
