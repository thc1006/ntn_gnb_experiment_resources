#!/usr/bin/env python3
"""
NTN Link Budget Calculator
Comprehensive link budget analysis for GEO, LEO, and HAPS scenarios
Includes atmospheric effects, rain fade, and safety margins
"""

import numpy as np
import matplotlib.pyplot as plt
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
import json
import argparse

@dataclass
class LinkBudgetParameters:
    """Link budget calculation parameters"""
    # Transmitter parameters
    tx_power_dbm: float = 27.0  # Transmit power (dBm)
    tx_antenna_gain_dbi: float = 2.0  # TX antenna gain (dBi)
    tx_cable_loss_db: float = 1.0  # TX cable/connector loss (dB)
    
    # Receiver parameters
    rx_antenna_gain_dbi: float = 18.0  # RX antenna gain (dBi)
    rx_cable_loss_db: float = 1.0  # RX cable/connector loss (dB)
    rx_noise_figure_db: float = 5.0  # Receiver noise figure (dB)
    
    # Channel parameters
    frequency_ghz: float = 1.5  # Operating frequency (GHz)
    bandwidth_mhz: float = 30.0  # Channel bandwidth (MHz)
    distance_km: float = 36000.0  # Link distance (km)
    elevation_angle_deg: float = 45.0  # Elevation angle (degrees)
    
    # Modulation and coding
    modulation_scheme: str = "QPSK"  # Modulation scheme
    coding_rate: float = 0.5  # Coding rate (1/2)
    required_ber: float = 1e-6  # Target bit error rate
    
    # Environmental factors
    rain_rate_mm_hr: float = 0.0  # Rain rate (mm/hr)
    atmospheric_pressure_hpa: float = 1013.25  # Atmospheric pressure
    temperature_c: float = 20.0  # Temperature (Celsius)
    humidity_percent: float = 50.0  # Relative humidity (%)

class NTNLinkBudget:
    """NTN Link Budget Calculator"""
    
    def __init__(self, scenario: str = "geo"):
        """
        Initialize link budget calculator
        
        Args:
            scenario: "geo", "leo", "haps", or "uav"
        """
        self.scenario = scenario
        self.params = self.get_default_params(scenario)
        
    def get_default_params(self, scenario: str) -> LinkBudgetParameters:
        """Get default parameters for different scenarios"""
        if scenario == "geo":
            return LinkBudgetParameters(
                tx_power_dbm=33.0,  # Higher power for GEO
                tx_antenna_gain_dbi=3.0,
                rx_antenna_gain_dbi=20.0,  # High gain for GEO
                frequency_ghz=1.5,  # L-band
                distance_km=36000.0,
                elevation_angle_deg=45.0
            )
        elif scenario == "leo":
            return LinkBudgetParameters(
                tx_power_dbm=27.0,
                tx_antenna_gain_dbi=2.0,
                rx_antenna_gain_dbi=15.0,
                frequency_ghz=2.0,  # S-band
                distance_km=600.0,
                elevation_angle_deg=30.0
            )
        elif scenario == "haps":
            return LinkBudgetParameters(
                tx_power_dbm=33.0,
                tx_antenna_gain_dbi=6.0,
                rx_antenna_gain_dbi=18.0,
                frequency_ghz=2.0,
                distance_km=30.0,
                elevation_angle_deg=60.0
            )
        elif scenario == "uav":
            return LinkBudgetParameters(
                tx_power_dbm=23.0,
                tx_antenna_gain_dbi=2.0,
                rx_antenna_gain_dbi=10.0,
                frequency_ghz=2.4,
                distance_km=5.0,
                elevation_angle_deg=70.0
            )
        else:
            return LinkBudgetParameters()
            
    def calculate_free_space_path_loss(self, distance_km: float, freq_ghz: float) -> float:
        """
        Calculate free space path loss
        
        FSPL = 20*log10(d) + 20*log10(f) + 92.45
        where d is in km and f is in GHz
        """
        fspl_db = 20 * np.log10(distance_km) + 20 * np.log10(freq_ghz) + 92.45
        return fspl_db
        
    def calculate_atmospheric_loss(self, distance_km: float, freq_ghz: float, 
                                  elevation_deg: float) -> float:
        """Calculate atmospheric absorption loss"""
        # ITU-R P.676 simplified model
        # Oxygen absorption
        if freq_ghz < 57:
            gamma_o = 0.0019 * freq_ghz**2  # dB/km at sea level
        else:
            gamma_o = 0.5  # Peak around 60 GHz
            
        # Water vapor absorption
        gamma_w = 0.005 * freq_ghz**2 if freq_ghz < 22 else 0.1
        
        # Total specific attenuation
        gamma_total = gamma_o + gamma_w  # dB/km
        
        # Effective path length through atmosphere
        # Simplified exponential atmosphere model
        h_s = 8.0  # Scale height in km
        effective_path = h_s * (1 - np.exp(-distance_km * np.sin(np.radians(elevation_deg)) / h_s))
        
        # For short paths (HAPS, UAV), use actual distance
        if distance_km < 100:
            effective_path = distance_km
            
        atmospheric_loss_db = gamma_total * effective_path
        
        return atmospheric_loss_db
        
    def calculate_rain_attenuation(self, distance_km: float, freq_ghz: float, 
                                  rain_rate_mm_hr: float, elevation_deg: float) -> float:
        """Calculate rain attenuation using ITU-R P.838"""
        if rain_rate_mm_hr == 0:
            return 0.0
            
        # Frequency-dependent coefficients (simplified)
        if freq_ghz < 2.5:
            k = 0.003 * freq_ghz**2
            alpha = 1.0
        elif freq_ghz < 10:
            k = 0.02 * freq_ghz**1.5
            alpha = 1.1
        else:
            k = 0.1 * freq_ghz
            alpha = 1.2
            
        # Specific attenuation
        gamma_rain = k * rain_rate_mm_hr**alpha  # dB/km
        
        # Effective path length
        # For satellite links, rain typically affects only lower atmosphere
        if distance_km > 100:  # Satellite link
            effective_rain_path = 5.0 / np.sin(np.radians(max(elevation_deg, 5)))
        else:  # Terrestrial or HAPS
            effective_rain_path = distance_km
            
        rain_loss_db = gamma_rain * effective_rain_path
        
        return rain_loss_db
        
    def calculate_scintillation_loss(self, freq_ghz: float, elevation_deg: float) -> float:
        """Calculate tropospheric scintillation fade margin"""
        # ITU-R P.618 simplified model
        if elevation_deg < 10:
            ref_fade = 3.0  # dB at 10 degrees
        else:
            ref_fade = 1.5  # dB at higher elevations
            
        # Frequency scaling
        freq_factor = (freq_ghz / 4.0)**0.7
        
        # Elevation scaling
        elev_factor = 1.0 / np.sin(np.radians(max(elevation_deg, 5)))
        
        scintillation_margin_db = ref_fade * freq_factor * np.sqrt(elev_factor)
        
        return scintillation_margin_db
        
    def calculate_doppler_shift(self, scenario: str, freq_ghz: float) -> float:
        """Calculate maximum Doppler shift"""
        c = 3e8  # Speed of light (m/s)
        freq_hz = freq_ghz * 1e9
        
        if scenario == "geo":
            relative_velocity = 3  # m/s (station keeping)
        elif scenario == "leo":
            relative_velocity = 7500  # m/s (orbital velocity)
        elif scenario == "haps":
            relative_velocity = 20  # m/s (station keeping)
        else:  # UAV
            relative_velocity = 50  # m/s (typical UAV speed)
            
        doppler_shift_hz = freq_hz * relative_velocity / c
        
        return doppler_shift_hz
        
    def calculate_thermal_noise(self, bandwidth_mhz: float, noise_figure_db: float) -> float:
        """Calculate thermal noise floor"""
        k_boltzmann = 1.38e-23  # Boltzmann constant (J/K)
        temperature_k = 290  # Standard temperature (K)
        bandwidth_hz = bandwidth_mhz * 1e6
        
        # Thermal noise power
        noise_power_watts = k_boltzmann * temperature_k * bandwidth_hz
        noise_power_dbm = 10 * np.log10(noise_power_watts * 1000)
        
        # Add noise figure
        total_noise_dbm = noise_power_dbm + noise_figure_db
        
        return total_noise_dbm
        
    def get_required_snr(self, modulation: str, ber: float) -> float:
        """Get required SNR for given modulation and BER"""
        # Simplified SNR requirements (dB)
        snr_table = {
            "BPSK": {1e-3: 6.8, 1e-6: 10.5, 1e-9: 12.6},
            "QPSK": {1e-3: 9.8, 1e-6: 13.5, 1e-9: 15.6},
            "16QAM": {1e-3: 16.5, 1e-6: 20.2, 1e-9: 22.3},
            "64QAM": {1e-3: 22.5, 1e-6: 26.2, 1e-9: 28.3}
        }
        
        if modulation not in snr_table:
            return 10.0  # Default
            
        ber_values = list(snr_table[modulation].keys())
        snr_values = list(snr_table[modulation].values())
        
        # Interpolate if needed
        if ber >= ber_values[0]:
            return snr_values[0]
        elif ber <= ber_values[-1]:
            return snr_values[-1]
        else:
            # Log interpolation
            log_ber = np.log10(ber)
            log_bers = np.log10(ber_values)
            return np.interp(log_ber, log_bers, snr_values)
            
    def calculate_link_budget(self, params: Optional[LinkBudgetParameters] = None) -> Dict:
        """Calculate complete link budget"""
        if params is None:
            params = self.params
            
        results = {}
        
        # Transmitter side
        results["tx_power_dbm"] = params.tx_power_dbm
        results["tx_antenna_gain_dbi"] = params.tx_antenna_gain_dbi
        results["tx_cable_loss_db"] = -params.tx_cable_loss_db
        results["eirp_dbm"] = (params.tx_power_dbm + params.tx_antenna_gain_dbi - 
                               params.tx_cable_loss_db)
        
        # Path losses
        results["distance_km"] = params.distance_km
        results["fspl_db"] = -self.calculate_free_space_path_loss(
            params.distance_km, params.frequency_ghz
        )
        
        results["atmospheric_loss_db"] = -self.calculate_atmospheric_loss(
            params.distance_km, params.frequency_ghz, params.elevation_angle_deg
        )
        
        results["rain_loss_db"] = -self.calculate_rain_attenuation(
            params.distance_km, params.frequency_ghz, 
            params.rain_rate_mm_hr, params.elevation_angle_deg
        )
        
        results["scintillation_margin_db"] = -self.calculate_scintillation_loss(
            params.frequency_ghz, params.elevation_angle_deg
        )
        
        # Additional losses
        results["polarization_loss_db"] = -0.5  # Typical polarization mismatch
        results["pointing_loss_db"] = -0.5  # Antenna pointing error
        results["implementation_loss_db"] = -2.0  # Implementation margin
        
        # Total path loss
        results["total_path_loss_db"] = (
            results["fspl_db"] + 
            results["atmospheric_loss_db"] + 
            results["rain_loss_db"] +
            results["scintillation_margin_db"] +
            results["polarization_loss_db"] +
            results["pointing_loss_db"] +
            results["implementation_loss_db"]
        )
        
        # Receiver side
        results["rx_antenna_gain_dbi"] = params.rx_antenna_gain_dbi
        results["rx_cable_loss_db"] = -params.rx_cable_loss_db
        
        # Received power
        results["rx_power_dbm"] = (
            results["eirp_dbm"] + 
            results["total_path_loss_db"] +
            results["rx_antenna_gain_dbi"] +
            results["rx_cable_loss_db"]
        )
        
        # Noise calculations
        results["thermal_noise_dbm"] = self.calculate_thermal_noise(
            params.bandwidth_mhz, params.rx_noise_figure_db
        )
        
        # SNR and margin
        results["snr_db"] = results["rx_power_dbm"] - results["thermal_noise_dbm"]
        results["required_snr_db"] = self.get_required_snr(
            params.modulation_scheme, params.required_ber
        )
        results["link_margin_db"] = results["snr_db"] - results["required_snr_db"]
        
        # Additional information
        results["doppler_shift_hz"] = self.calculate_doppler_shift(
            self.scenario, params.frequency_ghz
        )
        
        # Data rate estimation
        spectral_efficiency = {
            "BPSK": 1.0, "QPSK": 2.0, "16QAM": 4.0, "64QAM": 6.0
        }.get(params.modulation_scheme, 2.0)
        
        results["data_rate_mbps"] = (
            params.bandwidth_mhz * spectral_efficiency * params.coding_rate
        )
        
        return results
        
    def print_link_budget(self, results: Dict):
        """Print formatted link budget"""
        print("\n" + "="*70)
        print(f"LINK BUDGET ANALYSIS - {self.scenario.upper()}")
        print("="*70)
        
        # Uplink budget
        print("\n--- TRANSMITTER ---")
        print(f"TX Power:                 {results['tx_power_dbm']:>8.1f} dBm")
        print(f"TX Antenna Gain:          {results['tx_antenna_gain_dbi']:>8.1f} dBi")
        print(f"TX Cable Loss:            {results['tx_cable_loss_db']:>8.1f} dB")
        print(f"                          " + "-"*12)
        print(f"EIRP:                     {results['eirp_dbm']:>8.1f} dBm")
        
        print("\n--- PATH LOSSES ---")
        print(f"Distance:                 {results['distance_km']:>8.1f} km")
        print(f"Free Space Path Loss:     {results['fspl_db']:>8.1f} dB")
        print(f"Atmospheric Absorption:   {results['atmospheric_loss_db']:>8.1f} dB")
        print(f"Rain Attenuation:         {results['rain_loss_db']:>8.1f} dB")
        print(f"Scintillation Margin:     {results['scintillation_margin_db']:>8.1f} dB")
        print(f"Polarization Loss:        {results['polarization_loss_db']:>8.1f} dB")
        print(f"Pointing Loss:            {results['pointing_loss_db']:>8.1f} dB")
        print(f"Implementation Loss:      {results['implementation_loss_db']:>8.1f} dB")
        print(f"                          " + "-"*12)
        print(f"Total Path Loss:          {results['total_path_loss_db']:>8.1f} dB")
        
        print("\n--- RECEIVER ---")
        print(f"RX Antenna Gain:          {results['rx_antenna_gain_dbi']:>8.1f} dBi")
        print(f"RX Cable Loss:            {results['rx_cable_loss_db']:>8.1f} dB")
        print(f"                          " + "-"*12)
        print(f"Received Power:           {results['rx_power_dbm']:>8.1f} dBm")
        
        print("\n--- LINK PERFORMANCE ---")
        print(f"Thermal Noise:            {results['thermal_noise_dbm']:>8.1f} dBm")
        print(f"Signal-to-Noise Ratio:    {results['snr_db']:>8.1f} dB")
        print(f"Required SNR:             {results['required_snr_db']:>8.1f} dB")
        print(f"                          " + "-"*12)
        print(f"LINK MARGIN:              {results['link_margin_db']:>8.1f} dB")
        
        # Status indicator
        if results['link_margin_db'] >= 3:
            status = "✅ PASS - Link Closed"
            color = "\033[92m"  # Green
        elif results['link_margin_db'] >= 0:
            status = "⚠️  MARGINAL - Limited Margin"
            color = "\033[93m"  # Yellow
        else:
            status = "❌ FAIL - Insufficient Margin"
            color = "\033[91m"  # Red
            
        print(f"\n{color}STATUS: {status}\033[0m")
        
        print("\n--- ADDITIONAL INFORMATION ---")
        print(f"Doppler Shift:            {results['doppler_shift_hz']:>8.0f} Hz")
        print(f"Estimated Data Rate:      {results['data_rate_mbps']:>8.1f} Mbps")
        
    def analyze_elevation_impact(self):
        """Analyze link budget vs elevation angle"""
        elevations = np.linspace(10, 90, 17)
        margins = []
        path_losses = []
        
        for elev in elevations:
            self.params.elevation_angle_deg = elev
            results = self.calculate_link_budget()
            margins.append(results['link_margin_db'])
            path_losses.append(-results['total_path_loss_db'])
            
        # Create plot
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        
        ax1.plot(elevations, margins, 'b-', linewidth=2)
        ax1.axhline(y=0, color='r', linestyle='--', label='Minimum Margin')
        ax1.axhline(y=3, color='g', linestyle='--', label='Target Margin')
        ax1.grid(True, alpha=0.3)
        ax1.set_xlabel('Elevation Angle (degrees)')
        ax1.set_ylabel('Link Margin (dB)')
        ax1.set_title(f'Link Margin vs Elevation - {self.scenario.upper()}')
        ax1.legend()
        
        ax2.plot(elevations, path_losses, 'r-', linewidth=2)
        ax2.grid(True, alpha=0.3)
        ax2.set_xlabel('Elevation Angle (degrees)')
        ax2.set_ylabel('Total Path Loss (dB)')
        ax2.set_title('Path Loss vs Elevation')
        
        plt.tight_layout()
        plt.savefig(f'link_budget_{self.scenario}_elevation.png')
        print(f"\nElevation analysis saved to link_budget_{self.scenario}_elevation.png")
        
    def save_results(self, results: Dict, filename: str = None):
        """Save link budget results to JSON"""
        if filename is None:
            filename = f"link_budget_{self.scenario}.json"
            
        output = {
            "scenario": self.scenario,
            "parameters": {
                "tx_power_dbm": self.params.tx_power_dbm,
                "frequency_ghz": self.params.frequency_ghz,
                "distance_km": self.params.distance_km,
                "bandwidth_mhz": self.params.bandwidth_mhz,
                "modulation": self.params.modulation_scheme
            },
            "results": results
        }
        
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)
            
        print(f"\nResults saved to {filename}")

def main():
    parser = argparse.ArgumentParser(description="NTN Link Budget Calculator")
    parser.add_argument("--scenario", type=str, default="geo",
                        choices=["geo", "leo", "haps", "uav"],
                        help="NTN scenario")
    parser.add_argument("--freq", type=float, help="Frequency in GHz")
    parser.add_argument("--distance", type=float, help="Distance in km")
    parser.add_argument("--tx-power", type=float, help="TX power in dBm")
    parser.add_argument("--elevation", type=float, help="Elevation angle in degrees")
    parser.add_argument("--rain", type=float, default=0, help="Rain rate in mm/hr")
    parser.add_argument("--analyze", action="store_true", 
                        help="Analyze elevation impact")
    
    args = parser.parse_args()
    
    # Create calculator
    calculator = NTNLinkBudget(args.scenario)
    
    # Override parameters if provided
    if args.freq:
        calculator.params.frequency_ghz = args.freq
    if args.distance:
        calculator.params.distance_km = args.distance
    if args.tx_power:
        calculator.params.tx_power_dbm = args.tx_power
    if args.elevation:
        calculator.params.elevation_angle_deg = args.elevation
    if args.rain:
        calculator.params.rain_rate_mm_hr = args.rain
        
    # Calculate link budget
    results = calculator.calculate_link_budget()
    
    # Print results
    calculator.print_link_budget(results)
    
    # Save results
    calculator.save_results(results)
    
    # Analyze if requested
    if args.analyze:
        calculator.analyze_elevation_impact()

if __name__ == "__main__":
    main()
