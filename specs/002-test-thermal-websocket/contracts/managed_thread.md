# Contract: ManagedThread Interface

**Feature**: Phase 2 Infrastructure Improvements  
**Module**: `code/utils/lifecycle.py`  
**Priority**: P1 (CI/CD Reliability)

## Purpose

Provide thread lifecycle management with explicit stop signals, context manager support, and guaranteed cleanup for pytest compatibility.

---

## Interface Definition

```python
import threading
import logging
from typing import Optional, Callable, Any
from contextlib import contextmanager

class ManagedThread(threading.Thread):
    """
    Thread with explicit lifecycle management and stop signaling.

    Features:
    - Explicit stop() method with threading.Event signaling
    - Context manager support for automatic cleanup
    - Timeout-based join with warning on non-termination
    - should_stop() method for graceful shutdown from within thread

    Use cases:
    - Background workers in application code
    - Test fixtures requiring thread cleanup
    - Long-running tasks with graceful shutdown
    """

    def __init__(
        self,
        target: Callable,
        name: Optional[str] = None,
        daemon: bool = False,
        args: tuple = (),
        kwargs: Optional[dict] = None
    ):
        """
        Initialize managed thread.

        Args:
            target: Function to run in thread
            name: Thread name for logging (default: auto-generated)
            daemon: Whether thread is daemon (default: False)
            args: Positional arguments for target
            kwargs: Keyword arguments for target

        Behavior:
            - Creates threading.Event for stop signaling
            - Wraps target to catch exceptions
            - Initializes logger with thread name
        """
        ...

    def stop(self) -> None:
        """
        Signal thread to stop gracefully.

        Behavior:
            - Sets internal threading.Event
            - Does NOT force-kill thread (graceful only)
            - Logs INFO message with thread name
            - Safe to call multiple times (idempotent)

        Thread safety:
            - Safe to call from any thread
        """
        ...

    def should_stop(self) -> bool:
        """
        Check if thread should terminate (poll from within thread).

        Returns:
            bool: True if stop() has been called

        Usage:
            while not thread.should_stop():
                # Do work...
                time.sleep(0.1)  # Allow periodic checking

        Performance:
            - O(1) operation (Event.is_set())
            - Safe to call frequently (thousands per second)
        """
        ...

    def join(self, timeout: Optional[float] = 5.0) -> bool:
        """
        Wait for thread to terminate.

        Args:
            timeout: Maximum seconds to wait (default: 5.0)

        Returns:
            bool: True if thread stopped cleanly, False if timeout

        Behavior:
            - Calls threading.Thread.join(timeout)
            - Logs WARNING if thread still alive after timeout
            - Logs INFO if thread stopped cleanly

        Thread safety:
            - Safe to call from any thread (except self)
        """
        ...

    def __enter__(self) -> 'ManagedThread':
        """
        Context manager entry: start thread.

        Returns:
            ManagedThread: self for with statement

        Usage:
            with ManagedThread(target=worker) as thread:
                # Thread running...
                pass
            # Thread stopped automatically
        """
        ...

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[Any]
    ) -> bool:
        """
        Context manager exit: stop and join thread.

        Args:
            exc_type: Exception type if raised in with block
            exc_val: Exception value if raised
            exc_tb: Exception traceback if raised

        Returns:
            bool: False (don't suppress exceptions)

        Behavior:
            - Calls stop()
            - Calls join(timeout=5.0)
            - Returns False (propagates exceptions from with block)
        """
        ...
```

---

## Behavioral Contracts

### Thread Lifecycle

**MUST**:

- Start thread only when start() or **enter**() called explicitly
- Stop thread when stop() called OR **exit**() invoked
- Use threading.Event for stop signaling (not flags or queues)
- Join thread with configurable timeout (default 5 seconds)
- Log INFO on successful stop, WARNING on timeout

**MUST NOT**:

- Force-kill threads (no os.\_exit, sys.exit, or signal tricks)
- Auto-start thread in **init** (explicit start required)
- Block indefinitely in join (always use timeout)
- Suppress exceptions from target function

### Stop Signaling

**MUST**:

- Set threading.Event when stop() called
- Return True from should_stop() after stop() called
- Remain responsive to stop signal (<100ms check interval recommended)
- Allow target function to cleanup resources before exiting

**MUST NOT**:

- Guarantee immediate termination (graceful only)
- Interrupt blocking I/O operations forcefully
- Raise exceptions from stop() method

### Context Manager

**MUST**:

- Start thread in **enter**
- Stop thread in **exit**
- Join thread with timeout in **exit**
- Return False from **exit** (don't suppress exceptions)

**MUST NOT**:

- Swallow exceptions raised in with block
- Block indefinitely in **exit**
- Skip cleanup if exception occurred

### Exception Handling

**MUST**:

- Catch exceptions in target function wrapper
- Log exceptions with ERROR level (include thread name)
- Re-raise exceptions after logging (preserve stack trace)
- Continue cleanup even if target crashed

**MUST NOT**:

- Hide exceptions from target function
- Convert exceptions to different types
- Exit process on unhandled exception

---

## Integration Patterns

### Pattern 1: Application Worker

```python
from code.utils.lifecycle import ManagedThread
import queue
import time

class BackgroundWorker:
    """Worker with managed background thread"""

    def __init__(self):
        self.work_queue = queue.Queue()
        self.worker_thread = ManagedThread(
            target=self._worker_loop,
            name="background_worker",
            daemon=False
        )

    def start(self):
        """Start worker thread"""
        self.worker_thread.start()

    def _worker_loop(self):
        """Worker loop with stop signal checking"""
        while not self.worker_thread.should_stop():
            try:
                # Use timeout to allow periodic stop checking
                item = self.work_queue.get(timeout=0.1)
                self._process_item(item)
            except queue.Empty:
                continue  # Check stop signal

    def close(self):
        """Graceful shutdown"""
        self.worker_thread.stop()
        self.worker_thread.join(timeout=5.0)
```

### Pattern 2: Test Fixture

```python
import pytest

@pytest.fixture
def turn_detector():
    """Fixture with automatic cleanup"""
    from code.turndetect import TurnDetector

    with TurnDetector() as detector:
        yield detector
    # Cleanup happens automatically in __exit__

def test_turn_detection(turn_detector):
    """Test with automatic thread cleanup"""
    # Test logic...
    assert turn_detector.detect() is not None
# Threads cleaned up after test completes
```

### Pattern 3: TurnDetector Refactor

```python
# code/turndetect.py (Phase 2 refactor)
from code.utils.lifecycle import ManagedThread
import queue

class TurnDetector:
    """Turn detection with managed threads"""

    def __init__(self):
        self.text_queue = queue.Queue()
        self.text_worker = ManagedThread(
            target=self._process_text_queue,
            name="text_worker"
        )
        self.silence_worker = ManagedThread(
            target=self._detect_silence,
            name="silence_worker"
        )
        self.text_worker.start()
        self.silence_worker.start()

    def _process_text_queue(self):
        """Worker with stop signal checking"""
        while not self.text_worker.should_stop():
            try:
                item = self.text_queue.get(timeout=0.1)
                # Process item...
            except queue.Empty:
                continue

    def _detect_silence(self):
        """Worker with stop signal checking"""
        while not self.silence_worker.should_stop():
            time.sleep(0.1)  # Detect silence...
            if self.text_worker.should_stop():
                break

    def close(self):
        """Explicit cleanup"""
        self.text_worker.stop()
        self.silence_worker.stop()
        self.text_worker.join()
        self.silence_worker.join()

    def __enter__(self):
        """Context manager support"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Automatic cleanup"""
        self.close()
        return False
```

---

## Error Handling

### Thread Exception

```python
def failing_worker():
    raise ValueError("Worker crashed")

with ManagedThread(target=failing_worker) as thread:
    time.sleep(0.1)
# Logs ERROR, but cleanup still occurs
```

### Timeout on Join

```python
def blocking_worker():
    while True:
        time.sleep(1)  # Never checks should_stop()

thread = ManagedThread(target=blocking_worker)
thread.start()
thread.stop()
success = thread.join(timeout=5.0)
assert success == False  # Timeout, logs WARNING
```

### Multiple Stop Calls

```python
thread = ManagedThread(target=worker)
thread.start()
thread.stop()  # First call
thread.stop()  # Second call (safe, idempotent)
thread.join()
```

---

## Performance Guarantees

| Operation         | Maximum Latency | Notes                 |
| ----------------- | --------------- | --------------------- |
| **init**()        | 1 ms            | Event creation        |
| start()           | 50 ms           | Thread creation       |
| stop()            | <1 ms           | Event.set()           |
| should_stop()     | <0.001 ms       | Event.is_set()        |
| join(timeout=5.0) | 5 seconds       | Configurable timeout  |
| **enter**()       | 50 ms           | Calls start()         |
| **exit**()        | 5 seconds       | Calls stop() + join() |

**Overhead**: Negligible (<0.1% CPU for should_stop() checks every 100ms)

---

## Testing Contracts

### Unit Tests

```python
def test_stop_signal():
    """Verify stop signal terminates thread"""
    stopped = threading.Event()

    def worker(thread):
        while not thread.should_stop():
            time.sleep(0.01)
        stopped.set()

    thread = ManagedThread(target=lambda: worker(thread))
    thread.start()
    time.sleep(0.1)

    thread.stop()
    assert thread.join(timeout=1.0)
    assert stopped.is_set()

def test_context_manager():
    """Verify context manager cleanup"""
    started = threading.Event()
    stopped = threading.Event()

    def worker(thread):
        started.set()
        while not thread.should_stop():
            time.sleep(0.01)
        stopped.set()

    with ManagedThread(target=lambda: worker(thread)) as thread:
        started.wait(timeout=1.0)
        assert thread.is_alive()

    # After context exit
    stopped.wait(timeout=1.0)
    assert stopped.is_set()
    assert not thread.is_alive()

def test_exception_handling():
    """Verify exceptions are logged but cleanup occurs"""
    def failing_worker():
        raise ValueError("Test exception")

    with pytest.raises(ValueError):
        # Exception propagates from target
        thread = ManagedThread(target=failing_worker)
        thread.start()
        thread.join()
```

### Integration Tests

```python
def test_turn_detector_cleanup():
    """Verify TurnDetector threads cleaned up after test"""
    with TurnDetector() as detector:
        # Use detector...
        detector.start_recording()
        time.sleep(1.0)

    # Verify no orphaned threads
    active_threads = threading.enumerate()
    thread_names = [t.name for t in active_threads]
    assert "text_worker" not in thread_names
    assert "silence_worker" not in thread_names
```

---

## Compliance Checklist

✅ **Offline-First**: No external dependencies, pure threading module  
✅ **Reliability**: Graceful shutdown, timeout protection, exception handling  
✅ **Observability**: Structured logging (INFO/WARNING/ERROR with thread names)  
✅ **Security**: No security concerns (internal thread management)  
✅ **Maintainability**: Single responsibility (thread lifecycle only)  
✅ **Testability**: Context manager support for pytest fixtures

---

## Migration Guide

### Before (Phase 1)

```python
class TurnDetector:
    def __init__(self):
        self.text_worker = threading.Thread(target=self._process_text)
        self.text_worker.start()
    # NO CLEANUP - threads leak
```

### After (Phase 2)

```python
from code.utils.lifecycle import ManagedThread

class TurnDetector:
    def __init__(self):
        self.text_worker = ManagedThread(
            target=self._process_text,
            name="text_worker"
        )
        self.text_worker.start()

    def _process_text(self):
        while not self.text_worker.should_stop():
            # Work with periodic stop checking
            time.sleep(0.1)

    def close(self):
        self.text_worker.stop()
        self.text_worker.join()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
```

---

**Version**: 1.0  
**Last Updated**: October 19, 2025
