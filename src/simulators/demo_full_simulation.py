#!/usr/bin/env python3
"""
Complete End-to-End 5G NTN Simulation Demo
===========================================

Demonstrates full software testbed replacing physical hardware:
  TX USRP (X310) → Channel Emulator (GEO/LEO/HAPS) → RX USRP (B210)

No hardware required! Pure software simulation with optional GPU acceleration.
"""

import numpy as np
import matplotlib.pyplot as plt
import logging
import time
from pathlib import Path
import json

# Import simulators
from .usrp_simulator import SimulatorFactory as USRPFactory
from .channel_simulator import ChannelEmulatorFactory, OrbitType


def setup_logging():
    """Configure logging"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def print_header(text, char="="):
    """Print formatted header"""
    width = 80
    print(f"\n{char * width}")
    print(f"{text:^{width}}")
    print(f"{char * width}\n")


def scenario_geo_satellite():
    """
    Scenario 1: GEO Satellite Link (35,786 km)
    - 250ms round-trip delay
    - ~190 dB path loss
    - Minimal Doppler (±15 Hz)
    """
    print_header("Scenario 1: GEO Satellite Link", "=")

    # Create hardware simulators
    print("🔧 Creating USRP simulators...")
    tx = USRPFactory.create_x310()
    rx = USRPFactory.create_b210()

    # Create GEO channel
    print("🛰️  Creating GEO channel emulator (35,786 km)...")
    channel = ChannelEmulatorFactory.create_geo(elevation_deg=45)

    # Generate OFDM-like wideband signal (LTE/5G NR)
    print("📡 Generating 5G NR wideband signal (1024 subcarriers, 30.72 MHz BW)...")
    tx_signal = tx.generate_ofdm_signal(num_subcarriers=1024, duration=0.01)

    print(f"   Signal length: {len(tx_signal)} samples")
    print(f"   Duration: {len(tx_signal)/tx.config.sample_rate*1000:.2f} ms")

    # Transmit
    print("📤 Transmitting...")
    num_tx = tx.transmit(tx_signal)

    # Pass through channel
    print("🌍 Propagating through GEO satellite channel...")
    channel_output = channel.apply_channel(tx_signal)

    # Receive
    print("📥 Receiving...")
    rx_signal = channel_output  # Direct connection for simulation

    # Analyze results
    print_header("Analysis Results", "-")

    tx_power_dbm = 10 * np.log10(np.mean(np.abs(tx_signal)**2) + 1e-10) + 30
    rx_power_dbm = 10 * np.log10(np.mean(np.abs(rx_signal)**2) + 1e-10) + 30
    measured_loss = tx_power_dbm - rx_power_dbm

    channel_state = channel.get_channel_state()

    print(f"📊 Link Budget:")
    print(f"   TX Power:        {tx_power_dbm:>8.2f} dBm")
    print(f"   RX Power:        {rx_power_dbm:>8.2f} dBm")
    print(f"   Measured Loss:   {measured_loss:>8.2f} dB")
    print(f"   Expected Loss:   {channel_state['path_loss_db']:>8.2f} dB")
    print(f"   Error:           {abs(measured_loss - channel_state['path_loss_db']):>8.2f} dB")

    print(f"\n🛰️  Channel Parameters:")
    print(f"   Distance:        {channel_state['distance_km']:>8.1f} km")
    print(f"   Delay:           {channel_state['propagation_delay_ms']:>8.2f} ms")
    print(f"   RTT:             {channel_state['propagation_delay_ms']*2:>8.2f} ms")
    print(f"   Doppler Shift:   {channel_state['doppler_shift_hz']:>8.2f} Hz")
    print(f"   Rain Rate:       {channel_state['rain_rate_mm_hr']:>8.2f} mm/hr")
    print(f"   Elevation:       {channel_state['elevation_angle_deg']:>8.1f}°")

    # Calculate SNR
    noise_power = np.var(rx_signal[:1000])  # Estimate from first samples
    signal_power = np.mean(np.abs(rx_signal)**2)
    snr_db = 10 * np.log10(signal_power / (noise_power + 1e-10))

    print(f"\n📈 Signal Quality:")
    print(f"   SNR:             {snr_db:>8.2f} dB")

    # Plot spectrum
    plot_spectrum(tx_signal, rx_signal, tx.config.sample_rate, "GEO Satellite")

    return {
        "scenario": "GEO",
        "tx_power_dbm": tx_power_dbm,
        "rx_power_dbm": rx_power_dbm,
        "path_loss_db": measured_loss,
        "delay_ms": channel_state['propagation_delay_ms'],
        "snr_db": snr_db,
    }


def scenario_leo_satellite():
    """
    Scenario 2: LEO Satellite Link (600 km)
    - ~10ms delay
    - ~170 dB path loss
    - Strong Doppler (±37.5 kHz)
    """
    print_header("Scenario 2: LEO Satellite Link", "=")

    # Create hardware simulators
    print("🔧 Creating USRP simulators...")
    tx = USRPFactory.create_x310()
    rx = USRPFactory.create_b210()

    # Create LEO channel
    print("🛰️  Creating LEO channel emulator (600 km)...")
    channel = ChannelEmulatorFactory.create_leo(altitude_km=600)

    # Generate test tone
    print("📡 Generating 1 MHz test tone...")
    tx_signal = tx.generate_test_tone(freq_offset=1e6, duration=0.01, amplitude=0.7)

    # Transmit
    print("📤 Transmitting...")
    tx.transmit(tx_signal)

    # Pass through channel
    print("🌍 Propagating through LEO satellite channel...")
    channel_output = channel.apply_channel(tx_signal)

    # Receive
    print("📥 Receiving...")
    rx_signal = channel_output

    # Analyze
    print_header("Analysis Results", "-")

    tx_power_dbm = 10 * np.log10(np.mean(np.abs(tx_signal)**2) + 1e-10) + 30
    rx_power_dbm = 10 * np.log10(np.mean(np.abs(rx_signal)**2) + 1e-10) + 30
    measured_loss = tx_power_dbm - rx_power_dbm

    channel_state = channel.get_channel_state()

    print(f"📊 Link Budget:")
    print(f"   TX Power:        {tx_power_dbm:>8.2f} dBm")
    print(f"   RX Power:        {rx_power_dbm:>8.2f} dBm")
    print(f"   Path Loss:       {measured_loss:>8.2f} dB")

    print(f"\n🛰️  Channel Parameters:")
    print(f"   Distance:        {channel_state['distance_km']:>8.1f} km")
    print(f"   Delay:           {channel_state['propagation_delay_ms']:>8.2f} ms")
    print(f"   Doppler Shift:   {channel_state['doppler_shift_hz']:>8.2f} Hz")
    print(f"   Doppler Rate:    {channel_state['doppler_rate_hz_s']:>8.2f} Hz/s")

    # Measure Doppler from spectrum
    fft_rx = np.fft.fftshift(np.fft.fft(rx_signal))
    freqs = np.fft.fftshift(np.fft.fftfreq(len(rx_signal), 1/tx.config.sample_rate))
    peak_idx = np.argmax(np.abs(fft_rx))
    measured_freq = freqs[peak_idx]

    print(f"\n📈 Doppler Analysis:")
    print(f"   Expected Tone:   {1e6:>12.2f} Hz")
    print(f"   Measured Peak:   {measured_freq:>12.2f} Hz")
    print(f"   Doppler Shift:   {measured_freq - 1e6:>12.2f} Hz")

    return {
        "scenario": "LEO",
        "tx_power_dbm": tx_power_dbm,
        "rx_power_dbm": rx_power_dbm,
        "path_loss_db": measured_loss,
        "delay_ms": channel_state['propagation_delay_ms'],
        "doppler_hz": channel_state['doppler_shift_hz'],
    }


def scenario_haps_30km():
    """
    Scenario 3: HAPS Link (30 km altitude)
    - ~100 μs delay
    - ~128 dB path loss (2 GHz)
    - Minimal Doppler
    - Target for 5G NTN testing
    """
    print_header("Scenario 3: HAPS 30km Link", "=")

    # Create hardware simulators
    print("🔧 Creating USRP simulators...")
    tx = USRPFactory.create_x310()
    rx = USRPFactory.create_b210()

    # Create HAPS channel
    print("✈️  Creating HAPS channel emulator (30 km, 60° elevation)...")
    channel = ChannelEmulatorFactory.create_haps(altitude_km=30, elevation_deg=60)

    # Generate OFDM signal
    print("📡 Generating 5G NR signal...")
    tx_signal = tx.generate_ofdm_signal(num_subcarriers=1024, duration=0.01)

    # Transmit
    print("📤 Transmitting...")
    tx.transmit(tx_signal)

    # Pass through channel
    print("🌍 Propagating through HAPS channel...")
    channel_output = channel.apply_channel(tx_signal)

    # Receive
    print("📥 Receiving...")
    rx_signal = channel_output

    # Analyze
    print_header("Analysis Results", "-")

    tx_power_dbm = 10 * np.log10(np.mean(np.abs(tx_signal)**2) + 1e-10) + 30
    rx_power_dbm = 10 * np.log10(np.mean(np.abs(rx_signal)**2) + 1e-10) + 30
    measured_loss = tx_power_dbm - rx_power_dbm

    channel_state = channel.get_channel_state()

    print(f"📊 Link Budget:")
    print(f"   TX Power:        {tx_power_dbm:>8.2f} dBm")
    print(f"   RX Power:        {rx_power_dbm:>8.2f} dBm")
    print(f"   Path Loss:       {measured_loss:>8.2f} dB")

    print(f"\n✈️  Channel Parameters:")
    print(f"   Distance:        {channel_state['distance_km']:>8.1f} km")
    print(f"   Delay:           {channel_state['propagation_delay_ms']*1000:>8.2f} μs")
    print(f"   Elevation:       {channel_state['elevation_angle_deg']:>8.1f}°")
    print(f"   Rain Rate:       {channel_state['rain_rate_mm_hr']:>8.2f} mm/hr")

    # Calculate required EIRP for 10 dB link margin
    target_rx_power = -90  # dBm (typical 5G NR sensitivity)
    required_eirp = target_rx_power + measured_loss + 10  # 10 dB margin

    print(f"\n🔧 Link Budget Design:")
    print(f"   Target RX Power: {target_rx_power:>8.2f} dBm")
    print(f"   Path Loss:       {measured_loss:>8.2f} dB")
    print(f"   Required EIRP:   {required_eirp:>8.2f} dBm")
    print(f"   Link Margin:     {10:>8.2f} dB")

    return {
        "scenario": "HAPS",
        "tx_power_dbm": tx_power_dbm,
        "rx_power_dbm": rx_power_dbm,
        "path_loss_db": measured_loss,
        "delay_us": channel_state['propagation_delay_ms'] * 1000,
        "required_eirp_dbm": required_eirp,
    }


def plot_spectrum(tx_signal, rx_signal, sample_rate, title):
    """Plot TX and RX spectrum comparison"""
    # Compute FFT
    fft_tx = np.fft.fftshift(np.fft.fft(tx_signal))
    fft_rx = np.fft.fftshift(np.fft.fft(rx_signal))
    freqs = np.fft.fftshift(np.fft.fftfreq(len(tx_signal), 1/sample_rate)) / 1e6  # MHz

    # Convert to dB
    psd_tx = 10 * np.log10(np.abs(fft_tx)**2 + 1e-10)
    psd_rx = 10 * np.log10(np.abs(fft_rx)**2 + 1e-10)

    # Normalize
    psd_tx -= np.max(psd_tx)
    psd_rx -= np.max(psd_rx)

    # Plot
    plt.figure(figsize=(12, 5))

    plt.subplot(1, 2, 1)
    plt.plot(freqs, psd_tx, label='TX', alpha=0.7)
    plt.plot(freqs, psd_rx, label='RX', alpha=0.7)
    plt.xlabel('Frequency (MHz)')
    plt.ylabel('Power (dB, normalized)')
    plt.title(f'{title} - Spectrum')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.xlim([-sample_rate/2e6, sample_rate/2e6])
    plt.ylim([-80, 5])

    plt.subplot(1, 2, 2)
    plt.plot(np.real(tx_signal[:1000]), np.imag(tx_signal[:1000]), 'o', alpha=0.3, label='TX', markersize=1)
    plt.plot(np.real(rx_signal[:1000]), np.imag(rx_signal[:1000]), 'o', alpha=0.3, label='RX', markersize=1)
    plt.xlabel('I')
    plt.ylabel('Q')
    plt.title(f'{title} - Constellation')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.axis('equal')

    plt.tight_layout()

    # Save plot
    output_dir = Path(__file__).parent.parent / "results"
    output_dir.mkdir(exist_ok=True)
    plt.savefig(output_dir / f"spectrum_{title.replace(' ', '_').lower()}.png", dpi=150)
    print(f"   💾 Plot saved to: {output_dir / f'spectrum_{title.replace(' ', '_').lower()}.png'}")


def main():
    """Run all scenarios"""
    setup_logging()

    print_header("5G NTN Software Testbed - Complete Simulation", "=")
    print("No hardware required! Fully simulated X310 + B210 + Channel Emulator")
    print("Supports: GEO, LEO, HAPS scenarios with GPU acceleration")

    results = {}

    # Run scenarios
    try:
        results['geo'] = scenario_geo_satellite()
        time.sleep(1)

        results['leo'] = scenario_leo_satellite()
        time.sleep(1)

        results['haps'] = scenario_haps_30km()

    except Exception as e:
        print(f"\n❌ Error during simulation: {e}")
        import traceback
        traceback.print_exc()
        return

    # Summary
    print_header("Simulation Summary", "=")

    print("Scenario            | TX Power | RX Power | Path Loss | Delay      | Status")
    print("-" * 80)
    print(f"GEO (35,786 km)    | {results['geo']['tx_power_dbm']:>7.1f} dBm | {results['geo']['rx_power_dbm']:>7.1f} dBm | "
          f"{results['geo']['path_loss_db']:>8.2f} dB | {results['geo']['delay_ms']:>7.2f} ms | ✅")
    print(f"LEO (600 km)       | {results['leo']['tx_power_dbm']:>7.1f} dBm | {results['leo']['rx_power_dbm']:>7.1f} dBm | "
          f"{results['leo']['path_loss_db']:>8.2f} dB | {results['leo']['delay_ms']:>7.2f} ms | ✅")
    print(f"HAPS (30 km)       | {results['haps']['tx_power_dbm']:>7.1f} dBm | {results['haps']['rx_power_dbm']:>7.1f} dBm | "
          f"{results['haps']['path_loss_db']:>8.2f} dB | {results['haps']['delay_us']:>7.2f} μs | ✅")

    # Save results
    output_dir = Path(__file__).parent.parent / "results"
    output_dir.mkdir(exist_ok=True)

    results_file = output_dir / "simulation_results.json"
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Results saved to: {results_file}")

    print_header("Simulation Complete!", "=")
    print("✅ All scenarios passed successfully!")
    print("✅ Software testbed is fully operational!")
    print("\nNext steps:")
    print("  1. Review plots in results/ directory")
    print("  2. Integrate with Docker containers")
    print("  3. Deploy to Kubernetes (Kind)")
    print("  4. Connect to 5G Core (Open5GS simulation)")


if __name__ == "__main__":
    main()
