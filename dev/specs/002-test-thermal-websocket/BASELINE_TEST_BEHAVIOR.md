# Baseline Test Behavior - Phase 1 Complete

**Date**: October 19, 2025  
**Branch**: 002-test-thermal-websocket  
**Status**: Pre-Phase 2 Implementation

## Test Suite Structure

**Existing Tests** (from Phase 1):

- `tests/unit/test_audio_processing.py` - Audio processing unit tests
- `tests/unit/test_callbacks.py` - Callback handling tests
- `tests/unit/test_security_validators.py` - Security validation tests
- `tests/unit/test_text_utils.py` - Text utility tests
- `tests/unit/test_turn_detection.py` - Turn detection logic tests
- `tests/integration/test_interruption_handling.py` - Interruption flow tests
- `tests/integration/test_pipeline_e2e.py` - End-to-end pipeline tests
- `tests/conftest.py` - Shared pytest fixtures

**Total**: ~43 tests from Phase 1 (exact count TBD when pytest runs successfully)

## Known Issues (Pre-Phase 2)

### 1. Thread Cleanup Problem (P1 - CRITICAL)

**Symptom**: Test suite hangs indefinitely when running full `pytest tests/`

**Root Cause** (from investigation):

- `TurnDetector` class in `code/turndetect.py` creates background thread (`text_worker`)
- Thread is marked `daemon=True` but runs in infinite `while True` loop (line 375)
- No graceful stop mechanism exists
- Tests that instantiate `TurnDetector` leave orphaned threads running

**Impact**:

- Cannot run full test suite reliably
- CI/CD pipelines would timeout
- Forces file-by-file test execution (slow, blocks automation)

**Evidence**:

```python
# code/turndetect.py, line 208-212
self.text_worker = threading.Thread(
    target=self._text_worker,
    daemon=True  # ← Doesn't prevent hanging
)
self.text_worker.start()

# Line 375 - infinite loop, no exit condition
def _text_worker(self) -> None:
    while True:  # ← No way to stop gracefully
        try:
            text = self.text_queue.get(block=True, timeout=0.1)
        except queue.Empty:
            time.sleep(0.01)
            continue
        # ... processing ...
```

### 2. Module Name Conflict (DISCOVERED)

**Symptom**: `pytest` fails with `AttributeError: module 'code' has no attribute 'InteractiveConsole'`

**Root Cause**:

- Project uses `code/` directory for source files
- Python standard library has a `code` module
- When pytest imports, it shadows the stdlib module
- This breaks pytest's internal debugger initialization

**Workaround**: Tests must be run from project root with proper PYTHONPATH

**Note**: This is a pre-existing issue, not introduced in Phase 2. Will document but not fix in this phase.

## Baseline Metrics (Expected Post-Fix)

**Target Metrics** (Success Criteria for Phase 2 P1):

- Test suite execution time: **<5 minutes** (currently: hangs indefinitely)
- Coverage: **≥60%** for Phase 2 code
- Orphaned threads: **0** (currently: N threads left after each test)
- CI/CD completion: **100% success rate** (currently: 0% due to timeout)
- File-by-file improvement: **50% faster** than current workaround

## Test Execution Workarounds (Pre-Phase 2)

**Current approach** (to avoid hangs):

```bash
# Run tests file-by-file to avoid thread accumulation
pytest tests/unit/test_audio_processing.py
pytest tests/unit/test_callbacks.py
# ... repeat for each file ...
```

**Why this works**: Each file execution creates new threads, but Python process exits after each file, killing all threads.

**Why this is bad**:

- Slow (multiple Python interpreter startups)
- No aggregate coverage reporting
- Cannot run in CI/CD efficiently
- Masks integration issues between modules

## Phase 2 P1 Implementation Plan

**Solution**: Implement `ManagedThread` context manager

- Add `stop()` method with threading.Event
- Add `should_stop()` check in worker loops
- Add `__enter__`/`__exit__` for automatic cleanup
- Refactor `TurnDetector` to use `ManagedThread`
- Update test fixtures to use context manager pattern

**Expected Outcome**:

```python
# After Phase 2 P1
with TurnDetector(callback) as detector:
    detector.calculate_waiting_time("test text")
    # detector automatically cleaned up on exit
```

## Validation Approach

**Before Phase 2 P1**:

1. Attempt `pytest tests/` - observe hang
2. Press Ctrl+C after 30 seconds
3. Check for orphaned threads: `ps aux | grep python` shows lingering processes

**After Phase 2 P1**:

1. Run `pytest tests/` 10 times - all complete <5 min
2. Run `coverage run -m pytest tests/` - ≥60% for new code
3. Check `ps aux | grep python` after tests - no orphaned processes
4. Run in CI/CD - completes without timeout

## References

- Spec: `/specs/002-test-thermal-websocket/spec.md`
- Research: `/specs/002-test-thermal-websocket/research.md`
- Tasks: `/specs/002-test-thermal-websocket/tasks.md` (T009-T012 foundational tasks)
- Contract: `/specs/002-test-thermal-websocket/contracts/managed_thread.md`
