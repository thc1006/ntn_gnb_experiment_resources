"""
Software Simulators Package
============================

Replaces physical hardware with pure software simulation:
- USRP X310/B210 → usrp_simulator.py
- ITRI/Keysight Channel Emulator → channel_simulator.py

Features:
- GPU acceleration via CuPy (optional)
- Hardware imperfection simulation
- 3GPP NTN channel models (GEO/LEO/HAPS)
- Full end-to-end testbed simulation

Usage:
------
from src.simulators import SimulatorFactory, ChannelEmulatorFactory

# Create TX and RX USRP simulators
tx = SimulatorFactory.create_x310()
rx = SimulatorFactory.create_b210()

# Create GEO channel emulator
channel = ChannelEmulatorFactory.create_geo(elevation_deg=45)

# Generate signal
signal = tx.generate_test_tone(freq_offset=1e6, duration=0.01)

# Transmit -> Channel -> Receive
tx.transmit(signal)
channel_output = channel.apply_channel(signal)
rx_signal = rx.receive(len(signal))
"""

from .usrp_simulator import (
    SoftwareUSRP,
    USRPConfig,
    SimulatorFactory,
    GPU_AVAILABLE as USRP_GPU,
)

from .channel_simulator import (
    SoftwareChannelEmulator,
    ChannelConfig,
    ChannelEmulatorFactory,
    OrbitType,
    ChannelModel,
    SatelliteState,
    GPU_AVAILABLE as CHANNEL_GPU,
)

__version__ = "2.0.0"
__all__ = [
    # USRP Simulator
    "SoftwareUSRP",
    "USRPConfig",
    "SimulatorFactory",

    # Channel Emulator
    "SoftwareChannelEmulator",
    "ChannelConfig",
    "ChannelEmulatorFactory",
    "OrbitType",
    "ChannelModel",
    "SatelliteState",

    # GPU status
    "USRP_GPU",
    "CHANNEL_GPU",
]

# Check GPU availability
GPU_AVAILABLE = USRP_GPU and CHANNEL_GPU

# Note: Suppress output during imports (can be checked via GPU_AVAILABLE variable)
