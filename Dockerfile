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
    PROMETHEUS_PORT=8000 \
    PORT=10000

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libffi-dev \
    libssl-dev \
    pkg-config \
    gcc \
    git \
    postgresql-client \
    libpq-dev \
    iputils-ping \
    dnsutils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Upgrade pip and install dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories
RUN mkdir -p /app/data /app/static /app/templates /app/logs

# Set permissions
RUN chmod -R 755 /app

# Expose the port
EXPOSE ${PORT}

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Set the command to run the application
CMD ["python", "-m", "src.main"]
