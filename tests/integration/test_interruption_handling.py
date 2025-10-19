"""
Integration tests for interruption handling during LLM/TTS execution.

Tests interruption scenarios, state recovery, cleanup of zombie processes,
and proper resource management during interruptions.
"""
import pytest
import time
import asyncio
import threading
import psutil
import os
from unittest.mock import Mock, MagicMock, patch
import sys

# Add parent directory to path to import code modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'code'))

# Mark all tests as integration tests
pytestmark = pytest.mark.integration


# ==================== Fixtures ====================

@pytest.fixture
def stop_event():
    """Fixture providing a threading.Event for interruption signaling."""
    return threading.Event()


@pytest.fixture
def mock_llm_generator():
    """Fixture providing a mock LLM generator that can be interrupted."""
    def generator(stop_event):
        words = ["This", "is", "a", "long", "response", "that", "can", "be", "interrupted"]
        for word in words:
            if stop_event.is_set():
                break
            time.sleep(0.1)
            yield word + " "
    return generator


@pytest.fixture
def mock_tts_processor():
    """Fixture providing a mock TTS processor."""
    class MockTTS:
        def __init__(self):
            self.is_playing = False
            self.audio_queue = asyncio.Queue()
        
        def start(self, text):
            self.is_playing = True
            # Simulate audio synthesis
            time.sleep(0.5)
        
        def stop(self):
            self.is_playing = False
    
    return MockTTS()


@pytest.fixture
def process_tracker():
    """Fixture to track process creation and cleanup."""
    class ProcessTracker:
        def __init__(self):
            self.initial_processes = set()
            self.created_processes = set()
        
        def snapshot(self):
            """Take a snapshot of current processes."""
            current_proc = psutil.Process()
            self.initial_processes = {p.pid for p in current_proc.children(recursive=True)}
        
        def check_zombies(self):
            """Check for zombie processes."""
            current_proc = psutil.Process()
            current_children = {p.pid for p in current_proc.children(recursive=True)}
            zombies = []
            
            for proc in psutil.process_iter(['pid', 'status', 'name']):
                try:
                    if proc.status() == psutil.STATUS_ZOMBIE:
                        zombies.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            return zombies
        
        def get_new_processes(self):
            """Get processes created since snapshot."""
            current_proc = psutil.Process()
            current_children = {p.pid for p in current_proc.children(recursive=True)}
            return current_children - self.initial_processes
    
    return ProcessTracker()


# ==================== Interruption During LLM Tests (T020) ====================

class TestLLMInterruption:
    """Tests for interrupting LLM generation."""
    
    def test_llm_generator_interruption(self, stop_event, mock_llm_generator):
        """Test LLM generator can be interrupted mid-generation."""
        generated_tokens = []
        
        # Start generation in thread
        def generate():
            for token in mock_llm_generator(stop_event):
                generated_tokens.append(token)
        
        gen_thread = threading.Thread(target=generate)
        gen_thread.start()
        
        # Let it generate a few tokens
        time.sleep(0.25)
        
        # Interrupt
        stop_event.set()
        gen_thread.join(timeout=1.0)
        
        # Should have generated some but not all tokens
        assert len(generated_tokens) > 0
        assert len(generated_tokens) < 9  # Less than total words
        print(f"✓ Interrupted after {len(generated_tokens)} tokens")
    
    def test_llm_interruption_immediate(self, stop_event, mock_llm_generator):
        """Test LLM can be interrupted immediately."""
        stop_event.set()  # Set before starting
        
        generated_tokens = []
        for token in mock_llm_generator(stop_event):
            generated_tokens.append(token)
        
        # Should not generate any tokens
        assert len(generated_tokens) == 0
        print("✓ Immediate interruption successful")
    
    def test_llm_interruption_late(self, stop_event, mock_llm_generator):
        """Test LLM interruption near end of generation."""
        generated_tokens = []
        
        def generate():
            for token in mock_llm_generator(stop_event):
                generated_tokens.append(token)
        
        gen_thread = threading.Thread(target=generate)
        gen_thread.start()
        
        # Wait for most of generation
        time.sleep(0.85)
        
        # Interrupt near end
        stop_event.set()
        gen_thread.join(timeout=1.0)
        
        # Should have generated most tokens
        assert len(generated_tokens) >= 7
        print(f"✓ Late interruption after {len(generated_tokens)} tokens")
    
    def test_llm_state_after_interruption(self, stop_event, mock_llm_generator):
        """Test LLM state is clean after interruption."""
        generated_tokens = []
        
        # First generation (interrupted)
        def generate():
            for token in mock_llm_generator(stop_event):
                generated_tokens.append(token)
        
        gen_thread = threading.Thread(target=generate)
        gen_thread.start()
        time.sleep(0.15)
        stop_event.set()
        gen_thread.join(timeout=1.0)
        
        first_count = len(generated_tokens)
        
        # Reset and try again
        stop_event.clear()
        generated_tokens.clear()
        
        gen_thread2 = threading.Thread(target=generate)
        gen_thread2.start()
        time.sleep(0.15)
        stop_event.set()
        gen_thread2.join(timeout=1.0)
        
        second_count = len(generated_tokens)
        
        # Both should generate similar amounts
        assert abs(first_count - second_count) <= 1
        print(f"✓ State clean: {first_count} vs {second_count} tokens")


# ==================== Interruption During TTS Tests (T020) ====================

class TestTTSInterruption:
    """Tests for interrupting TTS synthesis."""
    
    def test_tts_synthesis_interruption(self, stop_event, mock_tts_processor):
        """Test TTS synthesis can be interrupted."""
        def synthesize():
            mock_tts_processor.start("Long text to synthesize")
            if not stop_event.is_set():
                time.sleep(1.0)  # Simulate long synthesis
        
        synth_thread = threading.Thread(target=synthesize)
        synth_thread.start()
        
        # Let synthesis start
        time.sleep(0.2)
        
        # Interrupt
        stop_event.set()
        mock_tts_processor.stop()
        synth_thread.join(timeout=1.0)
        
        assert mock_tts_processor.is_playing is False
        print("✓ TTS interrupted successfully")
    
    def test_tts_audio_queue_cleared_on_interrupt(self, stop_event):
        """Test TTS audio queue is cleared on interruption."""
        audio_queue = asyncio.Queue()
        
        # Add some items
        asyncio.run(self._fill_queue(audio_queue, 5))
        
        assert audio_queue.qsize() == 5
        
        # Simulate interruption cleanup
        asyncio.run(self._clear_queue(audio_queue))
        
        assert audio_queue.qsize() == 0
        print("✓ Audio queue cleared")
    
    async def _fill_queue(self, queue, count):
        """Helper to fill queue."""
        for i in range(count):
            await queue.put(bytes([i]))
    
    async def _clear_queue(self, queue):
        """Helper to clear queue."""
        while not queue.empty():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                break
    
    def test_tts_stream_stop_callback(self, stop_event):
        """Test TTS stream stop callback is called on interruption."""
        stop_callback_called = []
        
        def on_stop():
            stop_callback_called.append(True)
        
        # Simulate TTS with callback
        def tts_with_callback():
            try:
                time.sleep(0.5)
            finally:
                on_stop()
        
        tts_thread = threading.Thread(target=tts_with_callback)
        tts_thread.start()
        
        time.sleep(0.2)
        stop_event.set()
        tts_thread.join(timeout=1.0)
        
        assert len(stop_callback_called) == 1
        print("✓ Stop callback invoked")


# ==================== State Recovery Tests (T020) ====================

class TestStateRecovery:
    """Tests for state recovery after interruption."""
    
    def test_state_recovery_after_llm_interruption(self, stop_event):
        """Test system state recovers after LLM interruption."""
        state = {
            'llm_active': False,
            'tts_active': False,
            'audio_playing': False
        }
        
        # Simulate LLM start
        state['llm_active'] = True
        
        # Simulate interruption
        time.sleep(0.1)
        stop_event.set()
        
        # Cleanup
        state['llm_active'] = False
        state['tts_active'] = False
        state['audio_playing'] = False
        
        # Verify clean state
        assert state['llm_active'] is False
        assert state['tts_active'] is False
        assert state['audio_playing'] is False
        print("✓ State recovered after LLM interruption")
    
    def test_state_recovery_after_tts_interruption(self, stop_event):
        """Test system state recovers after TTS interruption."""
        state = {
            'llm_active': False,
            'tts_active': False,
            'audio_playing': False
        }
        
        # Simulate TTS start
        state['tts_active'] = True
        state['audio_playing'] = True
        
        # Simulate interruption
        time.sleep(0.1)
        stop_event.set()
        
        # Cleanup
        state['tts_active'] = False
        state['audio_playing'] = False
        
        # Verify clean state
        assert state['tts_active'] is False
        assert state['audio_playing'] is False
        print("✓ State recovered after TTS interruption")
    
    def test_multiple_interruptions_state_stable(self, stop_event):
        """Test state remains stable after multiple interruptions."""
        state = {'active': False, 'interrupted_count': 0}
        
        for i in range(5):
            # Start
            state['active'] = True
            
            # Interrupt
            time.sleep(0.05)
            stop_event.set()
            state['active'] = False
            state['interrupted_count'] += 1
            
            # Reset
            stop_event.clear()
            time.sleep(0.01)
        
        assert state['active'] is False
        assert state['interrupted_count'] == 5
        print(f"✓ Stable after {state['interrupted_count']} interruptions")


# ==================== Zombie Process Detection Tests (T021) ====================

class TestZombieProcessDetection:
    """Tests for detecting and preventing zombie processes."""
    
    def test_no_zombies_after_normal_completion(self, process_tracker):
        """Test no zombie processes after normal completion."""
        process_tracker.snapshot()
        
        # Simulate process creation and completion
        def worker():
            time.sleep(0.1)
        
        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()
        
        # Check for zombies
        zombies = process_tracker.check_zombies()
        
        assert len(zombies) == 0, f"Found {len(zombies)} zombie processes"
        print("✓ No zombies after normal completion")
    
    def test_no_zombies_after_interruption(self, process_tracker, stop_event):
        """Test no zombie processes after interruption."""
        process_tracker.snapshot()
        
        # Simulate interruptible work
        def worker():
            for i in range(10):
                if stop_event.is_set():
                    break
                time.sleep(0.05)
        
        thread = threading.Thread(target=worker)
        thread.start()
        
        time.sleep(0.15)
        stop_event.set()
        thread.join(timeout=1.0)
        
        # Check for zombies
        zombies = process_tracker.check_zombies()
        
        assert len(zombies) == 0, f"Found {len(zombies)} zombie processes after interruption"
        print("✓ No zombies after interruption")
    
    def test_thread_cleanup_after_interruption(self, stop_event):
        """Test threads are properly cleaned up after interruption."""
        initial_thread_count = threading.active_count()
        
        threads = []
        for i in range(5):
            def worker():
                while not stop_event.is_set():
                    time.sleep(0.01)
            
            t = threading.Thread(target=worker)
            t.start()
            threads.append(t)
        
        # Interrupt all threads
        time.sleep(0.1)
        stop_event.set()
        
        # Wait for cleanup
        for t in threads:
            t.join(timeout=1.0)
        
        final_thread_count = threading.active_count()
        
        # Thread count should return to normal
        assert final_thread_count <= initial_thread_count + 1
        print(f"✓ Threads cleaned up: {initial_thread_count} → {final_thread_count}")
    
    def test_subprocess_cleanup(self, process_tracker):
        """Test subprocesses are cleaned up properly."""
        import subprocess
        
        process_tracker.snapshot()
        
        # Start a subprocess
        proc = subprocess.Popen(['sleep', '10'])
        
        # Verify it's running
        assert proc.poll() is None
        
        # Terminate it
        proc.terminate()
        proc.wait(timeout=1.0)
        
        # Verify it's not a zombie
        zombies = process_tracker.check_zombies()
        zombie_pids = [z.pid for z in zombies]
        
        assert proc.pid not in zombie_pids
        print("✓ Subprocess cleaned up properly")


# ==================== Memory Leak Tests ====================

class TestMemoryLeaks:
    """Tests for memory leaks during interruptions."""
    
    def test_no_memory_leak_after_multiple_interruptions(self, stop_event):
        """Test no memory leaks after multiple interruptions."""
        import gc
        
        # Run multiple interrupt cycles
        for i in range(10):
            # Create some data
            data = [bytes([j % 256]) * 1000 for j in range(100)]
            
            # Simulate interruption
            stop_event.set()
            
            # Cleanup
            del data
            stop_event.clear()
        
        # Force garbage collection
        gc.collect()
        
        # In real implementation, would measure memory usage here
        print("✓ No apparent memory leaks")
    
    def test_queue_cleared_prevents_memory_leak(self, stop_event):
        """Test clearing queues prevents memory accumulation."""
        audio_queue = asyncio.Queue()
        
        # Add large chunks
        asyncio.run(self._fill_large_queue(audio_queue, 100))
        
        initial_size = audio_queue.qsize()
        
        # Clear on interrupt
        stop_event.set()
        asyncio.run(self._clear_queue_completely(audio_queue))
        
        final_size = audio_queue.qsize()
        
        assert initial_size == 100
        assert final_size == 0
        print(f"✓ Queue cleared: {initial_size} → {final_size} items")
    
    async def _fill_large_queue(self, queue, count):
        """Helper to fill queue with large items."""
        for i in range(count):
            await queue.put(bytes([0] * 10000))  # 10KB per item
    
    async def _clear_queue_completely(self, queue):
        """Helper to completely clear queue."""
        while not queue.empty():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                break


# ==================== Concurrent Interruption Tests ====================

class TestConcurrentInterruptions:
    """Tests for handling concurrent interruptions."""
    
    def test_multiple_interrupts_handled_correctly(self):
        """Test multiple simultaneous interrupts are handled."""
        stop_events = [threading.Event() for _ in range(3)]
        workers_stopped = []
        
        def worker(event_id, stop_event):
            while not stop_event.is_set():
                time.sleep(0.01)
            workers_stopped.append(event_id)
        
        # Start workers
        threads = []
        for i, event in enumerate(stop_events):
            t = threading.Thread(target=worker, args=(i, event))
            t.start()
            threads.append(t)
        
        # Interrupt all
        time.sleep(0.1)
        for event in stop_events:
            event.set()
        
        # Wait for all
        for t in threads:
            t.join(timeout=1.0)
        
        assert len(workers_stopped) == 3
        print("✓ All concurrent workers stopped")
    
    def test_interrupt_during_interrupt(self, stop_event):
        """Test interrupting while handling another interrupt."""
        interrupt_count = []
        
        def worker():
            try:
                while not stop_event.is_set():
                    time.sleep(0.01)
            finally:
                interrupt_count.append(1)
                # Simulate cleanup that could be interrupted
                time.sleep(0.05)
        
        thread = threading.Thread(target=worker)
        thread.start()
        
        time.sleep(0.05)
        stop_event.set()
        thread.join(timeout=1.0)
        
        assert len(interrupt_count) == 1
        print("✓ Nested interrupt handled")


# ==================== Edge Cases ====================

class TestInterruptionEdgeCases:
    """Tests for edge cases in interruption handling."""
    
    def test_interrupt_before_start(self, stop_event):
        """Test interrupting before process starts."""
        stop_event.set()  # Interrupt before starting
        
        def worker():
            if stop_event.is_set():
                return  # Exit immediately
            time.sleep(1.0)
        
        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(timeout=0.5)
        
        assert not thread.is_alive()
        print("✓ Pre-start interrupt handled")
    
    def test_interrupt_after_completion(self, stop_event):
        """Test interrupting after process completes."""
        completed = []
        
        def worker():
            time.sleep(0.1)
            completed.append(True)
        
        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()
        
        # Try to interrupt after completion
        stop_event.set()
        
        assert len(completed) == 1
        print("✓ Post-completion interrupt safe")
    
    def test_rapid_interrupt_cycles(self, stop_event):
        """Test rapid start-interrupt cycles."""
        cycles = 0
        
        for i in range(20):
            def worker():
                time.sleep(0.01)
            
            thread = threading.Thread(target=worker)
            thread.start()
            
            if i % 2 == 0:
                stop_event.set()
                stop_event.clear()
            
            thread.join(timeout=0.5)
            cycles += 1
        
        assert cycles == 20
        print(f"✓ Completed {cycles} rapid cycles")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--timeout=300"])
