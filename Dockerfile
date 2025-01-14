# Use Python 3.10 slim as base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PORT=8000 \
    PYTHONWARNINGS=ignore \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

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

# Create a virtual environment
RUN python -m venv $VIRTUAL_ENV

# Install core dependencies first
COPY requirements.txt .

# Upgrade pip and install core dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir \
        cffi==1.15.1 \
        pycparser==2.21 \
        cryptography==41.0.7

# Verify core dependencies
RUN python -c "import cryptography; print(f'Cryptography {cryptography.__version__} installed successfully')"

# Install remaining dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a non-root user
RUN useradd -m appuser && \
    chown -R appuser:appuser /app /opt/venv && \
    chmod -R 755 /app /opt/venv
USER appuser

# Verify all installations
RUN python scripts/verify_install.py

# Use the virtual environment's Python for running the application
ENTRYPOINT ["python", "-m"]
CMD ["uvicorn", "src.api.dashboard:app", "--host", "0.0.0.0", "--port", "8000"]
