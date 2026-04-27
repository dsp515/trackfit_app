FROM python:3.11-slim

# Minimal system libs needed for Pillow + httpx on Linux
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Disable HuggingFace Xet (not needed — food AI is off on Render)
ENV HF_HUB_DISABLE_XET=1
ENV ENABLE_FOOD_AI=false
ENV ENVIRONMENT=production

# Use lightweight requirements (no torch/mediapipe/opencv = ~150MB vs 4GB)
COPY requirements-render.txt .
RUN pip install --no-cache-dir -r requirements-render.txt

COPY . .

# Render sets $PORT dynamically; fall back to 8000 for local dev
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
