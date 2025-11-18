# 5G NTN Testbed - ITRI Channel Emulator Integration Project

## Project Overview
This project implements a comprehensive 5G Non-Terrestrial Network (NTN) testbed for integration with ITRI channel emulators, focusing on GEO satellite communication scenarios with 250ms RTT challenges and 30km HAPS link validation.

## Quick Start
```bash
# Initialize the testbed environment
./scripts/init_testbed.sh

# Run baseline performance tests
./scripts/run_baseline_tests.sh

# Start NTN channel emulation
./scripts/start_ntn_emulation.sh --mode geo --rtt 250
```

## Architecture Components

### 1. Core Infrastructure
- **Host 1**: Open5GS Core Network (AMF, SMF, UPF)
- **Host 2**: srsRAN/OpenAirInterface gNB with USRP X310
- **Host 3**: UE Simulator with USRP B210
- **Channel Emulator**: ITRI/Commercial (Keysight/R&S/ALifecom)

### 2. Critical NTN Parameters
- **GEO Satellite RTT**: 250-280ms (35,786 km altitude)
- **Common Timing Advance**: 7,373,000 Ts (~240ms)
- **K_offset**: 150-239 slots for GEO
- **Doppler Shift**: ±15 Hz (GEO), ±37.5 kHz (LEO)
- **Path Loss (L-band)**: 187.09 dB at 36,000 km

### 3. 30km HAPS Link Budget
- **Free Space Path Loss**: 128.01 dB at 2 GHz
- **Required EIRP**: 36 dBm minimum
- **Link Margin Target**: 10 dB fade margin
- **Coverage Radius**: 50-200 km per cell

## Test Procedures

### Phase 1: Baseline Establishment (Days 1-2)
```bash
# Hardware validation
uhd_usrp_probe --args="type=x310,addr=192.168.10.2"

# RF loopback with mandatory 30-40 dB attenuation
./tests/rf_loopback_test.py --tx_gain 20 --rx_gain 30 --atten 40

# Calibration suite
./calibration/run_all_calibrations.sh
```

### Phase 2: NTN Channel Characterization (Days 3-5)
```bash
# GEO delay simulation
./ntn/geo_delay_simulator.py --rtt 250 --variance 5

# Doppler profile testing
./ntn/doppler_compensation.py --orbit leo --freq 1.5e9

# Link budget validation
./analysis/link_budget_calculator.py --distance 36000 --freq 1.5e9
```

### Phase 3: 30km HAPS Validation (Days 6-7)
```bash
# Path loss verification
./haps/path_loss_test.py --distance 30 --freq 2e9

# Coverage mapping
./haps/coverage_mapper.py --altitude 30 --radius 100
```

### Phase 4: Integration & Compliance (Days 8-10)
```bash
# Protocol stack integration
./integration/5g_nr_stack_test.py --mode ntn

# RF safety compliance
./compliance/rf_safety_check.py --power 33 --antenna_gain 15
```

## MCP Servers

### 1. USRP Controller (`mcp-usrp`)
Controls X310/B210 hardware, manages calibration, and monitors performance metrics.

### 2. Channel Emulator Interface (`mcp-channel`)
Interfaces with ITRI/commercial channel emulators, configures delay/doppler/loss profiles.

### 3. Test Orchestrator (`mcp-orchestrator`)
Coordinates test sequences, manages data collection, generates reports.

### 4. Spectrum Monitor (`mcp-spectrum`)
Real-time spectrum analysis, interference detection, compliance monitoring.

## Skills

### 1. `ntn-link-budget`
Calculates comprehensive link budgets for GEO/LEO/HAPS scenarios with atmospheric effects.

### 2. `usrp-calibration`
Automated DC offset, IQ imbalance, and frequency calibration procedures.

### 3. `channel-profile`
Generates 3GPP-compliant NTN channel profiles for various orbital configurations.

### 4. `rf-safety`
Calculates safe distances, power densities, and ensures regulatory compliance.

## Subagents

### 1. Performance Monitor Agent
```yaml
name: perf-monitor
role: Continuously monitors KPIs and alerts on anomalies
metrics:
  - throughput
  - latency
  - packet_loss
  - snr
  - evm
```

### 2. Calibration Agent
```yaml
name: calibration-agent
role: Maintains USRP calibration and compensates for drift
tasks:
  - frequency_offset_tracking
  - power_calibration_update
  - phase_alignment_check
```

### 3. Safety Compliance Agent
```yaml
name: safety-agent
role: Ensures RF safety and regulatory compliance
monitors:
  - power_levels
  - spurious_emissions
  - occupied_bandwidth
  - safety_perimeter
```

## Equipment Requirements

### Essential Test Equipment
1. **Spectrum Analyzer**: Rigol DSA815-TG (min) or Keysight FieldFox
2. **RF Shielding**: 100 dB isolation at L-band
3. **GPSDO**: 1×10⁻¹¹ accuracy minimum
4. **Attenuators**: 0-60 dB variable, 30 dB fixed (mandatory)
5. **Power Meter**: -40 to +20 dBm range
6. **VNA**: NanoVNA V2 (budget) or MegiQ VNA-0440e

### Safety Equipment
- RF Field Strength Meter (Narda SRM-3006 or equivalent)
- Warning Signs and Barriers
- Power Interlocks
- EMF Monitoring System

## Regulatory Compliance

### FCC Requirements (USA)
- Experimental License: Form 442
- L-band coordination with GNSS operators
- Maximum EIRP limits per Part 5

### Safety Standards
- IEEE C95.1-2019: 4-10 W/m² public exposure
- ICNIRP 2020: 61-87 V/m field strength
- Minimum safe distance: 1.2m at 2W/15dBi

## Data Collection & Analysis

### Key Metrics
```python
metrics = {
    'bler_target': 0.01,      # Block error rate
    'throughput_min': 10e6,    # Minimum 10 Mbps
    'latency_max': 280e-3,     # GEO RTT constraint
    'snr_threshold': 10,       # dB for QPSK 1/2
    'evm_limit': 12.5,         # % for 64-QAM
}
```

### Report Generation
```bash
# Generate comprehensive test report
./reporting/generate_report.py \
  --test_suite baseline \
  --output_format pdf \
  --include_plots true
```

## Troubleshooting

### Common Issues
1. **GPS Lock Failure**: Check antenna placement, sky visibility
2. **Overflow/Underflow**: Reduce sample rate or adjust buffer sizes
3. **High EVM**: Perform IQ calibration, check for interference
4. **Link Budget Deficit**: Increase antenna gain or reduce distance

### Debug Commands
```bash
# Check USRP status
uhd_find_devices

# Monitor CPU/USB performance
./tools/performance_monitor.py

# Spectrum sweep for interference
./tools/spectrum_sweep.py --start 1e9 --stop 2e9 --rbw 100e3
```

## Project Structure
```
5g-ntn-testbed/
├── CLAUDE.md                 # This file
├── mcp-servers/             # MCP server implementations
├── skills/                  # Claude Code skills
├── subagents/              # Specialized subagents
├── scripts/                # Automation scripts
├── tests/                  # Test procedures
├── calibration/           # Calibration routines
├── ntn/                   # NTN-specific implementations
├── haps/                  # HAPS test scenarios
├── integration/           # System integration tests
├── compliance/            # Regulatory compliance tools
├── analysis/              # Data analysis tools
├── configs/               # Configuration files
├── docs/                  # Additional documentation
└── results/               # Test results storage
```

## Contact & Support
- Project Lead: NYCU 5G NTN Research Team
- Integration Support: ITRI Channel Emulator Team
- Safety Officer: RF Compliance Department

## Version History
- v1.0.0: Initial release with GEO/HAPS support
- v1.1.0: Added LEO doppler compensation
- v1.2.0: Enhanced safety compliance features
- Current: v1.3.0 - ITRI integration optimizations

---
*Last Updated: November 2024*
*Classification: Research & Development*
