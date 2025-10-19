"""
Integration tests for thermal protection workflow.

Tests the complete thermal monitoring system integrated with the LLM inference pipeline:
- Thermal protection triggers when temperature exceeds threshold
- LLM inference is paused during thermal protection
- Inference resumes after temperature drops below resume threshold
- Health check reflects thermal state

Phase 2 User Story 2 (P2): Hardware Protection
Tasks: T060-T062
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from src.llm_module import LLM


class TestThermalProtectionWorkflow:
    """Test complete thermal protection workflow from trigger to resume."""
    
    def test_thermal_protection_triggers_at_threshold(self):
        """Test thermal protection activates at 85°C threshold."""
        # Initialize LLM with thermal monitoring
        llm = LLM("ollama", "test-model")
        llm.enable_thermal_monitoring(trigger_threshold=85.0, resume_threshold=80.0, check_interval=0.2)
        
        # Get thermal monitor for simulation
        thermal_monitor = llm._thermal_monitor
        assert thermal_monitor is not None
        
        # Simulate normal temperature
        thermal_monitor._simulate_temperature(75.0)
        time.sleep(0.3)  # Wait for monitoring thread to check
        
        # Verify no protection
        assert not llm.is_inference_paused()
        assert not thermal_monitor.get_state().protection_active
        
        # Simulate temperature exceeding threshold
        thermal_monitor._simulate_temperature(86.0)
        time.sleep(0.3)  # Wait for monitoring thread to detect
        
        # Verify protection triggered
        assert llm.is_inference_paused()
        assert thermal_monitor.get_state().protection_active
        
        # Cleanup
        llm.disable_thermal_monitoring()
    
    def test_thermal_protection_resumes_at_threshold(self):
        """Test thermal protection deactivates at 80°C resume threshold."""
        # Initialize LLM with thermal monitoring
        llm = LLM("ollama", "test-model")
        llm.enable_thermal_monitoring(trigger_threshold=85.0, resume_threshold=80.0, check_interval=0.2)
        
        # Get thermal monitor
        thermal_monitor = llm._thermal_monitor
        
        # Trigger protection
        thermal_monitor._simulate_temperature(90.0)
        time.sleep(0.3)
        assert llm.is_inference_paused()
        
        # Temperature still above resume threshold - should stay paused
        thermal_monitor._simulate_temperature(82.0)
        time.sleep(0.3)
        assert llm.is_inference_paused()
        
        # Temperature drops below resume threshold
        thermal_monitor._simulate_temperature(78.0)
        time.sleep(0.3)
        
        # Verify protection resumed
        assert not llm.is_inference_paused()
        assert not thermal_monitor.get_state().protection_active
        
        # Cleanup
        llm.disable_thermal_monitoring()
    
    def test_hysteresis_prevents_rapid_oscillation(self):
        """Test hysteresis gap prevents rapid state changes."""
        llm = LLM("ollama", "test-model")
        llm.enable_thermal_monitoring(trigger_threshold=85.0, resume_threshold=80.0, check_interval=0.2)
        
        thermal_monitor = llm._thermal_monitor
        callback = Mock()
        thermal_monitor.register_callback(callback)
        
        # Start at normal temperature
        thermal_monitor._simulate_temperature(75.0)
        time.sleep(0.3)
        callback.reset_mock()
        
        # Temperature rises to trigger threshold
        thermal_monitor._simulate_temperature(85.0)
        time.sleep(0.3)
        
        # Should trigger once
        assert callback.call_count == 1
        assert callback.call_args[0][0] == True  # protection_active=True
        callback.reset_mock()
        
        # Temperature oscillates in hysteresis gap (80-85°C)
        for temp in [83, 84, 82, 83, 81]:
            thermal_monitor._simulate_temperature(temp)
            time.sleep(0.3)
        
        # Should NOT trigger callbacks (hysteresis gap)
        assert callback.call_count == 0
        assert llm.is_inference_paused()  # Still paused
        
        # Temperature drops below resume threshold
        thermal_monitor._simulate_temperature(79.0)
        time.sleep(0.3)
        
        # Should resume once
        assert callback.call_count == 1
        assert callback.call_args[0][0] == False  # protection_active=False
        
        # Cleanup
        llm.disable_thermal_monitoring()


class TestLLMThrottling:
    """Test LLM inference throttling during thermal protection."""
    
    def test_inference_blocked_during_thermal_protection(self):
        """Test LLM inference is blocked when thermal protection is active."""
        llm = LLM("ollama", "test-model")
        llm.enable_thermal_monitoring(trigger_threshold=85.0, resume_threshold=80.0, check_interval=0.2)
        
        # Trigger thermal protection
        llm.pause_inference()
        
        # Attempt to generate text - should be blocked
        # Mock the lazy initialization to avoid actual LLM connection
        llm._client_initialized = True
        llm._ollama_connection_ok = True
        llm.ollama_session = Mock()
        
        # Generate should return empty generator due to thermal pause
        generator = llm.generate("test prompt")
        
        # Verify generator returns nothing (paused)
        tokens = list(generator)
        assert len(tokens) == 0
        
        # Cleanup
        llm.disable_thermal_monitoring()
    
    def test_inference_allowed_after_thermal_resume(self):
        """Test LLM inference works after thermal protection resumes."""
        llm = LLM("ollama", "test-model")
        
        # Start with paused inference
        llm.pause_inference()
        assert llm.is_inference_paused()
        
        # Resume inference
        llm.resume_inference()
        assert not llm.is_inference_paused()
        
        # Verify inference is no longer blocked
        # (Actual generation would require mocking the full LLM stack)
    
    def test_pause_resume_idempotent(self):
        """Test pause and resume methods are idempotent."""
        llm = LLM("ollama", "test-model")
        
        # Multiple pauses should be safe
        llm.pause_inference()
        llm.pause_inference()
        llm.pause_inference()
        assert llm.is_inference_paused()
        
        # Multiple resumes should be safe
        llm.resume_inference()
        llm.resume_inference()
        llm.resume_inference()
        assert not llm.is_inference_paused()
    
    def test_thermal_state_tracking(self):
        """Test thermal state is accurately tracked."""
        llm = LLM("ollama", "test-model")
        
        # Before enabling thermal monitoring
        assert llm.get_thermal_state() is None
        
        # Enable thermal monitoring
        llm.enable_thermal_monitoring(trigger_threshold=85.0, resume_threshold=80.0)
        
        state = llm.get_thermal_state()
        assert state is not None
        assert "temperature" in state
        assert "protection_active" in state
        assert "inference_paused" in state
        assert state["trigger_threshold"] == 85.0
        assert state["resume_threshold"] == 80.0
        
        # Cleanup
        llm.disable_thermal_monitoring()


class TestThermalIntegrationScenarios:
    """End-to-end integration scenarios for thermal protection."""
    
    def test_complete_thermal_cycle(self):
        """Test complete thermal protection cycle from normal → protected → resumed."""
        llm = LLM("ollama", "test-model")
        llm.enable_thermal_monitoring(trigger_threshold=85.0, resume_threshold=80.0, check_interval=0.2)
        
        thermal_monitor = llm._thermal_monitor
        events = []
        
        def track_event(active, temp):
            events.append({"active": active, "temp": temp})
        
        thermal_monitor.register_callback(track_event)
        
        # Phase 1: Normal operation (70°C)
        thermal_monitor._simulate_temperature(70.0)
        time.sleep(0.3)
        assert not llm.is_inference_paused()
        assert len(events) == 0  # No state change
        
        # Phase 2: Temperature rising (82°C, still below trigger)
        thermal_monitor._simulate_temperature(82.0)
        time.sleep(0.3)
        assert not llm.is_inference_paused()
        assert len(events) == 0  # No state change
        
        # Phase 3: Thermal protection triggered (87°C)
        thermal_monitor._simulate_temperature(87.0)
        time.sleep(0.3)
        assert llm.is_inference_paused()
        assert len(events) == 1
        assert events[0]["active"] == True
        assert events[0]["temp"] == 87.0
        
        # Phase 4: Cooling down but still in hysteresis gap (83°C)
        thermal_monitor._simulate_temperature(83.0)
        time.sleep(0.3)
        assert llm.is_inference_paused()  # Still paused
        assert len(events) == 1  # No new event
        
        # Phase 5: Resumed (78°C, below resume threshold)
        thermal_monitor._simulate_temperature(78.0)
        time.sleep(0.3)
        assert not llm.is_inference_paused()
        assert len(events) == 2
        assert events[1]["active"] == False
        assert events[1]["temp"] == 78.0
        
        # Cleanup
        llm.disable_thermal_monitoring()
    
    def test_thermal_monitoring_can_be_disabled(self):
        """Test thermal monitoring can be safely disabled."""
        llm = LLM("ollama", "test-model")
        
        # Enable monitoring
        assert llm.enable_thermal_monitoring()
        assert llm._thermal_monitor is not None
        
        # Disable monitoring
        llm.disable_thermal_monitoring()
        assert llm._thermal_monitor is None
        assert not llm.is_inference_paused()
        
        # Should be safe to disable again
        llm.disable_thermal_monitoring()
    
    def test_thermal_monitoring_with_custom_thresholds(self):
        """Test thermal monitoring with custom temperature thresholds."""
        llm = LLM("ollama", "test-model")
        llm.enable_thermal_monitoring(trigger_threshold=90.0, resume_threshold=85.0, check_interval=0.2)
        
        thermal_monitor = llm._thermal_monitor
        
        # Temperature at 87°C - should NOT trigger (threshold is 90°C)
        thermal_monitor._simulate_temperature(87.0)
        time.sleep(0.3)
        assert not llm.is_inference_paused()
        
        # Temperature at 91°C - should trigger
        thermal_monitor._simulate_temperature(91.0)
        time.sleep(0.3)
        assert llm.is_inference_paused()
        
        # Temperature at 86°C - should NOT resume (threshold is 85°C)
        thermal_monitor._simulate_temperature(86.0)
        time.sleep(0.3)
        assert llm.is_inference_paused()
        
        # Temperature at 84°C - should resume
        thermal_monitor._simulate_temperature(84.0)
        time.sleep(0.3)
        assert not llm.is_inference_paused()
        
        # Cleanup
        llm.disable_thermal_monitoring()
    
    def test_thermal_protection_timestamp_tracking(self):
        """Test thermal events are timestamped correctly."""
        llm = LLM("ollama", "test-model")
        llm.enable_thermal_monitoring(trigger_threshold=85.0, resume_threshold=80.0, check_interval=0.2)
        
        thermal_monitor = llm._thermal_monitor
        
        # Trigger protection
        thermal_monitor._simulate_temperature(90.0)
        time.sleep(0.3)
        
        state = llm.get_thermal_state()
        assert state["last_trigger_time"] is not None
        assert state["last_resume_time"] is None
        trigger_time = state["last_trigger_time"]
        
        # Resume protection
        time.sleep(0.1)  # Ensure time difference
        thermal_monitor._simulate_temperature(75.0)
        time.sleep(0.3)
        
        state = llm.get_thermal_state()
        assert state["last_trigger_time"] == trigger_time  # Same trigger time
        assert state["last_resume_time"] is not None
        assert state["last_resume_time"] > trigger_time  # Resume after trigger
        
        # Cleanup
        llm.disable_thermal_monitoring()


class TestErrorHandling:
    """Test error handling in thermal integration."""
    
    def test_thermal_monitoring_unavailable(self):
        """Test graceful handling when ThermalMonitor is unavailable."""
        with patch('src.llm_module.THERMAL_MONITOR_AVAILABLE', False):
            llm = LLM("ollama", "test-model")
            
            # Should return False but not crash
            result = llm.enable_thermal_monitoring()
            assert result == False
            
            # Methods should be safe to call
            llm.pause_inference()
            llm.resume_inference()
            assert llm.get_thermal_state() is None
    
    def test_thermal_monitoring_already_enabled(self):
        """Test enabling thermal monitoring when already enabled."""
        llm = LLM("ollama", "test-model")
        
        # Enable twice
        result1 = llm.enable_thermal_monitoring()
        result2 = llm.enable_thermal_monitoring()
        
        assert result1 == True
        assert result2 == True  # Should succeed
        
        # Cleanup
        llm.disable_thermal_monitoring()
    
    def test_callback_exception_doesnt_crash_monitoring(self):
        """Test monitoring continues if callback raises exception."""
        llm = LLM("ollama", "test-model")
        llm.enable_thermal_monitoring(trigger_threshold=85.0, resume_threshold=80.0, check_interval=0.2)
        
        thermal_monitor = llm._thermal_monitor
        
        # Add callback that will raise exception
        def bad_callback(active, temp):
            raise RuntimeError("Callback failed!")
        
        thermal_monitor.register_callback(bad_callback)
        
        # Trigger protection - should not crash despite callback exception
        thermal_monitor._simulate_temperature(90.0)
        time.sleep(0.3)
        
        # Verify protection still worked
        assert llm.is_inference_paused()
        
        # Cleanup
        llm.disable_thermal_monitoring()
