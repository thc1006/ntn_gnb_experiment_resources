#!/usr/bin/env python3
"""
MCP Server: Channel Emulator Simulator Controller
==================================================
Software-only channel emulation - No hardware required!
Simulates ITRI/Keysight/Spirent channel emulators for GEO/LEO/HAPS scenarios
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

from src.simulators.channel_simulator import (
    ChannelEmulatorFactory,
    SoftwareChannelEmulator,
    ChannelConfig,
    OrbitType,
    ChannelModel
)


class ChannelSimulatorMCP:
    """MCP Server for Software Channel Emulator (No Hardware Required)"""

    def __init__(self):
        self.logger = logging.getLogger("mcp-channel-simulator")
        self.channels: Dict[str, SoftwareChannelEmulator] = {}
        self.channel_counter = 0
        self.simulation_tasks: Dict[str, asyncio.Task] = {}

        self.logger.info("✅ Channel Emulator Simulator MCP Server initialized (Software-only)")

    async def initialize(self):
        """Initialize MCP server and create default channel emulators"""
        self.logger.info("Initializing Channel Emulator Simulator MCP Server")

        # Create default channels
        await self.create_default_channels()

        self.logger.info(f"✅ MCP Server ready with {len(self.channels)} simulated channels")

    async def create_default_channels(self):
        """Create default channel emulators for common scenarios"""
        # GEO channel
        geo_id = "sim://geo-channel-001"
        self.channels[geo_id] = ChannelEmulatorFactory.create_geo(elevation_deg=45)
        self.channels[geo_id].channel_id = geo_id

        # LEO channel
        leo_id = "sim://leo-channel-001"
        self.channels[leo_id] = ChannelEmulatorFactory.create_leo(altitude_km=600)
        self.channels[leo_id].channel_id = leo_id

        # HAPS channel
        haps_id = "sim://haps-channel-001"
        self.channels[haps_id] = ChannelEmulatorFactory.create_haps(altitude_km=30, elevation_deg=60)
        self.channels[haps_id].channel_id = haps_id

        self.logger.info(f"Created default channels: GEO, LEO, HAPS")

    # ============ MCP Tool Functions ============

    async def list_channels(self) -> Dict[str, Any]:
        """
        List all available channel emulators

        Returns:
            Dictionary of channel information
        """
        channels_info = {}
        for channel_id, channel in self.channels.items():
            state = channel.get_channel_state()
            state["channel_id"] = channel_id
            state["simulation_running"] = channel_id in self.simulation_tasks

            channels_info[channel_id] = state

        return {
            "success": True,
            "channel_count": len(channels_info),
            "channels": channels_info
        }

    async def create_channel(self,
                           orbit_type: str,
                           channel_id: Optional[str] = None,
                           **params) -> Dict[str, Any]:
        """
        Create a new channel emulator

        Args:
            orbit_type: "geo", "leo", "meo", or "haps"
            channel_id: Optional custom channel ID
            params: Additional channel parameters (altitude_km, elevation_deg, etc.)

        Returns:
            Channel creation result
        """
        if channel_id is None:
            self.channel_counter += 1
            channel_id = f"sim://{orbit_type}-channel-{self.channel_counter:03d}"

        if channel_id in self.channels:
            return {
                "success": False,
                "error": f"Channel {channel_id} already exists"
            }

        try:
            orbit_type_lower = orbit_type.lower()

            if orbit_type_lower == "geo":
                elevation = params.get("elevation_deg", 45.0)
                channel = ChannelEmulatorFactory.create_geo(elevation_deg=elevation)

            elif orbit_type_lower == "leo":
                altitude = params.get("altitude_km", 600.0)
                channel = ChannelEmulatorFactory.create_leo(altitude_km=altitude)

            elif orbit_type_lower == "haps":
                altitude = params.get("altitude_km", 30.0)
                elevation = params.get("elevation_deg", 60.0)
                channel = ChannelEmulatorFactory.create_haps(altitude_km=altitude, elevation_deg=elevation)

            elif orbit_type_lower == "awgn":
                channel = ChannelEmulatorFactory.create_awgn_only()

            else:
                return {
                    "success": False,
                    "error": f"Unknown orbit type: {orbit_type}. Use 'geo', 'leo', 'haps', or 'awgn'"
                }

            channel.channel_id = channel_id
            self.channels[channel_id] = channel

            self.logger.info(f"Created {orbit_type} channel: {channel_id}")

            return {
                "success": True,
                "channel_id": channel_id,
                "orbit_type": orbit_type,
                "state": channel.get_channel_state()
            }

        except Exception as e:
            self.logger.error(f"Failed to create channel: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def get_channel_state(self, channel_id: str) -> Dict[str, Any]:
        """
        Get current channel state

        Args:
            channel_id: Channel identifier

        Returns:
            Channel state dictionary
        """
        if channel_id not in self.channels:
            return {
                "success": False,
                "error": f"Channel {channel_id} not found"
            }

        channel = self.channels[channel_id]
        state = channel.get_channel_state()
        state["channel_id"] = channel_id
        state["simulation_running"] = channel_id in self.simulation_tasks

        return {
            "success": True,
            "channel_state": state
        }

    async def set_elevation_angle(self, channel_id: str, elevation_deg: float) -> Dict[str, Any]:
        """
        Set elevation angle

        Args:
            channel_id: Channel identifier
            elevation_deg: Elevation angle in degrees (0-90)

        Returns:
            Operation result
        """
        if channel_id not in self.channels:
            return {"success": False, "error": f"Channel {channel_id} not found"}

        if not 0 <= elevation_deg <= 90:
            return {"success": False, "error": "Elevation must be between 0 and 90 degrees"}

        channel = self.channels[channel_id]

        try:
            channel.set_elevation_angle(elevation_deg)

            self.logger.info(f"Set elevation for {channel_id}: {elevation_deg}°")

            return {
                "success": True,
                "channel_id": channel_id,
                "elevation_deg": elevation_deg,
                "new_path_loss_db": channel.path_loss_db,
                "new_delay_ms": channel.propagation_delay_s * 1000
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def set_rain_rate(self, channel_id: str, rain_rate_mm_hr: float) -> Dict[str, Any]:
        """
        Set rain rate for rain attenuation

        Args:
            channel_id: Channel identifier
            rain_rate_mm_hr: Rain rate in mm/hr

        Returns:
            Operation result
        """
        if channel_id not in self.channels:
            return {"success": False, "error": f"Channel {channel_id} not found"}

        if rain_rate_mm_hr < 0:
            return {"success": False, "error": "Rain rate must be non-negative"}

        channel = self.channels[channel_id]

        try:
            channel.set_rain_rate(rain_rate_mm_hr)

            self.logger.info(f"Set rain rate for {channel_id}: {rain_rate_mm_hr} mm/hr")

            return {
                "success": True,
                "channel_id": channel_id,
                "rain_rate_mm_hr": rain_rate_mm_hr,
                "new_path_loss_db": channel.path_loss_db
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def apply_channel_effects(self,
                                   channel_id: str,
                                   tx_samples: List[complex]) -> Dict[str, Any]:
        """
        Apply channel effects to transmitted samples

        Args:
            channel_id: Channel identifier
            tx_samples: List of complex IQ samples

        Returns:
            Result with received samples statistics
        """
        if channel_id not in self.channels:
            return {"success": False, "error": f"Channel {channel_id} not found"}

        channel = self.channels[channel_id]

        try:
            # Convert to numpy array
            tx_array = np.array(tx_samples, dtype=np.complex64)

            # Apply channel
            rx_array = channel.apply_channel(tx_array)

            # Calculate statistics
            tx_power = 10 * np.log10(np.mean(np.abs(tx_array)**2) + 1e-10) + 30
            rx_power = 10 * np.log10(np.mean(np.abs(rx_array)**2) + 1e-10) + 30
            measured_loss = tx_power - rx_power

            self.logger.debug(f"Applied channel {channel_id}: loss={measured_loss:.2f} dB")

            return {
                "success": True,
                "channel_id": channel_id,
                "num_samples": len(rx_array),
                "tx_power_dbm": float(tx_power),
                "rx_power_dbm": float(rx_power),
                "measured_loss_db": float(measured_loss),
                "expected_loss_db": channel.path_loss_db,
                "delay_ms": channel.propagation_delay_s * 1000,
                "doppler_hz": channel.satellite_state.doppler_hz,
                # Note: Not returning actual samples to avoid large payloads
                # In real MCP, would return compressed or store for retrieval
            }

        except Exception as e:
            self.logger.error(f"Channel application failed: {e}")
            return {"success": False, "error": str(e)}

    async def start_dynamic_simulation(self,
                                      channel_id: str,
                                      duration_s: float = 60,
                                      update_rate_hz: float = 10) -> Dict[str, Any]:
        """
        Start dynamic channel simulation (for LEO/MEO)

        Args:
            channel_id: Channel identifier
            duration_s: Simulation duration in seconds
            update_rate_hz: Update rate in Hz

        Returns:
            Operation result
        """
        if channel_id not in self.channels:
            return {"success": False, "error": f"Channel {channel_id} not found"}

        if channel_id in self.simulation_tasks:
            return {"success": False, "error": f"Simulation already running for {channel_id}"}

        channel = self.channels[channel_id]

        try:
            # Create background task
            task = asyncio.create_task(
                channel.run_dynamic_simulation(duration_s, update_rate_hz)
            )
            self.simulation_tasks[channel_id] = task

            self.logger.info(f"Started dynamic simulation for {channel_id}: "
                           f"{duration_s}s at {update_rate_hz} Hz")

            return {
                "success": True,
                "channel_id": channel_id,
                "simulation_started": True,
                "duration_s": duration_s,
                "update_rate_hz": update_rate_hz
            }

        except Exception as e:
            self.logger.error(f"Failed to start simulation: {e}")
            return {"success": False, "error": str(e)}

    async def stop_dynamic_simulation(self, channel_id: str) -> Dict[str, Any]:
        """
        Stop dynamic channel simulation

        Args:
            channel_id: Channel identifier

        Returns:
            Operation result
        """
        if channel_id not in self.simulation_tasks:
            return {"success": False, "error": f"No simulation running for {channel_id}"}

        try:
            task = self.simulation_tasks[channel_id]
            task.cancel()

            try:
                await task
            except asyncio.CancelledError:
                pass

            del self.simulation_tasks[channel_id]

            self.logger.info(f"Stopped dynamic simulation for {channel_id}")

            return {
                "success": True,
                "channel_id": channel_id,
                "simulation_stopped": True
            }

        except Exception as e:
            self.logger.error(f"Failed to stop simulation: {e}")
            return {"success": False, "error": str(e)}

    async def get_link_budget(self, channel_id: str,
                             tx_power_dbm: float = 33,
                             tx_gain_dbi: float = 15,
                             rx_gain_dbi: float = 15) -> Dict[str, Any]:
        """
        Calculate complete link budget

        Args:
            channel_id: Channel identifier
            tx_power_dbm: Transmit power in dBm
            tx_gain_dbi: TX antenna gain in dBi
            rx_gain_dbi: RX antenna gain in dBi

        Returns:
            Link budget calculation
        """
        if channel_id not in self.channels:
            return {"success": False, "error": f"Channel {channel_id} not found"}

        channel = self.channels[channel_id]

        try:
            # Get channel state
            state = channel.get_channel_state()

            # Calculate link budget
            eirp_dbm = tx_power_dbm + tx_gain_dbi
            path_loss_db = state["path_loss_db"]
            rx_power_dbm = eirp_dbm - path_loss_db + rx_gain_dbi

            # Noise floor
            k = 1.38e-23  # Boltzmann
            T = 290  # K
            BW = 30e6  # 30 MHz
            NF_db = 5  # Noise figure
            noise_power_dbm = 10 * np.log10(k * T * BW) + 30 + NF_db

            # SNR
            snr_db = rx_power_dbm - noise_power_dbm

            # Link margin (target SNR = 10 dB for QPSK 1/2)
            target_snr_db = 10
            link_margin_db = snr_db - target_snr_db

            self.logger.info(f"Link budget calculated for {channel_id}: "
                           f"EIRP={eirp_dbm:.1f} dBm, RX={rx_power_dbm:.1f} dBm, "
                           f"SNR={snr_db:.1f} dB, Margin={link_margin_db:.1f} dB")

            return {
                "success": True,
                "channel_id": channel_id,
                "link_budget": {
                    "tx_power_dbm": tx_power_dbm,
                    "tx_gain_dbi": tx_gain_dbi,
                    "eirp_dbm": eirp_dbm,
                    "path_loss_db": path_loss_db,
                    "rx_gain_dbi": rx_gain_dbi,
                    "rx_power_dbm": rx_power_dbm,
                    "noise_floor_dbm": noise_power_dbm,
                    "snr_db": snr_db,
                    "target_snr_db": target_snr_db,
                    "link_margin_db": link_margin_db,
                    "link_status": "PASS" if link_margin_db > 0 else "FAIL"
                },
                "channel_state": state
            }

        except Exception as e:
            self.logger.error(f"Link budget calculation failed: {e}")
            return {"success": False, "error": str(e)}

    async def delete_channel(self, channel_id: str) -> Dict[str, Any]:
        """
        Delete a channel emulator

        Args:
            channel_id: Channel identifier

        Returns:
            Operation result
        """
        if channel_id not in self.channels:
            return {"success": False, "error": f"Channel {channel_id} not found"}

        try:
            # Stop simulation if running
            if channel_id in self.simulation_tasks:
                await self.stop_dynamic_simulation(channel_id)

            # Delete channel
            del self.channels[channel_id]

            self.logger.info(f"Deleted channel {channel_id}")

            return {
                "success": True,
                "channel_id": channel_id,
                "deleted": True
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


# ============ MCP Server Entry Point ============

async def main():
    """Run MCP server"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create and initialize server
    server = ChannelSimulatorMCP()
    await server.initialize()

    # Keep server running
    print("\n" + "="*60)
    print("Channel Emulator Simulator MCP Server Running")
    print("="*60)
    print("\nAvailable channels:")
    channels = await server.list_channels()
    for channel_id, state in channels["channels"].items():
        print(f"  - {channel_id}: {state['orbit_type']} "
              f"({state['distance_km']:.1f} km, "
              f"{state['propagation_delay_ms']:.2f} ms delay)")

    print("\n✅ Server ready for MCP calls")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        # Stop all simulations
        for channel_id in list(server.simulation_tasks.keys()):
            await server.stop_dynamic_simulation(channel_id)


if __name__ == "__main__":
    asyncio.run(main())
