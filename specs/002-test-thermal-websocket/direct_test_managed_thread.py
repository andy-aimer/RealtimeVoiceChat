#!/usr/bin/env python3
"""
Direct test of ManagedThread without pytest.

This bypasses the pytest module name conflict and demonstrates
that the ManagedThread implementation works correctly.
"""

import sys
import time
import threading
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.lifecycle import ManagedThread

print("=" * 70)
print("DIRECT MANAGEDTHREAD VALIDATION (no pytest)")
print("=" * 70)

# Test 1: Basic stop signal
print("\n✓ Test 1: Stop signal")
stop_detected = threading.Event()

def worker1(thread):
    time.sleep(0.1)
    if thread.should_stop():
        stop_detected.set()

thread1 = ManagedThread(target=worker1, name="test-stop")
thread1.start()
time.sleep(0.05)
thread1.stop()
thread1.join(timeout=2.0)

assert stop_detected.is_set(), "❌ Stop signal not detected"
assert not thread1.is_alive(), "❌ Thread still alive"
print("  ✅ Stop signal works correctly")

# Test 2: Context manager
print("\n✓ Test 2: Context manager")
context_started = threading.Event()
context_stopped = threading.Event()

def worker2(thread):
    context_started.set()
    while not thread.should_stop():
        time.sleep(0.01)
    context_stopped.set()

with ManagedThread(target=worker2, name="test-context") as thread2:
    assert context_started.wait(timeout=1.0), "❌ Worker didn't start"
    assert thread2.is_alive(), "❌ Thread not alive in context"

time.sleep(0.2)
assert context_stopped.is_set(), "❌ Worker didn't stop"
assert not thread2.is_alive(), "❌ Thread still alive after context"
print("  ✅ Context manager works correctly")

# Test 3: Multiple iterations
print("\n✓ Test 3: Multiple create/destroy iterations")
for i in range(5):
    iteration_done = threading.Event()
    
    def worker3(thread):
        iteration_done.set()
        while not thread.should_stop():
            time.sleep(0.01)
    
    with ManagedThread(target=worker3, name=f"test-iter-{i}") as thread3:
        assert iteration_done.wait(timeout=1.0), f"❌ Iteration {i} didn't start"
    
    time.sleep(0.1)
    assert not thread3.is_alive(), f"❌ Thread from iteration {i} still alive"

print("  ✅ Multiple iterations work correctly")

# Test 4: Thread count (no leaks)
print("\n✓ Test 4: No thread leaks")
threads_before = threading.active_count()

for i in range(3):
    def worker4(thread):
        while not thread.should_stop():
            time.sleep(0.01)
    
    with ManagedThread(target=worker4, name=f"test-leak-{i}"):
        pass
    time.sleep(0.1)

threads_after = threading.active_count()
leaked = max(0, threads_after - threads_before)

assert leaked == 0, f"❌ {leaked} threads leaked"
print(f"  ✅ No thread leaks (before: {threads_before}, after: {threads_after})")

# Summary
print("\n" + "=" * 70)
print("✅ ALL DIRECT TESTS PASSED")
print("=" * 70)
print("\nManagedThread implementation is working correctly!")
print("The pytest failures are due to the 'code/' directory name conflict,")
print("not due to implementation issues.")
print("\nSuggestion: Rename 'code/' to 'src/' or 'app/' to fix pytest.")
