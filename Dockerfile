# Use Python 3.10 slim as base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000 \
    PYTHONWARNINGS=ignore

# Create and set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libffi-dev \
    libssl-dev \
    pkg-config \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment and activate it
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip, setuptools and wheel in the virtual environment
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install core dependencies first
COPY requirements.txt .
RUN pip install --no-cache-dir \
    cffi==1.15.1 \
    pycparser==2.21 \
    cryptography==41.0.7

# Install remaining dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Verify cryptography installation
RUN python scripts/verify_install.py

# Run the application
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
