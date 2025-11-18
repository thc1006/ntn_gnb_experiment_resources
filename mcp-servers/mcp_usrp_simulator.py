#!/usr/bin/env python3
"""
MCP Server: USRP Simulator Controller
======================================
Software-only USRP control - No hardware required!
Manages simulated X310/B210 devices, calibration, and performance monitoring
"""

import asyncio
import json
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.simulators.usrp_simulator import SimulatorFactory, SoftwareUSRP, USRPConfig


class USRPSimulatorMCP:
    """MCP Server for Software USRP Control (No Hardware Required)"""

    def __init__(self):
        self.logger = logging.getLogger("mcp-usrp-simulator")
        self.devices: Dict[str, SoftwareUSRP] = {}
        self.calibration_data: Dict[str, Dict] = {}
        self.performance_metrics: Dict[str, Dict] = {}
        self.device_counter = 0

        self.logger.info("✅ USRP Simulator MCP Server initialized (Software-only)")

    async def initialize(self):
        """Initialize MCP server and create simulated USRP devices"""
        self.logger.info("Initializing USRP Simulator MCP Server")

        # Create default simulators
        await self.create_default_simulators()
        await self.load_calibrations()

        self.logger.info(f"✅ MCP Server ready with {len(self.devices)} simulated devices")

    async def create_default_simulators(self):
        """Create default TX (X310) and RX (B210) simulators"""
        # Create TX simulator (X310)
        tx_id = "sim://x310-tx-001"
        self.devices[tx_id] = SimulatorFactory.create_x310(addr=tx_id)
        self.devices[tx_id].device_id = tx_id

        # Create RX simulator (B210)
        rx_id = "sim://b210-rx-001"
        self.devices[rx_id] = SimulatorFactory.create_b210(serial=rx_id)
        self.devices[rx_id].device_id = rx_id

        self.logger.info(f"Created default simulators: {tx_id}, {rx_id}")

        # Initialize performance metrics
        for device_id in [tx_id, rx_id]:
            self.performance_metrics[device_id] = {
                "samples_transmitted": 0,
                "samples_received": 0,
                "overruns": 0,
                "underruns": 0,
                "late_commands": 0,
                "uptime_s": 0,
            }

    async def load_calibrations(self):
        """Load calibration data from file (if exists)"""
        calib_file = Path("calibrations.json")
        if calib_file.exists():
            try:
                with open(calib_file, 'r') as f:
                    self.calibration_data = json.load(f)
                self.logger.info(f"Loaded calibrations for {len(self.calibration_data)} devices")
            except Exception as e:
                self.logger.warning(f"Failed to load calibrations: {e}")
        else:
            self.logger.info("No calibration file found, starting fresh")

    async def save_calibrations(self):
        """Save calibration data to file"""
        try:
            with open("calibrations.json", 'w') as f:
                json.dump(self.calibration_data, f, indent=2)
            self.logger.info("Calibrations saved")
        except Exception as e:
            self.logger.error(f"Failed to save calibrations: {e}")

    # ============ MCP Tool Functions ============

    async def list_devices(self) -> Dict[str, Any]:
        """
        List all available simulated USRP devices

        Returns:
            Dictionary of device information
        """
        devices_info = {}
        for device_id, device in self.devices.items():
            info = device.get_device_info()
            info["device_id"] = device_id
            info["connected"] = True
            info["mode"] = "software_simulator"

            # Add performance metrics if available
            if device_id in self.performance_metrics:
                info["performance"] = self.performance_metrics[device_id]

            devices_info[device_id] = info

        return {
            "success": True,
            "device_count": len(devices_info),
            "devices": devices_info
        }

    async def create_device(self, device_type: str, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new simulated USRP device

        Args:
            device_type: "x310" or "b210"
            device_id: Optional custom device ID

        Returns:
            Device creation result
        """
        if device_id is None:
            self.device_counter += 1
            device_id = f"sim://{device_type}-{self.device_counter:03d}"

        if device_id in self.devices:
            return {
                "success": False,
                "error": f"Device {device_id} already exists"
            }

        try:
            if device_type.lower() == "x310":
                device = SimulatorFactory.create_x310(addr=device_id)
            elif device_type.lower() == "b210":
                device = SimulatorFactory.create_b210(serial=device_id)
            else:
                return {
                    "success": False,
                    "error": f"Unknown device type: {device_type}. Use 'x310' or 'b210'"
                }

            device.device_id = device_id
            self.devices[device_id] = device

            self.performance_metrics[device_id] = {
                "samples_transmitted": 0,
                "samples_received": 0,
                "overruns": 0,
                "underruns": 0,
                "late_commands": 0,
                "uptime_s": 0,
            }

            self.logger.info(f"Created {device_type} simulator: {device_id}")

            return {
                "success": True,
                "device_id": device_id,
                "device_type": device_type,
                "info": device.get_device_info()
            }

        except Exception as e:
            self.logger.error(f"Failed to create device: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_device_info(self, device_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a specific device

        Args:
            device_id: Device identifier

        Returns:
            Device information dictionary
        """
        if device_id not in self.devices:
            return {
                "success": False,
                "error": f"Device {device_id} not found"
            }

        device = self.devices[device_id]
        info = device.get_device_info()
        info["device_id"] = device_id

        # Add calibration data if available
        if device_id in self.calibration_data:
            info["calibration"] = self.calibration_data[device_id]

        # Add performance metrics
        if device_id in self.performance_metrics:
            info["performance"] = self.performance_metrics[device_id]

        return {
            "success": True,
            "device_info": info
        }

    async def set_frequency(self, device_id: str, freq_hz: float, direction: str = "both") -> Dict[str, Any]:
        """
        Set TX/RX frequency

        Args:
            device_id: Device identifier
            freq_hz: Frequency in Hz
            direction: "tx", "rx", or "both"

        Returns:
            Operation result
        """
        if device_id not in self.devices:
            return {"success": False, "error": f"Device {device_id} not found"}

        device = self.devices[device_id]

        try:
            if direction in ["tx", "both"]:
                device.set_tx_freq(freq_hz)
            if direction in ["rx", "both"]:
                device.set_rx_freq(freq_hz)

            self.logger.info(f"Set frequency for {device_id}: {freq_hz/1e9:.3f} GHz ({direction})")

            return {
                "success": True,
                "device_id": device_id,
                "frequency_hz": freq_hz,
                "frequency_ghz": freq_hz / 1e9,
                "direction": direction
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def set_gain(self, device_id: str, gain_db: float, direction: str = "both") -> Dict[str, Any]:
        """
        Set TX/RX gain

        Args:
            device_id: Device identifier
            gain_db: Gain in dB
            direction: "tx", "rx", or "both"

        Returns:
            Operation result
        """
        if device_id not in self.devices:
            return {"success": False, "error": f"Device {device_id} not found"}

        device = self.devices[device_id]

        try:
            if direction in ["tx", "both"]:
                device.set_tx_gain(gain_db)
            if direction in ["rx", "both"]:
                device.set_rx_gain(gain_db)

            self.logger.info(f"Set gain for {device_id}: {gain_db} dB ({direction})")

            return {
                "success": True,
                "device_id": device_id,
                "gain_db": gain_db,
                "direction": direction
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def calibrate_dc_offset(self, device_id: str) -> Dict[str, Any]:
        """
        Perform DC offset calibration

        Args:
            device_id: Device identifier

        Returns:
            Calibration results
        """
        if device_id not in self.devices:
            return {"success": False, "error": f"Device {device_id} not found"}

        device = self.devices[device_id]

        try:
            self.logger.info(f"Starting DC offset calibration for {device_id}")
            result = await device.calibrate_dc_offset()

            # Store calibration data
            if device_id not in self.calibration_data:
                self.calibration_data[device_id] = {}

            self.calibration_data[device_id]["dc_offset"] = {
                "dc_i": result["dc_i"],
                "dc_q": result["dc_q"],
                "corrected": result["corrected"],
                "timestamp": datetime.now().isoformat()
            }

            await self.save_calibrations()

            return {
                "success": True,
                "device_id": device_id,
                "calibration_type": "dc_offset",
                "results": result
            }

        except Exception as e:
            self.logger.error(f"DC offset calibration failed: {e}")
            return {"success": False, "error": str(e)}

    async def calibrate_iq_imbalance(self, device_id: str) -> Dict[str, Any]:
        """
        Perform IQ imbalance calibration

        Args:
            device_id: Device identifier

        Returns:
            Calibration results
        """
        if device_id not in self.devices:
            return {"success": False, "error": f"Device {device_id} not found"}

        device = self.devices[device_id]

        try:
            self.logger.info(f"Starting IQ imbalance calibration for {device_id}")
            result = await device.calibrate_iq_imbalance()

            # Store calibration data
            if device_id not in self.calibration_data:
                self.calibration_data[device_id] = {}

            self.calibration_data[device_id]["iq_imbalance"] = {
                "image_rejection_db": result["image_rejection_db"],
                "corrected": result["corrected"],
                "timestamp": datetime.now().isoformat()
            }

            await self.save_calibrations()

            return {
                "success": True,
                "device_id": device_id,
                "calibration_type": "iq_imbalance",
                "results": result
            }

        except Exception as e:
            self.logger.error(f"IQ imbalance calibration failed: {e}")
            return {"success": False, "error": str(e)}

    async def transmit_signal(self, device_id: str, signal_type: str, **params) -> Dict[str, Any]:
        """
        Generate and transmit signal

        Args:
            device_id: Device identifier
            signal_type: "tone", "ofdm", or "random"
            params: Signal generation parameters

        Returns:
            Transmission result
        """
        if device_id not in self.devices:
            return {"success": False, "error": f"Device {device_id} not found"}

        device = self.devices[device_id]

        try:
            if signal_type == "tone":
                freq_offset = params.get("freq_offset", 1e6)
                duration = params.get("duration", 0.01)
                amplitude = params.get("amplitude", 0.7)
                signal = device.generate_test_tone(freq_offset, duration, amplitude)

            elif signal_type == "ofdm":
                num_subcarriers = params.get("num_subcarriers", 1024)
                duration = params.get("duration", 0.01)
                signal = device.generate_ofdm_signal(num_subcarriers, duration)

            else:
                return {"success": False, "error": f"Unknown signal type: {signal_type}"}

            # Transmit
            num_samples = device.transmit(signal)

            # Update metrics
            self.performance_metrics[device_id]["samples_transmitted"] += num_samples

            self.logger.info(f"Transmitted {num_samples} samples from {device_id}")

            return {
                "success": True,
                "device_id": device_id,
                "signal_type": signal_type,
                "samples_transmitted": num_samples,
                "duration_ms": len(signal) / device.config.sample_rate * 1000,
                "params": params
            }

        except Exception as e:
            self.logger.error(f"Transmission failed: {e}")
            return {"success": False, "error": str(e)}

    async def receive_samples(self, device_id: str, num_samples: int, add_noise: bool = True) -> Dict[str, Any]:
        """
        Receive samples

        Args:
            device_id: Device identifier
            num_samples: Number of samples to receive
            add_noise: Whether to add noise

        Returns:
            Reception result with signal statistics
        """
        if device_id not in self.devices:
            return {"success": False, "error": f"Device {device_id} not found"}

        device = self.devices[device_id]

        try:
            # Receive samples
            samples = device.receive(num_samples, add_noise)

            # Update metrics
            self.performance_metrics[device_id]["samples_received"] += len(samples)

            # Calculate statistics
            power_dbm = 10 * np.log10(np.mean(np.abs(samples)**2) + 1e-10) + 30

            self.logger.debug(f"Received {len(samples)} samples from {device_id}")

            return {
                "success": True,
                "device_id": device_id,
                "samples_received": len(samples),
                "power_dbm": float(power_dbm),
                "duration_ms": len(samples) / device.config.sample_rate * 1000,
                # Note: Not returning actual samples to avoid large payloads
                # Use get_samples() if you need the actual data
            }

        except Exception as e:
            self.logger.error(f"Reception failed: {e}")
            return {"success": False, "error": str(e)}

    async def get_performance_metrics(self, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get performance metrics

        Args:
            device_id: Optional device identifier (returns all if None)

        Returns:
            Performance metrics
        """
        if device_id:
            if device_id not in self.performance_metrics:
                return {"success": False, "error": f"Device {device_id} not found"}

            return {
                "success": True,
                "device_id": device_id,
                "metrics": self.performance_metrics[device_id]
            }
        else:
            return {
                "success": True,
                "metrics": self.performance_metrics
            }


# ============ MCP Server Entry Point ============

async def main():
    """Run MCP server"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create and initialize server
    server = USRPSimulatorMCP()
    await server.initialize()

    # Keep server running
    print("\n" + "="*60)
    print("USRP Simulator MCP Server Running")
    print("="*60)
    print("\nAvailable devices:")
    devices = await server.list_devices()
    for device_id, info in devices["devices"].items():
        print(f"  - {device_id}: {info['device_type']} (mode: {info['mode']})")

    print("\n✅ Server ready for MCP calls")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down...")


if __name__ == "__main__":
    asyncio.run(main())
