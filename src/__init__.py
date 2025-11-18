"""
5G NTN Software Testbed - Source Package
=========================================

Main source code package for the 5G Non-Terrestrial Network software testbed.

Modules:
- simulators: Software USRP and channel emulator simulators
- analysis: Link budget calculators and analysis tools
- ntn: NTN-specific implementations (GEO delay, etc.)
- legacy: Archived hardware-dependent code (reference only)
"""

__version__ = "2.0.0"
__author__ = "5G NTN Research Team"

# Make subpackages easily importable
from . import simulators
from . import analysis
from . import ntn

__all__ = ['simulators', 'analysis', 'ntn']
