#!/bin/bash
# Quick test script - starts backend and runs tests

echo "Starting backend server..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "Waiting for backend to start..."
sleep 5

echo "Running isolation tests..."
python test_user_isolation.py

echo "Stopping backend..."
kill $BACKEND_PID

