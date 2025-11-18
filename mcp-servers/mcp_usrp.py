#!/usr/bin/env python3
"""
MCP Server: USRP Controller
Manages X310/B210 hardware, calibration, and performance monitoring
"""

import asyncio
import json
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional
import uhd
import logging

class USRPControllerMCP:
    """MCP Server for USRP Hardware Control"""
    
    def __init__(self):
        self.logger = logging.getLogger("mcp-usrp")
        self.devices = {}
        self.calibration_data = {}
        self.performance_metrics = {}
        
    async def initialize(self):
        """Initialize MCP server and discover USRP devices"""
        self.logger.info("Initializing USRP Controller MCP Server")
        await self.discover_devices()
        await self.load_calibrations()
        
    async def discover_devices(self):
        """Discover available USRP devices"""
        devices = uhd.find_devices()
        for device in devices:
            serial = device.get("serial")
            self.devices[serial] = {
                "type": device.get("type"),
                "addr": device.get("addr"),
                "status": "discovered",
                "last_seen": datetime.now().isoformat()
            }
        self.logger.info(f"Discovered {len(self.devices)} USRP devices")
        
    async def connect_device(self, serial: str, args: Dict[str, Any]) -> Dict:
        """Connect to a specific USRP device"""
        if serial not in self.devices:
            return {"error": "Device not found"}
            
        try:
            # Build device args string
            device_args = f"serial={serial}"
            if args.get("addr"):
                device_args += f",addr={args['addr']}"
            if args.get("master_clock_rate"):
                device_args += f",master_clock_rate={args['master_clock_rate']}"
                
            # Create USRP object
            usrp = uhd.usrp.MultiUSRP(device_args)
            
            # Store device handle
            self.devices[serial]["handle"] = usrp
            self.devices[serial]["status"] = "connected"
            
            # Get device info
            info = {
                "serial": serial,
                "status": "connected",
                "mboard_id": usrp.get_mboard_id(),
                "mboard_name": usrp.get_mboard_name(),
                "time_source": usrp.get_time_source(0),
                "clock_source": usrp.get_clock_source(0),
                "num_rx_channels": usrp.get_num_rx_channels(),
                "num_tx_channels": usrp.get_num_tx_channels(),
                "rx_rate": usrp.get_rx_rate(),
                "tx_rate": usrp.get_tx_rate()
            }
            
            return {"success": True, "device_info": info}
            
        except Exception as e:
            self.logger.error(f"Failed to connect to device {serial}: {e}")
            return {"error": str(e)}
            
    async def calibrate_dc_offset(self, serial: str, freq: float, channel: int = 0) -> Dict:
        """Perform DC offset calibration"""
        if serial not in self.devices or "handle" not in self.devices[serial]:
            return {"error": "Device not connected"}
            
        usrp = self.devices[serial]["handle"]
        
        try:
            # Set frequency
            usrp.set_rx_freq(freq, channel)
            usrp.set_tx_freq(freq, channel)
            
            # Measure DC offset
            samples = await self.capture_samples(usrp, 10000, channel)
            dc_i = np.mean(np.real(samples))
            dc_q = np.mean(np.imag(samples))
            
            # Apply correction
            usrp.set_rx_dc_offset(True, channel)
            usrp.set_tx_dc_offset(0, 0, channel)  # Auto correction
            
            # Store calibration data
            if serial not in self.calibration_data:
                self.calibration_data[serial] = {}
                
            self.calibration_data[serial]["dc_offset"] = {
                "frequency": freq,
                "dc_i": float(dc_i),
                "dc_q": float(dc_q),
                "timestamp": datetime.now().isoformat()
            }
            
            return {
                "success": True,
                "dc_offset": {"i": float(dc_i), "q": float(dc_q)},
                "correction_applied": True
            }
            
        except Exception as e:
            self.logger.error(f"DC offset calibration failed: {e}")
            return {"error": str(e)}
            
    async def calibrate_iq_imbalance(self, serial: str, freq: float, channel: int = 0) -> Dict:
        """Perform IQ imbalance calibration"""
        if serial not in self.devices or "handle" not in self.devices[serial]:
            return {"error": "Device not connected"}
            
        usrp = self.devices[serial]["handle"]
        
        try:
            # Set frequency
            usrp.set_rx_freq(freq, channel)
            usrp.set_tx_freq(freq, channel)
            
            # Generate test tone
            tone_freq = 100e3  # 100 kHz offset
            duration = 0.1  # 100ms
            sample_rate = usrp.get_rx_rate()
            
            # Transmit test tone
            tx_samples = self.generate_tone(tone_freq, sample_rate, duration)
            await self.transmit_samples(usrp, tx_samples, channel)
            
            # Receive and analyze
            rx_samples = await self.capture_samples(usrp, int(sample_rate * duration), channel)
            
            # Calculate IQ imbalance
            fft_data = np.fft.fft(rx_samples)
            fft_freqs = np.fft.fftfreq(len(rx_samples), 1/sample_rate)
            
            # Find signal and image frequencies
            signal_idx = np.argmax(np.abs(fft_data[fft_freqs > 0]))
            image_idx = np.argmax(np.abs(fft_data[fft_freqs < 0]))
            
            signal_power = np.abs(fft_data[signal_idx])**2
            image_power = np.abs(fft_data[image_idx])**2
            
            image_rejection = 10 * np.log10(signal_power / image_power)
            
            # Apply IQ correction if needed
            if image_rejection < 30:  # dB threshold
                usrp.set_rx_iq_balance(True, channel)
                usrp.set_tx_iq_balance(0, 0, channel)  # Auto correction
                
            # Store calibration data
            if serial not in self.calibration_data:
                self.calibration_data[serial] = {}
                
            self.calibration_data[serial]["iq_imbalance"] = {
                "frequency": freq,
                "image_rejection_db": float(image_rejection),
                "correction_applied": image_rejection < 30,
                "timestamp": datetime.now().isoformat()
            }
            
            return {
                "success": True,
                "image_rejection_db": float(image_rejection),
                "correction_applied": image_rejection < 30
            }
            
        except Exception as e:
            self.logger.error(f"IQ imbalance calibration failed: {e}")
            return {"error": str(e)}
            
    async def measure_frequency_offset(self, serial: str, ref_freq: float, channel: int = 0) -> Dict:
        """Measure frequency offset against reference"""
        if serial not in self.devices or "handle" not in self.devices[serial]:
            return {"error": "Device not connected"}
            
        usrp = self.devices[serial]["handle"]
        
        try:
            # Set to reference frequency
            usrp.set_rx_freq(ref_freq, channel)
            
            # Capture samples
            samples = await self.capture_samples(usrp, 100000, channel)
            
            # Estimate frequency offset using FFT
            sample_rate = usrp.get_rx_rate()
            fft_data = np.fft.fft(samples)
            fft_freqs = np.fft.fftfreq(len(samples), 1/sample_rate)
            
            # Find peak
            peak_idx = np.argmax(np.abs(fft_data))
            measured_freq = fft_freqs[peak_idx]
            
            offset_hz = measured_freq
            offset_ppm = (offset_hz / ref_freq) * 1e6
            
            return {
                "success": True,
                "frequency_offset_hz": float(offset_hz),
                "frequency_offset_ppm": float(offset_ppm),
                "reference_frequency": ref_freq
            }
            
        except Exception as e:
            self.logger.error(f"Frequency offset measurement failed: {e}")
            return {"error": str(e)}
            
    async def set_timing_reference(self, serial: str, source: str) -> Dict:
        """Set timing reference (internal, external, gpsdo)"""
        if serial not in self.devices or "handle" not in self.devices[serial]:
            return {"error": "Device not connected"}
            
        usrp = self.devices[serial]["handle"]
        
        try:
            # Set clock and time source
            usrp.set_clock_source(source)
            usrp.set_time_source(source)
            
            # Wait for reference lock
            await asyncio.sleep(1.0)
            
            # Check lock status
            ref_locked = usrp.get_mboard_sensor("ref_locked").to_bool()
            
            if source == "gpsdo":
                # Check GPS lock
                gps_locked = usrp.get_mboard_sensor("gps_locked").to_bool()
                gps_time = usrp.get_mboard_sensor("gps_time").to_int()
                
                return {
                    "success": True,
                    "reference_source": source,
                    "ref_locked": ref_locked,
                    "gps_locked": gps_locked,
                    "gps_time": gps_time
                }
            else:
                return {
                    "success": True,
                    "reference_source": source,
                    "ref_locked": ref_locked
                }
                
        except Exception as e:
            self.logger.error(f"Failed to set timing reference: {e}")
            return {"error": str(e)}
            
    async def monitor_performance(self, serial: str, duration: float = 10.0) -> Dict:
        """Monitor real-time performance metrics"""
        if serial not in self.devices or "handle" not in self.devices[serial]:
            return {"error": "Device not connected"}
            
        usrp = self.devices[serial]["handle"]
        
        try:
            metrics = {
                "overflows": 0,
                "underflows": 0,
                "sequence_errors": 0,
                "late_packets": 0,
                "throughput_mbps": 0,
                "cpu_usage": 0,
                "temperature": 0
            }
            
            # Run performance test
            sample_rate = usrp.get_rx_rate()
            num_samples = int(sample_rate * duration)
            
            # Create stream
            stream_args = uhd.usrp.StreamArgs("fc32", "sc16")
            rx_stream = usrp.get_rx_stream(stream_args)
            metadata = uhd.usrp.RXMetadata()
            
            # Start streaming
            stream_cmd = uhd.usrp.StreamCMD(uhd.usrp.StreamMode.num_done)
            stream_cmd.num_samps = num_samples
            stream_cmd.stream_now = True
            rx_stream.issue_stream_cmd(stream_cmd)
            
            # Monitor for duration
            buffer = np.zeros(10000, dtype=np.complex64)
            total_samples = 0
            start_time = asyncio.get_event_loop().time()
            
            while total_samples < num_samples:
                num_rx = rx_stream.recv(buffer, metadata, timeout=1.0)
                
                if metadata.error_code == uhd.usrp.RXMetadataErrorCode.overflow:
                    metrics["overflows"] += 1
                elif metadata.error_code == uhd.usrp.RXMetadataErrorCode.late:
                    metrics["late_packets"] += 1
                    
                total_samples += num_rx
                
            # Calculate throughput
            elapsed = asyncio.get_event_loop().time() - start_time
            metrics["throughput_mbps"] = (total_samples * 8) / (elapsed * 1e6)
            
            # Get temperature if available
            try:
                temp_sensor = usrp.get_mboard_sensor("temp")
                metrics["temperature"] = temp_sensor.to_real()
            except:
                pass
                
            # Store metrics
            self.performance_metrics[serial] = metrics
            
            return {"success": True, "metrics": metrics}
            
        except Exception as e:
            self.logger.error(f"Performance monitoring failed: {e}")
            return {"error": str(e)}
            
    async def capture_samples(self, usrp, num_samples: int, channel: int = 0) -> np.ndarray:
        """Capture IQ samples from USRP"""
        stream_args = uhd.usrp.StreamArgs("fc32", "sc16")
        stream_args.channels = [channel]
        rx_stream = usrp.get_rx_stream(stream_args)
        
        metadata = uhd.usrp.RXMetadata()
        buffer = np.zeros(num_samples, dtype=np.complex64)
        
        # Issue stream command
        stream_cmd = uhd.usrp.StreamCMD(uhd.usrp.StreamMode.num_done)
        stream_cmd.num_samps = num_samples
        stream_cmd.stream_now = True
        rx_stream.issue_stream_cmd(stream_cmd)
        
        # Receive samples
        rx_stream.recv(buffer, metadata)
        
        return buffer
        
    async def transmit_samples(self, usrp, samples: np.ndarray, channel: int = 0):
        """Transmit IQ samples through USRP"""
        stream_args = uhd.usrp.StreamArgs("fc32", "sc16")
        stream_args.channels = [channel]
        tx_stream = usrp.get_tx_stream(stream_args)
        
        metadata = uhd.usrp.TXMetadata()
        metadata.start_of_burst = True
        metadata.end_of_burst = True
        
        tx_stream.send(samples, metadata)
        
    def generate_tone(self, freq: float, sample_rate: float, duration: float) -> np.ndarray:
        """Generate a complex sinusoidal tone"""
        num_samples = int(sample_rate * duration)
        t = np.arange(num_samples) / sample_rate
        tone = np.exp(1j * 2 * np.pi * freq * t)
        return tone.astype(np.complex64)
        
    async def handle_command(self, command: str, params: Dict[str, Any]) -> Dict:
        """Handle incoming MCP commands"""
        handlers = {
            "discover": self.discover_devices,
            "connect": lambda: self.connect_device(params.get("serial"), params),
            "calibrate_dc": lambda: self.calibrate_dc_offset(
                params.get("serial"), params.get("frequency")
            ),
            "calibrate_iq": lambda: self.calibrate_iq_imbalance(
                params.get("serial"), params.get("frequency")
            ),
            "measure_freq_offset": lambda: self.measure_frequency_offset(
                params.get("serial"), params.get("ref_freq")
            ),
            "set_reference": lambda: self.set_timing_reference(
                params.get("serial"), params.get("source")
            ),
            "monitor": lambda: self.monitor_performance(
                params.get("serial"), params.get("duration", 10.0)
            )
        }
        
        handler = handlers.get(command)
        if handler:
            return await handler()
        else:
            return {"error": f"Unknown command: {command}"}
            
    async def load_calibrations(self):
        """Load saved calibration data"""
        try:
            with open("calibrations.json", "r") as f:
                self.calibration_data = json.load(f)
            self.logger.info("Loaded calibration data")
        except FileNotFoundError:
            self.logger.info("No calibration data found")
            
    async def save_calibrations(self):
        """Save calibration data"""
        with open("calibrations.json", "w") as f:
            json.dump(self.calibration_data, f, indent=2)
        self.logger.info("Saved calibration data")

# MCP Server entry point
async def main():
    logging.basicConfig(level=logging.INFO)
    server = USRPControllerMCP()
    await server.initialize()
    
    # Start MCP server loop
    while True:
        # In production, this would listen on a socket/port
        # For now, just keep the server alive
        await asyncio.sleep(1)
        
if __name__ == "__main__":
    asyncio.run(main())
