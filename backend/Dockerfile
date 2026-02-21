FROM python:3.12-slim

WORKDIR /app

# System dependencies
# - gcc / libffi-dev: C extensions (cryptography, gevent)
# - libglib2.0-0 / libgl1: OpenCV headless
# - curl: health-check probe
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libffi-dev \
        libglib2.0-0 \
        libgl1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (layer-cached unless requirements change)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Default: run the API server
# Worker services override this via `command:` in docker-compose.yml
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
