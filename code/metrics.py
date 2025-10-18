"""
Lightweight resource metrics for Phase 1 Foundation.

Provides:
- CPU temperature monitoring (Pi 5 specific with fallback)
- System resource metrics (memory, CPU %, swap)
- Prometheus plain text format export
"""
import os
import logging
import subprocess
from typing import Optional
import psutil

from exceptions import MonitoringError

logger = logging.getLogger(__name__)

# Platform detection state (cached after first check)
_platform_checked = False
_is_raspberry_pi = False
_temp_warning_logged = False


def _detect_raspberry_pi() -> bool:
    """Detect if running on Raspberry Pi.
    
    Returns:
        True if Raspberry Pi detected, False otherwise
    """
    global _platform_checked, _is_raspberry_pi
    
    if _platform_checked:
        return _is_raspberry_pi
    
    # Check for thermal zone (standard Linux thermal interface)
    if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
        _is_raspberry_pi = True
        _platform_checked = True
        return True
    
    # Check for vcgencmd (Raspberry Pi specific utility)
    try:
        result = subprocess.run(
            ["which", "vcgencmd"],
            capture_output=True,
            timeout=1.0
        )
        if result.returncode == 0:
            _is_raspberry_pi = True
            _platform_checked = True
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    _is_raspberry_pi = False
    _platform_checked = True
    return False


def get_cpu_temperature() -> float:
    """Get CPU temperature in Celsius.
    
    Platform-specific implementation:
    - Raspberry Pi 5: Read from /sys/class/thermal/thermal_zone0/temp or vcgencmd
    - Other platforms: Return -1 (unavailable)
    
    Returns:
        Temperature in Celsius, or -1 if unavailable
    """
    global _temp_warning_logged
    
    # Check if Raspberry Pi
    if not _detect_raspberry_pi():
        if not _temp_warning_logged:
            logger.info("CPU temperature monitoring not available on this platform (returning -1)")
            _temp_warning_logged = True
        return -1.0
    
    # Try reading from thermal zone (fastest method)
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp_millidegrees = int(f.read().strip())
            return temp_millidegrees / 1000.0
    except (FileNotFoundError, PermissionError, ValueError) as e:
        logger.debug(f"Could not read thermal_zone0: {e}")
    
    # Fallback to vcgencmd
    try:
        result = subprocess.run(
            ["vcgencmd", "measure_temp"],
            capture_output=True,
            text=True,
            timeout=1.0
        )
        if result.returncode == 0:
            # Output format: "temp=45.0'C"
            temp_str = result.stdout.strip()
            temp_value = float(temp_str.split("=")[1].split("'")[0])
            return temp_value
    except (subprocess.TimeoutExpired, FileNotFoundError, IndexError, ValueError) as e:
        logger.debug(f"Could not read vcgencmd: {e}")
    
    # If all methods fail, return -1
    if not _temp_warning_logged:
        logger.warning("CPU temperature unavailable despite Pi detection (returning -1)")
        _temp_warning_logged = True
    return -1.0


def get_metrics() -> str:
    """Collect system metrics and format as Prometheus plain text.
    
    Metrics:
    - system_memory_available_bytes: Available memory
    - system_cpu_temperature_celsius: CPU temperature
    - system_cpu_percent: CPU usage percentage
    - system_swap_usage_bytes: Swap usage
    
    Returns:
        Prometheus plain text format string
        
    Raises:
        MonitoringError: If metrics collection fails critically
    """
    try:
        # Collect metrics
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        cpu_percent = psutil.cpu_percent(interval=0.1)  # 100ms sample
        cpu_temp = get_cpu_temperature()
        
        # Cap CPU percent at 100% (psutil can report >100% on multi-core)
        if cpu_percent > 100.0:
            cpu_percent = 100.0
        
        # Format as Prometheus plain text
        lines = [
            "# HELP system_memory_available_bytes Available system memory in bytes",
            "# TYPE system_memory_available_bytes gauge",
            f"system_memory_available_bytes {mem.available}",
            "",
            "# HELP system_cpu_temperature_celsius CPU temperature in Celsius",
            "# TYPE system_cpu_temperature_celsius gauge",
            f"system_cpu_temperature_celsius {cpu_temp}",
            "",
            "# HELP system_cpu_percent CPU usage percentage",
            "# TYPE system_cpu_percent gauge",
            f"system_cpu_percent {cpu_percent}",
            "",
            "# HELP system_swap_usage_bytes Swap memory usage in bytes",
            "# TYPE system_swap_usage_bytes gauge",
            f"system_swap_usage_bytes {swap.used}",
            ""
        ]
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise MonitoringError(
            metric="all",
            message="Failed to collect system metrics",
            error=str(e)
        )
