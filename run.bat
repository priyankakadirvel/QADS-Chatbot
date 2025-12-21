@echo off
REM QADS Quick Start Script for Windows

echo.
echo ============================================
echo   QADS - Question Answering Data Science
echo   Assistant Quick Start
echo ============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.9+
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if .env exists
if not exist "backend\.env" (
    echo [WARNING] backend\.env not found!
    echo Please copy .env.example to backend\.env and add your API keys
    echo.
    echo Steps:
    echo 1. Copy .env.example to backend\.env
    echo 2. Add your API keys:
    echo    - COHERE_API_KEY
    echo    - GROQ_API_KEY
    echo    - PINECONE_API_KEY
    echo    - SERP_API_KEY
    echo.
    pause
)

REM Create virtual environment if not exists
if not exist "backend\venv" (
    echo [1/4] Creating virtual environment...
    cd backend
    python -m venv venv
    cd ..
)

REM Activate virtual environment
echo [2/4] Activating virtual environment...
call backend\venv\Scripts\activate.bat

REM Install dependencies
echo [3/4] Installing dependencies...
cd backend
pip install -q -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
cd ..

REM Start backend
echo [4/4] Starting QADS Backend Server...
echo.
echo ============================================
echo   Backend running on: http://localhost:8000
echo   API Docs: http://localhost:8000/docs
echo ============================================
echo.

cd backend
start cmd /k "uvicorn main:app --reload --host 0.0.0.0 --port 8000"

REM Wait a moment for backend to start
timeout /t 3 /nobreak

REM Start frontend
echo Starting Frontend Server...
echo.
echo ============================================
echo   Frontend running on: http://localhost:8080
echo   Open: http://localhost:8080/index.html
echo ============================================
echo.

cd ..\frontend
start cmd /k "python -m http.server 8080"

echo.
echo QADS is now running!
echo.
echo Browser will open automatically in 5 seconds...
timeout /t 5 /nobreak

start http://localhost:8080/index.html

echo.
echo Test Credentials:
echo Username: priyanka.k@msds.christuniversity.in
echo Password: password
echo.
pause
