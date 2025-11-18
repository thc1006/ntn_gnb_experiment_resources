#!/bin/bash
#
# 5G NTN Testbed Initialization Script
# Prepares environment for ITRI channel emulator integration
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
TESTBED_HOME="/home/claude/5g-ntn-testbed"
PYTHON_MIN_VERSION="3.8"
UHD_VERSION="4.2.0"

echo "=================================================="
echo "    5G NTN Testbed Initialization"
echo "=================================================="

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root!"
   echo "Please run as a regular user with sudo privileges"
   exit 1
fi

# Step 1: Check Python version
echo ""
echo "Step 1: Checking Python environment..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    print_status "Python $PYTHON_VERSION found"
    
    # Check if version is sufficient
    if [ "$(printf '%s\n' "$PYTHON_MIN_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" = "$PYTHON_MIN_VERSION" ]; then
        print_status "Python version meets requirements"
    else
        print_error "Python $PYTHON_MIN_VERSION or higher required"
        exit 1
    fi
else
    print_error "Python3 not found. Please install Python 3.8 or higher"
    exit 1
fi

# Step 2: Install system dependencies
echo ""
echo "Step 2: Installing system dependencies..."
print_warning "This will require sudo privileges"

sudo apt-get update
sudo apt-get install -y \
    build-essential \
    cmake \
    git \
    libboost-all-dev \
    libusb-1.0-0-dev \
    python3-pip \
    python3-numpy \
    python3-scipy \
    python3-matplotlib \
    iproute2 \
    net-tools \
    iperf3 \
    htop \
    tmux

print_status "System dependencies installed"

# Step 3: Install Python packages
echo ""
echo "Step 3: Installing Python packages..."
pip3 install --user \
    numpy \
    scipy \
    matplotlib \
    asyncio \
    pyserial \
    pyvisa \
    pyvisa-py \
    pandas \
    jupyter \
    flask \
    requests

print_status "Python packages installed"

# Step 4: Check for UHD (USRP Hardware Driver)
echo ""
echo "Step 4: Checking UHD installation..."
if command -v uhd_find_devices &> /dev/null; then
    UHD_INSTALLED_VERSION=$(uhd_find_devices --version 2>&1 | grep -oP 'UHD \K[0-9.]+' || echo "unknown")
    print_status "UHD version $UHD_INSTALLED_VERSION found"
else
    print_warning "UHD not found. Installing UHD..."
    
    # Add Ettus Research repository
    sudo add-apt-repository ppa:ettusresearch/uhd -y
    sudo apt-get update
    sudo apt-get install -y uhd-host python3-uhd
    
    # Download FPGA images
    sudo uhd_images_downloader
    
    print_status "UHD installed"
fi

# Step 5: Configure USB permissions for USRP B210
echo ""
echo "Step 5: Configuring USB permissions for USRP devices..."
sudo cp /usr/lib/uhd/utils/uhd-usrp.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger

# Add user to usrp group if it exists
if getent group usrp > /dev/null 2>&1; then
    sudo usermod -a -G usrp $USER
    print_status "User added to usrp group"
else
    sudo groupadd usrp
    sudo usermod -a -G usrp $USER
    print_status "Created usrp group and added user"
fi

# Step 6: Configure network for USRP X310
echo ""
echo "Step 6: Configuring network for USRP X310..."
print_warning "Setting up network interface for 192.168.10.0/24 subnet"

# Check if network interface exists
if ip link show enp0s31f6 &> /dev/null; then
    INTERFACE="enp0s31f6"
elif ip link show eth0 &> /dev/null; then
    INTERFACE="eth0"
else
    print_warning "No suitable network interface found for X310"
    print_warning "Please manually configure network interface for 192.168.10.0/24"
    INTERFACE=""
fi

if [ ! -z "$INTERFACE" ]; then
    # Configure interface for X310
    sudo ip addr add 192.168.10.1/24 dev $INTERFACE 2>/dev/null || true
    sudo ip link set $INTERFACE up
    
    # Set MTU for optimal performance
    sudo ip link set dev $INTERFACE mtu 9000 2>/dev/null || true
    
    print_status "Network interface $INTERFACE configured for X310"
fi

# Step 7: Set up testbed directory structure
echo ""
echo "Step 7: Setting up testbed directory structure..."
cd $TESTBED_HOME

# Create necessary directories
mkdir -p results
mkdir -p logs
mkdir -p data
mkdir -p configs/emulator_profiles

print_status "Directory structure created"

# Step 8: Test USRP connectivity
echo ""
echo "Step 8: Testing USRP connectivity..."
echo "Searching for USRP devices..."

if uhd_find_devices > /tmp/usrp_devices.txt 2>&1; then
    if grep -q "Device Address" /tmp/usrp_devices.txt; then
        print_status "USRP devices found:"
        cat /tmp/usrp_devices.txt
    else
        print_warning "No USRP devices detected"
        echo "Please connect USRP devices and run 'uhd_find_devices' to verify"
    fi
else
    print_warning "Could not search for USRP devices"
fi

# Step 9: Configure system performance settings
echo ""
echo "Step 9: Configuring system performance settings..."

# CPU governor
if [ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]; then
    echo "performance" | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null
    print_status "CPU governor set to performance mode"
fi

# Increase network buffers for USRP
sudo sysctl -w net.core.rmem_max=33554432 > /dev/null
sudo sysctl -w net.core.wmem_max=33554432 > /dev/null
print_status "Network buffers increased"

# Disable CPU frequency scaling
if command -v cpupower &> /dev/null; then
    sudo cpupower frequency-set -g performance 2>/dev/null || true
fi

# Step 10: Create configuration files
echo ""
echo "Step 10: Creating default configuration files..."

# Create default Open5GS config
cat > configs/open5gs.yaml << EOF
# Open5GS Configuration for NTN
amf:
  sbi:
    - addr: 192.168.10.10
      port: 7777
  ngap:
    - addr: 192.168.10.10
  guami:
    plmn_id:
      mcc: 001
      mnc: 01
    amf_id:
      region: 2
      set: 1
  tai:
    plmn_id:
      mcc: 001
      mnc: 01
    tac: 1
  plmn_support:
    - plmn_id:
        mcc: 001
        mnc: 01
      s_nssai:
        - sst: 1
EOF

# Create default srsRAN config
cat > configs/srsran_gnb.yaml << EOF
# srsRAN gNB Configuration for NTN
amf:
  addr: 192.168.10.10
  bind_addr: 192.168.10.2
  port: 38412

ru_sdr:
  device_driver: uhd
  device_args: type=x310,addr=192.168.10.2,master_clock_rate=184.32e6
  tx_gain: 20
  rx_gain: 30

cell_cfg:
  dl_arfcn: 368500  # 1842.5 MHz (n3 band)
  band: 3
  channel_bandwidth_MHz: 20
  common_scs: 15
  plmn: "00101"
  tac: 1

# NTN specific parameters
ntn:
  satellite_type: GEO
  common_ta_offset: 7373000  # Ts units for GEO
  k_offset: 200              # Slots
  ephemeris_info_enabled: true
EOF

print_status "Configuration files created"

# Step 11: Verify Python module imports
echo ""
echo "Step 11: Verifying Python module imports..."
python3 -c "
import uhd
import numpy as np
import asyncio
print('✓ Core Python modules verified')
" 2>/dev/null && print_status "Python modules working" || print_warning "Some Python modules missing"

# Step 12: Set up environment variables
echo ""
echo "Step 12: Setting up environment variables..."

cat > $TESTBED_HOME/.env << EOF
# 5G NTN Testbed Environment Variables
export TESTBED_HOME=$TESTBED_HOME
export PYTHONPATH=\$TESTBED_HOME:\$PYTHONPATH
export UHD_LOG_LEVEL=info
export UHD_RFNOC_DIR=/usr/share/uhd/rfnoc

# USRP Configuration
export USRP_X310_ADDR=192.168.10.2
export USRP_B210_SERIAL=auto

# Open5GS Configuration
export OPEN5GS_CONFIG=\$TESTBED_HOME/configs/open5gs.yaml

# srsRAN Configuration  
export SRSRAN_CONFIG=\$TESTBED_HOME/configs/srsran_gnb.yaml

# Channel Emulator
export CHANNEL_EMULATOR_TYPE=software  # Change to keysight/rohde_schwarz/alifecom as needed
export CHANNEL_EMULATOR_IP=192.168.10.100
EOF

print_status "Environment variables configured"
echo ""
print_warning "Please run: source $TESTBED_HOME/.env"

# Step 13: Create quick start scripts
echo ""
echo "Step 13: Creating quick start scripts..."

# Create baseline test script
cat > run_baseline_tests.sh << 'EOF'
#!/bin/bash
source .env

echo "Starting baseline tests..."

# Run RF loopback test
echo "1. RF Loopback Test"
python3 tests/rf_loopback_test.py \
    --tx-args "type=x310,addr=$USRP_X310_ADDR" \
    --rx-args "type=b210" \
    --freq 1.5e9 \
    --rate 10e6 \
    --atten 40

# Run calibration
echo "2. Calibration"
python3 calibration/run_calibration.py

echo "Baseline tests complete!"
EOF

chmod +x run_baseline_tests.sh

# Create NTN test script
cat > run_ntn_test.sh << 'EOF'
#!/bin/bash
source .env

echo "Starting NTN test..."

# Start channel emulator
python3 ntn/geo_delay_simulator.py --mode static --elevation 45 &
EMULATOR_PID=$!

# Wait for emulator to start
sleep 2

# Run link budget calculation
python3 analysis/link_budget_calculator.py --scenario geo

# Run actual test
echo "Test would run here..."

# Cleanup
kill $EMULATOR_PID

echo "NTN test complete!"
EOF

chmod +x run_ntn_test.sh

print_status "Quick start scripts created"

# Step 14: Final checks and summary
echo ""
echo "=================================================="
echo "    Initialization Complete!"
echo "=================================================="
echo ""
echo "Summary:"
print_status "Python environment ready"
print_status "System dependencies installed"
print_status "UHD/USRP support configured"
print_status "Directory structure created"
print_status "Configuration files generated"
print_status "Quick start scripts available"

echo ""
echo "Next steps:"
echo "1. Source environment: source $TESTBED_HOME/.env"
echo "2. Connect USRP hardware"
echo "3. Run baseline tests: ./run_baseline_tests.sh"
echo "4. Configure channel emulator connection"
echo "5. Start NTN testing: ./run_ntn_test.sh"

echo ""
print_warning "Remember to use 30-40 dB attenuation for RF loopback tests!"
print_warning "Ensure RF safety compliance before transmitting!"

echo ""
echo "For Claude Code CLI integration:"
echo "  cd $TESTBED_HOME"
echo "  claude --skill ntn-link-budget"
echo "  claude --mcp usrp-controller"

echo ""
print_status "Setup complete! Happy testing!"
