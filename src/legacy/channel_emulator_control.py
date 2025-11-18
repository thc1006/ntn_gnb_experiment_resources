#!/usr/bin/env python3
"""
Channel Emulator Control Interface for 5G NTN Testing
Supports multiple channel emulator models
Date: 2025-11-18
"""

import pyvisa
import socket
import time
import logging
import json
import numpy as np
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Optional, Tuple, List

logger = logging.getLogger(__name__)

class SatelliteOrbit(Enum):
    """Satellite orbit types"""
    GEO = "GEO"      # Geostationary
    MEO = "MEO"      # Medium Earth Orbit
    LEO = "LEO"      # Low Earth Orbit
    HAPS = "HAPS"    # High Altitude Platform Station

class ChannelModel(Enum):
    """3GPP NTN Channel Models"""
    NTN_TDL_A = "NTN-TDL-A"  # Rural
    NTN_TDL_B = "NTN-TDL-B"  # Urban
    NTN_TDL_C = "NTN-TDL-C"  # Dense Urban
    NTN_TDL_D = "NTN-TDL-D"  # LOS Dominant
    NTN_TDL_E = "NTN-TDL-E"  # NLOS

class NTNParameters:
    """NTN specific parameters"""
    
    # Orbit altitudes (km)
    ORBIT_ALTITUDE = {
        SatelliteOrbit.GEO: 35786,
        SatelliteOrbit.MEO: 10000,
        SatelliteOrbit.LEO: 600,
        SatelliteOrbit.HAPS: 20
    }
    
    # One-way propagation delays (ms)
    PROPAGATION_DELAY = {
        SatelliteOrbit.GEO: 250,
        SatelliteOrbit.MEO: 40,
        SatelliteOrbit.LEO: 4,
        SatelliteOrbit.HAPS: 0.1
    }
    
    # Typical path loss at L-band (dB)
    PATH_LOSS = {
        SatelliteOrbit.GEO: 190,
        SatelliteOrbit.MEO: 175,
        SatelliteOrbit.LEO: 160,
        SatelliteOrbit.HAPS: 120
    }
    
    # Maximum Doppler shift (Hz) at 2 GHz
    MAX_DOPPLER = {
        SatelliteOrbit.GEO: 0,      # Stationary relative to Earth
        SatelliteOrbit.MEO: 20000,  # ~20 kHz
        SatelliteOrbit.LEO: 50000,  # ~50 kHz
        SatelliteOrbit.HAPS: 100    # Minimal
    }

class BaseChannelEmulator(ABC):
    """Base class for channel emulator control"""
    
    def __init__(self, address: str, port: Optional[int] = None):
        self.address = address
        self.port = port
        self.connected = False
        self.orbit = SatelliteOrbit.GEO
        self.model = ChannelModel.NTN_TDL_D
        
    @abstractmethod
    def connect(self) -> bool:
        """Connect to the channel emulator"""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Disconnect from the channel emulator"""
        pass
    
    @abstractmethod
    def configure_ntn_channel(self, orbit: SatelliteOrbit, 
                            model: ChannelModel,
                            freq_ghz: float,
                            bandwidth_mhz: float) -> bool:
        """Configure NTN channel parameters"""
        pass
    
    @abstractmethod
    def set_path_loss(self, loss_db: float):
        """Set path loss in dB"""
        pass
    
    @abstractmethod
    def set_delay(self, delay_ms: float):
        """Set propagation delay in ms"""
        pass
    
    @abstractmethod
    def set_doppler(self, doppler_hz: float):
        """Set Doppler shift in Hz"""
        pass
    
    @abstractmethod
    def start_emulation(self):
        """Start channel emulation"""
        pass
    
    @abstractmethod
    def stop_emulation(self):
        """Stop channel emulation"""
        pass
    
    def get_orbit_parameters(self, orbit: SatelliteOrbit) -> Dict:
        """Get default parameters for orbit type"""
        return {
            'altitude_km': NTNParameters.ORBIT_ALTITUDE[orbit],
            'delay_ms': NTNParameters.PROPAGATION_DELAY[orbit],
            'path_loss_db': NTNParameters.PATH_LOSS[orbit],
            'max_doppler_hz': NTNParameters.MAX_DOPPLER[orbit]
        }

class KeysightPROPSIM(BaseChannelEmulator):
    """Keysight PROPSIM Channel Emulator Control"""
    
    def __init__(self, address: str, port: int = 5025):
        super().__init__(address, port)
        self.rm = pyvisa.ResourceManager()
        self.instrument = None
        
    def connect(self) -> bool:
        """Connect via VISA/SCPI"""
        try:
            visa_address = f"TCPIP::{self.address}::{self.port}::SOCKET"
            self.instrument = self.rm.open_resource(visa_address)
            self.instrument.timeout = 5000
            
            # Query IDN
            idn = self.instrument.query("*IDN?")
            logger.info(f"Connected to: {idn}")
            
            # Clear errors
            self.instrument.write("*CLS")
            
            self.connected = True
            return True
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from instrument"""
        if self.instrument:
            self.instrument.close()
            self.connected = False
    
    def configure_ntn_channel(self, orbit: SatelliteOrbit,
                            model: ChannelModel,
                            freq_ghz: float,
                            bandwidth_mhz: float) -> bool:
        """Configure NTN channel for PROPSIM"""
        if not self.connected:
            return False
        
        try:
            # Get orbit parameters
            params = self.get_orbit_parameters(orbit)
            
            # Load channel model
            model_name = f"3GPP_38811_{model.value}"
            self.instrument.write(f'CHAN:PROF:LOAD "{model_name}"')
            
            # Set frequency
            self.instrument.write(f'CHAN:FREQ {freq_ghz}E9')
            
            # Set bandwidth
            self.instrument.write(f'CHAN:BAND {bandwidth_mhz}E6')
            
            # Set delay
            self.instrument.write(f'CHAN:DELAY {params["delay_ms"]}E-3')
            
            # Set path loss
            self.instrument.write(f'CHAN:LOSS {params["path_loss_db"]}')
            
            # Set Doppler
            self.instrument.write(f'CHAN:DOPP {params["max_doppler_hz"]}')
            
            # Configure fading
            self.instrument.write('CHAN:FAD:STATE ON')
            
            # Set correlation (MIMO)
            self.instrument.write('CHAN:CORR:MAT MEDIUM')
            
            # Configure noise
            self.instrument.write('CHAN:NOISE:STATE ON')
            self.instrument.write(f'CHAN:NOISE:LEVEL -100')  # dBm
            
            self.orbit = orbit
            self.model = model
            
            logger.info(f"Configured {orbit.value} channel with {model.value}")
            return True
            
        except Exception as e:
            logger.error(f"Configuration failed: {e}")
            return False
    
    def set_path_loss(self, loss_db: float):
        """Set path loss"""
        if self.connected:
            self.instrument.write(f'CHAN:LOSS {loss_db}')
            
    def set_delay(self, delay_ms: float):
        """Set propagation delay"""
        if self.connected:
            self.instrument.write(f'CHAN:DELAY {delay_ms}E-3')
            
    def set_doppler(self, doppler_hz: float):
        """Set Doppler shift"""
        if self.connected:
            self.instrument.write(f'CHAN:DOPP {doppler_hz}')
            
    def start_emulation(self):
        """Start channel emulation"""
        if self.connected:
            self.instrument.write('CHAN:STATE ON')
            logger.info("Channel emulation started")
            
    def stop_emulation(self):
        """Stop channel emulation"""
        if self.connected:
            self.instrument.write('CHAN:STATE OFF')
            logger.info("Channel emulation stopped")
    
    def set_geo_specific_parameters(self):
        """Set GEO-specific parameters"""
        if not self.connected:
            return
            
        # GEO specific settings
        self.instrument.write('CHAN:SAT:TYPE GEO')
        self.instrument.write('CHAN:SAT:ELEV 30')  # 30 degrees elevation
        self.instrument.write('CHAN:SAT:AZIM 180')  # South
        
        # Atmospheric effects
        self.instrument.write('CHAN:ATM:RAIN OFF')  # No rain for initial tests
        self.instrument.write('CHAN:ATM:SCINT ON')   # Scintillation effects
        
        # Antenna pattern
        self.instrument.write('CHAN:ANT:PATTERN ISOTROPIC')

class SpirentVertex(BaseChannelEmulator):
    """Spirent Vertex Channel Emulator Control"""
    
    def __init__(self, address: str, port: int = 5000):
        super().__init__(address, port)
        self.socket = None
        
    def connect(self) -> bool:
        """Connect via TCP socket"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.address, self.port))
            self.socket.settimeout(5.0)
            
            # Send initial query
            self.send_command("SYSTEM:VERSION?")
            version = self.receive_response()
            logger.info(f"Connected to Spirent Vertex: {version}")
            
            self.connected = True
            return True
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from emulator"""
        if self.socket:
            self.socket.close()
            self.connected = False
    
    def send_command(self, cmd: str):
        """Send command to Vertex"""
        if self.socket:
            self.socket.send(f"{cmd}\n".encode())
    
    def receive_response(self) -> str:
        """Receive response from Vertex"""
        if self.socket:
            data = self.socket.recv(4096)
            return data.decode().strip()
        return ""
    
    def configure_ntn_channel(self, orbit: SatelliteOrbit,
                            model: ChannelModel,
                            freq_ghz: float,
                            bandwidth_mhz: float) -> bool:
        """Configure NTN channel for Vertex"""
        if not self.connected:
            return False
            
        try:
            params = self.get_orbit_parameters(orbit)
            
            # Configure scenario
            self.send_command(f"SCENARIO:TYPE SATELLITE_{orbit.value}")
            self.send_command(f"SCENARIO:MODEL {model.value}")
            
            # RF parameters
            self.send_command(f"RF:FREQ {freq_ghz * 1e9}")
            self.send_command(f"RF:BW {bandwidth_mhz * 1e6}")
            
            # Channel parameters
            self.send_command(f"CHANNEL:DELAY {params['delay_ms']}")
            self.send_command(f"CHANNEL:LOSS {params['path_loss_db']}")
            self.send_command(f"CHANNEL:DOPPLER {params['max_doppler_hz']}")
            
            self.orbit = orbit
            self.model = model
            
            logger.info(f"Configured {orbit.value} channel with {model.value}")
            return True
            
        except Exception as e:
            logger.error(f"Configuration failed: {e}")
            return False
    
    def set_path_loss(self, loss_db: float):
        """Set path loss"""
        if self.connected:
            self.send_command(f"CHANNEL:LOSS {loss_db}")
    
    def set_delay(self, delay_ms: float):
        """Set propagation delay"""
        if self.connected:
            self.send_command(f"CHANNEL:DELAY {delay_ms}")
    
    def set_doppler(self, doppler_hz: float):
        """Set Doppler shift"""
        if self.connected:
            self.send_command(f"CHANNEL:DOPPLER {doppler_hz}")
    
    def start_emulation(self):
        """Start channel emulation"""
        if self.connected:
            self.send_command("EMULATION:START")
            logger.info("Channel emulation started")
    
    def stop_emulation(self):
        """Stop channel emulation"""
        if self.connected:
            self.send_command("EMULATION:STOP")
            logger.info("Channel emulation stopped")

class ChannelEmulatorFactory:
    """Factory class to create appropriate channel emulator interface"""
    
    @staticmethod
    def create_emulator(model: str, address: str, port: Optional[int] = None) -> Optional[BaseChannelEmulator]:
        """Create channel emulator instance based on model"""
        
        emulator_map = {
            'keysight': KeysightPROPSIM,
            'propsim': KeysightPROPSIM,
            'spirent': SpirentVertex,
            'vertex': SpirentVertex,
        }
        
        model_lower = model.lower()
        for key, emulator_class in emulator_map.items():
            if key in model_lower:
                if port:
                    return emulator_class(address, port)
                else:
                    return emulator_class(address)
        
        logger.error(f"Unknown emulator model: {model}")
        return None

class NTNChannelEmulationManager:
    """High-level manager for NTN channel emulation"""
    
    def __init__(self, emulator_model: str, address: str):
        self.emulator = ChannelEmulatorFactory.create_emulator(emulator_model, address)
        self.current_orbit = None
        self.current_model = None
        
    def setup_geo_test(self, freq_ghz: float = 1.8, bandwidth_mhz: float = 30):
        """Setup standard GEO satellite test"""
        if not self.emulator:
            return False
            
        # Connect
        if not self.emulator.connect():
            return False
        
        # Configure GEO channel
        success = self.emulator.configure_ntn_channel(
            orbit=SatelliteOrbit.GEO,
            model=ChannelModel.NTN_TDL_D,  # LOS dominant for GEO
            freq_ghz=freq_ghz,
            bandwidth_mhz=bandwidth_mhz
        )
        
        if success:
            self.current_orbit = SatelliteOrbit.GEO
            self.current_model = ChannelModel.NTN_TDL_D
            logger.info("GEO test configuration complete")
            
        return success
    
    def setup_leo_test(self, freq_ghz: float = 1.8, bandwidth_mhz: float = 30):
        """Setup standard LEO satellite test"""
        if not self.emulator:
            return False
            
        # Connect
        if not self.emulator.connect():
            return False
        
        # Configure LEO channel
        success = self.emulator.configure_ntn_channel(
            orbit=SatelliteOrbit.LEO,
            model=ChannelModel.NTN_TDL_A,  # Rural for LEO
            freq_ghz=freq_ghz,
            bandwidth_mhz=bandwidth_mhz
        )
        
        if success:
            self.current_orbit = SatelliteOrbit.LEO
            self.current_model = ChannelModel.NTN_TDL_A
            logger.info("LEO test configuration complete")
            
        return success
    
    def run_test_sequence(self, duration_seconds: int = 60):
        """Run a test sequence with varying conditions"""
        if not self.emulator or not self.emulator.connected:
            logger.error("Emulator not connected")
            return
        
        logger.info(f"Starting test sequence for {duration_seconds} seconds")
        
        # Start emulation
        self.emulator.start_emulation()
        
        # Initial conditions
        time.sleep(duration_seconds // 3)
        
        # Simulate rain fade
        logger.info("Simulating rain fade")
        current_loss = NTNParameters.PATH_LOSS[self.current_orbit]
        self.emulator.set_path_loss(current_loss + 10)  # Add 10 dB rain fade
        
        time.sleep(duration_seconds // 3)
        
        # Simulate satellite handover (for LEO)
        if self.current_orbit == SatelliteOrbit.LEO:
            logger.info("Simulating satellite handover")
            self.emulator.set_doppler(NTNParameters.MAX_DOPPLER[SatelliteOrbit.LEO])
            time.sleep(5)
            self.emulator.set_doppler(-NTNParameters.MAX_DOPPLER[SatelliteOrbit.LEO])
        
        time.sleep(duration_seconds // 3)
        
        # Stop emulation
        self.emulator.stop_emulation()
        logger.info("Test sequence complete")
    
    def cleanup(self):
        """Cleanup and disconnect"""
        if self.emulator:
            self.emulator.stop_emulation()
            self.emulator.disconnect()

# Example usage and testing
def test_channel_emulator():
    """Test function for channel emulator control"""
    
    # Configure logging
    logging.basicConfig(level=logging.INFO,
                       format='%(asctime)s - %(levelname)s - %(message)s')
    
    # Create emulation manager (adjust model and IP as needed)
    manager = NTNChannelEmulationManager(
        emulator_model="keysight",  # or "spirent"
        address="192.168.1.100"
    )
    
    # Setup GEO test
    if manager.setup_geo_test(freq_ghz=1.8, bandwidth_mhz=30):
        # Run test sequence
        manager.run_test_sequence(duration_seconds=60)
    
    # Cleanup
    manager.cleanup()

if __name__ == "__main__":
    test_channel_emulator()
