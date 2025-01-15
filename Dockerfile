# Use Python 3.10 slim as base image
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libffi-dev \
    libssl-dev \
    pkg-config \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies with specific flags for cryptography
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir --no-binary cryptography -r requirements.txt

# Copy application code
COPY . .

# Run test script first
RUN python test_env.py

# Run the application
CMD ["python", "-m", "uvicorn", "src.api.dashboard:app", "--host", "0.0.0.0", "--port", "8000"]
