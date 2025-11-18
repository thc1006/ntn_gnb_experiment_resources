#!/usr/bin/env bash
#
# Quick Start Script for 5G NTN Software Testbed
# ===============================================
#
# One-command setup and launch
# Usage: ./scripts/quick_start.sh [--gpu]
#

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_header() {
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}======================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Parse arguments
GPU_SUPPORT=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --gpu)
            GPU_SUPPORT=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--gpu]"
            echo ""
            echo "Options:"
            echo "  --gpu    Install GPU support (CuPy for CUDA)"
            echo "  --help   Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

print_header "5G NTN Software Testbed - Quick Start"

# Step 1: Check Python version
print_info "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
print_success "Python $PYTHON_VERSION found"

# Step 2: Create virtual environment if not exists
if [ ! -d "venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv venv
    print_success "Virtual environment created"
else
    print_warning "Virtual environment already exists, skipping creation"
fi

# Step 3: Activate virtual environment
print_info "Activating virtual environment..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows (Git Bash / MSYS)
    source venv/Scripts/activate
elif [[ "$OSTYPE" == "darwin"* || "$OSTYPE" == "linux-gnu"* ]]; then
    # macOS / Linux
    source venv/bin/activate
else
    print_error "Unsupported OS: $OSTYPE"
    exit 1
fi
print_success "Virtual environment activated"

# Step 4: Upgrade pip
print_info "Upgrading pip..."
python -m pip install --upgrade pip --quiet
print_success "pip upgraded"

# Step 5: Install dependencies
print_info "Installing dependencies..."
pip install -r requirements.txt --quiet
print_success "Dependencies installed"

# Step 6: Install GPU support if requested
if [ "$GPU_SUPPORT" = true ]; then
    print_info "Checking for CUDA..."

    if command -v nvcc &> /dev/null; then
        CUDA_VERSION=$(nvcc --version | grep "release" | awk '{print $6}' | cut -d',' -f1)
        print_success "CUDA $CUDA_VERSION detected"

        # Determine CuPy version based on CUDA version
        CUDA_MAJOR=$(echo $CUDA_VERSION | cut -d'.' -f1)

        if [ "$CUDA_MAJOR" == "12" ]; then
            print_info "Installing CuPy for CUDA 12.x..."
            pip install cupy-cuda12x --quiet
        elif [ "$CUDA_MAJOR" == "11" ]; then
            print_info "Installing CuPy for CUDA 11.x..."
            pip install cupy-cuda11x --quiet
        else
            print_warning "CUDA $CUDA_VERSION not directly supported, trying generic CuPy..."
            pip install cupy --quiet
        fi

        print_success "GPU support installed"
    else
        print_warning "CUDA not found. GPU acceleration will not be available."
        print_info "To enable GPU: Install CUDA Toolkit from https://developer.nvidia.com/cuda-downloads"
    fi
fi

# Step 7: Create results directory if not exists
if [ ! -d "results" ]; then
    mkdir -p results
    print_success "Results directory created"
fi

# Step 8: Run basic validation
print_info "Running validation checks..."

# Check NumPy
python -c "import numpy; print('NumPy:', numpy.__version__)" 2>&1 | grep -q "NumPy:"
if [ $? -eq 0 ]; then
    print_success "NumPy installed"
else
    print_error "NumPy validation failed"
    exit 1
fi

# Check SciPy
python -c "import scipy; print('SciPy:', scipy.__version__)" 2>&1 | grep -q "SciPy:"
if [ $? -eq 0 ]; then
    print_success "SciPy installed"
else
    print_error "SciPy validation failed"
    exit 1
fi

# Check Matplotlib
python -c "import matplotlib; print('Matplotlib:', matplotlib.__version__)" 2>&1 | grep -q "Matplotlib:"
if [ $? -eq 0 ]; then
    print_success "Matplotlib installed"
else
    print_error "Matplotlib validation failed"
    exit 1
fi

# Check GPU (if enabled)
if [ "$GPU_SUPPORT" = true ]; then
    python -c "import cupy; print('CuPy:', cupy.__version__)" 2>&1 | grep -q "CuPy:"
    if [ $? -eq 0 ]; then
        print_success "GPU support verified (CuPy installed)"
    else
        print_warning "GPU support requested but CuPy not available"
    fi
fi

# Step 9: Display system information
print_header "System Information"
echo "Python: $(python --version)"
echo "NumPy: $(python -c 'import numpy; print(numpy.__version__)')"
echo "SciPy: $(python -c 'import scipy; print(scipy.__version__)')"
echo "Matplotlib: $(python -c 'import matplotlib; print(matplotlib.__version__)')"

if [ "$GPU_SUPPORT" = true ] && command -v nvidia-smi &> /dev/null; then
    echo ""
    echo "GPU Information:"
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader | head -1
fi

# Step 10: Run demo
print_header "Running Simulation Demo"
print_info "This will run GEO, LEO, and HAPS scenarios..."
echo ""

python -m src.simulators.demo_full_simulation

# Check if demo succeeded
if [ $? -eq 0 ]; then
    print_header "Setup Complete!"
    print_success "All systems operational"
    echo ""
    print_info "Next steps:"
    echo "  1. Review results in results/ directory"
    echo "  2. Check plots: results/spectrum_*.png"
    echo "  3. View JSON results: results/simulation_results.json"
    echo "  4. Try Docker: docker-compose up"
    echo "  5. Explore Jupyter notebooks (coming soon)"
    echo ""
    print_success "Ready for production use! 🚀"
else
    print_error "Demo failed. Please check errors above."
    exit 1
fi

# Step 11: Provide usage hints
print_header "Quick Usage Guide"
echo "Activate environment:"
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    echo "  source venv/Scripts/activate"
else
    echo "  source venv/bin/activate"
fi
echo ""
echo "Run individual scenarios:"
echo "  python -m src.simulators.usrp_simulator"
echo "  python -m src.simulators.channel_simulator"
echo ""
echo "Use link budget calculator:"
echo "  python analysis/link_budget_calculator.py --scenario geo --freq 1.5e9"
echo ""
echo "Docker deployment:"
echo "  docker-compose up -d"
echo ""
echo "Kubernetes deployment:"
echo "  kind create cluster --config kubernetes/kind-config.yaml"
echo "  kubectl apply -f kubernetes/deployment.yaml"
echo ""
print_info "For detailed documentation, see:"
echo "  - README.md (quick start)"
echo "  - PROJECT_ANALYSIS.md (comprehensive analysis)"
echo "  - SETUP_SUMMARY.md (setup details)"

print_header "Setup Successful!"
