#!/bin/bash

# Clean up dangling ports just in case
fuser -k 8000/tcp 2>/dev/null
fuser -k 5173/tcp 2>/dev/null

echo "🚀 Booting Competitor Intelligence Engine..."

# Start Backend
echo "Starting FastAPI Backend Engine on Port 8000..."
python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start Frontend
echo "Starting React Frontend Dashboard on Port 5173..."
cd frontend && npm run dev &
FRONTEND_PID=$!

echo "========================================="
echo "✅ Both servers are running natively!"
echo "Backend API: http://localhost:8000"
echo "Frontend Dashboard: http://localhost:5173"
echo "========================================="
echo "Press Ctrl+C to terminate both servers."

# Trap termination signal to kill both processes
trap "kill $BACKEND_PID $FRONTEND_PID" EXIT

# Wait indefinitely
wait
