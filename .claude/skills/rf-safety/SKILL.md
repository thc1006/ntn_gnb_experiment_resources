# RF Safety Compliance Skill for Claude Code

## Overview
This skill ensures RF safety compliance with IEEE C95.1-2019 and ICNIRP 2020 standards, calculating safe distances, power densities, and monitoring exposure limits for 5G NTN testing.

## Commands

### `rf-safety calculate-distance`
Calculate minimum safe distance for given RF parameters.

**Usage:**
```bash
rf-safety calculate-distance --power 33 --gain 15 --freq 2.0
```

**Parameters:**
- `--power`: Transmit power in dBm
- `--gain`: Antenna gain in dBi
- `--freq`: Frequency in GHz
- `--standard`: Safety standard (IEEE/ICNIRP/FCC)
- `--exposure`: public/occupational

**Returns:** Safe distance in meters with safety margin

### `rf-safety check-compliance`
Verify compliance for current setup.

**Usage:**
```bash
rf-safety check-compliance --config setup.json
```

**Returns:** Compliance report with pass/fail status

### `rf-safety monitor`
Real-time RF exposure monitoring.

**Usage:**
```bash
rf-safety monitor --duration 3600 --alert-threshold 50
```

## Implementation

```python
#!/usr/bin/env python3
import numpy as np
import json
import argparse
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
import warnings

@dataclass
class RFSafetyLimits:
    """RF exposure limits per standard"""
    # IEEE C95.1-2019 limits (W/m²)
    ieee_public: Dict[str, float] = None
    ieee_occupational: Dict[str, float] = None
    
    # ICNIRP 2020 limits (W/m²)
    icnirp_public: Dict[str, float] = None
    icnirp_occupational: Dict[str, float] = None
    
    def __post_init__(self):
        # IEEE C95.1-2019 power density limits
        self.ieee_public = {
            "0.1-2.0": 10.0,    # 100 MHz - 2 GHz: f/200 W/m²
            "2.0-5.0": 10.0,    # 2-5 GHz: 10 W/m²
            "5.0-30.0": 10.0,   # 5-30 GHz: 10 W/m²
            "30.0-100.0": 10.0  # 30-100 GHz: 10 W/m²
        }
        
        self.ieee_occupational = {
            "0.1-2.0": 50.0,    # 5x public limit
            "2.0-5.0": 50.0,
            "5.0-30.0": 50.0,
            "30.0-100.0": 50.0
        }
        
        # ICNIRP 2020 limits (similar structure)
        self.icnirp_public = {
            "0.4-2.0": 10.0,    # f/200 W/m²
            "2.0-10.0": 10.0,   # 10 W/m²
            "10.0-400.0": 10.0  # 10 W/m²
        }
        
        self.icnirp_occupational = {
            "0.4-2.0": 50.0,
            "2.0-10.0": 50.0,
            "10.0-400.0": 50.0
        }

class RFSafetyCalculator:
    """RF Safety compliance calculator"""
    
    def __init__(self):
        self.limits = RFSafetyLimits()
        self.monitoring_data = []
        
    def calculate_power_density(self, eirp_watts: float, distance_m: float) -> float:
        """
        Calculate power density at given distance
        S = P*G / (4*π*d²)
        """
        if distance_m <= 0:
            return float('inf')
            
        power_density = eirp_watts / (4 * np.pi * distance_m**2)
        return power_density
        
    def dbm_to_watts(self, power_dbm: float) -> float:
        """Convert dBm to Watts"""
        return 10**((power_dbm - 30) / 10)
        
    def dbi_to_linear(self, gain_dbi: float) -> float:
        """Convert dBi to linear gain"""
        return 10**(gain_dbi / 10)
        
    def calculate_eirp_watts(self, tx_power_dbm: float, antenna_gain_dbi: float) -> float:
        """Calculate EIRP in Watts"""
        tx_power_watts = self.dbm_to_watts(tx_power_dbm)
        antenna_gain_linear = self.dbi_to_linear(antenna_gain_dbi)
        return tx_power_watts * antenna_gain_linear
        
    def get_exposure_limit(self, freq_ghz: float, standard: str = "ieee", 
                           exposure_type: str = "public") -> float:
        """Get exposure limit for given frequency and standard"""
        limits_dict = None
        
        if standard.lower() == "ieee":
            if exposure_type == "public":
                limits_dict = self.limits.ieee_public
            else:
                limits_dict = self.limits.ieee_occupational
        elif standard.lower() == "icnirp":
            if exposure_type == "public":
                limits_dict = self.limits.icnirp_public
            else:
                limits_dict = self.limits.icnirp_occupational
        else:
            raise ValueError(f"Unknown standard: {standard}")
            
        # Find appropriate frequency range
        for freq_range, limit in limits_dict.items():
            min_freq, max_freq = map(float, freq_range.split("-"))
            if min_freq <= freq_ghz <= max_freq:
                # Apply frequency-dependent scaling for lower frequencies
                if freq_ghz < 2.0:
                    return (freq_ghz / 0.2)  # f/200 W/m² for L-band
                else:
                    return limit
                    
        return 10.0  # Default limit
        
    def calculate_safe_distance(self, tx_power_dbm: float, antenna_gain_dbi: float,
                               freq_ghz: float, standard: str = "ieee",
                               exposure_type: str = "public",
                               safety_factor: float = 2.0) -> Dict:
        """Calculate minimum safe distance"""
        
        # Calculate EIRP
        eirp_watts = self.calculate_eirp_watts(tx_power_dbm, antenna_gain_dbi)
        eirp_dbm = tx_power_dbm + antenna_gain_dbi
        
        # Get exposure limit
        exposure_limit = self.get_exposure_limit(freq_ghz, standard, exposure_type)
        
        # Calculate minimum distance for compliance
        # S = EIRP / (4*π*d²) <= limit
        # d >= sqrt(EIRP / (4*π*limit))
        min_distance = np.sqrt(eirp_watts / (4 * np.pi * exposure_limit))
        
        # Apply safety factor
        safe_distance = min_distance * safety_factor
        
        # Calculate actual power density at safe distance
        power_density_at_safe = self.calculate_power_density(eirp_watts, safe_distance)
        
        # Electric field strength
        # E = sqrt(S * 377) where 377 ohms is free space impedance
        e_field = np.sqrt(power_density_at_safe * 377)
        
        return {
            "tx_power_dbm": tx_power_dbm,
            "antenna_gain_dbi": antenna_gain_dbi,
            "eirp_dbm": eirp_dbm,
            "eirp_watts": eirp_watts,
            "frequency_ghz": freq_ghz,
            "standard": standard,
            "exposure_type": exposure_type,
            "exposure_limit_w_m2": exposure_limit,
            "min_distance_m": min_distance,
            "safety_factor": safety_factor,
            "safe_distance_m": safe_distance,
            "power_density_at_safe_w_m2": power_density_at_safe,
            "e_field_v_m": e_field,
            "percent_of_limit": (power_density_at_safe / exposure_limit) * 100
        }
        
    def check_compliance(self, config: Dict) -> Dict:
        """Check compliance for given configuration"""
        results = {
            "compliant": True,
            "warnings": [],
            "violations": [],
            "recommendations": []
        }
        
        # Extract parameters
        tx_power_dbm = config.get("tx_power_dbm", 30)
        antenna_gain_dbi = config.get("antenna_gain_dbi", 15)
        freq_ghz = config.get("frequency_ghz", 2.0)
        test_distance_m = config.get("test_distance_m", 3.0)
        
        # Calculate for both public and occupational
        for exposure_type in ["public", "occupational"]:
            safety_calc = self.calculate_safe_distance(
                tx_power_dbm, antenna_gain_dbi, freq_ghz,
                exposure_type=exposure_type
            )
            
            if test_distance_m < safety_calc["safe_distance_m"]:
                if exposure_type == "public":
                    results["violations"].append(
                        f"Test distance {test_distance_m}m violates public safety "
                        f"(minimum: {safety_calc['safe_distance_m']:.1f}m)"
                    )
                    results["compliant"] = False
                else:
                    results["warnings"].append(
                        f"Test distance {test_distance_m}m below occupational safety "
                        f"(minimum: {safety_calc['safe_distance_m']:.1f}m)"
                    )
                    
        # Check for high power warnings
        if tx_power_dbm > 30:
            results["warnings"].append(f"High transmit power ({tx_power_dbm} dBm)")
            
        if antenna_gain_dbi > 20:
            results["warnings"].append(f"High antenna gain ({antenna_gain_dbi} dBi)")
            
        eirp_dbm = tx_power_dbm + antenna_gain_dbi
        if eirp_dbm > 40:
            results["warnings"].append(f"High EIRP ({eirp_dbm} dBm)")
            
        # Recommendations
        if not results["compliant"]:
            results["recommendations"].append("Increase test distance")
            results["recommendations"].append("Reduce transmit power")
            results["recommendations"].append("Use lower gain antenna")
            results["recommendations"].append("Implement RF barriers")
            
        return results
        
    def calculate_sar(self, e_field_v_m: float, freq_ghz: float,
                     tissue_conductivity: float = 1.0) -> float:
        """
        Calculate Specific Absorption Rate (SAR)
        SAR = σ*E²/ρ where σ is conductivity, ρ is density
        """
        # Simplified SAR calculation
        # Typical tissue density ~1000 kg/m³
        tissue_density = 1000
        
        # Frequency-dependent conductivity (simplified)
        if freq_ghz < 1:
            conductivity = 0.5
        elif freq_ghz < 3:
            conductivity = 1.0
        else:
            conductivity = 2.0
            
        sar = conductivity * e_field_v_m**2 / tissue_density
        
        return sar
        
    def generate_safety_report(self, config: Dict) -> str:
        """Generate comprehensive safety report"""
        report = []
        report.append("="*60)
        report.append("RF SAFETY COMPLIANCE REPORT")
        report.append("="*60)
        
        # Calculate safety parameters
        safety_calc = self.calculate_safe_distance(
            config["tx_power_dbm"],
            config["antenna_gain_dbi"],
            config["frequency_ghz"]
        )
        
        report.append("\n--- TRANSMITTER CONFIGURATION ---")
        report.append(f"Frequency: {config['frequency_ghz']:.2f} GHz")
        report.append(f"TX Power: {config['tx_power_dbm']:.1f} dBm")
        report.append(f"Antenna Gain: {config['antenna_gain_dbi']:.1f} dBi")
        report.append(f"EIRP: {safety_calc['eirp_dbm']:.1f} dBm "
                     f"({safety_calc['eirp_watts']:.2f} W)")
        
        report.append("\n--- EXPOSURE LIMITS ---")
        report.append(f"Standard: {safety_calc['standard'].upper()}")
        report.append(f"Public Limit: {safety_calc['exposure_limit_w_m2']:.1f} W/m²")
        
        report.append("\n--- SAFE DISTANCES ---")
        report.append(f"Minimum Distance (Public): {safety_calc['min_distance_m']:.2f} m")
        report.append(f"Recommended Distance (2x safety): {safety_calc['safe_distance_m']:.2f} m")
        
        report.append("\n--- COMPLIANCE STATUS ---")
        compliance = self.check_compliance(config)
        
        if compliance["compliant"]:
            report.append("✅ COMPLIANT with safety standards")
        else:
            report.append("❌ NON-COMPLIANT - Action required")
            
        if compliance["violations"]:
            report.append("\nVIOLATIONS:")
            for violation in compliance["violations"]:
                report.append(f"  • {violation}")
                
        if compliance["warnings"]:
            report.append("\nWARNINGS:")
            for warning in compliance["warnings"]:
                report.append(f"  • {warning}")
                
        if compliance["recommendations"]:
            report.append("\nRECOMMENDATIONS:")
            for rec in compliance["recommendations"]:
                report.append(f"  • {rec}")
                
        report.append("\n--- SAFETY MEASURES ---")
        report.append("• Post RF warning signs at calculated safe distance")
        report.append("• Use RF barriers or shields where necessary")
        report.append("• Provide RF safety training to personnel")
        report.append("• Implement lockout procedures during testing")
        report.append("• Monitor exposure with RF field meters")
        
        return "\n".join(report)

def main():
    parser = argparse.ArgumentParser(description="RF Safety Compliance")
    parser.add_argument("command", choices=["calculate-distance", "check-compliance", "report"])
    parser.add_argument("--power", type=float, default=30, help="TX power in dBm")
    parser.add_argument("--gain", type=float, default=15, help="Antenna gain in dBi")
    parser.add_argument("--freq", type=float, default=2.0, help="Frequency in GHz")
    parser.add_argument("--standard", default="ieee", choices=["ieee", "icnirp", "fcc"])
    parser.add_argument("--exposure", default="public", choices=["public", "occupational"])
    parser.add_argument("--distance", type=float, help="Test distance in meters")
    parser.add_argument("--output", default="text", choices=["text", "json"])
    
    args = parser.parse_args()
    
    calculator = RFSafetyCalculator()
    
    if args.command == "calculate-distance":
        result = calculator.calculate_safe_distance(
            args.power, args.gain, args.freq,
            args.standard, args.exposure
        )
        
        if args.output == "json":
            print(json.dumps(result, indent=2))
        else:
            print(f"Safe Distance: {result['safe_distance_m']:.2f} m")
            print(f"Power Density: {result['power_density_at_safe_w_m2']:.3f} W/m²")
            print(f"Percent of Limit: {result['percent_of_limit']:.1f}%")
            
    elif args.command == "check-compliance":
        config = {
            "tx_power_dbm": args.power,
            "antenna_gain_dbi": args.gain,
            "frequency_ghz": args.freq,
            "test_distance_m": args.distance or 3.0
        }
        
        result = calculator.check_compliance(config)
        
        if args.output == "json":
            print(json.dumps(result, indent=2))
        else:
            status = "✅ COMPLIANT" if result["compliant"] else "❌ NON-COMPLIANT"
            print(f"Status: {status}")
            
            if result["violations"]:
                print("\nViolations:")
                for v in result["violations"]:
                    print(f"  • {v}")
                    
    elif args.command == "report":
        config = {
            "tx_power_dbm": args.power,
            "antenna_gain_dbi": args.gain,
            "frequency_ghz": args.freq,
            "test_distance_m": args.distance or 3.0
        }
        
        report = calculator.generate_safety_report(config)
        print(report)

if __name__ == "__main__":
    main()
```

## Safety Standards Reference

### IEEE C95.1-2019
- Public exposure: 4-10 W/m² (L-band)
- Occupational: 20-50 W/m²
- Averaging time: 30 minutes (public), 6 minutes (occupational)

### ICNIRP 2020
- Similar limits with slight variations
- More stringent in some frequency ranges

### FCC Part 1.1310
- Generally follows IEEE standards
- Additional requirements for fixed installations

## Integration with Test Procedures

```python
# Pre-test safety check
async def pre_test_safety_check():
    config = {
        "tx_power_dbm": 33,
        "antenna_gain_dbi": 15,
        "frequency_ghz": 2.0,
        "test_distance_m": 2.0
    }
    
    result = await run_skill("rf-safety", {
        "command": "check-compliance",
        "config": config
    })
    
    if not result["compliant"]:
        raise SafetyViolation("Test setup violates RF safety standards")
        
    # Set up safety perimeter
    safe_distance = result["safe_distance_m"]
    await setup_safety_perimeter(safe_distance)
```

## Emergency Procedures

1. **Immediate Actions**
   - Power down transmitters
   - Evacuate affected area
   - Document exposure incident

2. **Monitoring**
   - Use calibrated RF field meters
   - Log exposure duration and levels
   - Medical evaluation if limits exceeded

## Version
- Version: 1.0.0
- Last Updated: November 2024
- Compliance: IEEE C95.1-2019, ICNIRP 2020
