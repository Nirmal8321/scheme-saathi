#!/bin/bash
set -e

echo "=== Scheme Saathi - Hugging Face Space Startup ==="

# Build ChromaDB index if missing
if [ ! -d "./chroma_db" ] || [ -z "$(ls -A ./chroma_db 2>/dev/null)" ]; then
    echo "ChromaDB not found. Building index..."
    python -m backend.build_index
else
    echo "ChromaDB found. Skipping index build."
fi

# Start FastAPI backend on port 8000 in background
echo "Starting FastAPI backend on port 8000..."
uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend health check
echo "Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        echo "Backend is ready!"
        break
    fi
    echo "  Waiting... ($i/30)"
    sleep 2
done

# Verify backend is actually responding
if ! curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "ERROR: Backend failed to start properly"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi

# Start Streamlit on port 7860
echo "Starting Streamlit on port 7860..."
exec streamlit run ui/app.py \
    --server.address 0.0.0.0 \
    --server.port 7860 \
    --server.headless true \
    --server.enableCORS false \
    --server.enableXsrfProtection false