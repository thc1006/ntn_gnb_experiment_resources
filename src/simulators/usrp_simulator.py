#!/usr/bin/env python3
"""
Software USRP Simulator - No Hardware Required
Simulates X310/B210 behavior using pure software
Supports GPU acceleration via CuPy
"""

import numpy as np
import time
import logging
from dataclasses import dataclass
from typing import Optional, Tuple
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

@dataclass
class USRPConfig:
    """USRP Configuration"""
    center_freq: float = 1.8e9          # 1.8 GHz
    sample_rate: float = 30.72e6        # 30.72 MHz
    bandwidth: float = 30e6             # 30 MHz
    tx_gain: float = 20                 # dB
    rx_gain: float = 40                 # dB
    device_type: str = "x310"           # x310 or b210

class SoftwareUSRP:
    """Software USRP Simulator"""

    def __init__(self, config: USRPConfig):
        self.config = config
        self.logger = logging.getLogger(f"USRP-{config.device_type}")
        self.tx_buffer = []
        self.rx_buffer = []
        self.is_streaming = False
        self.use_gpu = GPU_AVAILABLE

        # Simulate hardware imperfections
        self.dc_offset_i = np.random.normal(0, 0.01)
        self.dc_offset_q = np.random.normal(0, 0.01)
        self.iq_imbalance = np.random.normal(1.0, 0.02)
        self.phase_noise_std = 0.01
        self.frequency_offset_hz = np.random.normal(0, 50)

        self.logger.info(f"✅ Software USRP initialized: {config.device_type}")
        self.logger.info(f"   Center Freq: {config.center_freq/1e9:.2f} GHz")
        self.logger.info(f"   Sample Rate: {config.sample_rate/1e6:.2f} MHz")
        self.logger.info(f"   GPU Mode: {'Enabled' if self.use_gpu else 'Disabled'}")

    def set_tx_freq(self, freq: float):
        """Set TX frequency"""
        self.config.center_freq = freq
        self.logger.debug(f"TX Freq set to {freq/1e9:.3f} GHz")

    def set_rx_freq(self, freq: float):
        """Set RX frequency"""
        self.config.center_freq = freq
        self.logger.debug(f"RX Freq set to {freq/1e9:.3f} GHz")

    def set_tx_gain(self, gain: float):
        """Set TX gain"""
        self.config.tx_gain = gain
        self.logger.debug(f"TX Gain set to {gain} dB")

    def set_rx_gain(self, gain: float):
        """Set RX gain"""
        self.config.rx_gain = gain
        self.logger.debug(f"RX Gain set to {gain} dB")

    def transmit(self, samples: np.ndarray) -> int:
        """
        Transmit IQ samples

        Args:
            samples: Complex IQ samples (numpy or cupy array)

        Returns:
            Number of samples transmitted
        """
        # Convert to numpy if cupy
        if self.use_gpu and isinstance(samples, cp.ndarray):
            samples_cpu = cp.asnumpy(samples)
        else:
            samples_cpu = samples

        # Apply TX gain
        gain_linear = 10**(self.config.tx_gain / 20)
        tx_samples = samples_cpu * gain_linear

        # Add hardware imperfections
        tx_samples = self._add_tx_imperfections(tx_samples)

        # Store in buffer
        self.tx_buffer.append(tx_samples)

        self.logger.debug(f"Transmitted {len(samples)} samples")
        return len(samples)

    def receive(self, num_samples: int, add_noise: bool = True) -> np.ndarray:
        """
        Receive IQ samples (simulated)

        Args:
            num_samples: Number of samples to receive
            add_noise: Add AWGN noise

        Returns:
            Complex IQ samples
        """
        # If we have TX data, use it as RX (loopback simulation)
        if len(self.tx_buffer) > 0:
            tx_samples = self.tx_buffer.pop(0)

            # Simulate channel effects
            rx_samples = self._simulate_channel(tx_samples, add_noise)

            # Apply RX gain
            gain_linear = 10**(self.config.rx_gain / 20)
            rx_samples = rx_samples * gain_linear

            # Add RX imperfections
            rx_samples = self._add_rx_imperfections(rx_samples)

        else:
            # No TX data, generate noise only
            if add_noise:
                rx_samples = self._generate_noise(num_samples)
            else:
                rx_samples = np.zeros(num_samples, dtype=np.complex64)

        self.logger.debug(f"Received {len(rx_samples)} samples")
        return rx_samples

    def _add_tx_imperfections(self, samples: np.ndarray) -> np.ndarray:
        """Add TX hardware imperfections"""
        # DC offset
        samples_with_dc = samples + self.dc_offset_i + 1j * self.dc_offset_q

        # IQ imbalance (I channel slightly different gain)
        i_channel = np.real(samples_with_dc) * self.iq_imbalance
        q_channel = np.imag(samples_with_dc)
        samples_imbalanced = i_channel + 1j * q_channel

        # Phase noise
        phase_noise = np.random.normal(0, self.phase_noise_std, len(samples))
        samples_with_noise = samples_imbalanced * np.exp(1j * phase_noise)

        return samples_with_noise

    def _add_rx_imperfections(self, samples: np.ndarray) -> np.ndarray:
        """Add RX hardware imperfections"""
        # Frequency offset
        t = np.arange(len(samples)) / self.config.sample_rate
        freq_offset = np.exp(1j * 2 * np.pi * self.frequency_offset_hz * t)
        samples_with_offset = samples * freq_offset

        # Additional phase noise
        phase_noise = np.random.normal(0, self.phase_noise_std, len(samples))
        samples_final = samples_with_offset * np.exp(1j * phase_noise)

        return samples_final

    def _simulate_channel(self, tx_samples: np.ndarray, add_noise: bool) -> np.ndarray:
        """Simulate RF channel (path loss, delay, noise)"""
        # Simple path loss (will be overridden by channel emulator)
        path_loss_db = 40  # Simulated cable loss
        path_loss_linear = 10**(-path_loss_db / 20)

        rx_samples = tx_samples * path_loss_linear

        # Add AWGN noise
        if add_noise:
            noise = self._generate_noise(len(tx_samples))
            rx_samples = rx_samples + noise

        return rx_samples

    def _generate_noise(self, num_samples: int) -> np.ndarray:
        """Generate AWGN noise"""
        # Calculate noise power from sample rate and bandwidth
        # N = kTB + NF
        k = 1.38e-23  # Boltzmann constant
        T = 290       # Temperature (K)
        BW = self.config.bandwidth
        NF_linear = 10**(5 / 10)  # 5 dB noise figure

        noise_power = k * T * BW * NF_linear
        noise_amplitude = np.sqrt(noise_power / 2)  # /2 for I and Q

        noise_i = np.random.normal(0, noise_amplitude, num_samples)
        noise_q = np.random.normal(0, noise_amplitude, num_samples)
        noise = noise_i + 1j * noise_q

        return noise.astype(np.complex64)

    def generate_test_tone(self, freq_offset: float, duration: float,
                          amplitude: float = 0.7) -> np.ndarray:
        """
        Generate test tone

        Args:
            freq_offset: Frequency offset from center (Hz)
            duration: Duration in seconds
            amplitude: Signal amplitude (0-1)

        Returns:
            Complex IQ samples
        """
        num_samples = int(self.config.sample_rate * duration)
        t = np.arange(num_samples) / self.config.sample_rate

        # Use GPU if available
        if self.use_gpu:
            t = cp.array(t)
            samples = amplitude * cp.exp(1j * 2 * cp.pi * freq_offset * t)
            return cp.asnumpy(samples).astype(np.complex64)
        else:
            samples = amplitude * np.exp(1j * 2 * np.pi * freq_offset * t)
            return samples.astype(np.complex64)

    def generate_ofdm_signal(self, num_subcarriers: int = 1024,
                            duration: float = 1.0) -> np.ndarray:
        """
        Generate OFDM-like wideband signal

        Args:
            num_subcarriers: Number of OFDM subcarriers
            duration: Duration in seconds

        Returns:
            Complex IQ samples
        """
        num_samples = int(self.config.sample_rate * duration)

        # Use GPU if available
        if self.use_gpu:
            # Random QPSK symbols
            symbols = (cp.random.randint(0, 2, num_subcarriers) * 2 - 1) + \
                     1j * (cp.random.randint(0, 2, num_subcarriers) * 2 - 1)
            symbols = symbols / cp.sqrt(2)  # Normalize

            # IFFT to time domain
            time_signal = cp.fft.ifft(symbols, num_samples)

            # Repeat and scale
            samples = cp.tile(time_signal, num_samples // len(time_signal))[:num_samples]
            samples = 0.5 * samples  # Scale amplitude

            return cp.asnumpy(samples).astype(np.complex64)
        else:
            # Random QPSK symbols
            symbols = (np.random.randint(0, 2, num_subcarriers) * 2 - 1) + \
                     1j * (np.random.randint(0, 2, num_subcarriers) * 2 - 1)
            symbols = symbols / np.sqrt(2)  # Normalize

            # IFFT to time domain
            time_signal = np.fft.ifft(symbols, num_samples)

            # Repeat and scale
            samples = np.tile(time_signal, num_samples // len(time_signal))[:num_samples]
            samples = 0.5 * samples  # Scale amplitude

            return samples.astype(np.complex64)

    async def calibrate_dc_offset(self):
        """Calibrate DC offset"""
        self.logger.info("Performing DC offset calibration...")

        # Simulate calibration
        await asyncio.sleep(0.5)

        # Measure DC offset
        noise = self._generate_noise(10000)
        measured_dc_i = np.mean(np.real(noise))
        measured_dc_q = np.mean(np.imag(noise))

        # Apply correction
        self.dc_offset_i = -measured_dc_i
        self.dc_offset_q = -measured_dc_q

        self.logger.info(f"✅ DC offset calibrated: I={measured_dc_i:.6f}, Q={measured_dc_q:.6f}")

        return {
            "dc_i": float(measured_dc_i),
            "dc_q": float(measured_dc_q),
            "corrected": True
        }

    async def calibrate_iq_imbalance(self):
        """Calibrate IQ imbalance"""
        self.logger.info("Performing IQ imbalance calibration...")

        # Simulate calibration
        await asyncio.sleep(0.5)

        # Generate test tone
        test_tone = self.generate_test_tone(100e3, 0.1, 0.7)
        self.transmit(test_tone)
        rx_signal = self.receive(len(test_tone))

        # Calculate image rejection
        fft_rx = np.fft.fft(rx_signal)
        fft_freqs = np.fft.fftfreq(len(rx_signal), 1/self.config.sample_rate)

        pos_idx = np.argmax(np.abs(fft_rx[fft_freqs > 0]))
        neg_idx = np.argmax(np.abs(fft_rx[fft_freqs < 0]))

        signal_power = np.abs(fft_rx[fft_freqs > 0][pos_idx])**2
        image_power = np.abs(fft_rx[fft_freqs < 0][neg_idx])**2

        image_rejection_db = 10 * np.log10(signal_power / (image_power + 1e-10))

        # Apply correction if needed
        if image_rejection_db < 30:
            self.iq_imbalance = 1.0  # Perfect balance

        self.logger.info(f"✅ IQ imbalance calibrated: Image rejection = {image_rejection_db:.1f} dB")

        return {
            "image_rejection_db": float(image_rejection_db),
            "corrected": image_rejection_db < 30
        }

    def get_device_info(self) -> dict:
        """Get device information"""
        return {
            "device_type": self.config.device_type,
            "mode": "software_simulator",
            "center_freq": self.config.center_freq,
            "sample_rate": self.config.sample_rate,
            "bandwidth": self.config.bandwidth,
            "tx_gain": self.config.tx_gain,
            "rx_gain": self.config.rx_gain,
            "gpu_enabled": self.use_gpu,
            "hardware_imperfections": {
                "dc_offset_i": self.dc_offset_i,
                "dc_offset_q": self.dc_offset_q,
                "iq_imbalance": self.iq_imbalance,
                "frequency_offset_hz": self.frequency_offset_hz
            }
        }


class SimulatorFactory:
    """Factory to create USRP simulators"""

    @staticmethod
    def create_x310(addr: str = "sim://x310") -> SoftwareUSRP:
        """Create X310 simulator"""
        config = USRPConfig(
            center_freq=1.8e9,
            sample_rate=30.72e6,
            bandwidth=30e6,
            tx_gain=20,
            rx_gain=30,
            device_type="x310"
        )
        return SoftwareUSRP(config)

    @staticmethod
    def create_b210(serial: str = "sim://b210") -> SoftwareUSRP:
        """Create B210 simulator"""
        config = USRPConfig(
            center_freq=1.8e9,
            sample_rate=30.72e6,
            bandwidth=30e6,
            tx_gain=0,
            rx_gain=40,
            device_type="b210"
        )
        return SoftwareUSRP(config)


# Example usage
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    print("="*60)
    print("Software USRP Simulator Demo")
    print("="*60)

    # Create X310 simulator (TX)
    tx = SimulatorFactory.create_x310()

    # Create B210 simulator (RX)
    rx = SimulatorFactory.create_b210()

    # Generate test tone
    print("\n📡 Generating 1 MHz test tone...")
    test_tone = tx.generate_test_tone(1e6, 0.01, 0.7)

    # Transmit
    print("📤 Transmitting...")
    tx.transmit(test_tone)

    # Receive
    print("📥 Receiving...")
    rx_signal = rx.receive(len(test_tone))

    # Analyze
    tx_power = 10 * np.log10(np.mean(np.abs(test_tone)**2) + 1e-10) + 30
    rx_power = 10 * np.log10(np.mean(np.abs(rx_signal)**2) + 1e-10) + 30
    path_loss = tx_power - rx_power

    print(f"\n📊 Results:")
    print(f"   TX Power: {tx_power:.1f} dBm")
    print(f"   RX Power: {rx_power:.1f} dBm")
    print(f"   Path Loss: {path_loss:.1f} dB")

    # Device info
    print(f"\n🔧 Device Info:")
    info = tx.get_device_info()
    print(f"   Device: {info['device_type']}")
    print(f"   Mode: {info['mode']}")
    print(f"   GPU: {info['gpu_enabled']}")

    print("\n✅ Simulation complete!")
