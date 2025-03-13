#!/bin/bash

echo "Starting all POC TECHNICIA components..."
echo ""

# Get the project root directory
PROJECT_ROOT="/home/ec2-user/POCTechnicia"
cd "${PROJECT_ROOT}" || { echo "Error: Could not change to project root directory"; exit 1; }

# Create necessary directories
mkdir -p logs uploads storage

# Step 1: Check/Start Qdrant with Docker
echo "Step 1: Checking Qdrant status..."

# Check if Docker is running
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo "Error: Docker daemon is not running. Please start Docker service."
    echo "You can usually start it with: sudo systemctl start docker"
    exit 1
fi

# Check if Qdrant is running
if curl -s -o /dev/null -w "%{http_code}" http://localhost:6333/dashboard &> /dev/null; then
    echo "Qdrant already running at http://localhost:6333"
else
    echo "Starting Qdrant with Docker..."
    if docker ps -a | grep qdrant &> /dev/null; then
        echo "Qdrant container already exists, starting it..."
        docker start qdrant
    else
        echo "Creating and starting Qdrant container..."
        docker run -d --name qdrant \
            -p 6333:6333 \
            -p 6334:6334 \
            -v "${PROJECT_ROOT}/storage:/qdrant/storage" \
            qdrant/qdrant
    fi
    
    # Wait for Qdrant to start (with timeout)
    echo "Waiting for Qdrant to start..."
    MAX_ATTEMPTS=30
    ATTEMPT=0
    until curl -s -o /dev/null -w "%{http_code}" http://localhost:6333/dashboard &> /dev/null || [ $ATTEMPT -eq $MAX_ATTEMPTS ]; do
        echo "Waiting for Qdrant to become available... ($ATTEMPT/$MAX_ATTEMPTS)"
        sleep 2
        ATTEMPT=$((ATTEMPT+1))
    done
    
    if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
        echo "Error: Qdrant failed to start within the expected time."
        echo "Check Docker logs with: docker logs qdrant"
        exit 1
    fi
    
    echo "Qdrant started successfully!"
fi
echo ""

# Step 2: Initialize collection
echo "Step 2: Initializing Qdrant collection..."
if [ -f "${PROJECT_ROOT}/init_qdrant.py" ]; then
    python "${PROJECT_ROOT}/init_qdrant.py"
else
    if [ -f "${PROJECT_ROOT}/scripts/python/initialize_qdrant.py" ]; then
        echo "Using initialize_qdrant.py script instead..."
        python "${PROJECT_ROOT}/scripts/python/initialize_qdrant.py"
    else
        echo "Error: Could not find qdrant initialization script"
        exit 1
    fi
fi
echo ""

# Step 3: Starting Backend
echo "Step 3: Starting Backend..."
# Create a new terminal window for the backend
if command -v gnome-terminal &> /dev/null; then
    gnome-terminal -- bash -c "cd ${PROJECT_ROOT} && source .venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --reload --port 8000" &
elif command -v xterm &> /dev/null; then
    xterm -e "cd ${PROJECT_ROOT} && source .venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --reload --port 8000" &
else
    # Fallback to running in the background
    cd "${PROJECT_ROOT}" && source .venv/bin/activate && python -m uvicorn app.main:app --host 0.0.0.0 --reload --port 8000 > logs/backend.log 2>&1 &
    BACKEND_PID=$!
    echo "Backend started with PID: $BACKEND_PID (logs in logs/backend.log)"
fi
sleep 3
echo ""

# Step 4: Starting Frontend
echo "Step 4: Starting Frontend..."
# Create a new terminal window for the frontend
if command -v gnome-terminal &> /dev/null; then
    gnome-terminal -- bash -c "cd ${PROJECT_ROOT}/frontend && npm run dev" &
elif command -v xterm &> /dev/null; then
    xterm -e "cd ${PROJECT_ROOT}/frontend && npm run dev" &
else
    # Fallback to running in the background
    cd "${PROJECT_ROOT}/frontend" && npm run dev > ../logs/frontend.log 2>&1 &
    FRONTEND_PID=$!
    echo "Frontend started with PID: $FRONTEND_PID (logs in logs/frontend.log)"
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
echo "To stop all components, you can run: kill $BACKEND_PID $FRONTEND_PID; docker stop qdrant"
echo ""