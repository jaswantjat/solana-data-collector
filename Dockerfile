# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV PYTHONPATH=/app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        python3-dev \
        pkg-config \
        libssl-dev \
        gcc \
        g++ \
        make \
        git \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/*

# Copy requirements first
COPY requirements.txt .

# Install Python dependencies
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Run deployment verification
RUN python scripts/deploy_verify.py

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "src.api.dashboard:app", "--host", "0.0.0.0", "--port", "8000"]
