"""
Monitoring modules for Phase 2 thermal protection.

This package contains thermal monitoring components for Raspberry Pi 5
hardware protection and workload reduction.

Modules:
    thermal_monitor: CPU temperature monitoring and thermal protection logic
"""

from src.monitoring.thermal_monitor import ThermalMonitor, ThermalState

__all__ = ["ThermalMonitor", "ThermalState"]
