"""
Pytest configuration and shared fixtures for Phase 1 Foundation tests.

Provides fixtures for:
- Async test support (via pytest-asyncio)
- HTTP client for API testing
- Mock data for testing
- FastAPI test client setup
"""
import pytest
from typing import AsyncGenerator
from httpx import AsyncClient


# Event loop is now managed by pytest-asyncio with asyncio_mode = "auto"


@pytest.fixture
async def async_client() -> AsyncGenerator:
    """Provide an async HTTP client for testing async endpoints."""
    async with AsyncClient() as client:
        yield client


@pytest.fixture
def mock_audio_data() -> bytes:
    """Provide mock audio data for testing."""
    # 1 second of silence at 16kHz, 16-bit PCM
    return b'\x00\x00' * 16000


@pytest.fixture
def mock_text_input() -> str:
    """Provide mock text input for testing."""
    return "Hello, this is a test message for the voice chat system."


@pytest.fixture
def mock_websocket_message() -> dict:
    """Provide a mock WebSocket message for testing."""
    return {
        "type": "text",
        "data": {
            "text": "Test message",
            "session_id": "test-session-123"
        }
    }


@pytest.fixture
def mock_health_response() -> dict:
    """Provide a mock health check response."""
    return {
        "status": "healthy",
        "timestamp": "2025-10-18T14:32:01.123Z",
        "components": {
            "audio": "healthy",
            "llm": "healthy",
            "tts": "healthy",
            "system": "healthy"
        }
    }


@pytest.fixture
def mock_metrics_response() -> str:
    """Provide a mock Prometheus metrics response."""
    return """# HELP system_memory_available_bytes Available system memory in bytes
# TYPE system_memory_available_bytes gauge
system_memory_available_bytes 4294967296
# HELP system_cpu_temperature_celsius CPU temperature in Celsius
# TYPE system_cpu_temperature_celsius gauge
system_cpu_temperature_celsius 65.0
# HELP system_cpu_percent CPU usage percentage
# TYPE system_cpu_percent gauge
system_cpu_percent 15.5
# HELP system_swap_usage_bytes Swap memory usage in bytes
# TYPE system_swap_usage_bytes gauge
system_swap_usage_bytes 0
"""


@pytest.fixture
def test_client():
    """Provide a FastAPI test client.
    
    Note: This requires server.py to be importable.
    Will be implemented after server.py is updated with new endpoints.
    """
    # Placeholder - will import from server.py once endpoints are added
    return None


# Phase 2 P1: TurnDetection fixture with automatic cleanup
@pytest.fixture
def turn_detector_factory():
    """
    Factory fixture for creating TurnDetection instances with automatic cleanup.
    
    Ensures all TurnDetection instances are properly cleaned up after tests,
    preventing thread leaks.
    
    Usage:
        def test_something(turn_detector_factory):
            def callback(time_val, text):
                pass
            
            detector = turn_detector_factory(on_new_waiting_time=callback)
            # Use detector...
            # No need to manually close, fixture handles cleanup
    
    Phase 2 Addition: Part of User Story 1 (P1) thread cleanup.
    """
    detectors = []
    
    def _create_detector(**kwargs):
        """Create a TurnDetection instance and register for cleanup."""
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

