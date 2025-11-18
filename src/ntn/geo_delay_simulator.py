#!/usr/bin/env python3
"""
GEO Satellite Delay Simulator
Implements 250ms RTT delay for GEO satellite at 35,786 km
Includes Common Timing Advance and K_offset calculations
"""

import numpy as np
import time
import asyncio
from dataclasses import dataclass
from typing import Optional, Tuple
import json
import argparse

@dataclass
class GEOParameters:
    """GEO Satellite NTN Parameters per 3GPP Release 17"""
    altitude_km: float = 35786  # Geostationary orbit altitude
    speed_of_light: float = 299792.458  # km/s
    elevation_angle_deg: float = 45  # Typical elevation angle
    
    # 3GPP NTN timing parameters
    Ts: float = 1 / (15000 * 2048)  # Basic time unit in seconds
    K_offset_min: int = 150  # Minimum K_offset for GEO (slots)
    K_offset_max: int = 239  # Maximum K_offset for GEO (slots)
    
    # NR timing
    subcarrier_spacing_khz: int = 15  # Default SCS
    slot_duration_ms: float = 1.0  # For 15 kHz SCS
    
    def calculate_propagation_delay(self, elevation_deg: Optional[float] = None) -> float:
        """Calculate one-way propagation delay in seconds"""
        if elevation_deg is None:
            elevation_deg = self.elevation_angle_deg
            
        # Calculate slant range based on elevation angle
        earth_radius_km = 6371
        elevation_rad = np.radians(elevation_deg)
        
        # Law of cosines for slant range
        slant_range_km = np.sqrt(
            earth_radius_km**2 + (earth_radius_km + self.altitude_km)**2 -
            2 * earth_radius_km * (earth_radius_km + self.altitude_km) * np.sin(elevation_rad)
        )
        
        # One-way propagation delay
        delay_seconds = slant_range_km / self.speed_of_light
        
        return delay_seconds
        
    def calculate_rtt(self, elevation_deg: Optional[float] = None) -> float:
        """Calculate round-trip time in seconds"""
        return 2 * self.calculate_propagation_delay(elevation_deg)
        
    def calculate_common_ta(self, elevation_deg: Optional[float] = None) -> int:
        """Calculate Common Timing Advance in Ts units"""
        rtt_seconds = self.calculate_rtt(elevation_deg)
        common_ta_ts = int(rtt_seconds / self.Ts)
        return common_ta_ts
        
    def calculate_k_offset(self, rtt_seconds: float) -> int:
        """Calculate K_offset value for HARQ timing"""
        # K_offset accounts for propagation delay in HARQ processes
        k_offset_slots = int(np.ceil(rtt_seconds * 1000 / self.slot_duration_ms))
        
        # Clamp to valid range for GEO
        k_offset = max(self.K_offset_min, min(k_offset_slots, self.K_offset_max))
        
        return k_offset

class GEODelaySimulator:
    """Simulates GEO satellite delay characteristics for NTN testing"""
    
    def __init__(self, interface: str = "lo", verbose: bool = True):
        self.interface = interface
        self.verbose = verbose
        self.params = GEOParameters()
        self.active = False
        self.statistics = {
            "packets_delayed": 0,
            "total_delay_applied_ms": 0,
            "min_delay_ms": float('inf'),
            "max_delay_ms": 0,
            "elevation_angles_tested": []
        }
        
    def print_configuration(self):
        """Print GEO NTN configuration parameters"""
        print("\n" + "="*60)
        print("GEO SATELLITE NTN CONFIGURATION")
        print("="*60)
        
        # Calculate for different elevation angles
        elevations = [20, 30, 45, 60, 90]
        
        print("\nPropagation Delays by Elevation Angle:")
        print("-" * 60)
        print(f"{'Elevation':>10} | {'Slant Range':>12} | {'One-way':>10} | {'RTT':>10} | {'Common TA':>12}")
        print(f"{'(degrees)':>10} | {'(km)':>12} | {'(ms)':>10} | {'(ms)':>10} | {'(Ts units)':>12}")
        print("-" * 60)
        
        for elev in elevations:
            earth_radius_km = 6371
            elevation_rad = np.radians(elev)
            slant_range_km = np.sqrt(
                earth_radius_km**2 + (earth_radius_km + self.params.altitude_km)**2 -
                2 * earth_radius_km * (earth_radius_km + self.params.altitude_km) * np.sin(elevation_rad)
            )
            
            one_way = self.params.calculate_propagation_delay(elev) * 1000
            rtt = self.params.calculate_rtt(elev) * 1000
            common_ta = self.params.calculate_common_ta(elev)
            
            print(f"{elev:>10.0f} | {slant_range_km:>12.0f} | {one_way:>10.1f} | {rtt:>10.1f} | {common_ta:>12,}")
            
        print("\n3GPP NTN Timing Parameters:")
        print("-" * 60)
        print(f"Basic Time Unit (Ts): {self.params.Ts*1e9:.3f} ns")
        print(f"Subcarrier Spacing: {self.params.subcarrier_spacing_khz} kHz")
        print(f"Slot Duration: {self.params.slot_duration_ms} ms")
        print(f"K_offset Range (GEO): {self.params.K_offset_min} - {self.params.K_offset_max} slots")
        
        # Calculate K2 timing
        typical_rtt = self.params.calculate_rtt(45) * 1000  # ms
        k_offset = self.params.calculate_k_offset(typical_rtt / 1000)
        k2_normal = 4  # Normal K2 value (slots)
        k_mac = 2  # MAC processing time (slots)
        k2_total = k2_normal + k_offset + k_mac
        
        print(f"\nHARQ Timing (45° elevation):")
        print(f"  K2_normal: {k2_normal} slots")
        print(f"  K_offset: {k_offset} slots")
        print(f"  K_mac: {k_mac} slots")
        print(f"  K2_total: {k2_total} slots ({k2_total * self.params.slot_duration_ms:.1f} ms)")
        
        print("\nHARQ Configuration Options:")
        print("  1. Disable HARQ, use RLC ARQ only (recommended for GEO)")
        print("  2. Increase HARQ processes to 32 (for LEO)")
        print("  3. Implement HARQ stalling with extended timers")
        
    async def apply_delay_netem(self, delay_ms: float, variance_ms: float = 5.0):
        """Apply delay using Linux tc/netem"""
        if self.verbose:
            print(f"\nApplying network delay: {delay_ms:.1f} ms ± {variance_ms:.1f} ms")
            
        # Remove existing qdisc
        cmd_remove = f"sudo tc qdisc del dev {self.interface} root 2>/dev/null"
        await self.run_command(cmd_remove)
        
        # Add delay with variance and distribution
        cmd_add = (
            f"sudo tc qdisc add dev {self.interface} root netem "
            f"delay {delay_ms}ms {variance_ms}ms distribution normal"
        )
        
        result = await self.run_command(cmd_add)
        
        if result == 0:
            self.active = True
            if self.verbose:
                print(f"✅ Delay applied successfully on {self.interface}")
        else:
            print(f"❌ Failed to apply delay on {self.interface}")
            
        return result == 0
        
    async def remove_delay(self):
        """Remove network delay"""
        if self.verbose:
            print(f"\nRemoving network delay from {self.interface}")
            
        cmd = f"sudo tc qdisc del dev {self.interface} root 2>/dev/null"
        result = await self.run_command(cmd)
        
        self.active = False
        
        if result == 0 and self.verbose:
            print(f"✅ Delay removed successfully")
            
        return result == 0
        
    async def simulate_elevation_sweep(self, start_elev: float = 20, end_elev: float = 90, 
                                      step: float = 10, duration_per_step: float = 5.0):
        """Simulate satellite pass by sweeping elevation angles"""
        print(f"\n{'='*60}")
        print("SIMULATING SATELLITE PASS")
        print(f"{'='*60}")
        print(f"Elevation range: {start_elev}° to {end_elev}°")
        print(f"Step size: {step}°")
        print(f"Duration per step: {duration_per_step} seconds")
        
        elevations = np.arange(start_elev, end_elev + step, step)
        
        for elev in elevations:
            # Calculate delay for this elevation
            one_way_delay = self.params.calculate_propagation_delay(elev) * 1000
            rtt_ms = 2 * one_way_delay
            
            # Apply delay
            await self.apply_delay_netem(one_way_delay)
            
            # Update statistics
            self.statistics["elevation_angles_tested"].append(elev)
            self.statistics["total_delay_applied_ms"] += rtt_ms
            self.statistics["min_delay_ms"] = min(self.statistics["min_delay_ms"], rtt_ms)
            self.statistics["max_delay_ms"] = max(self.statistics["max_delay_ms"], rtt_ms)
            
            print(f"\nElevation: {elev:>5.1f}° | One-way: {one_way_delay:>6.1f} ms | RTT: {rtt_ms:>6.1f} ms")
            
            # Simulate Common TA broadcast
            common_ta = self.params.calculate_common_ta(elev)
            print(f"  Broadcasting Common TA: {common_ta:,} Ts units")
            
            # Wait before next step
            await asyncio.sleep(duration_per_step)
            
        # Remove delay after sweep
        await self.remove_delay()
        
    async def simulate_handover(self, from_elevation: float, to_elevation: float, 
                               handover_duration: float = 2.0):
        """Simulate handover between two satellites"""
        print(f"\n{'='*60}")
        print("SIMULATING INTER-SATELLITE HANDOVER")
        print(f"{'='*60}")
        
        # Calculate delays for both satellites
        from_delay = self.params.calculate_propagation_delay(from_elevation) * 1000
        to_delay = self.params.calculate_propagation_delay(to_elevation) * 1000
        
        print(f"Source satellite (elevation {from_elevation}°): {from_delay:.1f} ms one-way")
        print(f"Target satellite (elevation {to_elevation}°): {to_delay:.1f} ms one-way")
        print(f"Delay difference: {abs(to_delay - from_delay):.1f} ms")
        
        # Apply source satellite delay
        print("\nPhase 1: Connected to source satellite")
        await self.apply_delay_netem(from_delay)
        await asyncio.sleep(2.0)
        
        # Handover period - simulate gradually changing delay
        print(f"\nPhase 2: Handover in progress ({handover_duration} seconds)")
        steps = 10
        for i in range(steps + 1):
            progress = i / steps
            current_delay = from_delay + (to_delay - from_delay) * progress
            await self.apply_delay_netem(current_delay, variance_ms=10.0)  # Higher variance during handover
            await asyncio.sleep(handover_duration / steps)
            
        # Apply target satellite delay
        print("\nPhase 3: Connected to target satellite")
        await self.apply_delay_netem(to_delay)
        await asyncio.sleep(2.0)
        
        # Calculate new timing parameters
        new_common_ta = self.params.calculate_common_ta(to_elevation)
        print(f"\nUpdated Common TA: {new_common_ta:,} Ts units")
        
    async def test_harq_timing(self, elevation: float = 45):
        """Test HARQ timing with GEO delay"""
        print(f"\n{'='*60}")
        print("TESTING HARQ TIMING")
        print(f"{'='*60}")
        
        rtt_seconds = self.params.calculate_rtt(elevation)
        rtt_ms = rtt_seconds * 1000
        
        # Apply delay
        await self.apply_delay_netem(rtt_ms / 2)  # One-way delay
        
        # HARQ timing calculation
        k_offset = self.params.calculate_k_offset(rtt_seconds)
        
        # Simulate HARQ processes
        num_processes_normal = 8  # Normal NR
        num_processes_ntn = 32  # Extended for NTN
        
        print(f"\nConfiguration for {elevation}° elevation:")
        print(f"  RTT: {rtt_ms:.1f} ms")
        print(f"  K_offset: {k_offset} slots")
        
        print("\nHARQ Process Comparison:")
        print(f"  Standard NR: {num_processes_normal} processes")
        print(f"    - Round-trip per process: {rtt_ms:.1f} ms")
        print(f"    - Total cycle time: {num_processes_normal * rtt_ms:.1f} ms")
        print(f"    - Status: ❌ Insufficient for GEO")
        
        print(f"  NTN Extended: {num_processes_ntn} processes")
        print(f"    - Round-trip per process: {rtt_ms:.1f} ms")
        print(f"    - Total cycle time: {num_processes_ntn * rtt_ms:.1f} ms")
        print(f"    - Status: ✅ Suitable for continuous transmission")
        
        print("\nRecommendation for GEO:")
        print("  Consider disabling HARQ and relying on RLC ARQ")
        print("  This avoids complexity of managing 250ms+ feedback delays")
        
    async def run_command(self, command: str) -> int:
        """Execute shell command"""
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        await proc.communicate()
        return proc.returncode
        
    def save_statistics(self, filename: str = "geo_delay_stats.json"):
        """Save test statistics"""
        stats = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "configuration": {
                "altitude_km": self.params.altitude_km,
                "interface": self.interface
            },
            "statistics": self.statistics,
            "timing_parameters": {
                "Ts_ns": self.params.Ts * 1e9,
                "K_offset_range": f"{self.params.K_offset_min}-{self.params.K_offset_max}",
                "typical_rtt_ms": self.params.calculate_rtt() * 1000,
                "typical_common_ta_ts": self.params.calculate_common_ta()
            }
        }
        
        with open(filename, 'w') as f:
            json.dump(stats, f, indent=2)
            
        print(f"\nStatistics saved to {filename}")

async def main():
    parser = argparse.ArgumentParser(description="GEO Satellite Delay Simulator")
    parser.add_argument("--interface", type=str, default="lo",
                        help="Network interface to apply delay")
    parser.add_argument("--elevation", type=float, default=45,
                        help="Satellite elevation angle in degrees")
    parser.add_argument("--rtt", type=float, default=250,
                        help="Override RTT in milliseconds")
    parser.add_argument("--variance", type=float, default=5,
                        help="Delay variance in milliseconds")
    parser.add_argument("--mode", type=str, default="static",
                        choices=["static", "sweep", "handover", "harq"],
                        help="Simulation mode")
    parser.add_argument("--duration", type=float, default=10,
                        help="Test duration in seconds")
    
    args = parser.parse_args()
    
    # Create simulator
    simulator = GEODelaySimulator(args.interface)
    
    # Print configuration
    simulator.print_configuration()
    
    try:
        if args.mode == "static":
            # Apply static delay
            one_way = args.rtt / 2 if args.rtt else \
                     simulator.params.calculate_propagation_delay(args.elevation) * 1000
            
            print(f"\nApplying static GEO delay:")
            print(f"  Elevation: {args.elevation}°")
            print(f"  One-way delay: {one_way:.1f} ms")
            print(f"  RTT: {one_way * 2:.1f} ms")
            
            await simulator.apply_delay_netem(one_way, args.variance)
            
            print(f"\nDelay active for {args.duration} seconds...")
            await asyncio.sleep(args.duration)
            
        elif args.mode == "sweep":
            # Simulate elevation sweep
            await simulator.simulate_elevation_sweep(
                start_elev=20,
                end_elev=90,
                step=10,
                duration_per_step=args.duration / 8
            )
            
        elif args.mode == "handover":
            # Simulate handover
            await simulator.simulate_handover(
                from_elevation=30,
                to_elevation=60,
                handover_duration=args.duration / 3
            )
            
        elif args.mode == "harq":
            # Test HARQ timing
            await simulator.test_harq_timing(args.elevation)
            await asyncio.sleep(args.duration)
            
    except KeyboardInterrupt:
        print("\n\nSimulation interrupted by user")
        
    finally:
        # Clean up
        await simulator.remove_delay()
        simulator.save_statistics()
        
        print("\n" + "="*60)
        print("SIMULATION COMPLETE")
        print("="*60)

if __name__ == "__main__":
    asyncio.run(main())
