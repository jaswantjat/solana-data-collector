# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CRYPTOGRAPHY_DONT_BUILD_RUST=1 \
    PYTHONPATH=/app \
    DATA_DIR=/app/data \
    STATIC_DIR=/app/static \
    TEMPLATES_DIR=/app/templates \
    API_RATE_LIMIT=10 \
    API_RATE_LIMIT_WINDOW=1 \
    API_TIMEOUT=30 \
    API_MAX_RETRIES=3 \
    API_RETRY_DELAY=1 \
    REDIS_URL=redis://localhost:6379 \
    REDIS_DB=0 \
    LOG_LEVEL=INFO \
    PROMETHEUS_PORT=8000

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

# Set work directory
WORKDIR /app

# Upgrade pip
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install security dependencies first
RUN pip install --no-cache-dir \
    cffi==1.15.1 \
    pycparser==2.21 \
    cryptography==41.0.7

# Copy requirements file
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories with proper permissions
RUN mkdir -p $DATA_DIR $STATIC_DIR $TEMPLATES_DIR && \
    chown -R nobody:nogroup $DATA_DIR $STATIC_DIR $TEMPLATES_DIR && \
    chmod 777 $DATA_DIR $STATIC_DIR $TEMPLATES_DIR

# Copy project
COPY . .

# Set proper permissions for all files
RUN chown -R nobody:nogroup /app && \
    chmod -R 755 /app

# Run tests
RUN python test_env.py

# Switch to non-root user
USER nobody

# Command to run the application
CMD ["python", "-m", "uvicorn", "src.api.dashboard:app", "--host", "0.0.0.0", "--port", "10000"]
