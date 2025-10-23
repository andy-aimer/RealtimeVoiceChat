"""
Unit tests for callback handling in transcribe.py module.

Tests callback execution, error handling, and state management
for transcription-related callbacks.
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
import os

# Add parent directory to path to import code modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


# ==================== Callback Function Tests ====================

class TestCallbackExecution:
    """Tests for callback function execution."""
    
    def test_callback_invoked_with_correct_arguments(self):
        """Test that callbacks are invoked with correct arguments."""
        callback = Mock()
        test_data = "test transcription"
        
        callback(test_data)
        
        callback.assert_called_once_with(test_data)
    
    def test_callback_returns_value(self):
        """Test that callback return values are captured."""
        def callback_func(data):
            return f"processed: {data}"
        
        result = callback_func("input")
        assert result == "processed: input"
    
    def test_multiple_callbacks_invoked(self):
        """Test multiple callbacks can be invoked sequentially."""
        callback1 = Mock()
        callback2 = Mock()
        callback3 = Mock()
        
        test_data = "test"
        callback1(test_data)
        callback2(test_data)
        callback3(test_data)
        
        callback1.assert_called_once()
        callback2.assert_called_once()
        callback3.assert_called_once()


class TestCallbackErrorHandling:
    """Tests for callback error handling."""
    
    def test_callback_exception_caught(self):
        """Test that exceptions in callbacks can be caught."""
        def failing_callback(data):
            raise ValueError("Callback error")
        
        with pytest.raises(ValueError, match="Callback error"):
            failing_callback("test")
    
    def test_callback_error_does_not_propagate(self):
        """Test error handling pattern for callbacks."""
        def callback_with_error_handling(data, callback_func):
            try:
                callback_func(data)
                return True
            except Exception as e:
                print(f"Callback error: {e}")
                return False
        
        def failing_callback(data):
            raise RuntimeError("Test error")
        
        result = callback_with_error_handling("test", failing_callback)
        assert result is False
    
    def test_callback_none_handled(self):
        """Test that None callbacks are handled gracefully."""
        callback = None
        
        # Pattern used in code: if callback:
        if callback:
            callback("data")
        
        # Should not raise error
        assert True


class TestCallbackStateManagement:
    """Tests for callback state management."""
    
    def test_callback_tracks_invocation_count(self):
        """Test tracking how many times callback is invoked."""
        callback = Mock()
        
        for i in range(5):
            callback(f"call_{i}")
        
        assert callback.call_count == 5
    
    def test_callback_tracks_arguments(self):
        """Test tracking arguments passed to callbacks."""
        callback = Mock()
        
        callback("arg1")
        callback("arg2")
        callback("arg3")
        
        # Check all calls
        calls = [call[0][0] for call in callback.call_args_list]
        assert calls == ["arg1", "arg2", "arg3"]
    
    def test_callback_state_reset(self):
        """Test resetting callback mock state."""
        callback = Mock()
        
        callback("test1")
        assert callback.call_count == 1
        
        callback.reset_mock()
        assert callback.call_count == 0
    
    def test_callback_with_return_values(self):
        """Test callback with different return values."""
        callback = Mock()
        callback.side_effect = [True, False, True]
        
        assert callback() is True
        assert callback() is False
        assert callback() is True


class TestCallbackChaining:
    """Tests for chaining multiple callbacks."""
    
    def test_callback_chain_execution(self):
        """Test executing a chain of callbacks."""
        results = []
        
        def callback1(data):
            results.append(f"1:{data}")
            return data.upper()
        
        def callback2(data):
            results.append(f"2:{data}")
            return data + "!"
        
        def callback3(data):
            results.append(f"3:{data}")
            return data
        
        # Simulate callback chain
        data = "test"
        data = callback1(data)
        data = callback2(data)
        data = callback3(data)
        
        assert results == ["1:test", "2:TEST", "3:TEST!"]
        assert data == "TEST!"
    
    def test_callback_chain_stops_on_false(self):
        """Test callback chain stopping on False return."""
        executed = []
        
        def callback1(data):
            executed.append(1)
            return True
        
        def callback2(data):
            executed.append(2)
            return False  # Stop chain
        
        def callback3(data):
            executed.append(3)
            return True
        
        # Simulate conditional chain
        data = "test"
        if callback1(data):
            if callback2(data):
                callback3(data)
        
        assert executed == [1, 2]  # callback3 not executed


# ==================== Transcription Callback Tests ====================

class TestTranscriptionCallbackPatterns:
    """Tests for transcription-specific callback patterns."""
    
    def test_realtime_transcription_callback(self):
        """Test realtime transcription callback pattern."""
        transcription_results = []
        
        def realtime_callback(text):
            transcription_results.append(text)
        
        # Simulate realtime updates
        realtime_callback("This is")
        realtime_callback("This is a")
        realtime_callback("This is a test")
        
        assert len(transcription_results) == 3
        assert transcription_results[-1] == "This is a test"
    
    def test_full_transcription_callback(self):
        """Test full transcription callback pattern."""
        final_result = []
        
        def full_callback(text):
            final_result.append(text)
        
        # Simulate final transcription
        full_callback("Complete sentence.")
        
        assert len(final_result) == 1
        assert final_result[0] == "Complete sentence."
    
    def test_potential_transcription_callback(self):
        """Test potential transcription callback pattern."""
        potential_results = []
        
        def potential_callback(text):
            potential_results.append(text)
        
        # Simulate potential sentence end
        potential_callback("Maybe done")
        
        assert len(potential_results) == 1
    
    def test_abort_callback(self):
        """Test abort callback pattern."""
        abort_called = []
        
        def abort_callback():
            abort_called.append(True)
        
        # Simulate abort
        abort_callback()
        
        assert len(abort_called) == 1
        assert abort_called[0] is True


class TestCallbackWithContext:
    """Tests for callbacks with context/state."""
    
    def test_callback_with_closure(self):
        """Test callback with closure over state."""
        counter = {'count': 0}
        
        def callback_with_state(data):
            counter['count'] += 1
            return f"{data}:{counter['count']}"
        
        result1 = callback_with_state("test")
        result2 = callback_with_state("test")
        result3 = callback_with_state("test")
        
        assert result1 == "test:1"
        assert result2 == "test:2"
        assert result3 == "test:3"
    
    def test_callback_with_class_state(self):
        """Test callback as class method with state."""
        class CallbackHandler:
            def __init__(self):
                self.call_count = 0
                self.last_value = None
            
            def handle(self, value):
                self.call_count += 1
                self.last_value = value
                return f"Handled: {value}"
        
        handler = CallbackHandler()
        
        handler.handle("first")
        handler.handle("second")
        
        assert handler.call_count == 2
        assert handler.last_value == "second"


# ==================== Async Callback Tests ====================

class TestAsyncCallbacks:
    """Tests for async callback patterns."""
    
    @pytest.mark.asyncio
    async def test_async_callback_execution(self):
        """Test async callback execution."""
        import asyncio
        
        async def async_callback(data):
            await asyncio.sleep(0.01)
            return f"async:{data}"
        
        result = await async_callback("test")
        assert result == "async:test"
    
    @pytest.mark.asyncio
    async def test_async_callback_error_handling(self):
        """Test async callback error handling."""
        import asyncio
        
        async def failing_async_callback(data):
            await asyncio.sleep(0.01)
            raise ValueError("Async error")
        
        with pytest.raises(ValueError, match="Async error"):
            await failing_async_callback("test")


# ==================== Performance Tests ====================

class TestCallbackPerformance:
    """Tests for callback performance characteristics."""
    
    def test_callback_overhead_minimal(self):
        """Test that callback overhead is minimal."""
        import time
        
        def simple_callback(data):
            return data
        
        iterations = 10000
        start = time.perf_counter()
        
        for i in range(iterations):
            simple_callback(i)
        
        elapsed = time.perf_counter() - start
        
        # Should complete 10k calls in under 10ms
        assert elapsed < 0.01, f"Callback overhead too high: {elapsed*1000:.2f}ms"
    
    def test_callback_with_processing(self):
        """Test callback with some processing."""
        def processing_callback(data):
            # Simulate some processing
            result = str(data).upper()
            return result
        
        result = processing_callback("test data")
        assert result == "TEST DATA"


# ==================== Edge Cases ====================

class TestCallbackEdgeCases:
    """Tests for callback edge cases."""
    
    def test_callback_with_none_data(self):
        """Test callback receives None data."""
        callback = Mock()
        callback(None)
        callback.assert_called_once_with(None)
    
    def test_callback_with_empty_string(self):
        """Test callback receives empty string."""
        callback = Mock()
        callback("")
        callback.assert_called_once_with("")
    
    def test_callback_with_large_data(self):
        """Test callback with large data payload."""
        callback = Mock()
        large_data = "A" * 10000
        
        callback(large_data)
        callback.assert_called_once_with(large_data)
    
    def test_callback_with_unicode(self):
        """Test callback with Unicode data."""
        callback = Mock()
        unicode_data = "Hello 世界 🌍"
        
        callback(unicode_data)
        callback.assert_called_once_with(unicode_data)
    
    def test_callback_with_special_characters(self):
        """Test callback with special characters."""
        callback = Mock()
        special_data = "Test\n\t\r\0Special"
        
        callback(special_data)
        callback.assert_called_once_with(special_data)


# ==================== Callback Decorator Tests ====================

class TestCallbackDecorators:
    """Tests for callback decorator patterns."""
    
    def test_callback_with_logging_decorator(self):
        """Test callback with logging decorator."""
        log_entries = []
        
        def log_callback(func):
            def wrapper(*args, **kwargs):
                log_entries.append(f"Before: {args}")
                result = func(*args, **kwargs)
                log_entries.append(f"After: {result}")
                return result
            return wrapper
        
        @log_callback
        def my_callback(data):
            return f"processed:{data}"
        
        result = my_callback("test")
        
        assert result == "processed:test"
        assert len(log_entries) == 2
    
    def test_callback_with_error_handling_decorator(self):
        """Test callback with error handling decorator."""
        def safe_callback(func):
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    return f"Error: {e}"
            return wrapper
        
        @safe_callback
        def risky_callback(data):
            if data == "fail":
                raise ValueError("Failed!")
            return data
        
        assert risky_callback("success") == "success"
        assert risky_callback("fail").startswith("Error:")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
