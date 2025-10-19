"""
Pi 5 specific resource monitoring module for Phase 1 Foundation.

Provides:
- CPU temperature monitoring with thermal alerts
- Resource threshold checks
- Temperature-based status determination
"""
import logging
from typing import Dict, Tuple
from metrics import get_cpu_temperature
import psutil

logger = logging.getLogger(__name__)

# Temperature thresholds (Celsius)
TEMP_WARNING = 75.0  # Approaching throttle
TEMP_CRITICAL = 80.0  # CPU throttling active
TEMP_EMERGENCY = 85.0  # Consider emergency shutdown


def check_cpu_temperature_status() -> Tuple[str, str]:
    """Check CPU temperature and return status with message.
    
    Temperature thresholds:
    - Below 75°C: healthy, no warning
    - 75-79°C: healthy, log WARNING (approaching throttle)
    - 80-84°C: unhealthy, log CRITICAL (CPU throttling active)
    - 85°C+: unhealthy, log CRITICAL (emergency shutdown recommended)
    
    Returns:
        Tuple of (status, message)
        status: "healthy", "degraded", or "unhealthy"
        message: Description of temperature status
    """
    temp = get_cpu_temperature()
    
    # Handle unavailable temperature
    if temp == -1.0:
        return ("healthy", "CPU temperature monitoring unavailable")
    
    # Check temperature thresholds
    if temp >= TEMP_EMERGENCY:
        logger.critical(f"CPU temperature critical: {temp}°C (emergency shutdown recommended)")
        return ("unhealthy", f"CPU temperature critical: {temp:.1f}°C (emergency)")
    
    elif temp >= TEMP_CRITICAL:
        logger.critical(f"CPU temperature high: {temp}°C (throttling active)")
        return ("unhealthy", f"CPU temperature high: {temp:.1f}°C (throttling)")
    
    elif temp >= TEMP_WARNING:
        logger.warning(f"CPU temperature elevated: {temp}°C (approaching throttle)")
        return ("healthy", f"CPU temperature elevated: {temp:.1f}°C (warning)")
    
    else:
        # Normal operating temperature
        return ("healthy", f"CPU temperature normal: {temp:.1f}°C")


def get_resource_status() -> Dict[str, any]:
    """Get comprehensive resource status for Pi 5.
    
    Checks:
    - CPU temperature with thermal alerts
    - Memory availability
    - Swap usage
    - CPU usage percentage
    
    Returns:
        Dict with status, metrics, and alerts
    """
    # Get CPU temperature status
    temp_status, temp_message = check_cpu_temperature_status()
    
    # Get system metrics
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    cpu_percent = psutil.cpu_percent(interval=0.1)
    
    # Determine overall status
    overall_status = temp_status
    alerts = []
    
    # Memory checks
    mem_available_gb = mem.available / (1024**3)
    if mem.available <= 500 * 1024**2:  # 500MB
        overall_status = "unhealthy"
        alerts.append(f"Critical memory: {mem_available_gb:.2f}GB available")
    elif mem.available <= 1 * 1024**3:  # 1GB
        if overall_status == "healthy":
            overall_status = "degraded"
        alerts.append(f"Low memory: {mem_available_gb:.2f}GB available")
    
    # Swap checks
    swap_used_gb = swap.used / (1024**3)
    if swap.used >= 4 * 1024**3:  # 4GB
        overall_status = "unhealthy"
        alerts.append(f"Critical swap: {swap_used_gb:.2f}GB used")
    elif swap.used >= 2 * 1024**3:  # 2GB
        if overall_status == "healthy":
            overall_status = "degraded"
        alerts.append(f"High swap: {swap_used_gb:.2f}GB used")
    
    # Add temperature message to alerts if not healthy status
    if temp_status != "healthy" or temp_message != f"CPU temperature normal: {get_cpu_temperature():.1f}°C":
        alerts.append(temp_message)
    
    return {
        "status": overall_status,
        "metrics": {
            "cpu_temp_celsius": get_cpu_temperature(),
            "memory_available_gb": mem_available_gb,
            "swap_used_gb": swap_used_gb,
            "cpu_percent": cpu_percent
        },
        "alerts": alerts
    }
