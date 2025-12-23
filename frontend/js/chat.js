import { userId, username } from "./auth.js";



document.addEventListener('DOMContentLoaded', () => {
    const chatInput = document.getElementById('chat-input');
    const chatForm = document.getElementById('chat-input-form');
    const chatMessages = document.getElementById('chat-messages');
    const newChatBtn = document.getElementById('new-chat-btn');

    if (!userId) {
        window.location.href = 'login.html';
        return;
    }

    // Set username in welcome bar
    const welcomeUsername = document.getElementById('welcome-username');
    if (welcomeUsername && username) {
        welcomeUsername.textContent = username;
    }

    // -------- Config --------
    // If your backend runs on a different port/host, change BASE accordingly.
    // Auto-detect: if served from backend (port 8000 or https), use relative path.
    // Otherwise (e.g. live server on 5500), use localhost:8000.
    const BASE = (window.location.port === '8000' || window.location.protocol === 'https:') 
        ? '' 
        : 'http://127.0.0.1:8000';

    function getAuthUser() {
        if (username) return username;
        try {
            const u = JSON.parse(localStorage.getItem("chatbot_user") || '{}').username;
            if (u) return u;
        } catch {}
        const w = document.getElementById('welcome-username');
        if (w && w.textContent) return w.textContent.trim();
        return null;
    }

    // -------- Session handling --------
    const SESSION_KEY = (u) => `qads_session_id_${u}`;
    function getSessionId() {
        let sid = localStorage.getItem(SESSION_KEY(username));
        if (!sid) {
            // Simple UUIDv4 generator
            sid = ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
                (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
            );
            localStorage.setItem(SESSION_KEY(username), sid);
        }
        return sid;
    }
    const sessionId = getSessionId();

    // -------- Persistence of active thread id --------
    const ACTIVE_THREAD_KEY = (u) => `qads_active_thread_${u}`;
    function getActiveThreadId() {
        return localStorage.getItem(ACTIVE_THREAD_KEY(username));
    }
    function setActiveThreadId(id) {
        if (!id) return localStorage.removeItem(ACTIVE_THREAD_KEY(username));
        localStorage.setItem(ACTIVE_THREAD_KEY(username), id);
    }

    // -------- LocalStorage Chat History --------
    const HISTORY_KEY = (u) => `qads_chat_history_${u}`;

    function getFullHistory() {
        try {
            const raw = localStorage.getItem(HISTORY_KEY(username));
            return raw ? JSON.parse(raw) : {};
        } catch (e) {
            console.error("Failed to parse chat history:", e);
            return {};
        }
    }

    function saveFullHistory(history) {
        try {
            localStorage.setItem(HISTORY_KEY(username), JSON.stringify(history));
        } catch (e) {
            console.error("Failed to save chat history:", e);
        }
    }

    function getThreadHistory(threadId) {
        if (!threadId) return [];
        const history = getFullHistory();
        return history[threadId] || [];
    }

    function saveThreadHistory(threadId, messages) {
        if (!threadId) return;
        const history = getFullHistory();
        history[threadId] = messages;
        saveFullHistory(history);
    }

    function addMessageToHistory(threadId, message) {
        if (!threadId) return;
        const history = getFullHistory();
        if (!history[threadId]) {
            history[threadId] = [];
        }
        history[threadId].push(message);
        saveFullHistory(history);
    }

    function removeThreadHistory(threadId) {
        if (!threadId) return;
        const history = getFullHistory();
        delete history[threadId];
        saveFullHistory(history);
    }

    // -------- API helpers --------
    async function apiListThreads() {
        const user = getAuthUser();
        if (!user) throw new Error("User not identified");
        const r = await fetch(`${BASE}/api/threads?username=${encodeURIComponent(user)}`);
        if (!r.ok) {
            const txt = await r.text();
            console.error("List threads failed", r.status, txt);
            throw new Error(`List threads failed: ${r.status} ${txt}`);
        }
        const data = await r.json();
        if (!data.ok) throw new Error('List threads not ok');
        return data.threads || [];
    }

    async function apiCreateThread(title) {
        const user = getAuthUser();
        if (!user) throw new Error("User not identified");
        const r = await fetch(`${BASE}/api/threads`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, title })
        });
        if (!r.ok) {
            const txt = await r.text();
            console.error("Create thread failed", r.status, txt);
            throw new Error(`Create thread failed: ${r.status} ${txt}`);
        }
        const data = await r.json();
        if (!data.ok) throw new Error('Create thread not ok');
        return data.thread;
    }

    async function apiGetThread(threadId) {
        const user = getAuthUser();
        if (!user) throw new Error("User not identified");
        const r = await fetch(`${BASE}/api/threads/${encodeURIComponent(threadId)}?username=${encodeURIComponent(user)}`);
        if (!r.ok) throw new Error(`Get thread failed: ${r.status}`);
        const data = await r.json();
        if (!data.ok) throw new Error('Get thread not ok');
        return data.thread;
    }

    async function apiSyncThread(threadId, messages) {
        const user = getAuthUser();
        if (!user) throw new Error("User not identified");
        const r = await fetch(`${BASE}/api/threads/${encodeURIComponent(threadId)}/sync?username=${encodeURIComponent(user)}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, session_id: sessionId, messages })
        });
        if (!r.ok) {
            const txt = await r.text();
            console.error("Sync failed", r.status, txt);
            throw new Error(`Sync failed: ${r.status} ${txt}`);
        }
        const data = await r.json();
        if (!data.ok) throw new Error('Sync not ok');
        return data.thread; // server thread after merge
    }

    async function apiRenameThread(threadId, title) {
        const user = getAuthUser();
        if (!user) throw new Error("User not identified");
        const r = await fetch(`${BASE}/api/threads/${encodeURIComponent(threadId)}?username=${encodeURIComponent(user)}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, title })
        });
        if (!r.ok) throw new Error(`Rename thread failed: ${r.status}`);
        const data = await r.json();
        if (!data.ok) throw new Error('Rename thread not ok');
        return true;
    }

    async function apiDeleteThread(threadId) {
        const user = getAuthUser();
        if (!user) throw new Error("User not identified");
        const r = await fetch(`${BASE}/api/threads/${encodeURIComponent(threadId)}?username=${encodeURIComponent(user)}`, {
            method: 'DELETE'
        });
        if (!r.ok) throw new Error(`Delete thread failed: ${r.status}`);
        const data = await r.json();
        if (!data.ok) throw new Error('Delete thread not ok');
        return true;
    }

    async function apiChat(threadId, prompt) {
        const user = getAuthUser();
        if (!user) throw new Error("User not identified");
        const r = await fetch(`${BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, query: prompt, thread_id: threadId, session_id: sessionId })
        });
        if (!r.ok) {
            if (r.status === 401) {
                alert("Session expired. Please log in again.");
                window.location.href = 'login.html';
                return;
            }
            const txt = await r.text();
            console.error("Chat failed", r.status, txt);
            throw new Error(`Chat failed: ${r.status} ${txt}`);
        }
        const data = await r.json();
        if (!data.ok) throw new Error('Chat not ok');
        return data; // { response, ts, thread_id }
    }

    // -------- UI helpers (neutral look) --------
    const displayMessage = (message, sender, isLoading = false, ts = null) => {
        const wrapper = document.createElement('div');
        wrapper.className = `max-w-xl mb-3 ${sender === 'user' ? 'self-end' : 'self-start'}`;

        const bubble = document.createElement('div');
        bubble.className = `p-3 rounded-lg shadow-sm border text-slate-800 ${
            sender === 'user'
                ? 'bg-white border-slate-200'
                : 'bg-slate-50 border-slate-200'
        }`;

        if (isLoading) {
            bubble.id = 'loading-indicator';
            bubble.textContent = 'Thinking…';
        } else {
            if (sender === 'bot' && window.marked && window.DOMPurify) {
                const html = DOMPurify.sanitize(marked.parse(message || ''));
                bubble.innerHTML = html;
                // Add copy buttons to code blocks
                const codeBlocks = bubble.querySelectorAll('pre');
                codeBlocks.forEach(block => {
                    const code = block.querySelector('code');
                    if (code) {
                        const copyBtn = document.createElement('button');
                        copyBtn.className = 'copy-btn';
                        copyBtn.textContent = 'Copy';
                        copyBtn.addEventListener('click', () => {
                            navigator.clipboard.writeText(code.textContent).then(() => {
                                copyBtn.textContent = 'Copied!';
                                setTimeout(() => {
                                    copyBtn.textContent = 'Copy';
                                }, 2000);
                            });
                        });
                        block.appendChild(copyBtn);
                    }
                });
            } else {
                bubble.textContent = message;
            }
        }
        wrapper.appendChild(bubble);

        if (ts && !isLoading) {
            const time = document.createElement('div');
            const d = new Date(ts);
            time.className = 'text-[10px] text-slate-400 mt-1 ' + (sender === 'user' ? 'text-right' : 'text-left');
            time.textContent = d.toLocaleString();
            wrapper.appendChild(time);
        }

        chatMessages.appendChild(wrapper);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    };

    function clearChatUI() {
        chatMessages.innerHTML = '';
    }

    function renderEmptyState() {
        clearChatUI();
        const empty = document.createElement('div');
        empty.className = 'flex-1 flex flex-col items-center justify-center text-slate-400 py-10';
        empty.innerHTML = `
            <div class="text-3xl mb-2">�️</div>
            <div class="text-sm">Start a new conversation whenever you're ready.</div>
        `;
        chatMessages.appendChild(empty);
    }

    function mapServerMsg(m) {
        // server: { role: 'user'|'assistant', content, ts }
        return { role: m.role === 'assistant' ? 'bot' : 'user', text: m.content, ts: m.ts };
    }

    // -------- State --------
    let threads = []; // list view
    let activeThreadId = null;

    async function loadAndRenderThreads() {
        threads = await apiListThreads();
        const saved = getActiveThreadId();
        if (saved && threads.some(t => t.id === saved)) {
            activeThreadId = saved;
        } else {
            activeThreadId = threads[0]?.id || null;
            if (activeThreadId) setActiveThreadId(activeThreadId); else setActiveThreadId(null);
        }
        renderHistoryList();
    }

    async function loadAndRenderActiveThreadMessages() {
        if (!activeThreadId) {
            renderEmptyState();
            return;
        }

        // 1) Render from localStorage first for speed
        clearChatUI();
        const localMessages = getThreadHistory(activeThreadId);
        if (localMessages && localMessages.length > 0) {
            localMessages.forEach(m => displayMessage(m.text, m.role, false, m.ts));
        } else {
            renderEmptyState();
        }

        // 2) Attempt to sync local -> server (merge), then fetch server truth
        try {
            if (localMessages && localMessages.length > 0) {
                await apiSyncThread(activeThreadId, localMessages);
            }
            const thread = await apiGetThread(activeThreadId);
            const serverMsgs = (thread.messages || []).map(mapServerMsg);

            // 3) Update UI and localStorage with server data (source of truth)
            clearChatUI();
            if (serverMsgs.length === 0) {
                renderEmptyState();
            } else {
                serverMsgs.forEach(m => displayMessage(m.text, m.role, false, m.ts));
            }
            saveThreadHistory(activeThreadId, serverMsgs);
        } catch (e) {
            console.error("Failed to sync/fetch thread:", e);
            // Fallback: keep showing local history
        }
    }

    // Sidebar rendering
    function renderHistoryList() {
        const list = document.getElementById('chat-history-list');
        if (!list) return;
        list.innerHTML = '';

        threads
            .slice()
            .sort((a, b) => new Date(b.updatedAt) - new Date(a.updatedAt))
            .forEach(thread => {
                const isActive = thread.id === activeThreadId;
                const item = document.createElement('div');
                item.className = `group border border-slate-200 rounded-lg ${isActive ? 'bg-slate-50' : 'bg-white'} hover:bg-slate-50 transition`;

                const row = document.createElement('div');
                row.className = 'w-full text-left p-3 flex items-start gap-2 cursor-pointer';

                const textWrap = document.createElement('div');
                textWrap.className = 'flex-1 min-w-0';

                const titleEl = document.createElement('div');
                titleEl.className = 'text-sm font-medium text-slate-800 truncate';
                titleEl.title = thread.title || 'New conversation';
                titleEl.textContent = thread.title || 'New conversation';

                const timeEl = document.createElement('div');
                timeEl.className = 'text-[10px] text-slate-400 mt-1';
                timeEl.textContent = `Updated: ${new Date(thread.lastTs || thread.updatedAt).toLocaleString()}`;

                textWrap.appendChild(titleEl);
                textWrap.appendChild(timeEl);

                const actions = document.createElement('div');
                actions.className = 'flex items-center gap-1 opacity-0 group-hover:opacity-100 transition';

                const renameBtn = document.createElement('button');
                renameBtn.className = 'rename-btn text-slate-500 hover:text-slate-700 px-2 py-1';
                renameBtn.title = 'Rename';
                renameBtn.textContent = 'Rename';

                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'delete-btn text-red-500 hover:text-red-600 px-2 py-1';
                deleteBtn.title = 'Delete';
                deleteBtn.textContent = 'Delete';

                actions.appendChild(renameBtn);
                actions.appendChild(deleteBtn);

                row.appendChild(textWrap);
                row.appendChild(actions);

                // Switch to thread
                row.addEventListener('click', async () => {
                    activeThreadId = thread.id;
                    setActiveThreadId(activeThreadId);
                    renderHistoryList();
                    await loadAndRenderActiveThreadMessages();
                    chatInput?.focus();
                });

                // Rename
                renameBtn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    const newTitle = prompt('Rename conversation:', thread.title || 'New conversation');
                    if (newTitle === null) return;
                    const trimmed = newTitle.trim();
                    if (!trimmed) return;
                    try {
                        await apiRenameThread(thread.id, trimmed);
                        await loadAndRenderThreads();
                        await loadAndRenderActiveThreadMessages();
                    } catch (err) {
                        console.error(err);
                        alert('Failed to rename');
                    }
                });

                // Delete
                deleteBtn.addEventListener('click', async (e) => {
                    e.stopPropagation();
                    if (!confirm('Delete this conversation?')) return;
                    try {
                        await apiDeleteThread(thread.id);
                        removeThreadHistory(thread.id); // Also remove from localStorage
                        await loadAndRenderThreads();
                        await loadAndRenderActiveThreadMessages();
                    } catch (err) {
                        console.error(err);
                        alert('Failed to delete');
                    }
                });

                item.appendChild(row);
                list.appendChild(item);
            });
    }

    // Send message flow
    async function sendMessage(message) {
        if (!message?.trim()) return;

        // Clear empty state if it's present
        if (chatMessages.querySelector('.flex-1.flex.flex-col.items-center.justify-center')) {
            clearChatUI();
        }

        // Ensure active thread exists (server-side)
        if (!activeThreadId) {
            try {
                const t = await apiCreateThread('New conversation');
                activeThreadId = t.id;
                setActiveThreadId(activeThreadId);
                await loadAndRenderThreads();
            } catch (e) {
                console.error(e);
                alert('Failed to create new chat: ' + e.message);
                return;
            }
        }

        // Render user message and save to local history immediately
        const userTs = new Date().toISOString();
        const userMessage = { role: 'user', text: message, ts: userTs };
        displayMessage(userMessage.text, userMessage.role, false, userMessage.ts);
        addMessageToHistory(activeThreadId, userMessage);

        chatInput.value = '';
        chatInput.style.height = 'auto'; // Reset height
        displayMessage('', 'bot', true); // Loading indicator

        try {
            // Proactively sync local -> server before sending to reduce duplication
            // const localMessages = getThreadHistory(activeThreadId);
            // if (localMessages?.length) {
            //     await apiSyncThread(activeThreadId, localMessages);
            // }

            const data = await apiChat(activeThreadId, message);
            const loadingIndicator = document.getElementById('loading-indicator');
            if (loadingIndicator) loadingIndicator.parentElement.remove();

            if (data.thread_id && data.thread_id !== activeThreadId) {
                activeThreadId = data.thread_id;
                setActiveThreadId(activeThreadId);
            }

            // Render bot message and save to local history
            const botMessage = { role: 'bot', text: data.response, ts: data.ts };
            displayMessage(botMessage.text, botMessage.role, false, botMessage.ts);
            addMessageToHistory(activeThreadId, botMessage);

            // Fetch server truth to keep cache accurate
            const thread = await apiGetThread(activeThreadId);
            const serverMsgs = (thread.messages || []).map(mapServerMsg);
            saveThreadHistory(activeThreadId, serverMsgs);

            await loadAndRenderThreads(); // update sidebar
        } catch (error) {
            console.error('Error sending message:', error);
            const loadingIndicator = document.getElementById('loading-indicator');
            if (loadingIndicator) loadingIndicator.parentElement.remove();
            displayMessage('Sorry, I could not connect to the server. Please check if the backend is running and try again.', 'bot');
        }
    }

    // Handlers
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const msg = chatInput.value.trim();
        if (msg) await sendMessage(msg);
    });

    chatInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit', { cancelable: true }));
        }
    });

    // New Chat -> create on server and switch
    if (newChatBtn) {
        newChatBtn.addEventListener('click', async () => {
            try {
                const t = await apiCreateThread('New conversation');
                activeThreadId = t.id;
                setActiveThreadId(activeThreadId);
                await loadAndRenderThreads();
                clearChatUI();
                renderEmptyState();
                chatInput.focus();
            } catch (e) {
                console.error(e);
                alert('Failed to start new chat: ' + e.message);
            }
        });
    }


    // Periodic sync of active thread (local -> server), then refresh local cache from server
    async function periodicSync() {
        if (!activeThreadId) return;
        const localMessages = getThreadHistory(activeThreadId);
        if (!localMessages?.length) return;
        try {
            const serverThread = await apiSyncThread(activeThreadId, localMessages);
            const serverMsgs = (serverThread.messages || []).map(mapServerMsg);
            saveThreadHistory(activeThreadId, serverMsgs);
        } catch (e) {
            // Silent fail; next tick will retry
            console.debug('Periodic sync failed:', e);
        }
    }

    // Init
    (async function init() {
        try {
            await loadAndRenderThreads();
            await loadAndRenderActiveThreadMessages();
        } catch (e) {
            console.error(e);
            renderEmptyState();
        }
        // Start periodic sync every 15s
        setInterval(periodicSync, 15000);

        // Final sync on page hide/unload
        const flush = async () => {
            try { await periodicSync(); } catch (_) {}
        };
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) flush();
        });
        window.addEventListener('beforeunload', () => { /* best-effort */ });
    })();
});
