FROM python:3.11-slim

# System libs required by mediapipe + opencv-python-headless on Linux
RUN apt-get update && apt-get install -y \
    libglib2.0-0 libsm6 libxrender1 libxext6 libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Use regular hub downloads instead of Xet-based path which is often rate-limited for anonymous Cloud Run egress.
ENV HF_HUB_DISABLE_XET=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run sets $PORT dynamically; fall back to 8000 for local dev
CMD ["sh", "-c", "gunicorn app.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT:-8000} --timeout 120 --preload"]
