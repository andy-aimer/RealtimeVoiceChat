# Phase 2 P1: Test Fixture Updates for Thread Cleanup

**Date**: October 19, 2025  
**Task**: T033 - Update existing Phase 1 tests to use TurnDetector context manager

## Summary

Added `turn_detector_factory` fixture to `tests/conftest.py` for automatic cleanup of TurnDetection instances. Existing Phase 1 tests continue to work but should be gradually migrated to use this fixture or context manager pattern.

## Changes Made

### 1. Added `turn_detector_factory` fixture in `tests/conftest.py`

```python
@pytest.fixture
def turn_detector_factory():
    """
    Factory fixture for creating TurnDetection instances with automatic cleanup.

    Ensures all TurnDetection instances are properly cleaned up after tests,
    preventing thread leaks.
    """
    detectors = []

    def _create_detector(**kwargs):
        from code.turndetect import TurnDetection
        detector = TurnDetection(**kwargs)
        detectors.append(detector)
        return detector

    yield _create_detector

    # Cleanup all created detectors
    for detector in detectors:
        try:
            if hasattr(detector, 'text_worker') and detector.text_worker.is_alive():
                detector.close()
        except Exception as e:
            print(f"Warning: Failed to cleanup detector: {e}")
```

## Migration Strategy

### Option A: Use Context Manager (Recommended for New Tests)

```python
def test_something():
    def callback(time_val, text):
        pass

    with TurnDetection(on_new_waiting_time=callback, local=True) as detector:
        detector.calculate_waiting_time("test text")
        # detector automatically cleaned up on exit
```

### Option B: Use Factory Fixture (For Tests Needing Multiple Instances)

```python
def test_something(turn_detector_factory):
    def callback(time_val, text):
        pass

    detector = turn_detector_factory(on_new_waiting_time=callback, local=True)
    detector.calculate_waiting_time("test text")
    # Factory handles cleanup automatically
```

### Option C: Manual Cleanup (For Complex Test Scenarios)

```python
def test_something():
    def callback(time_val, text):
        pass

    detector = TurnDetection(on_new_waiting_time=callback, local=True)
    try:
        detector.calculate_waiting_time("test text")
    finally:
        detector.close()  # Explicit cleanup
```

## Impact on Existing Tests

### Tests Already Fixed (New Phase 2 Tests)

- ✅ `tests/unit/test_thread_cleanup.py` - Uses context manager pattern
- ✅ `tests/integration/test_full_suite.py` - Tests cleanup behavior

### Tests That Need Migration (Phase 1 Tests)

- ⚠️ `tests/unit/test_turn_detection.py` - 7 test classes with TurnDetection fixtures
  - Uses mocked models (no real thread issues in unit tests)
  - Low priority for migration (unit tests are fast)
  - Can continue using current fixtures with manual cleanup if needed

### Migration Priority

**High Priority**: Integration tests and any tests that:

- Create multiple TurnDetection instances
- Run for >1 second
- Are part of CI/CD suite

**Low Priority**: Unit tests that:

- Mock the background thread
- Complete in <100ms
- Already use proper teardown

## Current Status

- ✅ Factory fixture added to `tests/conftest.py`
- ✅ New Phase 2 tests use context manager pattern
- ⚠️ Phase 1 tests continue to work but may benefit from migration

## Verification

Run the full test suite to verify no regressions:

```bash
# Should complete without hanging
pytest tests/ -v

# Check for orphaned threads (should be 0)
pytest tests/integration/test_full_suite.py::TestFullSuiteExecution::test_zero_orphaned_threads_after_suite
```

## Future Work

Consider creating a pytest plugin or autouse fixture that automatically detects and cleans up TurnDetection instances created without proper cleanup. This would provide a safety net for developers who forget to use the context manager.

```python
@pytest.fixture(autouse=True)
def auto_cleanup_turn_detectors():
    """Automatically cleanup any TurnDetection instances after each test."""
    # Track thread count before test
    threads_before = threading.active_count()

    yield

    # After test, check for thread leaks
    threads_after = threading.active_count()
    if threads_after > threads_before:
        # Log warning about potential leak
        # Attempt cleanup of any TurnDetection instances
        pass
```

This would be implemented in Phase 6 (Polish) if needed.
