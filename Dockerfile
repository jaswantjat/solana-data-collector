# Use Python 3.11.3 slim image
FROM python:3.11.3-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV PYTHONPATH=/app
ENV PYTHONWARNINGS=ignore
ENV PATH="/opt/venv/bin:$PATH"

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        python3.11-dev \
        python3.11-venv \
        libffi-dev \
        libssl-dev \
        pkg-config \
        gcc \
        g++ \
        make \
        git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python3.11 -m venv /opt/venv && \
    /opt/venv/bin/python -m pip install --no-cache-dir --upgrade pip setuptools wheel

# Install build dependencies first
COPY requirements.txt .
RUN /opt/venv/bin/pip install --no-cache-dir \
        wheel==0.42.0 \
        setuptools>=69.0.3 \
        cffi==1.15.1 \
        pycparser==2.21

# Install cryptography separately
RUN /opt/venv/bin/pip install --no-cache-dir cryptography==41.0.7

# Install remaining requirements
RUN /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Verify installation
RUN echo "Verifying cryptography installation..." && \
    /opt/venv/bin/python -c "from cryptography.fernet import Fernet; print('Cryptography installation verified')"

# Expose port
EXPOSE 8000

# Run the application
CMD ["/opt/venv/bin/python", "-m", "uvicorn", "src.api.dashboard:app", "--host", "0.0.0.0", "--port", "8000"]
