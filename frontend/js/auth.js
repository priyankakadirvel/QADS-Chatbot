// auth.js - Handles signup, login, and logout for FastAPI backend

export let userId = null;
export let username = null;
export let isAuthReady = false;

const BASE = (window.location.port === '8000' || window.location.protocol === 'https:') 
    ? '' 
    : 'http://127.0.0.1:8000';

// Initialize from localStorage if available
try {
    const savedUser = localStorage.getItem("chatbot_user");
    if (savedUser) {
        const userData = JSON.parse(savedUser);
        username = userData.username;
        userId = userData.username; // Using username as ID
    }
} catch (error) {
    console.error("Error parsing user data from localStorage:", error);
    localStorage.removeItem("chatbot_user");
} finally {
    isAuthReady = true;
}

/**
 * Signup function
 */
export const handleSignup = async (uname, password) => {
  try {
    const response = await fetch(`${BASE}/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: uname.trim(), password }),
    });

    const data = await response.json();

    if (!response.ok) throw new Error(data.detail || "Signup failed");

    localStorage.setItem(
      "chatbot_user",
      JSON.stringify({ username: uname })
    );
    username = uname;
    userId = uname;

    alert("Signup successful! Redirecting...");
    window.location.href = "index.html";
  } catch (error) {
    console.error("Signup failed:", error.message);
    alert(`Signup failed: ${error.message}`);
    return error.message;
  }
};

/**
 * Login function
 */
export const handleLogin = async (uname, password) => {
  try {
    const response = await fetch(`${BASE}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: uname.trim(), password }),
    });

    const data = await response.json();

    if (!response.ok) throw new Error(data.detail || "Login failed");

    localStorage.setItem(
      "chatbot_user",
      JSON.stringify({ username: uname })
    );
    username = uname;
    userId = uname;

    alert("Login successful! Redirecting...");
    window.location.href = "index.html";
  } catch (error) {
    console.error("Login failed:", error.message);
    alert(`Login failed: ${error.message}`);
    return error.message;
  }
};

/**
 * Logout function
 */
export const handleLogout = () => {
  localStorage.removeItem("chatbot_user");
  username = null;
  userId = null;
  alert("Logged out successfully");
  window.location.href = "login.html";
};
