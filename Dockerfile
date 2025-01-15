# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    CRYPTOGRAPHY_DONT_BUILD_RUST=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libffi-dev \
    libssl-dev \
    pkg-config \
    gcc \
    git \
    rustc \
    cargo \
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

# Create data directory
RUN mkdir -p /app/data && chmod 777 /app/data

# Copy project
COPY . .

# Run tests
RUN python test_env.py

# Command to run the application
CMD ["python", "-m", "uvicorn", "src.api.dashboard:app", "--host", "0.0.0.0", "--port", "10000"]
