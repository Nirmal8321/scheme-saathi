# Hugging Face Space - Scheme Saathi
# sdk: docker
# app_port: 7860

FROM python:3.11-slim

# System dependencies for faster-whisper, chromadb, pymupdf
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    STT_MODEL=base \
    BACKEND_URL=http://localhost:8000 \
    CHROMA_DIR=/app/chroma_db \
    TRANSFORMERS_CACHE=/app/.cache/huggingface \
    HF_HOME=/app/.cache/huggingface

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download embedding model (paraphrase-multilingual-MiniLM-L12-v2)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

# Pre-download Whisper base model
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('base', device='cpu', compute_type='int8')"

# Copy the entire project
COPY . .

# Make start script executable
RUN chmod +x start.sh

# Expose Streamlit port
EXPOSE 7860

# Run the startup script
CMD ["./start.sh"]