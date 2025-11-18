# ====================================
# 5G NTN Software Testbed - Dockerfile
# ====================================
# Multi-stage build for optimized image size

# ============ Stage 1: Base (CPU-only) ============
FROM python:3.11-slim as base

LABEL maintainer="5G NTN Research Team"
LABEL description="5G NTN Software Testbed - No Hardware Required"
LABEL version="2.0.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# Create app directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    wget \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ============ Stage 2: GPU Support ============
FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04 as gpu-base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install Python and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3-pip \
    build-essential \
    git \
    wget \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create symlink for python
RUN ln -s /usr/bin/python3 /usr/bin/python

# Copy requirements
COPY requirements.txt .

# Install Python dependencies including CuPy for GPU
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install cupy-cuda12x

# ============ Stage 3: Final Application ============
FROM base as final

# Copy application code
COPY simulators/ ./simulators/
COPY analysis/ ./analysis/
COPY ntn/ ./ntn/
COPY mcp-servers/ ./mcp-servers/
COPY .claude/ ./.claude/
COPY scripts/ ./scripts/
COPY config/ ./config/
COPY tests/ ./tests/

# Create directories for results and logs
RUN mkdir -p results logs

# Copy entrypoint script
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose ports
EXPOSE 8000 8001 8002 8080 8888 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import simulators; print('OK')" || exit 1

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command: run demo
CMD ["python", "simulators/demo_full_simulation.py"]

# ============ Stage 4: GPU-enabled Final ============
FROM gpu-base as gpu-final

# Copy application code
COPY simulators/ ./simulators/
COPY analysis/ ./analysis/
COPY ntn/ ./ntn/
COPY mcp-servers/ ./mcp-servers/
COPY .claude/ ./.claude/
COPY scripts/ ./scripts/
COPY config/ ./config/
COPY tests/ ./tests/

# Create directories
RUN mkdir -p results logs

# Copy entrypoint
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose ports
EXPOSE 8000 8001 8002 8080 8888 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import simulators; print('OK')" || exit 1

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "simulators/demo_full_simulation.py"]

# ============ Usage Instructions ============
# CPU-only build:
#   docker build --target final -t ntn-testbed:latest .
#
# GPU-enabled build:
#   docker build --target gpu-final -t ntn-testbed:gpu .
#
# Run CPU-only:
#   docker run -v $(pwd)/results:/app/results ntn-testbed:latest
#
# Run with GPU:
#   docker run --gpus all -v $(pwd)/results:/app/results ntn-testbed:gpu
