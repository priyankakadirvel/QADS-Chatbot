import { userId, username, handleLogout, isAuthReady } from "./auth.js";

// Update UI based on auth status
const updateAuthUI = () => {
  const authButtons = document.getElementById("auth-buttons");
  const userMenuContainer = document.getElementById("user-menu-container");
  const usernameDisplay = document.getElementById("username-display");
  const avatar = document.getElementById("user-avatar");
  const dropdown = document.getElementById("user-dropdown");

  if (authButtons && userMenuContainer && usernameDisplay) {
    if (userId) {
      authButtons.classList.add("hidden");
      userMenuContainer.classList.remove("hidden");
      usernameDisplay.textContent = `Signed in as ${username}`;

      // Ensure dropdown starts hidden and toggle on avatar click
      if (dropdown && !dropdown.classList.contains("hidden")) {
        dropdown.classList.add("hidden");
      }
      if (avatar && dropdown) {
        avatar.addEventListener("click", (e) => {
          e.stopPropagation();
          dropdown.classList.toggle("hidden");
        });
        document.addEventListener("click", (e) => {
          if (!dropdown.contains(e.target)) {
            dropdown.classList.add("hidden");
          }
        });
      }
    } else {
      authButtons.classList.remove("hidden");
      userMenuContainer.classList.add("hidden");
    }
  }
};

const initAuth = () => {
  if (isAuthReady) {
    updateAuthUI();
    const logoutBtn = document.getElementById("logout-btn");
    if (logoutBtn) {
      logoutBtn.addEventListener("click", handleLogout);
    }
  } else {
    setTimeout(initAuth, 100); // Wait and try again
  }
};

document.addEventListener("DOMContentLoaded", initAuth);
