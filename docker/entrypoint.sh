#!/bin/bash
#
# Docker Entrypoint for 5G NTN Testbed
# =====================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}5G NTN Software Testbed${NC}"
echo -e "${BLUE}Starting Container...${NC}"
echo -e "${BLUE}======================================${NC}"

# Check GPU availability
if command -v nvidia-smi &> /dev/null; then
    echo -e "${GREEN}✅ GPU detected${NC}"
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader | head -1
    export GPU_AVAILABLE=true
else
    echo -e "${YELLOW}⚠️  No GPU detected - using CPU only${NC}"
    export GPU_AVAILABLE=false
fi

# Check Python environment
echo -e "${BLUE}Python: $(python --version)${NC}"
echo -e "${BLUE}NumPy: $(python -c 'import numpy; print(numpy.__version__)')${NC}"
echo -e "${BLUE}SciPy: $(python -c 'import scipy; print(scipy.__version__)')${NC}"

if [ "$GPU_AVAILABLE" = true ]; then
    if python -c "import cupy" 2>/dev/null; then
        echo -e "${GREEN}✅ CuPy: $(python -c 'import cupy; print(cupy.__version__)')${NC}"
    else
        echo -e "${YELLOW}⚠️  CuPy not available${NC}"
    fi
fi

# Create necessary directories
mkdir -p /app/results /app/logs

# Set permissions
chmod 777 /app/results /app/logs

# Load configuration if available
if [ -f "/app/config/testbed_config.yaml" ]; then
    echo -e "${GREEN}✅ Configuration loaded from config/testbed_config.yaml${NC}"
else
    echo -e "${YELLOW}⚠️  No configuration file found, using defaults${NC}"
fi

echo -e "${GREEN}✅ Environment ready${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Execute the command
exec "$@"
