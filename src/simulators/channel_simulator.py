#!/usr/bin/env python3
"""
Software Channel Emulator - Replaces ITRI/Keysight/Spirent Hardware
Simulates NTN channel effects (delay, doppler, fading, attenuation)
Supports GPU acceleration via CuPy
"""

import numpy as np
import time
import logging
from dataclasses import dataclass
from typing import Optional, Tuple, List
from enum import Enum
import asyncio

# Try to import CuPy for GPU acceleration
try:
    import cupy as cp
    GPU_AVAILABLE = True
    logger = logging.getLogger(__name__)
    logger.info("✅ GPU (CuPy) available - using GPU acceleration")
except ImportError:
    cp = np
    GPU_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.info("⚠️  GPU not available - using CPU only")


class OrbitType(Enum):
    """Satellite orbit types"""
    GEO = "geo"          # Geostationary (35,786 km)
    LEO = "leo"          # Low Earth Orbit (600-1200 km)
    MEO = "meo"          # Medium Earth Orbit (8,000-20,000 km)
    HAPS = "haps"        # High Altitude Platform Station (20-50 km)


class ChannelModel(Enum):
    """3GPP NTN Channel Models"""
    TDL_A = "tdl_a"      # Tap Delay Line A (sparse)
    TDL_B = "tdl_b"      # Tap Delay Line B (moderate)
    TDL_C = "tdl_c"      # Tap Delay Line C (dense)
    TDL_D = "tdl_d"      # Tap Delay Line D with Doppler
    TDL_E = "tdl_e"      # Tap Delay Line E with strong Doppler
    AWGN = "awgn"        # AWGN only (no multipath)


@dataclass
class ChannelConfig:
    """Channel Configuration"""
    orbit_type: OrbitType = OrbitType.GEO
    channel_model: ChannelModel = ChannelModel.TDL_A
    center_freq: float = 2.0e9              # 2 GHz
    sample_rate: float = 30.72e6            # 30.72 MHz
    distance_km: float = 35786              # GEO altitude
    elevation_angle: float = 45.0           # degrees
    doppler_enabled: bool = True
    rain_attenuation: bool = True
    atmospheric_loss: bool = True
    scintillation: bool = False


@dataclass
class SatelliteState:
    """Satellite position and velocity state"""
    latitude: float = 0.0                   # degrees
    longitude: float = 0.0                  # degrees
    altitude_km: float = 35786              # km
    velocity_ms: float = 0.0                # m/s (0 for GEO)
    elevation: float = 45.0                 # degrees
    azimuth: float = 180.0                  # degrees
    doppler_hz: float = 0.0                 # Hz


class SoftwareChannelEmulator:
    """Software Channel Emulator for NTN scenarios"""

    def __init__(self, config: ChannelConfig):
        self.config = config
        self.logger = logging.getLogger(f"ChannelEmulator-{config.orbit_type.value}")
        self.use_gpu = GPU_AVAILABLE

        # Channel state
        self.satellite_state = self._init_satellite_state()
        self.path_loss_db = self._calculate_path_loss()
        self.propagation_delay_s = self._calculate_delay()

        # Multipath taps (3GPP NTN models)
        self.multipath_taps = self._generate_multipath_taps()

        # Doppler state
        self.doppler_shift_hz = 0.0
        self.doppler_rate_hz_s = 0.0

        # Rain and atmosphere state
        self.rain_rate_mm_hr = 0.0
        self.atmospheric_loss_db = 0.0

        self.logger.info(f"✅ Software Channel Emulator initialized: {config.orbit_type.value}")
        self.logger.info(f"   Distance: {config.distance_km:.1f} km")
        self.logger.info(f"   Path Loss: {self.path_loss_db:.2f} dB")
        self.logger.info(f"   Delay: {self.propagation_delay_s*1000:.2f} ms")
        self.logger.info(f"   GPU Mode: {'Enabled' if self.use_gpu else 'Disabled'}")

    def _init_satellite_state(self) -> SatelliteState:
        """Initialize satellite state based on orbit type"""
        state = SatelliteState()

        if self.config.orbit_type == OrbitType.GEO:
            state.altitude_km = 35786
            state.velocity_ms = 0.0  # Stationary relative to ground
            state.doppler_hz = np.random.normal(0, 15)  # ±15 Hz typical

        elif self.config.orbit_type == OrbitType.LEO:
            state.altitude_km = 600 + np.random.uniform(0, 600)  # 600-1200 km
            state.velocity_ms = 7500  # ~7.5 km/s orbital velocity
            state.doppler_hz = np.random.normal(0, 37500)  # ±37.5 kHz max

        elif self.config.orbit_type == OrbitType.MEO:
            state.altitude_km = 8000 + np.random.uniform(0, 12000)
            state.velocity_ms = 4000  # ~4 km/s
            state.doppler_hz = np.random.normal(0, 15000)  # ±15 kHz

        elif self.config.orbit_type == OrbitType.HAPS:
            state.altitude_km = 20 + np.random.uniform(0, 30)  # 20-50 km
            state.velocity_ms = 50  # ~50 m/s (slow drift)
            state.doppler_hz = np.random.normal(0, 2)  # Minimal Doppler

        state.elevation = self.config.elevation_angle
        return state

    def _calculate_path_loss(self) -> float:
        """Calculate Free Space Path Loss (FSPL)"""
        # FSPL = 20*log10(d) + 20*log10(f) + 20*log10(4π/c)
        c = 3e8  # Speed of light
        distance_m = self.config.distance_km * 1000
        freq_hz = self.config.center_freq

        fspl_db = 20 * np.log10(distance_m) + 20 * np.log10(freq_hz) + \
                  20 * np.log10(4 * np.pi / c)

        # Add atmospheric loss
        if self.config.atmospheric_loss:
            # ITU-R P.676 atmospheric attenuation (simplified)
            elevation_rad = np.radians(self.satellite_state.elevation)
            atm_loss = 0.2 / np.sin(elevation_rad)  # ~0.2-2 dB typical
            fspl_db += atm_loss
            self.atmospheric_loss_db = atm_loss

        # Add rain attenuation
        if self.config.rain_attenuation:
            # ITU-R P.618 rain attenuation (simplified)
            rain_loss = self._calculate_rain_attenuation()
            fspl_db += rain_loss

        return fspl_db

    def _calculate_rain_attenuation(self) -> float:
        """Calculate rain attenuation (ITU-R P.838)"""
        # Simplified model - typical rain rate 5 mm/hr
        rain_rate = 5.0 + np.random.exponential(2.0)  # mm/hr
        self.rain_rate_mm_hr = rain_rate

        # Frequency-dependent coefficients (2 GHz)
        freq_ghz = self.config.center_freq / 1e9
        k = 0.0000387 * (freq_ghz ** 2.03)
        alpha = 0.958 * (freq_ghz ** (-0.195))

        # Specific attenuation
        gamma = k * (rain_rate ** alpha)  # dB/km

        # Effective path length through rain
        elevation_rad = np.radians(self.satellite_state.elevation)
        path_length_km = 3.0 / np.sin(elevation_rad)  # Typical rain height 3 km

        rain_loss_db = gamma * path_length_km
        return rain_loss_db

    def _calculate_delay(self) -> float:
        """Calculate propagation delay"""
        c = 3e8  # Speed of light
        distance_m = self.config.distance_km * 1000
        delay_s = distance_m / c
        return delay_s

    def _generate_multipath_taps(self) -> List[Tuple[float, float]]:
        """
        Generate multipath tap delays and gains (3GPP NTN models)
        Returns: List of (delay_s, gain_linear) tuples
        """
        taps = []

        if self.config.channel_model == ChannelModel.AWGN:
            # No multipath
            taps = [(0.0, 1.0)]

        elif self.config.channel_model == ChannelModel.TDL_A:
            # Sparse multipath (2-3 taps)
            taps = [
                (0.0, 0.8),
                (50e-9, 0.15),
                (120e-9, 0.05),
            ]

        elif self.config.channel_model == ChannelModel.TDL_B:
            # Moderate multipath (4-5 taps)
            taps = [
                (0.0, 0.7),
                (30e-9, 0.2),
                (80e-9, 0.07),
                (150e-9, 0.02),
                (300e-9, 0.01),
            ]

        elif self.config.channel_model == ChannelModel.TDL_C:
            # Dense multipath (6-8 taps)
            taps = [
                (0.0, 0.6),
                (20e-9, 0.25),
                (50e-9, 0.1),
                (100e-9, 0.03),
                (200e-9, 0.015),
                (400e-9, 0.004),
                (600e-9, 0.001),
            ]

        elif self.config.channel_model in [ChannelModel.TDL_D, ChannelModel.TDL_E]:
            # Time-varying multipath with Doppler
            taps = [
                (0.0, 0.75),
                (40e-9, 0.18),
                (100e-9, 0.05),
                (250e-9, 0.02),
            ]

        return taps

    def apply_channel(self, tx_samples: np.ndarray) -> np.ndarray:
        """
        Apply channel effects to transmitted samples

        Args:
            tx_samples: Complex IQ samples from transmitter

        Returns:
            Complex IQ samples after channel propagation
        """
        # Convert to GPU if available
        if self.use_gpu and not isinstance(tx_samples, cp.ndarray):
            samples = cp.array(tx_samples)
            use_gpu_processing = True
        else:
            samples = tx_samples
            use_gpu_processing = False

        # 1. Apply path loss
        path_loss_linear = 10 ** (-self.path_loss_db / 20)
        samples = samples * path_loss_linear

        # 2. Apply propagation delay
        samples = self._apply_delay(samples)

        # 3. Apply multipath fading
        samples = self._apply_multipath(samples)

        # 4. Apply Doppler shift
        if self.config.doppler_enabled:
            samples = self._apply_doppler(samples)

        # 5. Add AWGN noise
        samples = self._add_noise(samples)

        # Convert back to numpy if using GPU
        if use_gpu_processing:
            samples = cp.asnumpy(samples)

        return samples

    def _apply_delay(self, samples: np.ndarray) -> np.ndarray:
        """Apply propagation delay"""
        delay_samples = int(self.propagation_delay_s * self.config.sample_rate)

        # Pad with zeros at the beginning
        if self.use_gpu and isinstance(samples, cp.ndarray):
            delayed = cp.pad(samples, (delay_samples, 0), mode='constant')[:len(samples)]
        else:
            delayed = np.pad(samples, (delay_samples, 0), mode='constant')[:len(samples)]

        return delayed

    def _apply_multipath(self, samples: np.ndarray) -> np.ndarray:
        """Apply multipath fading"""
        if len(self.multipath_taps) == 1 and self.multipath_taps[0][0] == 0:
            # No multipath
            return samples

        # Initialize output
        if self.use_gpu and isinstance(samples, cp.ndarray):
            output = cp.zeros_like(samples)
        else:
            output = np.zeros_like(samples)

        # Apply each tap
        for delay_s, gain in self.multipath_taps:
            delay_samples = int(delay_s * self.config.sample_rate)

            # Random phase for each tap (time-varying)
            phase = np.random.uniform(0, 2*np.pi)
            complex_gain = gain * np.exp(1j * phase)

            # Delay and add
            if delay_samples == 0:
                output += samples * complex_gain
            else:
                if self.use_gpu and isinstance(samples, cp.ndarray):
                    delayed_tap = cp.pad(samples, (delay_samples, 0), mode='constant')[:-delay_samples]
                else:
                    delayed_tap = np.pad(samples, (delay_samples, 0), mode='constant')[:-delay_samples]
                output += delayed_tap * complex_gain

        return output

    def _apply_doppler(self, samples: np.ndarray) -> np.ndarray:
        """Apply Doppler frequency shift"""
        doppler_hz = self.satellite_state.doppler_hz

        if abs(doppler_hz) < 0.1:
            return samples

        # Generate frequency shift
        t = np.arange(len(samples)) / self.config.sample_rate

        if self.use_gpu and isinstance(samples, cp.ndarray):
            t = cp.array(t)
            doppler_shift = cp.exp(1j * 2 * cp.pi * doppler_hz * t)
        else:
            doppler_shift = np.exp(1j * 2 * np.pi * doppler_hz * t)

        return samples * doppler_shift

    def _add_noise(self, samples: np.ndarray) -> np.ndarray:
        """Add AWGN noise"""
        # Calculate noise power from thermal noise
        k = 1.38e-23  # Boltzmann constant
        T = 290       # Temperature (K)
        BW = self.config.sample_rate
        NF_linear = 10 ** (5 / 10)  # 5 dB noise figure

        noise_power = k * T * BW * NF_linear
        noise_amplitude = np.sqrt(noise_power / 2)  # /2 for I and Q

        if self.use_gpu and isinstance(samples, cp.ndarray):
            noise_i = cp.random.normal(0, noise_amplitude, len(samples))
            noise_q = cp.random.normal(0, noise_amplitude, len(samples))
        else:
            noise_i = np.random.normal(0, noise_amplitude, len(samples))
            noise_q = np.random.normal(0, noise_amplitude, len(samples))

        noise = noise_i + 1j * noise_q
        return samples + noise

    def update_satellite_position(self, time_elapsed_s: float):
        """
        Update satellite position for LEO/MEO orbits

        Args:
            time_elapsed_s: Time elapsed since last update
        """
        if self.config.orbit_type == OrbitType.GEO:
            # GEO is stationary (but add small drift)
            self.satellite_state.doppler_hz += np.random.normal(0, 0.5)
            self.satellite_state.doppler_hz = np.clip(self.satellite_state.doppler_hz, -20, 20)

        elif self.config.orbit_type == OrbitType.LEO:
            # LEO moves fast - update Doppler
            # Simplified model: sinusoidal Doppler profile
            orbital_period = 90 * 60  # ~90 minutes
            phase = (time_elapsed_s / orbital_period) * 2 * np.pi

            max_doppler = 37500  # Hz at 2 GHz L-band
            self.satellite_state.doppler_hz = max_doppler * np.sin(phase)
            self.doppler_rate_hz_s = max_doppler * (2*np.pi/orbital_period) * np.cos(phase)

        elif self.config.orbit_type == OrbitType.MEO:
            # MEO moderate speed
            orbital_period = 6 * 3600  # ~6 hours
            phase = (time_elapsed_s / orbital_period) * 2 * np.pi

            max_doppler = 15000  # Hz
            self.satellite_state.doppler_hz = max_doppler * np.sin(phase)

        elif self.config.orbit_type == OrbitType.HAPS:
            # HAPS slow drift
            self.satellite_state.doppler_hz += np.random.normal(0, 0.1)
            self.satellite_state.doppler_hz = np.clip(self.satellite_state.doppler_hz, -5, 5)

        # Recalculate delay if distance changes
        self.propagation_delay_s = self._calculate_delay()

    def set_rain_rate(self, rain_rate_mm_hr: float):
        """Manually set rain rate"""
        self.rain_rate_mm_hr = rain_rate_mm_hr
        self.path_loss_db = self._calculate_path_loss()
        self.logger.info(f"Rain rate set to {rain_rate_mm_hr:.1f} mm/hr, path loss: {self.path_loss_db:.2f} dB")

    def set_elevation_angle(self, elevation_deg: float):
        """Update elevation angle"""
        self.satellite_state.elevation = elevation_deg
        self.config.elevation_angle = elevation_deg
        self.path_loss_db = self._calculate_path_loss()
        self.logger.info(f"Elevation set to {elevation_deg:.1f}°, path loss: {self.path_loss_db:.2f} dB")

    def get_channel_state(self) -> dict:
        """Get current channel state"""
        return {
            "orbit_type": self.config.orbit_type.value,
            "channel_model": self.config.channel_model.value,
            "distance_km": self.config.distance_km,
            "path_loss_db": self.path_loss_db,
            "propagation_delay_ms": self.propagation_delay_s * 1000,
            "doppler_shift_hz": self.satellite_state.doppler_hz,
            "doppler_rate_hz_s": self.doppler_rate_hz_s,
            "rain_rate_mm_hr": self.rain_rate_mm_hr,
            "atmospheric_loss_db": self.atmospheric_loss_db,
            "elevation_angle_deg": self.satellite_state.elevation,
            "multipath_taps": len(self.multipath_taps),
            "gpu_enabled": self.use_gpu,
        }

    async def run_dynamic_simulation(self, duration_s: float, update_rate_hz: float = 10):
        """
        Run dynamic channel simulation (for LEO/MEO)

        Args:
            duration_s: Simulation duration
            update_rate_hz: How often to update satellite position
        """
        self.logger.info(f"Starting dynamic simulation for {duration_s}s at {update_rate_hz} Hz")

        start_time = time.time()
        update_interval = 1.0 / update_rate_hz

        while (time.time() - start_time) < duration_s:
            elapsed = time.time() - start_time

            # Update satellite position
            self.update_satellite_position(elapsed)

            # Log state
            state = self.get_channel_state()
            self.logger.debug(f"[{elapsed:.1f}s] Doppler: {state['doppler_shift_hz']:.1f} Hz, "
                            f"Delay: {state['propagation_delay_ms']:.2f} ms")

            await asyncio.sleep(update_interval)

        self.logger.info("✅ Dynamic simulation complete")


class ChannelEmulatorFactory:
    """Factory to create channel emulators for different scenarios"""

    @staticmethod
    def create_geo(elevation_deg: float = 45.0) -> SoftwareChannelEmulator:
        """Create GEO satellite channel (35,786 km, 250ms RTT)"""
        config = ChannelConfig(
            orbit_type=OrbitType.GEO,
            channel_model=ChannelModel.TDL_A,  # Sparse multipath
            distance_km=35786,
            elevation_angle=elevation_deg,
            doppler_enabled=True,
        )
        return SoftwareChannelEmulator(config)

    @staticmethod
    def create_leo(altitude_km: float = 600.0) -> SoftwareChannelEmulator:
        """Create LEO satellite channel (600-1200 km)"""
        config = ChannelConfig(
            orbit_type=OrbitType.LEO,
            channel_model=ChannelModel.TDL_D,  # Time-varying with strong Doppler
            distance_km=altitude_km,
            elevation_angle=45.0,
            doppler_enabled=True,
        )
        return SoftwareChannelEmulator(config)

    @staticmethod
    def create_haps(altitude_km: float = 30.0, elevation_deg: float = 60.0) -> SoftwareChannelEmulator:
        """Create HAPS channel (20-50 km)"""
        config = ChannelConfig(
            orbit_type=OrbitType.HAPS,
            channel_model=ChannelModel.AWGN,  # Minimal multipath at high elevation
            distance_km=altitude_km,
            elevation_angle=elevation_deg,
            doppler_enabled=False,  # Negligible Doppler
            rain_attenuation=True,
            atmospheric_loss=True,
        )
        return SoftwareChannelEmulator(config)

    @staticmethod
    def create_awgn_only() -> SoftwareChannelEmulator:
        """Create simple AWGN channel (for testing)"""
        config = ChannelConfig(
            orbit_type=OrbitType.GEO,
            channel_model=ChannelModel.AWGN,
            distance_km=1.0,  # Minimal distance
            doppler_enabled=False,
            rain_attenuation=False,
            atmospheric_loss=False,
        )
        return SoftwareChannelEmulator(config)


# Example usage
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("="*60)
    print("Software Channel Emulator Demo")
    print("="*60)

    # Create GEO channel
    print("\n🛰️  Creating GEO channel (35,786 km, 250ms RTT)...")
    geo_channel = ChannelEmulatorFactory.create_geo(elevation_deg=45)

    # Generate test signal
    sample_rate = 30.72e6
    duration = 0.01  # 10ms
    num_samples = int(sample_rate * duration)

    print(f"\n📡 Generating test signal ({num_samples} samples)...")
    t = np.arange(num_samples) / sample_rate
    test_signal = 0.7 * np.exp(1j * 2 * np.pi * 1e6 * t)  # 1 MHz tone

    # Pass through channel
    print("🌍 Propagating through channel...")
    rx_signal = geo_channel.apply_channel(test_signal)

    # Analyze
    tx_power = 10 * np.log10(np.mean(np.abs(test_signal)**2) + 1e-10) + 30
    rx_power = 10 * np.log10(np.mean(np.abs(rx_signal)**2) + 1e-10) + 30
    measured_loss = tx_power - rx_power

    print(f"\n📊 Results:")
    print(f"   TX Power: {tx_power:.1f} dBm")
    print(f"   RX Power: {rx_power:.1f} dBm")
    print(f"   Measured Loss: {measured_loss:.2f} dB")
    print(f"   Expected Loss: {geo_channel.path_loss_db:.2f} dB")
    print(f"   Error: {abs(measured_loss - geo_channel.path_loss_db):.2f} dB")

    # Channel state
    print(f"\n🔧 Channel State:")
    state = geo_channel.get_channel_state()
    print(f"   Orbit: {state['orbit_type']}")
    print(f"   Model: {state['channel_model']}")
    print(f"   Delay: {state['propagation_delay_ms']:.2f} ms")
    print(f"   Doppler: {state['doppler_shift_hz']:.2f} Hz")
    print(f"   Rain: {state['rain_rate_mm_hr']:.2f} mm/hr")
    print(f"   Multipath Taps: {state['multipath_taps']}")
    print(f"   GPU: {state['gpu_enabled']}")

    # Test HAPS channel
    print(f"\n✈️  Creating HAPS channel (30 km)...")
    haps_channel = ChannelEmulatorFactory.create_haps(altitude_km=30, elevation_deg=60)

    rx_haps = haps_channel.apply_channel(test_signal)
    haps_loss = tx_power - (10 * np.log10(np.mean(np.abs(rx_haps)**2) + 1e-10) + 30)

    print(f"   HAPS Loss: {haps_loss:.2f} dB")
    print(f"   HAPS Delay: {haps_channel.propagation_delay_s * 1e6:.2f} μs")

    print("\n✅ Simulation complete!")
