# main.py
import os
import sys
import json
import requests
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, Path
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
SERP_API_KEY = os.getenv("SERP_API_KEY")

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
pdf_paths = config.get_all_pdf_paths(BOOKS_FOLDER_PATH)
print(f"\n{'='*60}")
print(f"QADS Chatbot initialized!")
print(f"Total PDFs available: {len(pdf_paths)}")
print(f"{'='*60}\n")

if pdf_paths:
    try:
        print(f"\n[LOG] Ingesting {len(pdf_paths)} PDFs into Pinecone...")
        embeddings_client = get_clients()
        setup_vector_store(embeddings_client, pdf_paths, INGEST_LOG)
        print("[LOG] PDFs ingested successfully!")
    except Exception as e:
        print(f"[WARNING] Could not ingest PDFs: {e}")
else:
    print("[WARNING] No PDF files found in books_pdfs folder")


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
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    hashed_password = pwd_context.hash(user.password)
    
    # Save user
    users[user.username] = {"password": hashed_password, "created_at": str(datetime.now())}
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
    
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    stored_hash = users[user.username]["password"]
    
    if not pwd_context.verify(user.password, stored_hash):
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
        embeddings_client = get_clients()
        context = retrieve_context(embeddings_client, message.query, index_name=config.PINECONE_INDEX_NAME)
        
        # If no context from PDFs, use SerpAPI for web search
        if not context or context.strip() == "":
            print(f"[LOG] No context found in PDFs for query: {message.query}")
            print("[LOG] Attempting web search via SerpAPI...")
            try:
                from google_search_results import GoogleSearch
                params = {"q": message.query, "api_key": SERP_API_KEY}
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
        response = generate_llm_response(groq_client, message.query, context)
        
        # Save chat to history
        threads_file = THREADS_FILE_TMPL.format(username=message.username)
        thread_id = message.thread_id or f"thread_{int(datetime.now().timestamp())}"
        
        if os.path.exists(threads_file):
            with open(threads_file, "r") as f:
                threads = json.load(f)
        else:
            threads = {}
        
        if thread_id not in threads:
            threads[thread_id] = []
        
        threads[thread_id].append({
            "timestamp": str(datetime.now()),
            "query": message.query,
            "response": response,
            "context_used": context[:200]  # Store first 200 chars of context
        })
        
        with open(threads_file, "w") as f:
            json.dump(threads, f, indent=4)
        
        return {
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


@app.get("/history/{username}")
async def get_history(username: str, thread_id: Optional[str] = None):
    """Retrieve chat history for a user"""
    threads_file = THREADS_FILE_TMPL.format(username=username)
    
    if not os.path.exists(threads_file):
        return {"threads": {}}
    
    with open(threads_file, "r") as f:
        threads = json.load(f)
    
    if thread_id:
        return {"thread_id": thread_id, "messages": threads.get(thread_id, [])}
    
    return {"threads": threads}


@app.post("/chat/thread/{username}")
async def create_thread(username: str):
    """Create a new chat thread"""
    threads_file = THREADS_FILE_TMPL.format(username=username)
    
    if os.path.exists(threads_file):
        with open(threads_file, "r") as f:
            threads = json.load(f)
    else:
        threads = {}
    
    thread_id = f"thread_{int(datetime.now().timestamp())}"
    threads[thread_id] = []
    
    with open(threads_file, "w") as f:
        json.dump(threads, f, indent=4)
    
    return {"thread_id": thread_id, "created_at": str(datetime.now())}


@app.delete("/chat/thread/{username}/{thread_id}")
async def delete_thread(username: str, thread_id: str):
    """Delete a chat thread"""
    threads_file = THREADS_FILE_TMPL.format(username=username)
    
    if not os.path.exists(threads_file):
        raise HTTPException(status_code=404, detail="No threads found")
    
    with open(threads_file, "r") as f:
        threads = json.load(f)
    
    if thread_id not in threads:
        raise HTTPException(status_code=404, detail="Thread not found")
    
    del threads[thread_id]
    
    with open(threads_file, "w") as f:
        json.dump(threads, f, indent=4)
    
    return {"message": "Thread deleted", "thread_id": thread_id}


@app.get("/pdfs")
async def get_pdf_list():
    """Get list of available PDFs"""
    pdf_paths = config.get_all_pdf_paths(BOOKS_FOLDER_PATH)
    pdf_names = [os.path.basename(path) for path in pdf_paths]
    return {"count": len(pdf_names), "pdfs": pdf_names}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
