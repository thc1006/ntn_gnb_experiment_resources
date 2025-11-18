# 📁 Project Structure - 5G NTN Software Testbed

**Version**: 2.0.0 | **Updated**: 2024-11-18 | **Claude Code Best Practices** ✅

---

## 🎯 Overview

This document describes the reorganized project structure following **Claude Code official best practices**. The structure is designed for:
- **Immediate usability** in new Claude Code sessions
- **Clear separation of concerns**
- **Easy navigation and maintenance**
- **Production-ready deployment**

---

## 📂 Directory Structure

```
NTN_ITRI/
├── .claude/                      # Claude Code configuration
│   ├── skills/                   # Custom skills (ntn-link-budget, rf-safety)
│   └── subagents/                # Subagents (performance_monitor)
│
├── src/                          # Main source code (NEW!)
│   ├── __init__.py              # Package initialization
│   ├── simulators/              # Software simulators
│   │   ├── __init__.py
│   │   ├── usrp_simulator.py         # USRP X310/B210 simulation
│   │   ├── channel_simulator.py      # Channel emulator simulation
│   │   └── demo_full_simulation.py   # End-to-end demo
│   ├── analysis/                # Analysis tools
│   │   ├── __init__.py
│   │   └── link_budget_calculator.py
│   ├── ntn/                     # NTN-specific implementations
│   │   ├── __init__.py
│   │   └── geo_delay_simulator.py
│   └── legacy/                  # Archived hardware code (reference only)
│       ├── channel_emulator_control.py  # Old hardware controller
│       ├── usrp_ntn_test.py             # Old USRP test
│       └── rf_loopback_test.py          # Old RF loopback
│
├── mcp-servers/                 # MCP servers for Claude Code
│   ├── mcp_usrp_simulator.py         # Software USRP MCP server
│   ├── mcp_channel_simulator.py      # Software channel MCP server
│   ├── mcp_usrp.py                   # Old hardware USRP server (legacy)
│   └── mcp_channel.py                # Old hardware channel server (legacy)
│
├── tests/                       # Test suite (empty - to be populated)
│
├── scripts/                     # Automation scripts
│   ├── quick_start.sh                # One-command setup
│   ├── setup_ntn_environment.sh      # Environment setup
│   └── init_testbed.sh               # Testbed initialization
│
├── config/                      # Configuration files
│   └── testbed_config.yaml           # Central configuration
│
├── docker/                      # Docker deployment
│   ├── Dockerfile                    # Multi-stage build
│   ├── docker-compose.yml            # Full stack (testbed + jupyter + monitoring)
│   └── entrypoint.sh                 # Container entrypoint
│
├── kubernetes/                  # Kubernetes deployment
│   ├── deployment.yaml               # K8s manifests
│   └── kind-config.yaml              # Kind cluster configuration
│
├── docs/                        # Documentation (NEW!)
│   ├── PROJECT_ANALYSIS.md           # Comprehensive project analysis (46k+ words)
│   ├── SETUP_SUMMARY.md              # Setup completion report
│   ├── REFACTORING_COMPLETE.md       # Refactoring documentation
│   ├── guides/                       # User guides
│   │   ├── ntn_experiment_preparation.md
│   │   └── 376355b_getting started guide.pdf
│   └── api/                          # API documentation (to be added)
│
├── results/                     # Output results (created on first run)
│   ├── simulation_results.json
│   └── spectrum_*.png
│
├── venv/                        # Python virtual environment (local dev)
│
├── .gitignore                   # Git ignore rules
├── .mcp.json                    # MCP server configuration
├── LICENSE                      # MIT License
├── README.md                    # Main readme (software-focused)
├── QUICKSTART.md                # 5-minute quick start guide
├── CLAUDE.md                    # Claude Code instructions
├── PROJECT_STRUCTURE.md         # This file
└── requirements.txt             # Python dependencies
```

---

## 🗂️ Key Directories Explained

### `src/` - Main Source Code
**NEW in v2.0!** All production source code lives here.

- **`src/simulators/`**: Core simulation engines
  - Replace physical USRP and channel emulator hardware
  - GPU-accelerated (CuPy optional)
  - 3GPP-compliant NTN channel models

- **`src/analysis/`**: Analysis and calculation tools
  - Link budget calculators
  - Performance analyzers

- **`src/ntn/`**: NTN-specific implementations
  - GEO delay simulation
  - Timing advance calculations

- **`src/legacy/`**: Archived hardware-dependent code
  - **Do NOT use** for new development
  - Kept for reference only

### `mcp-servers/` - MCP Servers
Claude Code Model Context Protocol servers for external control.

- **Software-only servers** (use these!):
  - `mcp_usrp_simulator.py` - Software USRP control
  - `mcp_channel_simulator.py` - Software channel control

- **Legacy hardware servers** (archived):
  - `mcp_usrp.py`
  - `mcp_channel.py`

### `docs/` - Documentation
**NEW in v2.0!** All documentation centralized here.

- **Root docs**:
  - `PROJECT_ANALYSIS.md` - Deep dive (46,000+ words)
  - `SETUP_SUMMARY.md` - Setup completion report
  - `REFACTORING_COMPLETE.md` - Refactoring details

- **`docs/guides/`**: User guides and tutorials
- **`docs/api/`**: API documentation (to be added)

### `scripts/` - Automation Scripts
Useful automation and setup scripts.

- **`quick_start.sh`**: One-command setup and demo
- **`setup_ntn_environment.sh`**: Environment configuration
- **`init_testbed.sh`**: Testbed initialization

### `config/` - Configuration
Centralized configuration management.

- **`testbed_config.yaml`**: Complete system configuration
  - USRP parameters
  - Channel settings
  - Simulation options
  - Monitoring and logging

### `docker/` & `kubernetes/` - Deployment
Production-ready deployment configurations.

- **Docker**: Containerized deployment with GPU support
- **Kubernetes**: Scalable cloud deployment

---

## 🚀 Quick Usage Guide

### Import from New Structure

#### Before (v1.x) - WRONG! ❌
```python
from simulators import SimulatorFactory  # Old path
from analysis.link_budget_calculator import calculate_link_budget
```

#### After (v2.0) - CORRECT! ✅
```python
from src.simulators import SimulatorFactory
from src.analysis.link_budget_calculator import calculate_link_budget
```

### Running Demo

```bash
# From project root
python -m src.simulators.demo_full_simulation

# Or navigate into src/
cd src/simulators
python demo_full_simulation.py
```

### Using MCP Servers

```bash
# Start software USRP MCP server
python mcp-servers/mcp_usrp_simulator.py

# Start software channel MCP server
python mcp-servers/mcp_channel_simulator.py
```

---

## 📦 Package Structure

The `src/` directory is now a proper Python package:

```python
src/
├── __init__.py              # Exports: simulators, analysis, ntn
├── simulators/
│   ├── __init__.py          # Exports: SimulatorFactory, ChannelEmulatorFactory, etc.
│   ├── usrp_simulator.py
│   ├── channel_simulator.py
│   └── demo_full_simulation.py
├── analysis/
│   ├── __init__.py
│   └── link_budget_calculator.py
├── ntn/
│   ├── __init__.py
│   └── geo_delay_simulator.py
└── legacy/
    └── (old hardware code - do not use)
```

---

## 🎯 What Changed from v1.x

### Files Moved
| Old Location | New Location | Reason |
|--------------|--------------|--------|
| `simulators/` | `src/simulators/` | Source code organization |
| `analysis/` | `src/analysis/` | Source code organization |
| `ntn/` | `src/ntn/` | Source code organization |
| `channel_emulator_control.py` | `src/legacy/` | Hardware-dependent (archived) |
| `usrp_ntn_test.py` | `src/legacy/` | Hardware-dependent (archived) |
| `PROJECT_ANALYSIS.md` | `docs/` | Documentation centralization |
| `SETUP_SUMMARY.md` | `docs/` | Documentation centralization |
| `REFACTORING_COMPLETE.md` | `docs/` | Documentation centralization |
| `ntn_experiment_preparation.md` | `docs/guides/` | User guide |
| `376355b_getting started guide.pdf` | `docs/guides/` | User guide |
| `setup_ntn_environment.sh` | `scripts/` | Script organization |

### Files Deleted
| File | Reason |
|------|--------|
| `README (2).md` | Duplicate |
| `ntn_experiment_preparation_1.md` | Duplicate |

### New Files Created
| File | Purpose |
|------|---------|
| `src/__init__.py` | Package initialization |
| `src/analysis/__init__.py` | Package initialization |
| `src/ntn/__init__.py` | Package initialization |
| `PROJECT_STRUCTURE.md` | This file |

---

## 🔄 Migration Guide

### For Existing Code

If you have existing code that imports from old paths:

```python
# Find and replace these imports:

# OLD
from simulators import SimulatorFactory
from simulators.usrp_simulator import SoftwareUSRP
from analysis.link_budget_calculator import calculate_link_budget

# NEW
from src.simulators import SimulatorFactory
from src.simulators.usrp_simulator import SoftwareUSRP
from src.analysis.link_budget_calculator import calculate_link_budget
```

### For Scripts

Update Python path in scripts:

```python
# OLD
import sys
sys.path.append('.')
from simulators import SimulatorFactory

# NEW
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.simulators import SimulatorFactory
```

---

## ✅ Verification Checklist

After restructuring, verify:

- [ ] `python -m src.simulators.demo_full_simulation` runs successfully
- [ ] `python mcp-servers/mcp_usrp_simulator.py` starts without errors
- [ ] `python mcp-servers/mcp_channel_simulator.py` starts without errors
- [ ] `from src.simulators import SimulatorFactory` works in Python REPL
- [ ] All imports resolve correctly
- [ ] No broken links in documentation
- [ ] Docker build succeeds: `docker build -f docker/Dockerfile .`
- [ ] Scripts run: `./scripts/quick_start.sh`

---

## 🎓 Claude Code Best Practices Followed

✅ **Clear Separation of Concerns**
- `src/` for source code
- `docs/` for documentation
- `scripts/` for automation
- `config/` for configuration
- `tests/` for tests

✅ **Python Package Structure**
- Proper `__init__.py` files
- Relative imports within packages
- Clear module hierarchy

✅ **Documentation Organization**
- Centralized in `docs/`
- Quick start in root (`QUICKSTART.md`)
- Project instructions in root (`CLAUDE.md`)

✅ **Deployment Ready**
- Docker configurations
- Kubernetes manifests
- CI/CD friendly structure

✅ **Version Control Friendly**
- `.gitignore` properly configured
- No generated files in repo
- Clear separation of code and data

✅ **Claude Code Integration**
- `.claude/` for skills and subagents
- MCP servers properly organized
- `CLAUDE.md` for instructions
- Immediate new session usability

---

## 📞 Support

For questions about the new structure:
1. **Quick Start**: See [QUICKSTART.md](QUICKSTART.md)
2. **Full Docs**: See [docs/PROJECT_ANALYSIS.md](docs/PROJECT_ANALYSIS.md)
3. **Claude Instructions**: See [CLAUDE.md](CLAUDE.md)

---

**Last Updated**: 2024-11-18
**Structure Version**: 2.0.0
**Status**: ✅ Production Ready | 🎯 Claude Code Native

**Ready for new sessions!** The project structure is now clean, organized, and immediately usable. 🚀
