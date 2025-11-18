#!/usr/bin/env python3
"""
5G NTN USRP Configuration and Testing Script
For USRP X310 (Transmitter) and B210 (Receiver)
Date: 2025-11-18
"""

import uhd
import numpy as np
import time
import argparse
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NTNTestConfig:
    """Configuration for NTN testing"""
    
    # Frequency parameters (L-band n8)
    CENTER_FREQ = 1.8e9  # 1.8 GHz
    SAMPLE_RATE = 30.72e6  # 30.72 MHz (suitable for 30 MHz bandwidth)
    BANDWIDTH = 30e6  # 30 MHz
    
    # Power parameters
    TX_GAIN = 20  # dB (adjust based on channel emulator input requirements)
    RX_GAIN = 40  # dB
    
    # Timing parameters
    CLOCK_RATE = 61.44e6  # Master clock rate
    
    # GEO satellite parameters
    PROPAGATION_DELAY = 0.25  # 250ms one-way delay
    PATH_LOSS_DB = 190  # Typical GEO path loss
    
    # Test signal parameters
    TONE_FREQ = 1e6  # 1 MHz test tone
    DURATION = 10  # seconds

class USRPDevice:
    """Base class for USRP device control"""
    
    def __init__(self, args="", cpu_format="fc32", otw_format="sc16"):
        self.usrp = uhd.usrp.MultiUSRP(args)
        self.cpu_format = cpu_format
        self.otw_format = otw_format
        self.stream_args = uhd.usrp.StreamArgs(cpu_format, otw_format)
        
    def set_clock_source(self, source="internal"):
        """Set clock source (internal, external, gpsdo)"""
        self.usrp.set_clock_source(source)
        logger.info(f"Clock source set to: {source}")
        
    def set_time_source(self, source="internal"):
        """Set time source (internal, external, gpsdo)"""
        self.usrp.set_time_source(source)
        logger.info(f"Time source set to: {source}")
        
    def check_gpsdo_lock(self):
        """Check if GPSDO is locked (for X310)"""
        if "gpsdo" in self.usrp.get_clock_sources():
            locked = self.usrp.get_mboard_sensor("gps_locked").to_bool()
            logger.info(f"GPSDO lock status: {locked}")
            return locked
        return False

class TransmitterX310(USRPDevice):
    """USRP X310 Transmitter configuration"""
    
    def __init__(self, args="addr=192.168.10.2"):
        super().__init__(args)
        self.tx_streamer = self.usrp.get_tx_stream(self.stream_args)
        
    def configure_tx(self, freq, rate, gain, bandwidth):
        """Configure transmitter parameters"""
        self.usrp.set_tx_rate(rate)
        self.usrp.set_tx_freq(uhd.types.TuneRequest(freq))
        self.usrp.set_tx_gain(gain)
        self.usrp.set_tx_bandwidth(bandwidth)
        
        # Wait for settling
        time.sleep(0.1)
        
        logger.info(f"TX configured: Freq={freq/1e9:.3f}GHz, Rate={rate/1e6:.2f}MHz, Gain={gain}dB")
        
    def transmit_test_signal(self, duration=10, tone_freq=1e6):
        """Transmit a test tone"""
        rate = self.usrp.get_tx_rate()
        n_samples = int(duration * rate)
        
        # Generate test tone
        t = np.arange(n_samples) / rate
        samples = np.exp(2j * np.pi * tone_freq * t).astype(np.complex64)
        
        # Transmit
        metadata = uhd.types.TXMetadata()
        metadata.start_of_burst = True
        metadata.end_of_burst = False
        metadata.has_time_spec = False
        
        logger.info(f"Transmitting {tone_freq/1e6:.1f}MHz tone for {duration}s...")
        
        samples_sent = 0
        chunk_size = self.tx_streamer.get_max_num_samps()
        
        while samples_sent < n_samples:
            chunk = samples[samples_sent:samples_sent + chunk_size]
            samples_sent += self.tx_streamer.send(chunk, metadata)
            metadata.start_of_burst = False
        
        # Send end of burst
        metadata.end_of_burst = True
        self.tx_streamer.send(np.array([]), metadata)
        
        logger.info(f"Transmission complete. Sent {samples_sent} samples")

class ReceiverB210(USRPDevice):
    """USRP B210 Receiver configuration"""
    
    def __init__(self, args="type=b200"):
        super().__init__(args)
        self.rx_streamer = self.usrp.get_rx_stream(self.stream_args)
        
    def configure_rx(self, freq, rate, gain, bandwidth):
        """Configure receiver parameters"""
        self.usrp.set_rx_rate(rate)
        self.usrp.set_rx_freq(uhd.types.TuneRequest(freq))
        self.usrp.set_rx_gain(gain)
        self.usrp.set_rx_bandwidth(bandwidth)
        
        # Wait for settling
        time.sleep(0.1)
        
        logger.info(f"RX configured: Freq={freq/1e9:.3f}GHz, Rate={rate/1e6:.2f}MHz, Gain={gain}dB")
        
    def receive_samples(self, n_samples):
        """Receive samples"""
        samples = np.zeros(n_samples, dtype=np.complex64)
        metadata = uhd.types.RXMetadata()
        
        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.start_cont)
        stream_cmd.stream_now = True
        self.rx_streamer.issue_stream_cmd(stream_cmd)
        
        samples_received = 0
        while samples_received < n_samples:
            chunk = samples[samples_received:samples_received + self.rx_streamer.get_max_num_samps()]
            samples_received += self.rx_streamer.recv(chunk, metadata)
        
        # Stop streaming
        stream_cmd = uhd.types.StreamCMD(uhd.types.StreamMode.stop_cont)
        self.rx_streamer.issue_stream_cmd(stream_cmd)
        
        return samples[:samples_received]
    
    def measure_power(self, duration=1.0):
        """Measure received signal power"""
        n_samples = int(self.usrp.get_rx_rate() * duration)
        samples = self.receive_samples(n_samples)
        
        power_dbm = 10 * np.log10(np.mean(np.abs(samples)**2)) + 30
        logger.info(f"Measured power: {power_dbm:.2f} dBm")
        
        return power_dbm

class ChannelEmulatorInterface:
    """Interface for channel emulator control (placeholder)"""
    
    def __init__(self, ip_address="192.168.1.100"):
        self.ip_address = ip_address
        logger.info(f"Channel emulator interface initialized for {ip_address}")
        
    def configure_geo_channel(self):
        """Configure GEO satellite channel parameters"""
        # This would interface with the actual channel emulator
        # Using SCPI commands or proprietary API
        config = {
            "profile": "3GPP_38.811_NTN_GEO",
            "delay_ms": 250,
            "path_loss_db": 190,
            "doppler_hz": 0,  # Static for GEO
            "frequency_ghz": 1.8,
            "bandwidth_mhz": 30
        }
        logger.info(f"Channel emulator configured: {config}")
        return config

def run_loopback_test():
    """Run a simple loopback test without channel emulator"""
    logger.info("Starting loopback test...")
    
    # Initialize devices
    tx = TransmitterX310()
    rx = ReceiverB210()
    
    # Configure
    config = NTNTestConfig()
    tx.configure_tx(config.CENTER_FREQ, config.SAMPLE_RATE, 
                   config.TX_GAIN, config.BANDWIDTH)
    rx.configure_rx(config.CENTER_FREQ, config.SAMPLE_RATE,
                   config.RX_GAIN, config.BANDWIDTH)
    
    # Start receiver first
    logger.info("Starting receiver...")
    rx_thread = threading.Thread(target=rx.measure_power, args=(5.0,))
    rx_thread.start()
    
    # Wait a moment then transmit
    time.sleep(1)
    tx.transmit_test_signal(duration=3, tone_freq=config.TONE_FREQ)
    
    rx_thread.join()
    logger.info("Loopback test complete")

def run_channel_emulator_test():
    """Run test with channel emulator"""
    logger.info("Starting channel emulator test...")
    
    # Initialize channel emulator interface
    emulator = ChannelEmulatorInterface()
    emulator.configure_geo_channel()
    
    # Initialize USRP devices
    tx = TransmitterX310()
    rx = ReceiverB210()
    
    # Use GPSDO for synchronization if available
    if tx.check_gpsdo_lock():
        tx.set_clock_source("gpsdo")
        tx.set_time_source("gpsdo")
    
    # Configure devices
    config = NTNTestConfig()
    tx.configure_tx(config.CENTER_FREQ, config.SAMPLE_RATE,
                   config.TX_GAIN - 10,  # Reduce gain for channel emulator
                   config.BANDWIDTH)
    rx.configure_rx(config.CENTER_FREQ, config.SAMPLE_RATE,
                   config.RX_GAIN + 20,  # Increase gain due to path loss
                   config.BANDWIDTH)
    
    # Perform test
    logger.info("Transmitting through channel emulator...")
    tx.transmit_test_signal(duration=10, tone_freq=config.TONE_FREQ)
    
    logger.info("Test complete")

def check_system_requirements():
    """Check system requirements and configuration"""
    logger.info("Checking system requirements...")
    
    # Check UHD version
    logger.info(f"UHD Version: {uhd.get_version_string()}")
    
    # Find USRP devices
    devices = uhd.find("")
    logger.info(f"Found {len(devices)} USRP device(s)")
    
    for d in devices:
        logger.info(f"  Device: {d.to_pp_string()}")
    
    # Check CPU governor (Linux)
    try:
        with open('/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor', 'r') as f:
            governor = f.read().strip()
            if governor != 'performance':
                logger.warning(f"CPU governor is '{governor}', recommend 'performance'")
            else:
                logger.info("CPU governor set to 'performance' ✓")
    except:
        logger.warning("Could not check CPU governor")
    
    return len(devices) > 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='5G NTN USRP Test Script')
    parser.add_argument('--mode', choices=['check', 'loopback', 'emulator'],
                       default='check', help='Test mode')
    parser.add_argument('--tx-addr', default='addr=192.168.10.2',
                       help='X310 transmitter address')
    parser.add_argument('--log-file', help='Log file path')
    
    args = parser.parse_args()
    
    if args.log_file:
        file_handler = logging.FileHandler(args.log_file)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(file_handler)
    
    logger.info("5G NTN USRP Test Script Started")
    logger.info(f"Timestamp: {datetime.now().isoformat()}")
    
    if args.mode == 'check':
        if check_system_requirements():
            logger.info("System check passed ✓")
        else:
            logger.error("System check failed ✗")
    
    elif args.mode == 'loopback':
        import threading
        run_loopback_test()
    
    elif args.mode == 'emulator':
        run_channel_emulator_test()
    
    logger.info("Script completed")
