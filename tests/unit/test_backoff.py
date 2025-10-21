"""
Unit tests for exponential backoff utility.

Tests the ExponentialBackoff class used for WebSocket reconnection retry logic.
Validates delay calculations, attempt tracking, and reset behavior.

Phase 2 P3 Tasks: T095
"""

import pytest
from src.utils.backoff import ExponentialBackoff


class TestExponentialBackoffInitialization:
    """Test ExponentialBackoff initialization and validation."""
    
    def test_default_initialization(self):
        """Test default parameter values."""
        backoff = ExponentialBackoff()
        
        assert backoff.initial_delay == 1.0
        assert backoff.max_delay == 30.0
        assert backoff.max_attempts == 10
        assert backoff.attempt == 0
    
    def test_custom_initialization(self):
        """Test initialization with custom parameters."""
        backoff = ExponentialBackoff(
            initial_delay=2.0,
            max_delay=60.0,
            max_attempts=5
        )
        
        assert backoff.initial_delay == 2.0
        assert backoff.max_delay == 60.0
        assert backoff.max_attempts == 5
        assert backoff.attempt == 0
    
    def test_unlimited_attempts(self):
        """Test initialization with unlimited attempts."""
        backoff = ExponentialBackoff(max_attempts=None)
        
        assert backoff.max_attempts is None
        assert not backoff.should_give_up()
    
    def test_invalid_initial_delay(self):
        """Test that initial_delay must be positive."""
        with pytest.raises(ValueError, match="initial_delay must be positive"):
            ExponentialBackoff(initial_delay=0)
        
        with pytest.raises(ValueError, match="initial_delay must be positive"):
            ExponentialBackoff(initial_delay=-1)
    
    def test_invalid_max_delay(self):
        """Test that max_delay must be >= initial_delay."""
        with pytest.raises(ValueError, match="max_delay must be >= initial_delay"):
            ExponentialBackoff(initial_delay=10.0, max_delay=5.0)


class TestExponentialBackoffDelayCalculation:
    """Test exponential delay calculation logic."""
    
    def test_first_delay(self):
        """Test first delay equals initial_delay."""
        backoff = ExponentialBackoff(initial_delay=1.0)
        
        delay = backoff.next_delay()
        
        assert delay == 1.0
        assert backoff.attempt == 1
    
    def test_exponential_growth(self):
        """Test delay doubles on each attempt."""
        backoff = ExponentialBackoff(initial_delay=1.0, max_delay=100.0)
        
        delays = [backoff.next_delay() for _ in range(5)]
        
        assert delays == [1.0, 2.0, 4.0, 8.0, 16.0]
        assert backoff.attempt == 5
    
    def test_max_delay_cap(self):
        """Test delay capped at max_delay."""
        backoff = ExponentialBackoff(initial_delay=1.0, max_delay=30.0)
        
        # Attempts: 1s, 2s, 4s, 8s, 16s, 32s -> 30s (capped)
        delays = [backoff.next_delay() for _ in range(6)]
        
        assert delays == [1.0, 2.0, 4.0, 8.0, 16.0, 30.0]
        assert delays[-1] == 30.0  # Capped at max
    
    def test_consistent_max_delay(self):
        """Test all subsequent delays stay at max_delay."""
        backoff = ExponentialBackoff(initial_delay=1.0, max_delay=30.0)
        
        # Get to max delay
        for _ in range(5):
            backoff.next_delay()
        
        # Next attempts should all be max_delay
        for _ in range(5):
            delay = backoff.next_delay()
            assert delay == 30.0
    
    def test_custom_initial_delay(self):
        """Test exponential growth with custom initial delay."""
        backoff = ExponentialBackoff(initial_delay=0.5, max_delay=100.0)
        
        delays = [backoff.next_delay() for _ in range(5)]
        
        assert delays == [0.5, 1.0, 2.0, 4.0, 8.0]


class TestExponentialBackoffAttemptTracking:
    """Test attempt counter and give-up logic."""
    
    def test_attempt_counter_increments(self):
        """Test attempt counter increments on each next_delay call."""
        backoff = ExponentialBackoff()
        
        assert backoff.attempt == 0
        backoff.next_delay()
        assert backoff.attempt == 1
        backoff.next_delay()
        assert backoff.attempt == 2
    
    def test_should_give_up_after_max_attempts(self):
        """Test should_give_up returns True after max_attempts."""
        backoff = ExponentialBackoff(max_attempts=3)
        
        assert not backoff.should_give_up()
        backoff.next_delay()  # Attempt 1
        assert not backoff.should_give_up()
        backoff.next_delay()  # Attempt 2
        assert not backoff.should_give_up()
        backoff.next_delay()  # Attempt 3
        assert backoff.should_give_up()
    
    def test_should_give_up_with_unlimited_attempts(self):
        """Test should_give_up always returns False with max_attempts=None."""
        backoff = ExponentialBackoff(max_attempts=None)
        
        for _ in range(100):
            assert not backoff.should_give_up()
            backoff.next_delay()
        
        assert not backoff.should_give_up()
    
    def test_attempt_property(self):
        """Test attempt property returns current attempt number."""
        backoff = ExponentialBackoff()
        
        assert backoff.attempt == 0
        
        for i in range(1, 6):
            backoff.next_delay()
            assert backoff.attempt == i


class TestExponentialBackoffReset:
    """Test reset functionality."""
    
    def test_reset_after_attempts(self):
        """Test reset clears attempt counter."""
        backoff = ExponentialBackoff()
        
        # Make some attempts
        for _ in range(5):
            backoff.next_delay()
        
        assert backoff.attempt == 5
        
        # Reset
        backoff.reset()
        
        assert backoff.attempt == 0
    
    def test_reset_restarts_delay_sequence(self):
        """Test reset causes next delay to start from initial_delay."""
        backoff = ExponentialBackoff(initial_delay=1.0)
        
        # Get to high delay
        for _ in range(5):
            backoff.next_delay()
        
        # Reset and verify delay restarts
        backoff.reset()
        delay = backoff.next_delay()
        
        assert delay == 1.0
        assert backoff.attempt == 1
    
    def test_reset_clears_give_up_state(self):
        """Test reset allows retries after giving up."""
        backoff = ExponentialBackoff(max_attempts=3)
        
        # Exhaust attempts
        for _ in range(3):
            backoff.next_delay()
        
        assert backoff.should_give_up()
        
        # Reset and verify can retry
        backoff.reset()
        
        assert not backoff.should_give_up()
        assert backoff.attempt == 0


class TestExponentialBackoffTotalWaitTime:
    """Test total wait time calculation."""
    
    def test_get_total_wait_time_simple(self):
        """Test total wait time with simple parameters."""
        backoff = ExponentialBackoff(initial_delay=1.0, max_delay=30.0, max_attempts=5)
        
        # 1 + 2 + 4 + 8 + 16 = 31
        total = backoff.get_total_wait_time()
        
        assert total == 31.0
    
    def test_get_total_wait_time_with_cap(self):
        """Test total wait time respects max_delay cap."""
        backoff = ExponentialBackoff(initial_delay=1.0, max_delay=30.0, max_attempts=10)
        
        # 1 + 2 + 4 + 8 + 16 + 30 + 30 + 30 + 30 + 30 = 181
        total = backoff.get_total_wait_time()
        
        assert total == 181.0
    
    def test_get_total_wait_time_unlimited_raises(self):
        """Test get_total_wait_time raises with unlimited attempts."""
        backoff = ExponentialBackoff(max_attempts=None)
        
        with pytest.raises(ValueError, match="Cannot calculate total wait time for unlimited attempts"):
            backoff.get_total_wait_time()
    
    def test_get_total_wait_time_custom_params(self):
        """Test total wait time with custom parameters."""
        backoff = ExponentialBackoff(initial_delay=2.0, max_delay=50.0, max_attempts=4)
        
        # 2 + 4 + 8 + 16 = 30
        total = backoff.get_total_wait_time()
        
        assert total == 30.0


class TestExponentialBackoffProperties:
    """Test read-only properties."""
    
    def test_properties_accessible(self):
        """Test all properties are accessible."""
        backoff = ExponentialBackoff(
            initial_delay=2.0,
            max_delay=60.0,
            max_attempts=5
        )
        
        assert backoff.initial_delay == 2.0
        assert backoff.max_delay == 60.0
        assert backoff.max_attempts == 5
        assert backoff.attempt == 0
    
    def test_repr_format(self):
        """Test string representation format."""
        backoff = ExponentialBackoff(initial_delay=1.0, max_delay=30.0, max_attempts=10)
        
        repr_str = repr(backoff)
        
        assert "ExponentialBackoff" in repr_str
        assert "initial=1.0s" in repr_str
        assert "max=30.0s" in repr_str
        assert "max_attempts=10" in repr_str
        assert "current_attempt=0" in repr_str
    
    def test_repr_after_attempts(self):
        """Test repr reflects current attempt after calls."""
        backoff = ExponentialBackoff()
        
        backoff.next_delay()
        backoff.next_delay()
        
        repr_str = repr(backoff)
        assert "current_attempt=2" in repr_str


class TestExponentialBackoffUseCases:
    """Test realistic usage scenarios."""
    
    def test_typical_reconnection_scenario(self):
        """Test typical WebSocket reconnection pattern."""
        backoff = ExponentialBackoff(initial_delay=1.0, max_delay=30.0, max_attempts=10)
        
        # Simulate reconnection attempts
        attempts = []
        while not backoff.should_give_up():
            delay = backoff.next_delay()
            attempts.append(delay)
        
        # Verify expected sequence
        expected = [1.0, 2.0, 4.0, 8.0, 16.0, 30.0, 30.0, 30.0, 30.0, 30.0]
        assert attempts == expected
        assert len(attempts) == 10
    
    def test_successful_reconnection_resets(self):
        """Test successful reconnection resets backoff."""
        backoff = ExponentialBackoff()
        
        # First connection attempt fails
        delay1 = backoff.next_delay()
        delay2 = backoff.next_delay()
        
        assert delay1 == 1.0
        assert delay2 == 2.0
        
        # Success - reset
        backoff.reset()
        
        # Next failure starts from beginning
        delay3 = backoff.next_delay()
        assert delay3 == 1.0
    
    def test_multiple_disconnect_cycles(self):
        """Test multiple disconnect/reconnect cycles."""
        backoff = ExponentialBackoff(max_attempts=3)
        
        # Cycle 1: Fail 2 times, then success
        backoff.next_delay()
        backoff.next_delay()
        backoff.reset()
        
        # Cycle 2: Fail 3 times, give up
        backoff.next_delay()
        backoff.next_delay()
        backoff.next_delay()
        
        assert backoff.should_give_up()
        
        # Cycle 3: Reset and retry
        backoff.reset()
        assert not backoff.should_give_up()
    
    def test_fast_recovery_for_transient_issues(self):
        """Test first retry is quick for transient network issues."""
        backoff = ExponentialBackoff(initial_delay=1.0)
        
        first_delay = backoff.next_delay()
        
        # First retry should be quick (1 second)
        assert first_delay == 1.0
        assert first_delay < 2.0  # Much faster than typical 5-10s delays


class TestExponentialBackoffEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_zero_max_attempts(self):
        """Test behavior with max_attempts=0."""
        backoff = ExponentialBackoff(max_attempts=0)
        
        # Should give up immediately
        assert backoff.should_give_up()
    
    def test_one_max_attempt(self):
        """Test behavior with max_attempts=1."""
        backoff = ExponentialBackoff(max_attempts=1)
        
        assert not backoff.should_give_up()
        backoff.next_delay()
        assert backoff.should_give_up()
    
    def test_very_large_max_delay(self):
        """Test behavior with very large max_delay."""
        backoff = ExponentialBackoff(initial_delay=1.0, max_delay=1000000.0, max_attempts=20)
        
        # Should grow exponentially without hitting cap for many attempts
        delays = [backoff.next_delay() for _ in range(10)]
        
        # Verify exponential growth: 1, 2, 4, 8, 16, 32, 64, 128, 256, 512
        expected = [2**i for i in range(10)]
        assert delays == expected
    
    def test_equal_initial_and_max_delay(self):
        """Test behavior when initial_delay == max_delay."""
        backoff = ExponentialBackoff(initial_delay=5.0, max_delay=5.0)
        
        # All delays should be 5.0
        delays = [backoff.next_delay() for _ in range(5)]
        
        assert all(d == 5.0 for d in delays)
    
    def test_fractional_delays(self):
        """Test behavior with fractional second delays."""
        backoff = ExponentialBackoff(initial_delay=0.1, max_delay=1.0)
        
        delays = [backoff.next_delay() for _ in range(5)]
        
        # 0.1, 0.2, 0.4, 0.8, 1.0 (capped)
        assert delays == [0.1, 0.2, 0.4, 0.8, 1.0]
