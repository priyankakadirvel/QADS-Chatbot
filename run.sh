#!/bin/bash

# QADS Quick Start Script for macOS/Linux

echo ""
echo "============================================"
echo "  QADS - Question Answering Data Science"
echo "  Assistant Quick Start"
echo "============================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 not found. Please install Python 3.9+"
    echo "macOS: brew install python3"
    echo "Ubuntu: sudo apt-get install python3 python3-pip"
    exit 1
fi

# Check if .env exists
if [ ! -f "backend/.env" ]; then
    echo "[WARNING] backend/.env not found!"
    echo "Please copy .env.example to backend/.env and add your API keys"
    echo ""
    echo "Steps:"
    echo "1. cp .env.example backend/.env"
    echo "2. Add your API keys:"
    echo "   - COHERE_API_KEY"
    echo "   - GROQ_API_KEY"
    echo "   - PINECONE_API_KEY"
    echo "   - SERP_API_KEY"
    echo ""
    read -p "Press Enter to continue..."
fi

# Create virtual environment if not exists
if [ ! -d "backend/venv" ]; then
    echo "[1/4] Creating virtual environment..."
    cd backend
    python3 -m venv venv
    cd ..
fi

# Activate virtual environment
echo "[2/4] Activating virtual environment..."
source backend/venv/bin/activate

# Install dependencies
echo "[3/4] Installing dependencies..."
cd backend
pip install -q -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies"
    exit 1
fi
cd ..

# Start backend
echo "[4/4] Starting QADS Backend Server..."
echo ""
echo "============================================"
echo "  Backend running on: http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo "============================================"
echo ""

cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start frontend
echo "Starting Frontend Server..."
echo ""
echo "============================================"
echo "  Frontend running on: http://localhost:8080"
echo "  Open: http://localhost:8080/index.html"
echo "============================================"
echo ""

cd ../frontend
python3 -m http.server 8080 &
FRONTEND_PID=$!

# Wait a bit
sleep 2

# Open browser if possible
if command -v open &> /dev/null; then
    open http://localhost:8080/index.html
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:8080/index.html
fi

echo ""
echo "QADS is now running!"
echo ""
echo "Test Credentials:"
echo "Username: priyanka.k@msds.christuniversity.in"
echo "Password: password"
echo ""
echo "Press Ctrl+C to stop the servers..."
echo ""

# Wait for user interrupt
wait
