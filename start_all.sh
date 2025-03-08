#!/bin/bash

echo "Starting all POC TECHNICIA components..."
echo ""

# Create necessary directories
mkdir -p logs uploads storage

# Step 1: Check/Start Qdrant with Docker
echo "Step 1: Checking Qdrant status..."

# Check if Qdrant is running
if curl -s -o /dev/null -w "%{http_code}" http://localhost:6333/dashboard > /dev/null; then
    echo "Qdrant already running at http://localhost:6333"
else
    echo "Starting Qdrant with Docker..."
    docker ps | grep qdrant > /dev/null
    if [ $? -eq 0 ]; then
        echo "Qdrant container already exists, starting it..."
        docker start qdrant
    else
        echo "Creating and starting Qdrant container..."
        docker run -d --name qdrant \
            -p 6333:6333 \
            -p 6334:6334 \
            -v $(pwd)/storage:/qdrant/storage \
            qdrant/qdrant
    fi
    sleep 5
fi
echo ""

# Step 2: Initialize collection
echo "Step 2: Initializing Qdrant collection..."
python init_qdrant.py
echo ""

# Step 3: Starting Backend
echo "Step 3: Starting Backend..."
# Create a new terminal window for the backend
if command -v gnome-terminal &> /dev/null; then
    gnome-terminal -- bash -c "cd $(pwd) && source .venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --reload --port 8000" &
elif command -v xterm &> /dev/null; then
    xterm -e "cd $(pwd) && source .venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --reload --port 8000" &
else
    # Fallback to running in the background
    cd $(pwd) && source .venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --reload --port 8000 &
fi
sleep 3
echo ""

# Step 4: Starting Frontend
echo "Step 4: Starting Frontend..."
# Create a new terminal window for the frontend
if command -v gnome-terminal &> /dev/null; then
    gnome-terminal -- bash -c "cd $(pwd)/frontend && npm run dev" &
elif command -v xterm &> /dev/null; then
    xterm -e "cd $(pwd)/frontend && npm run dev" &
else
    # Fallback to running in the background
    cd $(pwd)/frontend && npm run dev &
fi
echo ""

echo "All components started successfully!"
echo "- Qdrant: http://localhost:6333"
echo "- Backend: http://localhost:8000"
echo "- Frontend: http://localhost:3001"
echo ""
echo "You can check if Qdrant is running with: curl -s http://localhost:6333"
echo "You can view the Qdrant dashboard at: http://localhost:6333/dashboard"
echo ""