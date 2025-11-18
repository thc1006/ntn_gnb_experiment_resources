# 🚀 Quick Start Guide - 5G NTN Software Testbed

**Get running in under 5 minutes!**

---

## ⚡ One-Line Installation

```bash
# Linux/macOS
./scripts/quick_start.sh --gpu

# Windows PowerShell
python scripts\quick_start.py --gpu

# Or manually
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python -m src.simulators.demo_full_simulation
```

That's it! The simulation will run and generate results.

---

## 📋 Prerequisites

**Minimum:**
- Python 3.8+
- 8 GB RAM
- Any modern CPU

**Recommended:**
- Python 3.11+
- 16 GB RAM
- NVIDIA GPU with CUDA (for 10-100x speedup)

**No hardware required!** No USRP, no channel emulator, no RF equipment.

---

## 🎯 Quick Examples

### Example 1: Run Complete Demo (All Scenarios)
```bash
# Activates venv and runs GEO, LEO, and HAPS simulations
python -m src.simulators.demo_full_simulation

# Results saved to:
# - results/simulation_results.json
# - results/spectrum_*.png
```

**Expected output:**
```
========================================
Scenario 1: GEO Satellite Link
========================================
🔧 Creating USRP simulators...
✅ Software USRP initialized: x310
✅ Software USRP initialized: b210

🛰️  Creating GEO channel emulator (35,786 km)...
✅ Software Channel Emulator initialized: geo

📡 Generating 5G NR wideband signal...
📤 Transmitting...
🌍 Propagating through GEO satellite channel...
📥 Receiving...

📊 Results:
   TX Power: 23.4 dBm
   RX Power: -166.7 dBm
   Path Loss: 190.1 dB
   Delay: 250.3 ms
   SNR: 15.2 dB
```

### Example 2: Run Individual USRP Simulator
```bash
# Test USRP simulation only
python -m src.simulators.usrp_simulator
```

### Example 3: Run Channel Simulator
```bash
# Test channel emulation only
python -m src.simulators.channel_simulator
```

### Example 4: Use Python API
```python
from src.simulators import SimulatorFactory, ChannelEmulatorFactory

# Create TX and RX
tx = SimulatorFactory.create_x310()
rx = SimulatorFactory.create_b210()

# Create GEO channel
channel = ChannelEmulatorFactory.create_geo(elevation_deg=45)

# Generate signal
signal = tx.generate_test_tone(freq_offset=1e6, duration=0.01)

# Propagate through channel
tx.transmit(signal)
rx_signal = channel.apply_channel(signal)

# Analyze
import numpy as np
tx_power = 10 * np.log10(np.mean(np.abs(signal)**2)) + 30
rx_power = 10 * np.log10(np.mean(np.abs(rx_signal)**2)) + 30
print(f"Path Loss: {tx_power - rx_power:.2f} dB")
```

---

## 🐳 Docker Quick Start

### Option 1: Docker Run (Simple)
```bash
# CPU-only
docker build -t ntn-testbed .
docker run -v $(pwd)/results:/app/results ntn-testbed

# With GPU
docker build --target gpu-final -t ntn-testbed:gpu .
docker run --gpus all -v $(pwd)/results:/app/results ntn-testbed:gpu
```

### Option 2: Docker Compose (Full Stack)
```bash
# Start all services (testbed + jupyter + monitoring)
docker-compose up -d

# View logs
docker-compose logs -f ntn-testbed

# Access services:
# - Results: ./results/
# - Jupyter: http://localhost:8888 (token: ntn-testbed-2024)
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/ntn-testbed-2024)

# Stop all
docker-compose down
```

---

## ☸️ Kubernetes (Kind) Quick Start

```bash
# Create Kind cluster
kind create cluster --config kubernetes/kind-config.yaml

# Deploy testbed
kubectl apply -f kubernetes/deployment.yaml

# Check status
kubectl get pods -n ntn-testbed

# View logs
kubectl logs -f deployment/ntn-testbed -n ntn-testbed

# Port forward Jupyter
kubectl port-forward svc/jupyter 8888:8888 -n ntn-testbed

# Access Jupyter at http://localhost:8888
```

---

## 🧪 Running Different Scenarios

### GEO Satellite (35,786 km, 250ms RTT)
```python
from src.simulators import SimulatorFactory, ChannelEmulatorFactory

tx = SimulatorFactory.create_x310()
rx = SimulatorFactory.create_b210()
channel = ChannelEmulatorFactory.create_geo(elevation_deg=45)

signal = tx.generate_ofdm_signal(1024, 0.01)
tx.transmit(signal)
rx_signal = channel.apply_channel(signal)

print(f"Delay: {channel.propagation_delay_s * 1000:.2f} ms")
print(f"Path Loss: {channel.path_loss_db:.2f} dB")
```

### LEO Satellite (600 km, strong Doppler)
```python
channel = ChannelEmulatorFactory.create_leo(altitude_km=600)

signal = tx.generate_test_tone(1e6, 0.01)
rx_signal = channel.apply_channel(signal)

print(f"Doppler Shift: {channel.satellite_state.doppler_hz:.2f} Hz")
print(f"Delay: {channel.propagation_delay_s * 1000:.2f} ms")
```

### HAPS (30 km, minimal delay)
```python
channel = ChannelEmulatorFactory.create_haps(altitude_km=30, elevation_deg=60)

signal = tx.generate_ofdm_signal(1024, 0.01)
rx_signal = channel.apply_channel(signal)

print(f"Delay: {channel.propagation_delay_s * 1e6:.2f} μs")
print(f"Path Loss: {channel.path_loss_db:.2f} dB")
```

---

## 🔧 MCP Server Usage

### Start MCP Servers

#### USRP Simulator MCP
```bash
python mcp-servers/mcp_usrp_simulator.py
```

Available functions:
- `list_devices()` - List all simulated USRPs
- `create_device(device_type)` - Create X310 or B210
- `set_frequency(device_id, freq_hz)` - Set TX/RX frequency
- `set_gain(device_id, gain_db)` - Set TX/RX gain
- `calibrate_dc_offset(device_id)` - Run DC offset calibration
- `transmit_signal(device_id, signal_type)` - Transmit signal
- `receive_samples(device_id, num_samples)` - Receive samples

#### Channel Emulator MCP
```bash
python mcp-servers/mcp_channel_simulator.py
```

Available functions:
- `list_channels()` - List all channels
- `create_channel(orbit_type)` - Create GEO/LEO/HAPS channel
- `get_channel_state(channel_id)` - Get current state
- `set_elevation_angle(channel_id, angle)` - Change elevation
- `set_rain_rate(channel_id, rate)` - Set rain attenuation
- `get_link_budget(channel_id, ...)` - Calculate link budget
- `start_dynamic_simulation(channel_id)` - Start LEO orbit simulation

---

## 📊 Analysis Tools

### Link Budget Calculator
```bash
# GEO scenario
python analysis/link_budget_calculator.py --scenario geo --freq 1.5e9

# LEO scenario
python analysis/link_budget_calculator.py --scenario leo --freq 2.0e9 --altitude 600

# HAPS 30km
python analysis/link_budget_calculator.py --scenario haps --freq 2.0e9 --altitude 30
```

### GEO Delay Simulator
```bash
# Static delay
python ntn/geo_delay_simulator.py --mode static --rtt 250

# Dynamic with elevation changes
python ntn/geo_delay_simulator.py --mode dynamic --elevation 45
```

---

## 🎓 Using Claude Code Skills

### NTN Link Budget Skill
```bash
# Calculate GEO link budget
ntn-link-budget calculate --scenario geo --freq 1.5

# Optimize for required SNR
ntn-link-budget optimize --scenario haps --target_snr 15

# Compare scenarios
ntn-link-budget compare --scenarios geo,leo,haps --freq 2.0
```

### RF Safety Skill
```bash
# Calculate safe distance
rf-safety calculate-distance --power 33 --gain 15 --freq 2.0

# Check compliance
rf-safety check-compliance --power 40 --gain 20 --distance 2.0

# Power density calculation
rf-safety power-density --eirp 46 --distance 10
```

---

## 🐛 Troubleshooting

### Issue: "Module 'simulators' not found"
**Solution:**
```bash
# Make sure you're in the project root directory
cd NTN_ITRI

# Activate virtual environment
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Verify installation
python -c "import simulators; print('OK')"
```

### Issue: "CuPy not found" (GPU)
**Solution:**
```bash
# Check CUDA version
nvcc --version

# Install matching CuPy
pip install cupy-cuda12x  # CUDA 12.x
pip install cupy-cuda11x  # CUDA 11.x

# Verify
python -c "import cupy; print(f'CuPy {cupy.__version__}')"
```

### Issue: Plots not showing
**Solution:**
```bash
# Check matplotlib backend
python -c "import matplotlib; print(matplotlib.get_backend())"

# If using headless server, results are saved to files
ls results/spectrum_*.png
```

### Issue: Permission denied on scripts/quick_start.sh
**Solution:**
```bash
chmod +x scripts/quick_start.sh
./scripts/quick_start.sh
```

---

## 📈 Performance Tips

### Enable GPU Acceleration
```bash
# Install CuPy
pip install cupy-cuda12x

# Verify GPU detected
python -c "from src.simulators import GPU_AVAILABLE; print(f'GPU: {GPU_AVAILABLE}')"
```

**Speed improvements:**
- GEO 1s signal: 2.5s (CPU) → 0.3s (GPU) = **8.3x faster**
- LEO 10s signal: 25s (CPU) → 1.8s (GPU) = **13.9x faster**

### Reduce Memory Usage
```python
# Use smaller signal durations
signal = tx.generate_ofdm_signal(1024, duration=0.001)  # 1ms instead of 10ms

# Disable IQ sample saving in config
config["simulation"]["save_iq_samples"] = False
```

### Parallel Processing
```python
import multiprocessing as mp

# Run multiple scenarios in parallel
with mp.Pool(processes=3) as pool:
    results = pool.map(run_scenario, ['geo', 'leo', 'haps'])
```

---

## 📚 Next Steps

1. **Review Results**: Check `results/` directory for plots and JSON data
2. **Modify Configuration**: Edit `config/testbed_config.yaml`
3. **Read Documentation**:
   - [PROJECT_ANALYSIS.md](PROJECT_ANALYSIS.md) - Comprehensive analysis
   - [SETUP_SUMMARY.md](SETUP_SUMMARY.md) - Setup details
   - [CLAUDE.md](CLAUDE.md) - Claude Code integration
4. **Explore Code**: Check `src/simulators/` for implementation details
5. **Run Tests**: `pytest tests/`
6. **Deploy**: Use Docker or Kubernetes for production

---

## 🎉 Success Criteria

✅ **Basic Success** (1 minute):
```bash
python -m src.simulators.demo_full_simulation
# See "✅ Simulation complete!" message
```

✅ **Docker Success** (5 minutes):
```bash
docker-compose up -d
docker-compose logs ntn-testbed | grep "Simulation complete"
```

✅ **K8s Success** (10 minutes):
```bash
kubectl get pods -n ntn-testbed
kubectl logs deployment/ntn-testbed -n ntn-testbed | grep "complete"
```

---

## 💡 Tips for Claude Code Users

### New Session Quick Start
```bash
# In any new Claude Code session:
cd NTN_ITRI
source venv/bin/activate
python -m src.simulators.demo_full_simulation
```

### MCP Integration
- MCP servers auto-discovered from `mcp-servers/`
- Skills available: `ntn-link-budget`, `rf-safety`
- Subagent: `performance_monitor`

### Immediate Testing
```python
# Quick validation in Python REPL
from src.simulators import SimulatorFactory, ChannelEmulatorFactory
tx = SimulatorFactory.create_x310()
print(tx.get_device_info())
```

---

**Questions?** See [README.md](README.md) or [PROJECT_ANALYSIS.md](PROJECT_ANALYSIS.md) for detailed documentation.

**Ready?** Run `python -m src.simulators.demo_full_simulation` now! 🚀
