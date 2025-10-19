"""
Unit tests for thermal monitoring system.

Tests cover:
- Temperature reading from system
- Platform detection (non-Pi returns -1)
- Hysteresis logic (85°C trigger, 80°C resume)
- Callback notifications
- Simulation mode for testing
- Threshold configuration

Phase 2 User Story 2 (P2): Hardware Protection
Tasks: T054-T059
"""

import pytest
import time
import tempfile
import os
from unittest.mock import Mock, patch, mock_open
from src.monitoring.thermal_monitor import ThermalMonitor, ThermalState


class TestThermalState:
    """Test ThermalState dataclass and hysteresis logic."""
    
    def test_initial_state(self):
        """Test default thermal state initialization."""
        state = ThermalState()
        
        assert state.current_temp == -1.0
        assert state.protection_active == False
        assert state.last_trigger_time is None
        assert state.last_resume_time is None
        assert state.trigger_threshold == 85.0
        assert state.resume_threshold == 80.0
    
    def test_custom_thresholds(self):
        """Test thermal state with custom thresholds."""
        state = ThermalState(trigger_threshold=90.0, resume_threshold=85.0)
        
        assert state.trigger_threshold == 90.0
        assert state.resume_threshold == 85.0
    
    def test_trigger_protection(self):
        """Test protection triggers at threshold."""
        state = ThermalState(trigger_threshold=85.0, resume_threshold=80.0)
        
        # Below threshold - no trigger
        state.current_temp = 84.0
        assert state.should_trigger_protection() == False
        
        # At threshold - triggers
        state.current_temp = 85.0
        assert state.should_trigger_protection() == True
        
        # Above threshold - triggers
        state.current_temp = 90.0
        assert state.should_trigger_protection() == True
    
    def test_protection_already_active(self):
        """Test protection doesn't re-trigger when already active."""
        state = ThermalState()
        state.current_temp = 90.0
        state.protection_active = True
        
        assert state.should_trigger_protection() == False
    
    def test_resume_normal(self):
        """Test normal operation resumes below threshold."""
        state = ThermalState(trigger_threshold=85.0, resume_threshold=80.0)
        state.protection_active = True
        
        # Above resume threshold - no resume
        state.current_temp = 80.0
        assert state.should_resume_normal() == False
        
        # Below resume threshold - resumes
        state.current_temp = 79.0
        assert state.should_resume_normal() == True
        
        # Much lower - resumes
        state.current_temp = 50.0
        assert state.should_resume_normal() == True
    
    def test_resume_when_not_active(self):
        """Test resume doesn't trigger when protection not active."""
        state = ThermalState()
        state.current_temp = 70.0
        state.protection_active = False
        
        assert state.should_resume_normal() == False
    
    def test_hysteresis_gap(self):
        """Test hysteresis prevents rapid oscillation."""
        state = ThermalState(trigger_threshold=85.0, resume_threshold=80.0)
        
        # Start at 82°C - normal operation
        state.current_temp = 82.0
        assert state.protection_active == False
        assert state.should_trigger_protection() == False
        
        # Heat up to 85°C - trigger protection
        state.update_temperature(85.0)
        assert state.protection_active == True
        assert state.last_trigger_time is not None
        
        # Drop to 82°C - protection still active (hysteresis gap)
        state.update_temperature(82.0)
        assert state.protection_active == True
        assert state.should_resume_normal() == False
        
        # Drop to 79°C - resume normal operation
        state.update_temperature(79.0)
        assert state.protection_active == False
        assert state.last_resume_time is not None
        
        # Temperature back to 82°C - stays normal (hysteresis gap)
        state.update_temperature(82.0)
        assert state.protection_active == False
        assert state.should_trigger_protection() == False
    
    def test_update_temperature_timestamps(self):
        """Test temperature updates track timestamps."""
        state = ThermalState(trigger_threshold=85.0, resume_threshold=80.0)
        
        # Trigger protection
        state.update_temperature(90.0)
        assert state.last_trigger_time is not None
        trigger_time = state.last_trigger_time
        
        # Resume normal
        time.sleep(0.01)  # Ensure time difference
        state.update_temperature(75.0)
        assert state.last_resume_time is not None
        resume_time = state.last_resume_time
        
        assert resume_time > trigger_time


class TestThermalMonitor:
    """Test ThermalMonitor class functionality."""
    
    def test_initialization(self):
        """Test monitor initializes with correct defaults."""
        monitor = ThermalMonitor()
        
        assert monitor.state.trigger_threshold == 85.0
        assert monitor.state.resume_threshold == 80.0
        assert monitor.check_interval == 5.0
        assert monitor.simulate_mode == False
        assert len(monitor.callbacks) == 0
    
    def test_custom_thresholds(self):
        """Test monitor accepts custom thresholds."""
        monitor = ThermalMonitor(
            trigger_threshold=90.0,
            resume_threshold=85.0,
            check_interval=10.0
        )
        
        assert monitor.state.trigger_threshold == 90.0
        assert monitor.state.resume_threshold == 85.0
        assert monitor.check_interval == 10.0
    
    def test_invalid_thresholds(self):
        """Test monitor rejects invalid thresholds."""
        # Resume >= trigger (no hysteresis)
        with pytest.raises(ValueError, match="must be less than"):
            ThermalMonitor(trigger_threshold=85.0, resume_threshold=85.0)
        
        with pytest.raises(ValueError, match="must be less than"):
            ThermalMonitor(trigger_threshold=85.0, resume_threshold=90.0)
    
    def test_platform_detection_no_thermal_path(self):
        """Test returns -1 on non-Pi systems."""
        monitor = ThermalMonitor()
        
        # Mock thermal path doesn't exist
        with patch('os.path.exists', return_value=False):
            temp = monitor.get_temperature()
            assert temp == -1.0
    
    def test_temperature_reading_success(self):
        """Test successful temperature reading."""
        monitor = ThermalMonitor()
        
        # Mock thermal file with 45.123°C (45123 millidegrees)
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data='45123\n')):
                temp = monitor.get_temperature()
                assert temp == 45.123
    
    def test_temperature_reading_error(self):
        """Test handles read errors gracefully."""
        monitor = ThermalMonitor()
        
        # Mock thermal path exists but read fails
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', side_effect=IOError("Permission denied")):
                temp = monitor.get_temperature()
                assert temp == -1.0
    
    def test_temperature_reading_invalid_data(self):
        """Test handles invalid data gracefully."""
        monitor = ThermalMonitor()
        
        # Mock thermal file with invalid data
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data='invalid\n')):
                temp = monitor.get_temperature()
                assert temp == -1.0
    
    def test_simulation_mode(self):
        """Test simulated temperature for testing."""
        monitor = ThermalMonitor()
        
        # Set simulated temperature
        monitor._simulate_temperature(55.5)
        
        assert monitor.simulate_mode == True
        assert monitor._simulated_temp == 55.5
        assert monitor.get_temperature() == 55.5
        
        # Change simulated temperature
        monitor._simulate_temperature(75.0)
        assert monitor.get_temperature() == 75.0
    
    def test_callback_registration(self):
        """Test callback registration."""
        monitor = ThermalMonitor()
        
        callback1 = Mock()
        callback2 = Mock()
        
        monitor.register_callback(callback1)
        assert len(monitor.callbacks) == 1
        
        monitor.register_callback(callback2)
        assert len(monitor.callbacks) == 2
        
        # Duplicate registration ignored
        monitor.register_callback(callback1)
        assert len(monitor.callbacks) == 2
    
    def test_callback_notification_on_trigger(self):
        """Test callbacks invoked when protection triggers."""
        monitor = ThermalMonitor(trigger_threshold=85.0, resume_threshold=80.0)
        callback = Mock()
        monitor.register_callback(callback)
        
        # Simulate temperature rise
        monitor._simulate_temperature(90.0)
        monitor.check_thermal_protection()
        
        # Callback should be invoked with protection=True
        callback.assert_called_once_with(True, 90.0)
    
    def test_callback_notification_on_resume(self):
        """Test callbacks invoked when protection resumes."""
        monitor = ThermalMonitor(trigger_threshold=85.0, resume_threshold=80.0)
        callback = Mock()
        monitor.register_callback(callback)
        
        # Trigger protection first
        monitor._simulate_temperature(90.0)
        monitor.check_thermal_protection()
        callback.reset_mock()
        
        # Resume normal operation
        monitor._simulate_temperature(75.0)
        monitor.check_thermal_protection()
        
        # Callback should be invoked with protection=False
        callback.assert_called_once_with(False, 75.0)
    
    def test_callback_not_invoked_when_no_change(self):
        """Test callbacks not invoked when state doesn't change."""
        monitor = ThermalMonitor(trigger_threshold=85.0, resume_threshold=80.0)
        callback = Mock()
        monitor.register_callback(callback)
        
        # Normal temperature - no callback
        monitor._simulate_temperature(70.0)
        monitor.check_thermal_protection()
        callback.assert_not_called()
        
        # Still normal - no callback
        monitor._simulate_temperature(75.0)
        monitor.check_thermal_protection()
        callback.assert_not_called()
    
    def test_callback_exception_handling(self):
        """Test monitor handles callback exceptions gracefully."""
        monitor = ThermalMonitor(trigger_threshold=85.0, resume_threshold=80.0)
        
        # Register callback that raises exception
        bad_callback = Mock(side_effect=RuntimeError("Callback failed"))
        good_callback = Mock()
        
        monitor.register_callback(bad_callback)
        monitor.register_callback(good_callback)
        
        # Trigger protection - should not crash
        monitor._simulate_temperature(90.0)
        monitor.check_thermal_protection()
        
        # Both callbacks invoked (exception doesn't stop others)
        bad_callback.assert_called_once()
        good_callback.assert_called_once()
    
    def test_set_thresholds(self):
        """Test dynamic threshold configuration."""
        monitor = ThermalMonitor(trigger_threshold=85.0, resume_threshold=80.0)
        
        # Update both thresholds
        monitor.set_thresholds(trigger_threshold=90.0, resume_threshold=85.0)
        assert monitor.state.trigger_threshold == 90.0
        assert monitor.state.resume_threshold == 85.0
        
        # Update only trigger
        monitor.set_thresholds(trigger_threshold=95.0)
        assert monitor.state.trigger_threshold == 95.0
        assert monitor.state.resume_threshold == 85.0
        
        # Update only resume
        monitor.set_thresholds(resume_threshold=88.0)
        assert monitor.state.trigger_threshold == 95.0
        assert monitor.state.resume_threshold == 88.0
    
    def test_set_thresholds_invalid(self):
        """Test set_thresholds rejects invalid values."""
        monitor = ThermalMonitor(trigger_threshold=85.0, resume_threshold=80.0)
        
        # Resume >= trigger
        with pytest.raises(ValueError, match="must be less than"):
            monitor.set_thresholds(trigger_threshold=80.0, resume_threshold=85.0)
    
    def test_get_state(self):
        """Test get_state returns current state."""
        monitor = ThermalMonitor()
        
        state = monitor.get_state()
        assert isinstance(state, ThermalState)
        assert state.current_temp == -1.0
        assert state.protection_active == False
    
    def test_check_thermal_protection_with_unavailable_temp(self):
        """Test check_thermal_protection handles unavailable temperature."""
        monitor = ThermalMonitor()
        
        # Mock temperature unavailable
        with patch('os.path.exists', return_value=False):
            monitor.check_thermal_protection()
            
            # State should remain unchanged
            assert monitor.state.current_temp == -1.0
            assert monitor.state.protection_active == False
    
    def test_monitoring_thread_lifecycle(self):
        """Test start and stop monitoring."""
        monitor = ThermalMonitor(check_interval=0.5)
        monitor._simulate_temperature(70.0)
        
        # Start monitoring
        assert monitor._monitor_thread is None
        monitor.start_monitoring()
        assert monitor._monitor_thread is not None
        
        # Let it run briefly
        time.sleep(0.3)
        
        # Stop monitoring
        monitor.stop_monitoring()
        assert monitor._monitor_thread is None
    
    def test_monitoring_thread_checks_temperature(self):
        """Test monitoring thread performs periodic checks."""
        monitor = ThermalMonitor(
            trigger_threshold=85.0,
            resume_threshold=80.0,
            check_interval=0.2
        )
        callback = Mock()
        monitor.register_callback(callback)
        
        # Start with normal temperature
        monitor._simulate_temperature(70.0)
        monitor.start_monitoring()
        
        # Heat up after a moment
        time.sleep(0.1)
        monitor._simulate_temperature(90.0)
        
        # Wait for monitoring thread to detect it
        time.sleep(0.4)
        
        # Callback should have been invoked
        callback.assert_called()
        assert monitor.state.protection_active == True
        
        monitor.stop_monitoring()
    
    def test_start_monitoring_idempotent(self):
        """Test start_monitoring is idempotent."""
        monitor = ThermalMonitor()
        monitor._simulate_temperature(70.0)
        
        monitor.start_monitoring()
        thread1 = monitor._monitor_thread
        
        # Start again - should not create new thread
        monitor.start_monitoring()
        thread2 = monitor._monitor_thread
        
        assert thread1 is thread2
        
        monitor.stop_monitoring()
    
    def test_stop_monitoring_idempotent(self):
        """Test stop_monitoring is idempotent."""
        monitor = ThermalMonitor()
        monitor._simulate_temperature(70.0)
        
        # Stop without starting - should not crash
        monitor.stop_monitoring()
        
        # Start, stop, stop again
        monitor.start_monitoring()
        monitor.stop_monitoring()
        monitor.stop_monitoring()  # Should not crash


class TestThermalProtectionScenarios:
    """Integration-style tests for realistic thermal scenarios."""
    
    def test_gradual_heating_scenario(self):
        """Test thermal protection during gradual heating."""
        monitor = ThermalMonitor(trigger_threshold=85.0, resume_threshold=80.0)
        events = []
        
        def track_events(active, temp):
            events.append((active, temp))
        
        monitor.register_callback(track_events)
        
        # Gradual temperature rise
        temps = [70, 75, 80, 82, 84, 85, 87, 90]
        for temp in temps:
            monitor._simulate_temperature(temp)
            monitor.check_thermal_protection()
        
        # Should trigger at 85°C
        assert len(events) == 1
        assert events[0] == (True, 85.0)
        assert monitor.state.protection_active == True
    
    def test_cooling_down_scenario(self):
        """Test thermal resume during cooling."""
        monitor = ThermalMonitor(trigger_threshold=85.0, resume_threshold=80.0)
        events = []
        
        def track_events(active, temp):
            events.append((active, temp))
        
        monitor.register_callback(track_events)
        
        # Start in protection mode
        monitor._simulate_temperature(90.0)
        monitor.check_thermal_protection()
        events.clear()  # Clear trigger event
        
        # Gradual temperature drop
        temps = [88, 85, 82, 80, 79, 75, 70]
        for temp in temps:
            monitor._simulate_temperature(temp)
            monitor.check_thermal_protection()
        
        # Should resume at 79°C
        assert len(events) == 1
        assert events[0] == (False, 79.0)
        assert monitor.state.protection_active == False
    
    def test_oscillating_temperature_scenario(self):
        """Test hysteresis prevents rapid state changes."""
        monitor = ThermalMonitor(trigger_threshold=85.0, resume_threshold=80.0)
        events = []
        
        def track_events(active, temp):
            events.append((active, temp))
        
        monitor.register_callback(track_events)
        
        # Oscillate around trigger threshold
        temps = [82, 85, 83, 86, 84, 87, 83]
        for temp in temps:
            monitor._simulate_temperature(temp)
            monitor.check_thermal_protection()
        
        # Should trigger once at 85°C, stay active during oscillations
        assert len(events) == 1
        assert events[0] == (True, 85.0)
        
        # Cool below resume threshold
        monitor._simulate_temperature(79.0)
        monitor.check_thermal_protection()
        
        # Should resume once
        assert len(events) == 2
        assert events[1] == (False, 79.0)
        
        # Oscillate around resume threshold
        temps = [80, 81, 79, 82, 80]
        for temp in temps:
            monitor._simulate_temperature(temp)
            monitor.check_thermal_protection()
        
        # Should stay in normal mode (no re-trigger until 85°C)
        assert len(events) == 2
