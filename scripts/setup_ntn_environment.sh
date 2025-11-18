#!/bin/bash
#
# 5G NTN Experiment Environment Setup Script
# For Ubuntu 22.04/24.04 LTS
# Date: 2025-11-18
#

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Log functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
       log_error "This script should not be run as root!"
       exit 1
    fi
}

# Check Ubuntu version
check_ubuntu_version() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        if [[ "$ID" != "ubuntu" ]]; then
            log_error "This script is designed for Ubuntu only"
            exit 1
        fi
        if [[ "$VERSION_ID" != "22.04" && "$VERSION_ID" != "24.04" ]]; then
            log_warn "This script is tested on Ubuntu 22.04 and 24.04"
        fi
        log_info "Ubuntu version: $VERSION"
    else
        log_error "Cannot determine OS version"
        exit 1
    fi
}

# Update system packages
update_system() {
    log_info "Updating system packages..."
    sudo apt-get update
    sudo apt-get upgrade -y
}

# Install basic dependencies
install_basic_deps() {
    log_info "Installing basic dependencies..."
    sudo apt-get install -y \
        build-essential \
        cmake \
        git \
        python3-pip \
        python3-dev \
        python3-numpy \
        python3-scipy \
        python3-matplotlib \
        libboost-all-dev \
        libusb-1.0-0-dev \
        libudev-dev \
        libncurses5-dev \
        libfftw3-dev \
        libssl-dev \
        libgmp-dev \
        libgnutls28-dev \
        libsctp-dev \
        libconfig++-dev \
        curl \
        wget \
        vim \
        htop \
        iperf3 \
        wireshark \
        tcpdump
}

# Install UHD (USRP Hardware Driver)
install_uhd() {
    log_info "Installing UHD (USRP Hardware Driver)..."
    
    # Add Ettus Research PPA
    sudo add-apt-repository ppa:ettusresearch/uhd -y
    sudo apt-get update
    
    # Install UHD
    sudo apt-get install -y libuhd-dev uhd-host
    
    # Download FPGA images
    log_info "Downloading USRP FPGA images..."
    sudo uhd_images_downloader
    
    # Set up udev rules
    log_info "Setting up USRP udev rules..."
    sudo cp /usr/lib/uhd/utils/uhd-usrp.rules /etc/udev/rules.d/
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    
    # Add user to usrp group
    sudo groupadd -f usrp
    sudo usermod -a -G usrp $USER
    
    log_info "UHD installed. Version: $(uhd_config_info --version)"
}

# Install GNU Radio
install_gnuradio() {
    log_info "Installing GNU Radio..."
    
    # Ubuntu 22.04 and 24.04 have GNU Radio in standard repos
    sudo apt-get install -y gnuradio gnuradio-dev
    
    # Install additional GNU Radio modules
    sudo apt-get install -y \
        gr-osmosdr \
        gr-gsm \
        gqrx-sdr
    
    log_info "GNU Radio installed"
}

# Install srsRAN with NTN support
install_srsran_ntn() {
    log_info "Installing srsRAN with NTN support..."
    
    # Create workspace
    mkdir -p ~/ntn_workspace/srsran
    cd ~/ntn_workspace/srsran
    
    # Clone srsRAN Project (assuming NTN branch exists)
    if [[ ! -d "srsRAN_Project" ]]; then
        git clone https://github.com/srsran/srsRAN_Project.git
        cd srsRAN_Project
        
        # Check for NTN branch/tag
        if git branch -r | grep -q "ntn"; then
            git checkout ntn
        else
            log_warn "NTN branch not found, using main branch"
        fi
    else
        cd srsRAN_Project
        git pull
    fi
    
    # Build srsRAN
    mkdir -p build
    cd build
    cmake -DCMAKE_BUILD_TYPE=Release \
          -DENABLE_NTN=ON \
          -DUSE_LTE_RATES=ON ..
    make -j$(nproc)
    sudo make install
    sudo ldconfig
    
    log_info "srsRAN installed"
}

# Install Open5GS
install_open5gs() {
    log_info "Installing Open5GS..."
    
    # Add Open5GS repository
    sudo add-apt-repository ppa:open5gs/latest -y
    sudo apt-get update
    
    # Install Open5GS
    sudo apt-get install -y open5gs
    
    # Install WebUI dependencies
    curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    sudo apt-get install -y nodejs
    
    cd ~/ntn_workspace
    if [[ ! -d "open5gs" ]]; then
        git clone https://github.com/open5gs/open5gs.git
    fi
    
    log_info "Open5GS installed"
}

# Install Python packages for testing
install_python_packages() {
    log_info "Installing Python packages..."
    
    pip3 install --user \
        numpy \
        scipy \
        matplotlib \
        pyvisa \
        pyvisa-py \
        pyserial \
        pandas \
        jupyter \
        ipython \
        pyqt5 \
        pyqtgraph
        
    # Install UHD Python bindings
    pip3 install --user uhd
    
    log_info "Python packages installed"
}

# Configure system performance
configure_performance() {
    log_info "Configuring system for optimal performance..."
    
    # CPU Governor
    if command -v cpupower &> /dev/null; then
        sudo cpupower frequency-set -g performance
    else
        log_warn "cpupower not found, installing..."
        sudo apt-get install -y linux-tools-common linux-tools-generic
        sudo cpupower frequency-set -g performance
    fi
    
    # Increase network buffer sizes
    cat << EOF | sudo tee /etc/sysctl.d/99-ntn-performance.conf
# Network buffer tuning for SDR
net.core.rmem_max = 50000000
net.core.wmem_max = 50000000
net.core.rmem_default = 50000000
net.core.wmem_default = 50000000
net.ipv4.tcp_rmem = 4096 87380 50000000
net.ipv4.tcp_wmem = 4096 65536 50000000
net.ipv4.tcp_congestion_control = bbr
net.core.netdev_max_backlog = 5000

# Real-time settings
kernel.sched_rt_runtime_us = -1
kernel.sched_rt_period_us = 1000000
EOF
    
    sudo sysctl -p /etc/sysctl.d/99-ntn-performance.conf
    
    # Configure USB autosuspend
    echo 'SUBSYSTEM=="usb", ATTR{idVendor}=="2500", ATTR{idProduct}=="0020", MODE="0666", GROUP="usrp"' | \
        sudo tee /etc/udev/rules.d/99-usrp-b210.rules
    
    # Disable USB autosuspend for USRP devices
    echo 'ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="2500", TEST=="power/control", ATTR{power/control}="on"' | \
        sudo tee -a /etc/udev/rules.d/99-usrp-b210.rules
    
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    
    log_info "Performance configuration complete"
}

# Create workspace structure
create_workspace() {
    log_info "Creating workspace structure..."
    
    mkdir -p ~/ntn_workspace/{configs,logs,data,scripts,docs}
    
    # Create a sample configuration file
    cat << EOF > ~/ntn_workspace/configs/ntn_config.yaml
# 5G NTN Configuration File
# Generated: $(date)

system:
  name: "5G NTN Experiment"
  version: "1.0"

usrp_x310:
  ip_address: "192.168.10.2"
  clock_source: "gpsdo"
  time_source: "gpsdo"
  
usrp_b210:
  serial: "auto"
  clock_source: "internal"
  
rf_parameters:
  center_frequency: 1.8e9  # 1.8 GHz (L-band)
  bandwidth: 30e6          # 30 MHz
  sample_rate: 30.72e6     # 30.72 MHz
  tx_gain: 20              # dB
  rx_gain: 40              # dB
  
channel_emulator:
  ip_address: "192.168.1.100"
  profile: "GEO_NTN"
  delay_ms: 250
  path_loss_db: 190
EOF
    
    log_info "Workspace created at ~/ntn_workspace"
}

# Test USRP connectivity
test_usrp() {
    log_info "Testing USRP connectivity..."
    
    # Find USRP devices
    uhd_find_devices
    
    # Test USRP B210
    if lsusb | grep -q "2500:0020"; then
        log_info "USRP B210 detected via USB"
        uhd_usrp_probe --args="type=b200"
    else
        log_warn "USRP B210 not detected"
    fi
    
    # Test USRP X310 (if network configured)
    if ping -c 1 192.168.10.2 &> /dev/null; then
        log_info "USRP X310 reachable at 192.168.10.2"
        uhd_usrp_probe --args="addr=192.168.10.2"
    else
        log_warn "USRP X310 not reachable at default IP"
    fi
}

# Install monitoring tools
install_monitoring() {
    log_info "Installing monitoring tools..."
    
    # Install monitoring tools
    sudo apt-get install -y \
        iftop \
        nethogs \
        bmon \
        nload \
        speedometer \
        slurm \
        tcptrack \
        vnstat \
        bwm-ng \
        cbm \
        netstat-nat \
        ifstat \
        dstat \
        collectl
    
    # Install Grafana and Prometheus (optional)
    read -p "Install Grafana and Prometheus for advanced monitoring? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Prometheus
        wget https://github.com/prometheus/prometheus/releases/download/v2.40.0/prometheus-2.40.0.linux-amd64.tar.gz
        tar xvf prometheus-*.tar.gz
        sudo cp prometheus-*/prometheus /usr/local/bin/
        sudo cp prometheus-*/promtool /usr/local/bin/
        
        # Grafana
        sudo apt-get install -y software-properties-common
        wget -q -O - https://packages.grafana.com/gpg.key | sudo apt-key add -
        sudo add-apt-repository "deb https://packages.grafana.com/oss/deb stable main"
        sudo apt-get update
        sudo apt-get install -y grafana
        
        log_info "Grafana and Prometheus installed"
    fi
}

# Main installation menu
main_menu() {
    echo "=================================="
    echo "5G NTN Environment Setup Script"
    echo "=================================="
    echo "1) Full installation (recommended)"
    echo "2) Install UHD only"
    echo "3) Install GNU Radio only"
    echo "4) Install srsRAN NTN only"
    echo "5) Install Open5GS only"
    echo "6) Configure performance only"
    echo "7) Test USRP devices"
    echo "8) Exit"
    echo "=================================="
    read -p "Select option: " choice
    
    case $choice in
        1)
            update_system
            install_basic_deps
            install_uhd
            install_gnuradio
            install_srsran_ntn
            install_open5gs
            install_python_packages
            configure_performance
            create_workspace
            install_monitoring
            test_usrp
            ;;
        2) install_uhd ;;
        3) install_gnuradio ;;
        4) install_srsran_ntn ;;
        5) install_open5gs ;;
        6) configure_performance ;;
        7) test_usrp ;;
        8) exit 0 ;;
        *) log_error "Invalid option" ;;
    esac
}

# Main execution
main() {
    check_root
    check_ubuntu_version
    
    log_info "Starting 5G NTN Environment Setup"
    log_info "This will configure your system for NTN experiments"
    
    main_menu
    
    log_info "Setup complete!"
    log_warn "Please log out and log in again for group changes to take effect"
    log_info "Check ~/ntn_workspace for configuration files and scripts"
}

# Run main function
main "$@"
