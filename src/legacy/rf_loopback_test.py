#!/usr/bin/env python3
"""
RF Loopback Test for USRP Baseline Performance
Validates X310 to B210 connectivity with mandatory attenuation
"""

import numpy as np
import uhd
import argparse
import time
import sys
from datetime import datetime
import json

class RFLoopbackTest:
    def __init__(self, tx_args, rx_args, freq, rate, gain_tx, gain_rx, attenuation):
        """
        Initialize RF loopback test
        
        Args:
            tx_args: TX USRP arguments (e.g., "type=x310,addr=192.168.10.2")
            rx_args: RX USRP arguments (e.g., "type=b210")
            freq: Center frequency in Hz
            rate: Sample rate in Hz
            gain_tx: TX gain in dB
            gain_rx: RX gain in dB
            attenuation: External attenuation in dB (MUST be 30-40 dB)
        """
        self.freq = freq
        self.rate = rate
        self.gain_tx = gain_tx
        self.gain_rx = gain_rx
        self.attenuation = attenuation
        
        # Safety check for attenuation
        if attenuation < 30:
            raise ValueError("DANGER: Attenuation must be at least 30 dB to protect RX!")
        
        # Initialize TX USRP (X310)
        print(f"Initializing TX USRP: {tx_args}")
        self.usrp_tx = uhd.usrp.MultiUSRP(tx_args)
        
        # Initialize RX USRP (B210)
        print(f"Initializing RX USRP: {rx_args}")
        self.usrp_rx = uhd.usrp.MultiUSRP(rx_args)
        
        # Configure USRPs
        self.configure_usrps()
        
        # Test results
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "configuration": {
                "frequency": freq,
                "sample_rate": rate,
                "tx_gain": gain_tx,
                "rx_gain": gain_rx,
                "attenuation": attenuation
            },
            "tests": {}
        }
        
    def configure_usrps(self):
        """Configure TX and RX USRPs"""
        # TX Configuration (X310)
        self.usrp_tx.set_tx_rate(self.rate, 0)
        self.usrp_tx.set_tx_freq(uhd.libpyuhd.types.tune_request(self.freq), 0)
        self.usrp_tx.set_tx_gain(self.gain_tx, 0)
        
        # RX Configuration (B210)
        self.usrp_rx.set_rx_rate(self.rate, 0)
        self.usrp_rx.set_rx_freq(uhd.libpyuhd.types.tune_request(self.freq), 0)
        self.usrp_rx.set_rx_gain(self.gain_rx, 0)
        
        # Allow settling time
        time.sleep(0.5)
        
        # Print configuration
        print("\nTX Configuration (X310):")
        print(f"  Frequency: {self.usrp_tx.get_tx_freq(0)/1e6:.2f} MHz")
        print(f"  Sample Rate: {self.usrp_tx.get_tx_rate(0)/1e6:.2f} Msps")
        print(f"  Gain: {self.usrp_tx.get_tx_gain(0):.1f} dB")
        
        print("\nRX Configuration (B210):")
        print(f"  Frequency: {self.usrp_rx.get_rx_freq(0)/1e6:.2f} MHz")
        print(f"  Sample Rate: {self.usrp_rx.get_rx_rate(0)/1e6:.2f} Msps")
        print(f"  Gain: {self.usrp_rx.get_rx_gain(0):.1f} dB")
        print(f"\nExternal Attenuation: {self.attenuation} dB")
        
    def test_single_tone(self, tone_freq=100e3, duration=1.0):
        """
        Test with single tone transmission
        
        Args:
            tone_freq: Tone frequency offset from carrier (Hz)
            duration: Test duration (seconds)
        """
        print(f"\n--- Single Tone Test ({tone_freq/1e3:.1f} kHz) ---")
        
        num_samples = int(self.rate * duration)
        
        # Generate test tone
        t = np.arange(num_samples) / self.rate
        tx_signal = 0.7 * np.exp(1j * 2 * np.pi * tone_freq * t)
        tx_signal = tx_signal.astype(np.complex64)
        
        # Setup streams
        tx_streamer = self.usrp_tx.get_tx_stream(uhd.usrp.StreamArgs("fc32", "sc16"))
        rx_streamer = self.usrp_rx.get_rx_stream(uhd.usrp.StreamArgs("fc32", "sc16"))
        
        # Receive buffer
        rx_buffer = np.zeros(num_samples, dtype=np.complex64)
        
        # Start RX streaming
        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.num_done)
        stream_cmd.num_samps = num_samples
        stream_cmd.stream_now = True
        rx_streamer.issue_stream_cmd(stream_cmd)
        
        # Transmit
        metadata_tx = uhd.types.TXMetadata()
        metadata_tx.start_of_burst = True
        metadata_tx.end_of_burst = True
        
        tx_streamer.send(tx_signal, metadata_tx)
        
        # Receive
        metadata_rx = uhd.types.RXMetadata()
        rx_streamer.recv(rx_buffer, metadata_rx)
        
        # Analyze results
        results = self.analyze_signal(tx_signal, rx_buffer, tone_freq)
        
        print(f"  TX Power: {results['tx_power_dbm']:.1f} dBm")
        print(f"  RX Power: {results['rx_power_dbm']:.1f} dBm")
        print(f"  Path Loss: {results['path_loss_db']:.1f} dB")
        print(f"  Expected Loss: {self.attenuation} dB")
        print(f"  Frequency Offset: {results['freq_offset_hz']:.1f} Hz")
        print(f"  SNR: {results['snr_db']:.1f} dB")
        print(f"  EVM: {results['evm_percent']:.2f} %")
        
        self.results["tests"]["single_tone"] = results
        
        # Pass/Fail criteria
        if abs(results['path_loss_db'] - self.attenuation) > 3:
            print("  WARNING: Path loss differs from expected attenuation!")
        if results['snr_db'] < 30:
            print("  WARNING: Low SNR detected!")
        if results['evm_percent'] > 5:
            print("  WARNING: High EVM detected!")
            
        return results
        
    def test_wideband(self, duration=1.0):
        """Test with wideband signal (OFDM-like)"""
        print(f"\n--- Wideband Signal Test ---")
        
        num_samples = int(self.rate * duration)
        
        # Generate OFDM-like signal
        num_subcarriers = 1024
        tx_symbols = np.random.randn(num_subcarriers) + 1j * np.random.randn(num_subcarriers)
        tx_symbols = tx_symbols / np.sqrt(2)  # Normalize
        
        # IFFT to time domain
        tx_time = np.fft.ifft(tx_symbols, num_samples)
        tx_signal = 0.5 * tx_time.astype(np.complex64)
        
        # Setup streams
        tx_streamer = self.usrp_tx.get_tx_stream(uhd.usrp.StreamArgs("fc32", "sc16"))
        rx_streamer = self.usrp_rx.get_rx_stream(uhd.usrp.StreamArgs("fc32", "sc16"))
        
        # Receive buffer
        rx_buffer = np.zeros(num_samples, dtype=np.complex64)
        
        # Start RX streaming
        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.num_done)
        stream_cmd.num_samps = num_samples
        stream_cmd.stream_now = True
        rx_streamer.issue_stream_cmd(stream_cmd)
        
        # Transmit
        metadata_tx = uhd.types.TXMetadata()
        metadata_tx.start_of_burst = True
        metadata_tx.end_of_burst = True
        
        tx_streamer.send(tx_signal, metadata_tx)
        
        # Receive
        metadata_rx = uhd.types.RXMetadata()
        rx_streamer.recv(rx_buffer, metadata_rx)
        
        # Analyze spectrum
        tx_spectrum = 20 * np.log10(np.abs(np.fft.fft(tx_signal)) + 1e-10)
        rx_spectrum = 20 * np.log10(np.abs(np.fft.fft(rx_buffer)) + 1e-10)
        
        # Calculate metrics
        tx_power = 10 * np.log10(np.mean(np.abs(tx_signal)**2) + 1e-10) + 30
        rx_power = 10 * np.log10(np.mean(np.abs(rx_buffer)**2) + 1e-10) + 30
        
        # Channel frequency response
        H = np.fft.fft(rx_buffer) / (np.fft.fft(tx_signal) + 1e-10)
        channel_flatness = np.std(20 * np.log10(np.abs(H[:num_subcarriers])))
        
        results = {
            "tx_power_dbm": tx_power,
            "rx_power_dbm": rx_power,
            "path_loss_db": tx_power - rx_power,
            "channel_flatness_db": channel_flatness
        }
        
        print(f"  TX Power: {results['tx_power_dbm']:.1f} dBm")
        print(f"  RX Power: {results['rx_power_dbm']:.1f} dBm")
        print(f"  Path Loss: {results['path_loss_db']:.1f} dB")
        print(f"  Channel Flatness: {results['channel_flatness_db']:.2f} dB")
        
        self.results["tests"]["wideband"] = results
        
        return results
        
    def test_phase_coherence(self, duration=0.1):
        """Test phase coherence between TX and RX"""
        print(f"\n--- Phase Coherence Test ---")
        
        num_samples = int(self.rate * duration)
        phases = []
        
        for i in range(10):
            # Generate constant envelope signal
            tx_signal = np.ones(num_samples, dtype=np.complex64) * 0.7
            
            # Setup streams
            tx_streamer = self.usrp_tx.get_tx_stream(uhd.usrp.StreamArgs("fc32", "sc16"))
            rx_streamer = self.usrp_rx.get_rx_stream(uhd.usrp.StreamArgs("fc32", "sc16"))
            
            # Receive buffer
            rx_buffer = np.zeros(num_samples, dtype=np.complex64)
            
            # Start RX streaming
            stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.num_done)
            stream_cmd.num_samps = num_samples
            stream_cmd.stream_now = True
            rx_streamer.issue_stream_cmd(stream_cmd)
            
            # Transmit
            metadata_tx = uhd.types.TXMetadata()
            metadata_tx.start_of_burst = True
            metadata_tx.end_of_burst = True
            
            tx_streamer.send(tx_signal, metadata_tx)
            
            # Receive
            metadata_rx = uhd.types.RXMetadata()
            rx_streamer.recv(rx_buffer, metadata_rx)
            
            # Calculate phase
            phase = np.angle(np.mean(rx_buffer))
            phases.append(phase)
            
            time.sleep(0.1)
            
        # Calculate phase stability
        phases = np.array(phases)
        phase_drift = np.std(np.unwrap(phases)) * 180 / np.pi
        
        results = {
            "phase_drift_deg": phase_drift,
            "phase_measurements": phases.tolist()
        }
        
        print(f"  Phase Drift: {phase_drift:.2f} degrees")
        
        if phase_drift > 10:
            print("  WARNING: High phase drift detected!")
            
        self.results["tests"]["phase_coherence"] = results
        
        return results
        
    def analyze_signal(self, tx_signal, rx_signal, expected_freq):
        """Analyze received signal quality"""
        # Power measurements
        tx_power = 10 * np.log10(np.mean(np.abs(tx_signal)**2) + 1e-10) + 30
        rx_power = 10 * np.log10(np.mean(np.abs(rx_signal)**2) + 1e-10) + 30
        
        # FFT for frequency analysis
        fft_rx = np.fft.fft(rx_signal)
        fft_freqs = np.fft.fftfreq(len(rx_signal), 1/self.rate)
        
        # Find peak
        peak_idx = np.argmax(np.abs(fft_rx))
        measured_freq = fft_freqs[peak_idx]
        freq_offset = measured_freq - expected_freq
        
        # SNR estimation
        signal_power = np.abs(fft_rx[peak_idx])**2
        noise_power = np.mean(np.abs(fft_rx)**2) - signal_power
        snr = 10 * np.log10(signal_power / (noise_power + 1e-10))
        
        # EVM calculation (simplified)
        # Normalize and align signals
        rx_aligned = rx_signal * np.exp(-1j * np.angle(np.mean(rx_signal * np.conj(tx_signal))))
        rx_scaled = rx_aligned * (np.abs(np.mean(tx_signal)) / np.abs(np.mean(rx_aligned)))
        
        error = rx_scaled - tx_signal
        evm = 100 * np.sqrt(np.mean(np.abs(error)**2) / np.mean(np.abs(tx_signal)**2))
        
        return {
            "tx_power_dbm": tx_power,
            "rx_power_dbm": rx_power,
            "path_loss_db": tx_power - rx_power,
            "freq_offset_hz": freq_offset,
            "snr_db": snr,
            "evm_percent": evm
        }
        
    def save_results(self, filename="rf_loopback_results.json"):
        """Save test results to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResults saved to {filename}")
        
    def run_all_tests(self):
        """Run complete test suite"""
        print("\n" + "="*50)
        print("Starting RF Loopback Test Suite")
        print("="*50)
        
        # Safety reminder
        print(f"\n⚠️  SAFETY CHECK: Ensure {self.attenuation} dB attenuator is connected!")
        input("Press Enter to continue...")
        
        # Run tests
        self.test_single_tone(100e3)
        self.test_single_tone(1e6)
        self.test_wideband()
        self.test_phase_coherence()
        
        # Overall assessment
        print("\n" + "="*50)
        print("Test Suite Complete")
        print("="*50)
        
        # Check for issues
        issues = []
        
        if "single_tone" in self.results["tests"]:
            tone_results = self.results["tests"]["single_tone"]
            if abs(tone_results['path_loss_db'] - self.attenuation) > 3:
                issues.append("Path loss mismatch")
            if tone_results['snr_db'] < 30:
                issues.append("Low SNR")
            if tone_results['evm_percent'] > 5:
                issues.append("High EVM")
                
        if "phase_coherence" in self.results["tests"]:
            if self.results["tests"]["phase_coherence"]["phase_drift_deg"] > 10:
                issues.append("Phase instability")
                
        if issues:
            print(f"\n⚠️  Issues detected: {', '.join(issues)}")
            print("Please check connections and calibration")
        else:
            print("\n✅ All tests passed successfully!")
            
        # Save results
        self.save_results()

def main():
    parser = argparse.ArgumentParser(description="RF Loopback Test for USRP")
    parser.add_argument("--tx-args", type=str, default="type=x310,addr=192.168.10.2",
                        help="TX USRP device arguments")
    parser.add_argument("--rx-args", type=str, default="type=b210",
                        help="RX USRP device arguments")
    parser.add_argument("--freq", type=float, default=1.5e9,
                        help="Center frequency in Hz (default: 1.5 GHz)")
    parser.add_argument("--rate", type=float, default=10e6,
                        help="Sample rate in Hz (default: 10 MHz)")
    parser.add_argument("--tx-gain", type=float, default=20,
                        help="TX gain in dB (default: 20)")
    parser.add_argument("--rx-gain", type=float, default=30,
                        help="RX gain in dB (default: 30)")
    parser.add_argument("--atten", type=float, default=40,
                        help="External attenuation in dB (MUST be 30-40, default: 40)")
    
    args = parser.parse_args()
    
    # Safety check
    if args.atten < 30:
        print("ERROR: Attenuation must be at least 30 dB for safety!")
        sys.exit(1)
        
    try:
        tester = RFLoopbackTest(
            args.tx_args,
            args.rx_args,
            args.freq,
            args.rate,
            args.tx_gain,
            args.rx_gain,
            args.atten
        )
        
        tester.run_all_tests()
        
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
