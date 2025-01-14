# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    python3-dev \
    pkg-config \
    libssl-dev \
    python3.11-dev \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install build tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install cryptography first
RUN pip install --no-cache-dir cryptography==41.0.7

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Run deployment verification
RUN python scripts/deploy_verify.py

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "src.api.dashboard:app", "--host", "0.0.0.0", "--port", "8000"]
