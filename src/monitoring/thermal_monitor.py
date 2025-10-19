"""
Thermal monitoring for Raspberry Pi 5 hardware protection.

This module provides CPU temperature monitoring with configurable thresholds
and automatic workload reduction to prevent thermal throttling and hardware damage.

Key Features:
    - Real-time temperature monitoring from /sys/class/thermal
    - Hysteresis-based protection (85°C trigger, 80°C resume)
    - Callback system for thermal events
    - Background monitoring thread using ManagedThread
    - Platform detection (graceful degradation on non-Pi systems)
    - Simulation mode for testing without hardware

Usage:
    >>> from src.monitoring.thermal_monitor import ThermalMonitor
    >>> 
    >>> def on_thermal_event(protection_active, temperature):
    ...     if protection_active:
    ...         print(f"THERMAL PROTECTION: {temperature}°C - reducing workload")
    ...     else:
    ...         print(f"THERMAL RESUME: {temperature}°C - resuming normal operation")
    >>> 
    >>> monitor = ThermalMonitor(trigger_threshold=85, resume_threshold=80)
    >>> monitor.register_callback(on_thermal_event)
    >>> monitor.start_monitoring()
    >>> 
    >>> # Later...
    >>> state = monitor.get_state()
    >>> print(f"Temperature: {state.current_temp}°C")
    >>> monitor.stop_monitoring()

Configuration:
    - THERMAL_TRIGGER_THRESHOLD: Temperature to trigger protection (default: 85°C)
    - THERMAL_RESUME_THRESHOLD: Temperature to resume normal operation (default: 80°C)
    - THERMAL_CHECK_INTERVAL: Seconds between temperature checks (default: 5)

Phase 2 User Story 2 (P2): Hardware Protection
Tasks: T037-T047
"""

import os
import time
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Optional
from src.utils.lifecycle import ManagedThread


# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class ThermalState:
    """
    Represents the current thermal state with hysteresis logic.
    
    Hysteresis prevents rapid oscillation:
    - Protection triggers when temp >= trigger_threshold (85°C)
    - Protection resumes when temp < resume_threshold (80°C)
    - 5°C gap prevents flickering between states
    
    Attributes:
        current_temp: Current CPU temperature in Celsius (-1 if unavailable)
        protection_active: Whether thermal protection is currently active
        last_trigger_time: Timestamp when protection was last triggered
        last_resume_time: Timestamp when protection was last resumed
        trigger_threshold: Temperature threshold to trigger protection (default: 85°C)
        resume_threshold: Temperature threshold to resume normal operation (default: 80°C)
    """
    current_temp: float = -1.0
    protection_active: bool = False
    last_trigger_time: Optional[datetime] = None
    last_resume_time: Optional[datetime] = None
    trigger_threshold: float = 85.0
    resume_threshold: float = 80.0
    
    def should_trigger_protection(self) -> bool:
        """
        Check if protection should be triggered based on current temperature.
        
        Protection triggers when:
        - Temperature >= trigger_threshold (85°C) AND
        - Protection is not already active
        
        Returns:
            True if protection should be triggered, False otherwise
        """
        if self.protection_active:
            return False  # Already active
        
        return self.current_temp >= self.trigger_threshold
    
    def should_resume_normal(self) -> bool:
        """
        Check if normal operation should resume based on current temperature.
        
        Normal operation resumes when:
        - Temperature < resume_threshold (80°C) AND
        - Protection is currently active
        
        Returns:
            True if normal operation should resume, False otherwise
        """
        if not self.protection_active:
            return False  # Already normal
        
        return self.current_temp < self.resume_threshold
    
    def update_temperature(self, temp: float) -> None:
        """
        Update current temperature and handle state transitions.
        
        Args:
            temp: New temperature reading in Celsius
        """
        self.current_temp = temp
        
        if self.should_trigger_protection():
            self.protection_active = True
            self.last_trigger_time = datetime.now()
            logger.warning(
                f"THERMAL PROTECTION TRIGGERED: {temp:.1f}°C "
                f"(threshold: {self.trigger_threshold}°C)"
            )
        
        elif self.should_resume_normal():
            self.protection_active = False
            self.last_resume_time = datetime.now()
            logger.info(
                f"THERMAL PROTECTION RESUMED: {temp:.1f}°C "
                f"(threshold: {self.resume_threshold}°C)"
            )


class ThermalMonitor:
    """
    Monitors CPU temperature and triggers thermal protection callbacks.
    
    This class provides real-time temperature monitoring with configurable
    thresholds and callback notifications for thermal events. It uses a
    background thread (ManagedThread) for continuous monitoring.
    
    Attributes:
        state: Current thermal state
        callbacks: List of registered callbacks
        check_interval: Seconds between temperature checks (default: 5)
        simulate_mode: If True, use simulated temperature instead of hardware
        _simulated_temp: Simulated temperature for testing
        _monitor_thread: Background monitoring thread
    
    Example:
        >>> monitor = ThermalMonitor(trigger_threshold=85, resume_threshold=80)
        >>> monitor.register_callback(lambda active, temp: print(f"Thermal: {temp}°C"))
        >>> monitor.start_monitoring()
        >>> # ... do work ...
        >>> monitor.stop_monitoring()
    """
    
    THERMAL_PATH = "/sys/class/thermal/thermal_zone0/temp"
    
    def __init__(
        self,
        trigger_threshold: float = 85.0,
        resume_threshold: float = 80.0,
        check_interval: float = 5.0
    ):
        """
        Initialize thermal monitor with configurable thresholds.
        
        Args:
            trigger_threshold: Temperature to trigger protection (default: 85°C)
            resume_threshold: Temperature to resume normal operation (default: 80°C)
            check_interval: Seconds between temperature checks (default: 5)
        
        Raises:
            ValueError: If resume_threshold >= trigger_threshold (no hysteresis gap)
        """
        if resume_threshold >= trigger_threshold:
            raise ValueError(
                f"Resume threshold ({resume_threshold}°C) must be less than "
                f"trigger threshold ({trigger_threshold}°C) for hysteresis"
            )
        
        self.state = ThermalState(
            trigger_threshold=trigger_threshold,
            resume_threshold=resume_threshold
        )
        self.callbacks: List[Callable[[bool, float], None]] = []
        self.check_interval = check_interval
        self.simulate_mode = False
        self._simulated_temp: float = 25.0  # Default simulated temp
        self._monitor_thread: Optional[ManagedThread] = None
        
        logger.info(
            f"ThermalMonitor initialized: trigger={trigger_threshold}°C, "
            f"resume={resume_threshold}°C, interval={check_interval}s"
        )
    
    def get_temperature(self) -> float:
        """
        Read current CPU temperature from system.
        
        Reads from /sys/class/thermal/thermal_zone0/temp on Raspberry Pi.
        Returns -1 on non-Pi systems or if reading fails.
        
        In simulate_mode, returns the simulated temperature instead.
        
        Returns:
            Temperature in Celsius, or -1 if unavailable
        """
        if self.simulate_mode:
            return self._simulated_temp
        
        # Platform detection - check if thermal path exists
        if not os.path.exists(self.THERMAL_PATH):
            logger.debug("Thermal path not found - not running on Raspberry Pi")
            return -1.0
        
        try:
            with open(self.THERMAL_PATH, 'r') as f:
                # Temperature is in millidegrees Celsius
                temp_millidegrees = int(f.read().strip())
                temp_celsius = temp_millidegrees / 1000.0
                return temp_celsius
        
        except (IOError, ValueError) as e:
            logger.error(f"Failed to read temperature: {e}")
            return -1.0
    
    def check_thermal_protection(self) -> None:
        """
        Check temperature and update thermal state.
        
        This method:
        1. Reads current temperature
        2. Updates thermal state (triggers hysteresis logic)
        3. Notifies callbacks if state changed
        
        Called periodically by the background monitoring thread.
        """
        previous_state = self.state.protection_active
        
        # Read and update temperature
        temp = self.get_temperature()
        if temp == -1.0:
            # Temperature unavailable - no action
            return
        
        self.state.update_temperature(temp)
        
        # Notify callbacks if state changed
        if self.state.protection_active != previous_state:
            self._notify_callbacks()
    
    def register_callback(self, callback: Callable[[bool, float], None]) -> None:
        """
        Register a callback for thermal events.
        
        Callbacks are invoked when thermal protection state changes:
        - callback(True, temp) when protection activates
        - callback(False, temp) when protection resumes
        
        Args:
            callback: Function accepting (protection_active: bool, temperature: float)
        
        Example:
            >>> def on_thermal(active, temp):
            ...     if active:
            ...         print(f"Reduce workload at {temp}°C")
            ...     else:
            ...         print(f"Resume normal operation at {temp}°C")
            >>> monitor.register_callback(on_thermal)
        """
        if callback not in self.callbacks:
            self.callbacks.append(callback)
            callback_name = getattr(callback, '__name__', repr(callback))
            logger.debug(f"Registered thermal callback: {callback_name}")
    
    def _notify_callbacks(self) -> None:
        """
        Notify all registered callbacks of thermal state change.
        
        Invokes each callback with current protection state and temperature.
        Logs but doesn't raise callback exceptions to prevent monitoring failure.
        """
        for callback in self.callbacks:
            try:
                callback(self.state.protection_active, self.state.current_temp)
            except Exception as e:
                callback_name = getattr(callback, '__name__', repr(callback))
                logger.error(
                    f"Thermal callback {callback_name} failed: {e}",
                    exc_info=True
                )
    
    def start_monitoring(self) -> None:
        """
        Start background temperature monitoring thread.
        
        Creates a ManagedThread that checks temperature every check_interval seconds.
        Does nothing if monitoring is already active.
        
        Raises:
            RuntimeError: If thread fails to start
        """
        if self._monitor_thread is not None:
            logger.warning("Thermal monitoring already active")
            return
        
        logger.info("Starting thermal monitoring thread")
        self._monitor_thread = ManagedThread(
            target=self._monitoring_loop,
            name="ThermalMonitor",
            daemon=True
        )
        self._monitor_thread.start()
    
    def stop_monitoring(self) -> None:
        """
        Stop background temperature monitoring thread.
        
        Signals the monitoring thread to stop and waits for it to complete.
        Does nothing if monitoring is not active.
        """
        if self._monitor_thread is None:
            logger.warning("Thermal monitoring not active")
            return
        
        logger.info("Stopping thermal monitoring thread")
        self._monitor_thread.stop()
        self._monitor_thread.join(timeout=self.check_interval + 2.0)
        self._monitor_thread = None
    
    def _monitoring_loop(self, managed_thread: ManagedThread) -> None:
        """
        Background monitoring loop (runs in ManagedThread).
        
        Continuously checks temperature at check_interval until stopped.
        
        Args:
            managed_thread: The ManagedThread instance running this loop
        """
        logger.info("Thermal monitoring loop started")
        
        while not managed_thread.should_stop():
            try:
                self.check_thermal_protection()
            except Exception as e:
                logger.error(f"Error in thermal monitoring loop: {e}", exc_info=True)
            
            # Sleep in small intervals to allow quick shutdown
            elapsed = 0.0
            while elapsed < self.check_interval and not managed_thread.should_stop():
                time.sleep(0.5)
                elapsed += 0.5
        
        logger.info("Thermal monitoring loop stopped")
    
    def get_state(self) -> ThermalState:
        """
        Get current thermal state.
        
        Returns:
            Copy of current thermal state
        """
        return self.state
    
    def set_thresholds(
        self,
        trigger_threshold: Optional[float] = None,
        resume_threshold: Optional[float] = None
    ) -> None:
        """
        Update thermal thresholds dynamically.
        
        Args:
            trigger_threshold: New trigger threshold in °C (optional)
            resume_threshold: New resume threshold in °C (optional)
        
        Raises:
            ValueError: If new thresholds violate hysteresis constraint
        """
        new_trigger = trigger_threshold if trigger_threshold is not None else self.state.trigger_threshold
        new_resume = resume_threshold if resume_threshold is not None else self.state.resume_threshold
        
        if new_resume >= new_trigger:
            raise ValueError(
                f"Resume threshold ({new_resume}°C) must be less than "
                f"trigger threshold ({new_trigger}°C) for hysteresis"
            )
        
        self.state.trigger_threshold = new_trigger
        self.state.resume_threshold = new_resume
        
        logger.info(
            f"Thermal thresholds updated: trigger={new_trigger}°C, "
            f"resume={new_resume}°C"
        )
    
    def _simulate_temperature(self, temp: float) -> None:
        """
        Set simulated temperature for testing.
        
        Automatically enables simulate_mode if not already enabled.
        
        Args:
            temp: Simulated temperature in Celsius
        
        Example:
            >>> monitor = ThermalMonitor()
            >>> monitor._simulate_temperature(90.0)  # Trigger protection
            >>> monitor.check_thermal_protection()
            >>> assert monitor.get_state().protection_active
        """
        self.simulate_mode = True
        self._simulated_temp = temp
        logger.debug(f"Simulated temperature set to {temp}°C")
