"""
Exponential backoff utility for WebSocket reconnection.

Implements exponential backoff with configurable min/max delays and maximum
retry attempts per Phase 2 P3 specification (T086).

Key Features:
- Exponential delay calculation: delay = min(initial * 2^attempt, max_delay)
- Configurable initial delay (default: 1s)
- Configurable maximum delay (default: 30s)
- Configurable maximum attempts (default: 10)
- Reset mechanism after successful connection
- Attempt tracking for failure detection
"""

import time
from typing import Optional


class ExponentialBackoff:
    """
    Implements exponential backoff for retry operations.
    
    Calculates increasing delays between retry attempts using exponential
    growth, capped at a maximum delay. Tracks attempts and provides
    failure detection.
    
    Usage:
        backoff = ExponentialBackoff(initial_delay=1.0, max_delay=30.0, max_attempts=10)
        
        while not backoff.should_give_up():
            try:
                connect()
                backoff.reset()  # Success - reset counter
                break
            except ConnectionError:
                delay = backoff.next_delay()
                time.sleep(delay)
    
    Delay sequence (initial=1s, max=30s):
        Attempt 1: 1s
        Attempt 2: 2s
        Attempt 3: 4s
        Attempt 4: 8s
        Attempt 5: 16s
        Attempt 6: 30s (capped)
        Attempt 7: 30s (capped)
        ...
        Attempt 10: 30s (last attempt)
    """
    
    def __init__(
        self,
        initial_delay: float = 1.0,
        max_delay: float = 30.0,
        max_attempts: Optional[int] = 10
    ):
        """
        Initialize exponential backoff calculator.
        
        Args:
            initial_delay: Starting delay in seconds (default: 1.0)
            max_delay: Maximum delay cap in seconds (default: 30.0)
            max_attempts: Maximum retry attempts (None = unlimited, default: 10)
        
        Raises:
            ValueError: If initial_delay <= 0 or max_delay < initial_delay
        """
        if initial_delay <= 0:
            raise ValueError("initial_delay must be positive")
        if max_delay < initial_delay:
            raise ValueError("max_delay must be >= initial_delay")
        
        self._initial_delay = initial_delay
        self._max_delay = max_delay
        self._max_attempts = max_attempts
        self._attempt = 0
    
    @property
    def attempt(self) -> int:
        """Current attempt number (0-indexed)."""
        return self._attempt
    
    @property
    def initial_delay(self) -> float:
        """Initial delay in seconds."""
        return self._initial_delay
    
    @property
    def max_delay(self) -> float:
        """Maximum delay cap in seconds."""
        return self._max_delay
    
    @property
    def max_attempts(self) -> Optional[int]:
        """Maximum retry attempts (None = unlimited)."""
        return self._max_attempts
    
    def next_delay(self) -> float:
        """
        Calculate and return the next delay, incrementing the attempt counter.
        
        Returns:
            Delay in seconds for the current attempt
        
        Calculation:
            delay = min(initial_delay * 2^attempt, max_delay)
        
        Example:
            backoff = ExponentialBackoff(initial_delay=1.0, max_delay=30.0)
            backoff.next_delay()  # Returns 1.0 (2^0 = 1)
            backoff.next_delay()  # Returns 2.0 (2^1 = 2)
            backoff.next_delay()  # Returns 4.0 (2^2 = 4)
            backoff.next_delay()  # Returns 8.0 (2^3 = 8)
            backoff.next_delay()  # Returns 16.0 (2^4 = 16)
            backoff.next_delay()  # Returns 30.0 (2^5 = 32, capped at 30)
        """
        # Calculate exponential delay: initial * 2^attempt
        delay = self._initial_delay * (2 ** self._attempt)
        
        # Cap at maximum delay
        delay = min(delay, self._max_delay)
        
        # Increment attempt counter
        self._attempt += 1
        
        return delay
    
    def should_give_up(self) -> bool:
        """
        Check if maximum retry attempts have been reached.
        
        Returns:
            True if max_attempts exceeded, False otherwise (or if unlimited)
        
        Example:
            backoff = ExponentialBackoff(max_attempts=3)
            backoff.next_delay()  # Attempt 1
            backoff.next_delay()  # Attempt 2
            backoff.next_delay()  # Attempt 3
            backoff.should_give_up()  # Returns True (3 >= 3)
        """
        if self._max_attempts is None:
            return False
        return self._attempt >= self._max_attempts
    
    def reset(self):
        """
        Reset attempt counter to zero after successful operation.
        
        Call this after a successful connection/operation to reset
        the backoff state for future failures.
        
        Example:
            backoff = ExponentialBackoff()
            backoff.next_delay()  # Attempt 1
            backoff.next_delay()  # Attempt 2
            # Connection succeeds
            backoff.reset()
            backoff.next_delay()  # Attempt 1 again (reset)
        """
        self._attempt = 0
    
    def get_total_wait_time(self) -> float:
        """
        Calculate total wait time if all attempts are used.
        
        Useful for estimating maximum retry duration.
        
        Returns:
            Total seconds spent waiting across all attempts
        
        Example:
            backoff = ExponentialBackoff(initial_delay=1.0, max_delay=30.0, max_attempts=5)
            backoff.get_total_wait_time()  # Returns 31.0 (1+2+4+8+16)
        """
        if self._max_attempts is None:
            # Cannot calculate for unlimited attempts
            raise ValueError("Cannot calculate total wait time for unlimited attempts")
        
        total = 0.0
        for i in range(self._max_attempts):
            delay = min(self._initial_delay * (2 ** i), self._max_delay)
            total += delay
        
        return total
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"ExponentialBackoff("
            f"initial={self._initial_delay}s, "
            f"max={self._max_delay}s, "
            f"max_attempts={self._max_attempts}, "
            f"current_attempt={self._attempt})"
        )
