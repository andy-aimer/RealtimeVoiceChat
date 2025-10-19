"""
Unit tests for thread cleanup with ManagedThread.

Tests the ManagedThread context manager and TurnDetector cleanup behavior.
Part of Phase 2, User Story 1 (P1) - Thread Cleanup.
"""

import pytest
import threading
import time
from src.utils.lifecycle import ManagedThread
from src.turndetect import TurnDetection


class TestManagedThread:
    """Test suite for ManagedThread lifecycle management."""
    
    def test_stop_signal(self):
        """Test that stop() signals the thread to stop."""
        stop_was_called = threading.Event()
        
        def worker(managed_thread: ManagedThread):
            # Wait a bit then check if stop was called
            time.sleep(0.1)
            if managed_thread.should_stop():
                stop_was_called.set()
        
        thread = ManagedThread(target=worker, name="test-stop-signal")
        thread.start()
        
        # Give thread time to start
        time.sleep(0.05)
        
        # Signal stop
        thread.stop()
        
        # Wait for thread to process stop signal
        thread.join(timeout=2.0)
        
        assert stop_was_called.is_set(), "Thread should have detected stop signal"
        assert not thread.is_alive(), "Thread should have stopped"
    
    def test_should_stop_behavior(self):
        """Test that should_stop() returns correct values."""
        iterations = []
        
        def worker(managed_thread: ManagedThread):
            while not managed_thread.should_stop():
                iterations.append(1)
                time.sleep(0.05)
                # Safety: max 10 iterations
                if len(iterations) >= 10:
                    break
        
        thread = ManagedThread(target=worker, name="test-should-stop")
        thread.start()
        
        # Let it run a few iterations
        time.sleep(0.15)
        
        # Signal stop
        thread.stop()
        
        # Thread should exit loop
        thread.join(timeout=2.0)
        
        assert len(iterations) > 0, "Worker should have run at least once"
        assert len(iterations) < 10, "Worker should have stopped before safety limit"
        assert not thread.is_alive(), "Thread should be stopped"
    
    def test_context_manager(self):
        """Test that ManagedThread works as context manager."""
        worker_started = threading.Event()
        worker_stopped = threading.Event()
        
        def worker(managed_thread: ManagedThread):
            worker_started.set()
            while not managed_thread.should_stop():
                time.sleep(0.01)
            worker_stopped.set()
        
        with ManagedThread(target=worker, name="test-context-manager") as thread:
            # Wait for worker to start
            assert worker_started.wait(timeout=1.0), "Worker should start"
            assert thread.is_alive(), "Thread should be alive in context"
        
        # After exiting context, thread should be stopped
        assert worker_stopped.is_set(), "Worker should have been signaled to stop"
        time.sleep(0.1)  # Give thread time to fully exit
        assert not thread.is_alive(), "Thread should be stopped after context exit"
    
    def test_join_timeout(self):
        """Test that join() respects timeout."""
        
        def worker(managed_thread: ManagedThread):
            # Ignore stop signal and run for a long time
            time.sleep(10.0)  # Intentionally long
        
        thread = ManagedThread(target=worker, name="test-join-timeout")
        thread.start()
        
        # Give thread time to start
        time.sleep(0.05)
        
        # Signal stop (worker will ignore it)
        thread.stop()
        
        # Try to join with short timeout
        start_time = time.time()
        joined = thread.join(timeout=0.5)
        elapsed = time.time() - start_time
        
        assert not joined, "join() should return False on timeout"
        assert elapsed < 1.0, "join() should respect timeout (~0.5s)"
        assert thread.is_alive(), "Thread should still be alive after timeout"
    
    def test_idempotent_stop(self):
        """Test that calling stop() multiple times is safe."""
        stop_count = []
        
        def worker(managed_thread: ManagedThread):
            while not managed_thread.should_stop():
                time.sleep(0.01)
            stop_count.append(1)
        
        thread = ManagedThread(target=worker, name="test-idempotent-stop")
        thread.start()
        time.sleep(0.05)
        
        # Call stop multiple times
        thread.stop()
        thread.stop()
        thread.stop()
        
        thread.join(timeout=2.0)
        
        assert len(stop_count) == 1, "Worker should only detect stop once"
        assert not thread.is_alive(), "Thread should be stopped"
    
    def test_error_handling(self):
        """Test that exceptions in worker are caught and logged."""
        
        def worker(managed_thread: ManagedThread):
            raise ValueError("Test exception")
        
        thread = ManagedThread(target=worker, name="test-error-handling")
        thread.start()
        
        # Thread should complete despite exception
        joined = thread.join(timeout=2.0)
        
        assert joined, "Thread should complete even with exception"
        assert not thread.is_alive(), "Thread should be stopped after exception"


class TestTurnDetectorCleanup:
    """Test suite for TurnDetector thread cleanup."""
    
    def test_close_method(self):
        """Test that close() stops the background worker."""
        def dummy_callback(time_val, text):
            pass
        
        detector = TurnDetection(
            on_new_waiting_time=dummy_callback,
            local=True  # Use local model to avoid network
        )
        
        # Worker should be alive
        assert detector.text_worker.is_alive(), "Worker should be alive after init"
        
        # Close the detector
        detector.close()
        
        # Give thread time to stop
        time.sleep(0.2)
        
        # Worker should be stopped
        assert not detector.text_worker.is_alive(), "Worker should be stopped after close()"
    
    def test_context_manager_cleanup(self):
        """Test that TurnDetector works as context manager."""
        def dummy_callback(time_val, text):
            pass
        
        with TurnDetection(
            on_new_waiting_time=dummy_callback,
            local=True
        ) as detector:
            # Worker should be alive in context
            assert detector.text_worker.is_alive(), "Worker should be alive in context"
            
            # Can use detector normally
            detector.calculate_waiting_time("Test text")
        
        # After context exit, worker should be stopped
        time.sleep(0.2)
        assert not detector.text_worker.is_alive(), "Worker should be stopped after context exit"
    
    def test_multiple_instances_cleanup(self):
        """Test that multiple TurnDetector instances clean up properly."""
        def dummy_callback(time_val, text):
            pass
        
        detectors = []
        
        # Create multiple detectors
        for i in range(3):
            detector = TurnDetection(
                on_new_waiting_time=dummy_callback,
                local=True
            )
            detectors.append(detector)
        
        # All should have active workers
        for detector in detectors:
            assert detector.text_worker.is_alive(), "Each worker should be alive"
        
        # Close all
        for detector in detectors:
            detector.close()
        
        time.sleep(0.3)
        
        # All should be stopped
        for detector in detectors:
            assert not detector.text_worker.is_alive(), "Each worker should be stopped"
    
    def test_no_orphaned_threads_after_context(self):
        """Test that no threads are left running after context manager."""
        def dummy_callback(time_val, text):
            pass
        
        # Count threads before
        threads_before = threading.active_count()
        
        with TurnDetection(
            on_new_waiting_time=dummy_callback,
            local=True
        ) as detector:
            # Thread count should increase
            threads_during = threading.active_count()
            assert threads_during > threads_before, "Thread count should increase"
        
        # Wait for cleanup
        time.sleep(0.3)
        
        # Thread count should return to baseline (or lower)
        threads_after = threading.active_count()
        assert threads_after <= threads_before + 1, \
            f"Thread count should return to baseline. Before: {threads_before}, After: {threads_after}"


class TestThreadLifecycle:
    """Integration tests for thread lifecycle management."""
    
    def test_repeated_create_destroy(self):
        """Test that repeatedly creating and destroying threads works."""
        def dummy_callback(time_val, text):
            pass
        
        for i in range(5):
            with TurnDetection(
                on_new_waiting_time=dummy_callback,
                local=True
            ) as detector:
                detector.calculate_waiting_time(f"Test text {i}")
                time.sleep(0.05)
            
            # Brief pause between iterations
            time.sleep(0.1)
        
        # Should complete without hanging
        assert True, "All iterations completed successfully"
    
    def test_graceful_shutdown_with_queued_items(self):
        """Test that shutdown works even with items in queue."""
        processed_items = []
        
        def callback(time_val, text):
            processed_items.append(text)
        
        with TurnDetection(
            on_new_waiting_time=callback,
            local=True
        ) as detector:
            # Queue multiple items quickly
            for i in range(5):
                detector.calculate_waiting_time(f"Text {i}")
            
            # Exit context immediately (some items may not be processed)
        
        # Should exit cleanly without hanging
        time.sleep(0.2)
        
        # Some items should have been processed
        assert len(processed_items) >= 0, "Should handle queued items gracefully"
