# main.py
import os
import json
import requests
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

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

# Vector DB
index = None


@app.on_event("startup")
async def startup_event():
    """
    Load PDFs only if not already ingested.
    """
    global index
    print("Starting QADS server...")
    try:
        cohere_client, pinecone_client = get_clients()
        chunks = load_and_chunk_pdfs(BOOKS_FOLDER_PATH)
        index = setup_vector_store(chunks, cohere_client, pinecone_client)
        print("Ingestion complete. Vector DB ready.")
    except Exception as e:
        print(f"[Startup Error]: {e}")


# ------------------ Utility functions ------------------
def load_json(path: str):
    return json.load(open(path)) if os.path.exists(path) else {}


def save_json(path: str, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)


def load_users():
    return load_json(USERS_FILE)


def save_users(users: dict):
    save_json(USERS_FILE, users)


# Legacy single-history helpers (for migration only)
def get_user_legacy_history_path(username: str) -> str:
    return LEGACY_HISTORY_FILE_TMPL.format(username=username)


def load_legacy_history(username: str):
    p = get_user_legacy_history_path(username)
    return json.load(open(p)) if os.path.exists(p) else []


# Threads helpers

def get_user_threads_path(username: str) -> str:
    return THREADS_FILE_TMPL.format(username=username)


def load_threads(username: str):
    p = get_user_threads_path(username)
    return json.load(open(p)) if os.path.exists(p) else []


def save_threads(username: str, threads: list):
    p = get_user_threads_path(username)
    save_json(p, threads)


def migrate_history_to_threads(username: str) -> list:
    """Migrate legacy flat history into a single thread if threads are empty and legacy exists."""
    threads = load_threads(username)
    if threads:
        return threads
    legacy = load_legacy_history(username)
    if not legacy:
        return []
    # Build a single thread from legacy
    # Legacy entries: {role: 'user'|'assistant', content: str, ts: iso}
    first_user = next((m for m in legacy if m.get("role") == "user" and m.get("content")), None)
    title = (first_user.get("content", "New chat")[:60] + ("…" if len(first_user.get("content", "")) > 60 else "")) if first_user else "New chat"
    now = datetime.utcnow().isoformat() + "Z"
    thread = {
        "id": f"t_{int(datetime.utcnow().timestamp())}",
        "title": title or "New chat",
        "createdAt": legacy[0].get("ts", now) if legacy else now,
        "updatedAt": legacy[-1].get("ts", now) if legacy else now,
        "messages": legacy,
    }
    save_threads(username, [thread])
    return [thread]


# ------------------ Pydantic models ------------------
class UserAuth(BaseModel):
    username: str
    password: str


class ChatRequest(BaseModel):
    username: str
    prompt: str
    thread_id: Optional[str] = None
    session_id: Optional[str] = None


class CreateThreadRequest(BaseModel):
    username: str
    title: Optional[str] = None


class RenameThreadRequest(BaseModel):
    username: str
    title: str


class SyncThreadRequest(BaseModel):
    username: str
    session_id: Optional[str] = None
    messages: list


# ------------------ Auth endpoints ------------------
@app.post("/api/signup")
async def signup(user: UserAuth):
    users = load_users()
    if user.username in users:
        raise HTTPException(status_code=400, detail="User already exists")
    users[user.username] = {"password": user.password}
    save_users(users)
    return {"ok": True, "message": "Signup successful"}


@app.post("/api/login")
async def login(user: UserAuth):
    users = load_users()
    if user.username not in users or users[user.username]["password"] != user.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"ok": True, "message": "Login successful"}


# ------------------ Threads endpoints ------------------
@app.get("/api/threads")
async def list_threads(username: str = Query(...)):
    threads = migrate_history_to_threads(username) or []
    # Minimal info + preview
    items = []
    for t in threads:
        last_msg = t.get("messages", [])[-1] if t.get("messages") else None
        preview_src = next((m for m in reversed(t.get("messages", [])) if m.get("content")), None)
        preview = (preview_src.get("content", "")[:60] + ("…" if preview_src and len(preview_src.get("content", "")) > 60 else "")) if preview_src else ""
        items.append({
            "id": t.get("id"),
            "title": t.get("title", "New chat"),
            "createdAt": t.get("createdAt"),
            "updatedAt": t.get("updatedAt"),
            "lastTs": (last_msg or {}).get("ts", t.get("updatedAt")),
            "preview": preview,
        })
    # Sort most recent first
    items.sort(key=lambda x: x.get("updatedAt") or "", reverse=True)
    return {"ok": True, "threads": items}


@app.post("/api/threads")
async def create_thread(req: CreateThreadRequest):
    threads = load_threads(req.username)
    now = datetime.utcnow().isoformat() + "Z"
    new_thread = {
        "id": f"t_{int(datetime.utcnow().timestamp()*1000)}",
        "title": (req.title or "New chat").strip() or "New chat",
        "createdAt": now,
        "updatedAt": now,
        "messages": []
    }
    threads.append(new_thread)
    save_threads(req.username, threads)
    return {"ok": True, "thread": new_thread}


@app.get("/api/threads/{thread_id}")
async def get_thread(thread_id: str = Path(...), username: str = Query(...)):
    threads = load_threads(username)
    t = next((x for x in threads if x.get("id") == thread_id), None)
    if not t:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"ok": True, "thread": t}


@app.patch("/api/threads/{thread_id}")
async def rename_thread(thread_id: str = Path(...), username: str = Query(...), req: RenameThreadRequest = None):
    if not req or not req.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")
    threads = load_threads(username)
    found = False
    for t in threads:
        if t.get("id") == thread_id:
            t["title"] = req.title.strip()
            t["updatedAt"] = datetime.utcnow().isoformat() + "Z"
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail="Thread not found")
    save_threads(username, threads)
    return {"ok": True}


@app.delete("/api/threads/{thread_id}")
async def delete_thread(thread_id: str = Path(...), username: str = Query(...)):
    threads = load_threads(username)
    new_threads = [t for t in threads if t.get("id") != thread_id]
    if len(new_threads) == len(threads):
        raise HTTPException(status_code=404, detail="Thread not found")
    save_threads(username, new_threads)
    return {"ok": True}


@app.post("/api/threads/{thread_id}/sync")
async def sync_thread(thread_id: str = Path(...), username: str = Query(...), req: SyncThreadRequest = None):
    """Merge client messages into server thread.
    - Server remains source of truth
    - Deduplicate by (role, content, ts)
    """
    if not req or not isinstance(req.messages, list):
        raise HTTPException(status_code=400, detail="messages list required")

    threads = load_threads(username)
    thread = next((t for t in threads if t.get("id") == thread_id), None)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    server_msgs = thread.get("messages", [])

    # Normalize incoming messages: frontend uses 'bot' vs 'user'
    def to_server_msg(m):
        role = m.get("role")
        if role == "bot":
            role = "assistant"
        elif role == "assistant":
            role = "assistant"
        else:
            role = "user"
        return {
            "role": role,
            "content": m.get("text") if m.get("text") is not None else m.get("content"),
            "ts": m.get("ts"),
        }

    client_msgs = [to_server_msg(m) for m in req.messages if (m.get("text") or m.get("content")) and m.get("ts")]

    def key(m):
        return (m.get("role"), m.get("content"), m.get("ts"))

    server_set = {key(m) for m in server_msgs}

    # Append only client messages that are not already in server
    new_msgs = [m for m in client_msgs if key(m) not in server_set]
    if new_msgs:
        # Merge and sort by timestamp
        merged = server_msgs + new_msgs
        merged.sort(key=lambda x: x.get("ts") or "")
        thread["messages"] = merged
        # Update updatedAt as max ts
        max_ts = max((m.get("ts") or "" for m in merged), default=datetime.utcnow().isoformat() + "Z")
        thread["updatedAt"] = max_ts
        save_threads(username, threads)

    return {"ok": True, "thread": thread}


# ------------------ Legacy history endpoints (kept for compatibility) ------------------
@app.get("/api/history")
async def get_history(username: str = Query(...)):
    threads = migrate_history_to_threads(username)
    # Return flat messages of the most recent thread for compatibility
    if not threads:
        return {"ok": True, "messages": []}
    threads.sort(key=lambda t: t.get("updatedAt") or "", reverse=True)
    return {"ok": True, "messages": threads[0].get("messages", [])}


@app.delete("/api/history")
async def clear_history(username: str = Query(...)):
    # Clear all threads
    save_threads(username, [])
    return {"ok": True, "message": "History cleared"}


# ------------------ Web search helper ------------------
def search_serpapi(query: str) -> str:
    if not SERP_API_KEY:
        return "Web search unavailable (SERP_API_KEY not configured)."
    params = {"q": query, "api_key": SERP_API_KEY, "engine": "google", "num": 3}
    try:
        resp = requests.get("https://serpapi.com/search", params=params)
        if resp.status_code != 200:
            return "Web search failed."
        data = resp.json()
        snippets = []
        for res in data.get("organic_results", []):
            title = res.get("title", "")
            link = res.get("link", "")
            snippet = res.get("snippet", "")
            snippets.append(f"{title}\n{snippet}\n{link}")
        return "\n\n".join(snippets) if snippets else "No relevant web results found."
    except Exception as e:
        return f"SerpAPI request error: {e}"


# ------------------ Chat endpoint ------------------
@app.post("/api/chat")
async def chat(req: ChatRequest):
    global index
    if not req.prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required")
    if index is None:
        raise HTTPException(status_code=503, detail="Vector store not ready")

    cohere_client, _ = get_clients()
    groq_client = get_groq_client()

    # Load threads and resolve thread
    threads = load_threads(req.username)

    # Create a new thread if none provided
    # Auto-title threads from the first user message (ChatGPT-like)
    def _title_from_prompt(text: str) -> str:
        t = (text or "").strip()
        if not t:
            return "New chat"
        return (t[:60] + ("…" if len(t) > 60 else ""))

    if not req.thread_id:
        now = datetime.utcnow().isoformat() + "Z"
        new_thread = {
            "id": f"t_{int(datetime.utcnow().timestamp()*1000)}",
            "title": _title_from_prompt(req.prompt),
            "createdAt": now,
            "updatedAt": now,
            "messages": []
        }
        threads.append(new_thread)
        save_threads(req.username, threads)
        thread = new_thread
    else:
        thread = next((t for t in threads if t.get("id") == req.thread_id), None)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

    # Build LLM history from the thread
    user_history = thread.get("messages", [])
    llm_history = [{"role": ("assistant" if m.get("role") == "assistant" else "user"), "content": m.get("content")} for m in user_history]
    llm_history.append({"role": "user", "content": req.prompt})

    # Try vector DB context
    context = retrieve_context(req.prompt, cohere_client, index)
    context_source = "vector_db"
    if not context:
        context_source = "serpapi"
        print("No vector DB context found, using SerpAPI...")
        context = search_serpapi(req.prompt)

    # Generate response (streaming collected to a string)
    response_text = "".join([chunk or "" for chunk in generate_llm_response(llm_history, context, groq_client)])

    # Save messages to the thread (and ensure title is set if this was the first message)
    now = datetime.utcnow().isoformat() + "Z"
    was_empty = len(thread.get("messages", [])) == 0
    thread.setdefault("messages", []).append({"role": "user", "content": req.prompt, "ts": now})
    thread["messages"].append({"role": "assistant", "content": response_text, "ts": now})
    if was_empty and (not thread.get("title") or thread.get("title") == "New chat"):
        thread["title"] = _title_from_prompt(req.prompt)
    thread["updatedAt"] = now
    save_threads(req.username, threads)

    return {"ok": True, "response": response_text, "context_source": context_source, "ts": now, "thread_id": thread.get("id")}
