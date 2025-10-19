# Contract: ThermalMonitor Interface

**Feature**: Phase 2 Infrastructure Improvements  
**Module**: `code/monitoring/thermal_monitor.py`  
**Priority**: P2 (Hardware Protection)

## Purpose

Provide CPU temperature monitoring for Raspberry Pi 5 with thermal protection state management and callback notification system.

---

## Interface Definition

```python
from typing import Callable, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

class ThermalMonitor:
    """
    Monitors CPU temperature and manages thermal protection state.

    Implements Schmitt trigger hysteresis to prevent oscillation:
    - Trigger protection at 85°C
    - Resume normal operation at 80°C

    Platform support:
    - Raspberry Pi 5: Read from /sys/class/thermal/thermal_zone0/temp
    - Other platforms: Return -1.0 (graceful fallback)
    """

    def __init__(
        self,
        trigger_threshold: float = 85.0,
        resume_threshold: float = 80.0,
        poll_interval: float = 1.0,
        simulation_mode: bool = False
    ):
        """
        Initialize thermal monitor.

        Args:
            trigger_threshold: Temperature (°C) to activate protection
            resume_threshold: Temperature (°C) to deactivate protection
            poll_interval: Seconds between temperature readings
            simulation_mode: Use simulated temperature for testing

        Raises:
            ValueError: If trigger_threshold <= resume_threshold
        """
        ...

    def get_temperature(self) -> float:
        """
        Read current CPU temperature.

        Returns:
            float: Temperature in Celsius, or -1.0 if unavailable

        Platform behavior:
            - Raspberry Pi 5: Read /sys/class/thermal/thermal_zone0/temp
            - Other platforms: Return -1.0 (no error raised)
        """
        ...

    def check_thermal_protection(self) -> bool:
        """
        Check current thermal protection state.

        Returns:
            bool: True if protection active, False otherwise

        Side effects:
            - Updates internal ThermalState
            - Triggers registered callbacks if state changed
            - Logs CRITICAL on protection trigger
            - Logs INFO on protection resume
        """
        ...

    def register_callback(
        self,
        callback: Callable[[ThermalState], None]
    ) -> None:
        """
        Register callback to be notified of thermal state changes.

        Args:
            callback: Function accepting ThermalState parameter

        Callback timing:
            - Called immediately when protection activates (≥85°C)
            - Called immediately when protection deactivates (<80°C)
            - NOT called on every temperature reading (only state changes)

        Example:
            def on_thermal_event(state: ThermalState):
                if state.protection_active:
                    llm.pause_inference()
                else:
                    llm.resume_inference()

            monitor.register_callback(on_thermal_event)
        """
        ...

    def start_monitoring(self) -> None:
        """
        Start background temperature monitoring thread.

        Behavior:
            - Creates daemon thread polling at configured interval
            - Thread stops automatically when object garbage collected
            - Safe to call multiple times (idempotent)

        Thread safety:
            - Monitoring thread is daemon (won't block shutdown)
            - Uses threading.Event for clean termination
        """
        ...

    def stop_monitoring(self) -> None:
        """
        Stop background monitoring thread gracefully.

        Behavior:
            - Signals thread to stop via threading.Event
            - Waits up to 5 seconds for thread termination
            - Logs warning if thread doesn't stop cleanly

        Thread safety:
            - Safe to call from any thread
            - Safe to call multiple times (idempotent)
        """
        ...

    def get_state(self) -> ThermalState:
        """
        Get current thermal state snapshot.

        Returns:
            ThermalState: Current temperature, thresholds, and protection status

        Thread safety:
            - Returns copy of state (safe for concurrent access)
        """
        ...

    def set_thresholds(
        self,
        trigger: Optional[float] = None,
        resume: Optional[float] = None
    ) -> None:
        """
        Update thermal protection thresholds dynamically.

        Args:
            trigger: New trigger threshold (°C), or None to keep current
            resume: New resume threshold (°C), or None to keep current

        Raises:
            ValueError: If trigger <= resume

        Thread safety:
            - Safe to call during monitoring
            - New thresholds apply to next temperature check
        """
        ...
```

---

## Data Structures

### ThermalState

```python
@dataclass
class ThermalState:
    """Snapshot of thermal monitoring state"""

    current_temp: float          # Current temperature (°C) or -1.0
    trigger_threshold: float     # Protection activation threshold
    resume_threshold: float      # Protection deactivation threshold
    protection_active: bool      # Current protection state
    platform_supported: bool     # False if temperature unavailable
    trigger_count: int           # Historical trigger count
    max_temp_observed: float     # Historical maximum temperature
    last_checked: datetime       # Timestamp of last temperature reading
```

---

## Behavioral Contracts

### Temperature Reading

**MUST**:

- Return -1.0 on non-Pi platforms (no exceptions raised)
- Read from `/sys/class/thermal/thermal_zone0/temp` on Pi 5
- Convert millidegrees to degrees Celsius (divide by 1000)
- Handle FileNotFoundError, PermissionError gracefully (return -1.0)
- Complete read operation in <10ms (no blocking)

**MUST NOT**:

- Raise exceptions for missing thermal interfaces
- Require sudo/elevated permissions
- Block indefinitely on file I/O
- Cache temperature longer than poll_interval

### Hysteresis Logic

**MUST**:

- Trigger protection when temp ≥ trigger_threshold (default 85°C)
- Resume normal when temp < resume_threshold (default 80°C)
- Maintain state during intermediate temperatures (80-85°C band)
- Use Schmitt trigger pattern (no oscillation)

**Example**:

```
Temp sequence: 84.0 → 85.0 → 84.5 → 83.0 → 79.8
State:         NORMAL → PROTECTED → PROTECTED → PROTECTED → NORMAL
Callbacks:     (none) → (trigger) → (none) → (none) → (resume)
```

### Callback Notification

**MUST**:

- Call callbacks only on state changes (not every temperature reading)
- Call callbacks synchronously from monitoring thread
- Pass ThermalState copy (not mutable reference)
- Continue monitoring if callback raises exception (log error)
- Call callbacks in registration order

**MUST NOT**:

- Block monitoring thread if callback hangs (timeout enforced)
- Skip callbacks due to previous callback failure
- Call same callback multiple times per state change

### Thread Management

**MUST**:

- Use daemon thread for monitoring loop
- Check threading.Event every poll_interval
- Stop cleanly within 5 seconds of stop_monitoring() call
- Release all resources on stop (no thread leaks)

**MUST NOT**:

- Create multiple monitoring threads (enforce singleton)
- Block shutdown if monitoring thread hangs
- Raise exceptions from monitoring thread (log only)

---

## Error Handling

### Platform Unsupported

```python
# Behavior on macOS/Windows/non-Pi Linux
monitor = ThermalMonitor()
temp = monitor.get_temperature()
assert temp == -1.0  # No exception raised

state = monitor.get_state()
assert state.platform_supported == False
assert state.protection_active == False  # Never activates
```

### File Read Errors

```python
# /sys/class/thermal/thermal_zone0/temp missing or unreadable
try:
    temp = monitor.get_temperature()
    assert temp == -1.0  # Graceful fallback
except Exception:
    pytest.fail("Should not raise exception")
```

### Threshold Configuration Errors

```python
# Invalid thresholds
with pytest.raises(ValueError):
    monitor = ThermalMonitor(
        trigger_threshold=80.0,
        resume_threshold=85.0  # INVALID: resume > trigger
    )
```

---

## Performance Guarantees

| Operation                  | Maximum Latency | Notes                           |
| -------------------------- | --------------- | ------------------------------- |
| get_temperature()          | 10 ms           | Single file read                |
| check_thermal_protection() | 15 ms           | Read + state update + callbacks |
| register_callback()        | 1 ms            | Append to list                  |
| start_monitoring()         | 50 ms           | Thread creation                 |
| stop_monitoring()          | 5 seconds       | Graceful shutdown timeout       |

**CPU Overhead**: <0.5% on Raspberry Pi 5 (1-second poll interval)

---

## Integration Examples

### LLM Throttling Integration

```python
# code/llm_module.py
from code.monitoring.thermal_monitor import ThermalMonitor, ThermalState

class LLMModule:
    def __init__(self):
        self.thermal_monitor = ThermalMonitor()
        self.thermal_monitor.register_callback(self._on_thermal_event)
        self.thermal_monitor.start_monitoring()

    def _on_thermal_event(self, state: ThermalState):
        if state.protection_active:
            logging.critical(
                f"THERMAL PROTECTION: Pausing LLM inference "
                f"(temp: {state.current_temp:.1f}°C)"
            )
            self.pause_inference()
        else:
            logging.info(
                f"THERMAL RESUME: Resuming LLM inference "
                f"(temp: {state.current_temp:.1f}°C)"
            )
            self.resume_inference()

    def close(self):
        self.thermal_monitor.stop_monitoring()
```

### Health Check Integration

```python
# code/monitoring/resource_metrics.py
def get_health_status() -> dict:
    """Include thermal state in health check"""
    thermal_state = thermal_monitor.get_state()

    return {
        "status": "critical" if thermal_state.protection_active else "healthy",
        "temperature": thermal_state.current_temp,
        "thermal_protection_active": thermal_state.protection_active,
        "trigger_count": thermal_state.trigger_count,
        "max_temp": thermal_state.max_temp_observed
    }
```

---

## Testing Contracts

### Unit Tests

```python
def test_temperature_reading_unavailable():
    """Verify graceful fallback on non-Pi platforms"""
    monitor = ThermalMonitor()
    temp = monitor.get_temperature()
    assert temp == -1.0 or temp > 0  # Valid on both platforms

def test_hysteresis_logic():
    """Verify Schmitt trigger prevents oscillation"""
    monitor = ThermalMonitor(
        trigger_threshold=85.0,
        resume_threshold=80.0,
        simulation_mode=True
    )

    # Start below threshold
    assert not monitor.check_thermal_protection()

    # Trigger protection
    monitor._simulate_temperature(85.0)
    assert monitor.check_thermal_protection()

    # Stay protected in hysteresis band
    monitor._simulate_temperature(82.0)
    assert monitor.check_thermal_protection()

    # Resume below lower threshold
    monitor._simulate_temperature(79.0)
    assert not monitor.check_thermal_protection()

def test_callback_notification():
    """Verify callbacks called only on state changes"""
    monitor = ThermalMonitor(simulation_mode=True)

    callback_count = 0
    def callback(state: ThermalState):
        nonlocal callback_count
        callback_count += 1

    monitor.register_callback(callback)
    monitor.start_monitoring()

    # No callbacks yet
    assert callback_count == 0

    # Trigger protection
    monitor._simulate_temperature(85.0)
    time.sleep(1.5)  # Wait for polling
    assert callback_count == 1

    # No callback for stable state
    monitor._simulate_temperature(85.5)
    time.sleep(1.5)
    assert callback_count == 1  # Still 1

    # Callback on resume
    monitor._simulate_temperature(79.0)
    time.sleep(1.5)
    assert callback_count == 2
```

### Integration Tests

```python
def test_thermal_protection_integration():
    """Verify thermal protection triggers LLM throttling"""
    llm = LLMModule()
    thermal_monitor = llm.thermal_monitor

    # Start inference
    llm.start_inference()
    assert llm.is_inference_active()

    # Simulate high temperature
    thermal_monitor._simulate_temperature(85.0)
    time.sleep(1.5)  # Wait for callback

    # Verify inference paused
    assert not llm.is_inference_active()

    # Simulate temperature drop
    thermal_monitor._simulate_temperature(79.0)
    time.sleep(1.5)

    # Verify inference resumed
    assert llm.is_inference_active()
```

---

## Compliance Checklist

✅ **Offline-First**: No external dependencies, all data local  
✅ **Reliability**: Graceful fallback on unsupported platforms  
✅ **Observability**: Structured logging (CRITICAL/INFO), state exposure  
✅ **Security**: No sudo required, input validation on thresholds  
✅ **Maintainability**: Single responsibility (temperature monitoring only)  
✅ **Testability**: Simulation mode for testing without hardware

---

**Version**: 1.0  
**Last Updated**: October 19, 2025
