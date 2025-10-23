"""
Integration tests for WebSocket lifecycle management.

Tests end-to-end WebSocket reconnection flows, session persistence,
and conversation context preservation across disconnections.

Phase 2 P3 Tasks: T101-T105
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from src.session.session_manager import SessionManager, ConnectionState


# Mock the dependencies that aren't needed for lifecycle tests
@pytest.fixture
def mock_audio_components():
    """Mock audio processing components."""
    with patch('src.server.SpeechPipelineManager'), \
         patch('src.server.UpsampleOverlap'), \
         patch('src.server.AudioInputProcessor'):
        yield


@pytest.fixture
async def session_manager():
    """Create a SessionManager instance for testing."""
    manager = SessionManager(timeout_minutes=5, cleanup_interval=60)
    yield manager
    # Cleanup
    if manager._cleanup_task and not manager._cleanup_task.done():
        await manager.stop_cleanup_task()


class TestWebSocketConnection:
    """Test WebSocket connection establishment (T101)."""
    
    @pytest.mark.asyncio
    async def test_new_connection_creates_session(self, session_manager):
        """Test new WebSocket connection creates session."""
        # Simulate new connection (no session_id)
        session_id = await session_manager.create_session()
        
        # Verify session created
        assert session_id is not None
        assert len(session_id) == 36  # UUID format
        
        session = await session_manager.get_session(session_id)
        assert session is not None
        assert session.connection_state == ConnectionState.CONNECTED
    
    @pytest.mark.asyncio
    async def test_connection_with_valid_session_id(self, session_manager):
        """Test connection with valid existing session_id."""
        # Create initial session
        original_session_id = await session_manager.create_session()
        await session_manager.update_session(original_session_id, "user", "Previous message")
        
        # Disconnect
        await session_manager.disconnect_session(original_session_id)
        
        # Reconnect with same session_id
        restored = await session_manager.restore_session(original_session_id)
        
        assert restored is not None
        assert restored.session_id == original_session_id
        assert restored.connection_state == ConnectionState.CONNECTED
        assert len(restored.conversation_context) == 1
    
    @pytest.mark.asyncio
    async def test_connection_with_expired_session_id(self, session_manager):
        """Test connection with expired session_id creates new session."""
        # Create and expire session
        old_session_id = await session_manager.create_session()
        session = await session_manager.get_session(old_session_id)
        session.last_active = datetime.now() - timedelta(minutes=10)
        
        # Attempt to restore expired session
        restored = await session_manager.restore_session(old_session_id)
        
        # Should return None (expired)
        assert restored is None
        
        # Client would create new session
        new_session_id = await session_manager.create_session()
        assert new_session_id != old_session_id


class TestWebSocketDisconnectReconnect:
    """Test disconnect/reconnect flow (T102)."""
    
    @pytest.mark.asyncio
    async def test_disconnect_preserves_session_data(self, session_manager):
        """Test disconnection preserves session and conversation context."""
        # Create session and add messages
        session_id = await session_manager.create_session()
        await session_manager.update_session(session_id, "user", "Message 1")
        await session_manager.update_session(session_id, "assistant", "Response 1")
        await session_manager.update_session(session_id, "user", "Message 2")
        
        # Disconnect
        await session_manager.disconnect_session(session_id)
        
        # Verify session still exists
        session = await session_manager.get_session(session_id)
        assert session is not None
        assert session.connection_state == ConnectionState.DISCONNECTED
        assert len(session.conversation_context) == 3
    
    @pytest.mark.asyncio
    async def test_quick_reconnect_within_timeout(self, session_manager):
        """Test reconnection within 5-minute timeout window."""
        # Create session and add context
        session_id = await session_manager.create_session()
        await session_manager.update_session(session_id, "user", "Hello")
        
        # Disconnect
        await session_manager.disconnect_session(session_id)
        
        # Wait briefly (simulate network blip)
        await asyncio.sleep(0.1)
        
        # Reconnect
        restored = await session_manager.restore_session(session_id)
        
        assert restored is not None
        assert restored.session_id == session_id
        assert restored.connection_state == ConnectionState.CONNECTED
        assert len(restored.conversation_context) == 1
    
    @pytest.mark.asyncio
    async def test_multiple_reconnect_cycles(self, session_manager):
        """Test multiple disconnect/reconnect cycles."""
        session_id = await session_manager.create_session()
        
        # Cycle 1
        await session_manager.update_session(session_id, "user", "Cycle 1")
        await session_manager.disconnect_session(session_id)
        await session_manager.restore_session(session_id)
        
        # Cycle 2
        await session_manager.update_session(session_id, "user", "Cycle 2")
        await session_manager.disconnect_session(session_id)
        await session_manager.restore_session(session_id)
        
        # Cycle 3
        await session_manager.update_session(session_id, "user", "Cycle 3")
        
        session = await session_manager.get_session(session_id)
        assert len(session.conversation_context) == 3
        assert session.connection_state == ConnectionState.CONNECTED
    
    @pytest.mark.asyncio
    async def test_reconnect_after_timeout_fails(self, session_manager):
        """Test reconnection after timeout period fails gracefully."""
        manager = SessionManager(timeout_minutes=1)
        
        session_id = await manager.create_session()
        await manager.disconnect_session(session_id)
        
        # Simulate time passing beyond timeout
        session = manager._sessions[session_id]
        session.last_active = datetime.now() - timedelta(minutes=2)
        
        # Attempt reconnection
        restored = await manager.restore_session(session_id)
        
        assert restored is None


class TestSessionPersistence:
    """Test session persistence across reconnections (T103)."""
    
    @pytest.mark.asyncio
    async def test_conversation_context_preserved(self, session_manager):
        """Test conversation context preserved across reconnection."""
        session_id = await session_manager.create_session()
        
        # Add conversation history
        messages = [
            ("user", "What is the weather?"),
            ("assistant", "The weather is sunny."),
            ("user", "What about tomorrow?"),
            ("assistant", "Tomorrow will be cloudy."),
        ]
        
        for role, content in messages:
            await session_manager.update_session(session_id, role, content)
        
        # Disconnect and reconnect
        await session_manager.disconnect_session(session_id)
        restored = await session_manager.restore_session(session_id)
        
        # Verify all messages preserved
        assert len(restored.conversation_context) == 4
        for i, (role, content) in enumerate(messages):
            assert restored.conversation_context[i]["role"] == role
            assert restored.conversation_context[i]["content"] == content
    
    @pytest.mark.asyncio
    async def test_recent_context_filtering(self, session_manager):
        """Test get_recent_context filters old messages."""
        session_id = await session_manager.create_session()
        session = await session_manager.get_session(session_id)
        
        # Add old message
        session.add_message("user", "Old message")
        old_msg = session.conversation_context[0]
        old_msg["timestamp"] = datetime.now() - timedelta(minutes=10)
        
        # Add recent messages
        await session_manager.update_session(session_id, "user", "Recent 1")
        await session_manager.update_session(session_id, "assistant", "Recent 2")
        
        # Get recent context (5-minute window)
        recent = session.get_recent_context(window_minutes=5)
        
        # Should only include recent messages
        assert len(recent) == 2
        assert all("Recent" in msg["content"] for msg in recent)
    
    @pytest.mark.asyncio
    async def test_session_activity_prevents_expiration(self, session_manager):
        """Test session activity updates prevent expiration."""
        manager = SessionManager(timeout_minutes=1)
        
        session_id = await manager.create_session()
        
        # Touch session repeatedly to prevent expiration
        for _ in range(5):
            await asyncio.sleep(0.2)
            await manager.touch_session(session_id)
        
        # Session should still be valid
        session = await manager.get_session(session_id)
        assert session is not None
        assert not session.is_expired(timeout_minutes=1)
    
    @pytest.mark.asyncio
    async def test_conversation_buffer_limit(self, session_manager):
        """Test conversation buffer respects 100-message limit."""
        session_id = await session_manager.create_session()
        
        # Add 150 messages
        for i in range(150):
            await session_manager.update_session(session_id, "user", f"Message {i}")
        
        session = await session_manager.get_session(session_id)
        
        # Should only keep last 100
        assert len(session.conversation_context) == 100
        assert session.conversation_context[0]["content"] == "Message 50"
        assert session.conversation_context[-1]["content"] == "Message 149"


class TestSessionExpiration:
    """Test session expiration after timeout (T104)."""
    
    @pytest.mark.asyncio
    async def test_session_expires_after_5_minutes(self, session_manager):
        """Test session expires after configured timeout."""
        manager = SessionManager(timeout_minutes=5)
        
        session_id = await manager.create_session()
        
        # Manually set last_active to 6 minutes ago
        session = manager._sessions[session_id]
        session.last_active = datetime.now() - timedelta(minutes=6)
        
        # Verify session is expired
        assert session.is_expired(timeout_minutes=5)
        
        # get_session should return None and clean up
        retrieved = await manager.get_session(session_id)
        assert retrieved is None
        assert session_id not in manager._sessions
    
    @pytest.mark.asyncio
    async def test_cleanup_removes_expired_sessions(self, session_manager):
        """Test background cleanup removes expired sessions."""
        manager = SessionManager(timeout_minutes=1, cleanup_interval=1)
        
        # Create sessions
        active_id = await manager.create_session()
        expired_id1 = await manager.create_session()
        expired_id2 = await manager.create_session()
        
        # Expire 2 sessions
        manager._sessions[expired_id1].last_active = datetime.now() - timedelta(minutes=2)
        manager._sessions[expired_id2].last_active = datetime.now() - timedelta(minutes=2)
        
        # Run cleanup
        count = await manager.cleanup_expired_sessions()
        
        assert count == 2
        assert active_id in manager._sessions
        assert expired_id1 not in manager._sessions
        assert expired_id2 not in manager._sessions
    
    @pytest.mark.asyncio
    async def test_cleanup_task_runs_automatically(self, session_manager):
        """Test cleanup task runs automatically at interval."""
        manager = SessionManager(timeout_minutes=1, cleanup_interval=1)
        
        # Create expired session
        session_id = await manager.create_session()
        manager._sessions[session_id].last_active = datetime.now() - timedelta(minutes=2)
        
        # Start cleanup task
        await manager.start_cleanup_task()
        
        # Wait for cleanup to run
        await asyncio.sleep(1.5)
        
        # Session should be cleaned up
        assert session_id not in manager._sessions
        
        # Stop cleanup
        await manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_inactive_session_expires(self, session_manager):
        """Test session expires without activity."""
        manager = SessionManager(timeout_minutes=1)
        
        session_id = await manager.create_session()
        
        # Don't touch the session
        # Manually advance time
        session = manager._sessions[session_id]
        session.last_active = datetime.now() - timedelta(minutes=2)
        
        # Session should be expired
        assert session.is_expired(timeout_minutes=1)


class TestReconnectionLatency:
    """Test reconnection performance (T105)."""
    
    @pytest.mark.asyncio
    async def test_session_creation_latency(self, session_manager):
        """Test session creation completes quickly."""
        start = asyncio.get_event_loop().time()
        
        session_id = await session_manager.create_session()
        
        end = asyncio.get_event_loop().time()
        latency_ms = (end - start) * 1000
        
        # Should complete in <10ms
        assert latency_ms < 10
        assert session_id is not None
    
    @pytest.mark.asyncio
    async def test_session_restoration_latency(self, session_manager):
        """Test session restoration completes quickly."""
        # Create session with context
        session_id = await session_manager.create_session()
        for i in range(10):
            await session_manager.update_session(session_id, "user", f"Message {i}")
        
        await session_manager.disconnect_session(session_id)
        
        # Measure restoration time
        start = asyncio.get_event_loop().time()
        
        restored = await session_manager.restore_session(session_id)
        
        end = asyncio.get_event_loop().time()
        latency_ms = (end - start) * 1000
        
        # Should complete in <10ms
        assert latency_ms < 10
        assert restored is not None
    
    @pytest.mark.asyncio
    async def test_concurrent_session_operations(self, session_manager):
        """Test multiple concurrent session operations."""
        # Create multiple sessions concurrently
        start = asyncio.get_event_loop().time()
        
        session_ids = await asyncio.gather(
            session_manager.create_session(),
            session_manager.create_session(),
            session_manager.create_session(),
        )
        
        end = asyncio.get_event_loop().time()
        latency_ms = (end - start) * 1000
        
        # Should complete in <50ms total
        assert latency_ms < 50
        assert len(session_ids) == 3
        assert len(set(session_ids)) == 3  # All unique
    
    @pytest.mark.asyncio
    async def test_high_volume_session_updates(self, session_manager):
        """Test high volume of session updates."""
        session_id = await session_manager.create_session()
        
        start = asyncio.get_event_loop().time()
        
        # Add 100 messages
        for i in range(100):
            await session_manager.update_session(session_id, "user", f"Message {i}")
        
        end = asyncio.get_event_loop().time()
        total_ms = (end - start) * 1000
        avg_ms = total_ms / 100
        
        # Average should be <1ms per update
        assert avg_ms < 1.0


class TestWebSocketLifecycleEndToEnd:
    """End-to-end WebSocket lifecycle scenarios."""
    
    @pytest.mark.asyncio
    async def test_complete_conversation_with_disconnect(self, session_manager):
        """Test complete conversation flow with network interruption."""
        # Initial connection
        session_id = await session_manager.create_session()
        
        # Conversation part 1
        await session_manager.update_session(session_id, "user", "Tell me about Python")
        await session_manager.update_session(session_id, "assistant", "Python is a programming language...")
        
        # Network disconnect
        await session_manager.disconnect_session(session_id)
        
        # Wait briefly
        await asyncio.sleep(0.1)
        
        # Reconnect
        restored = await session_manager.restore_session(session_id)
        assert restored is not None
        
        # Conversation part 2 continues
        await session_manager.update_session(session_id, "user", "Tell me more")
        await session_manager.update_session(session_id, "assistant", "Python supports multiple paradigms...")
        
        # Verify complete conversation
        session = await session_manager.get_session(session_id)
        assert len(session.conversation_context) == 4
        assert session.connection_state == ConnectionState.CONNECTED
    
    @pytest.mark.asyncio
    async def test_multiple_rapid_disconnects(self, session_manager):
        """Test handling of multiple rapid disconnect/reconnect cycles."""
        session_id = await session_manager.create_session()
        
        # Simulate 5 rapid disconnect/reconnect cycles
        for i in range(5):
            await session_manager.update_session(session_id, "user", f"Message {i}")
            await session_manager.disconnect_session(session_id)
            await asyncio.sleep(0.05)
            await session_manager.restore_session(session_id)
        
        # Verify session still valid with all messages
        session = await session_manager.get_session(session_id)
        assert session is not None
        assert session.connection_state == ConnectionState.CONNECTED
        assert len(session.conversation_context) == 5
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_on_timeout(self, session_manager):
        """Test graceful handling when session times out."""
        manager = SessionManager(timeout_minutes=1)
        
        # Create session
        old_session_id = await manager.create_session()
        await manager.update_session(old_session_id, "user", "Previous conversation")
        
        # Disconnect and expire
        await manager.disconnect_session(old_session_id)
        session = manager._sessions[old_session_id]
        session.last_active = datetime.now() - timedelta(minutes=2)
        
        # Attempt to restore (should fail)
        restored = await manager.restore_session(old_session_id)
        assert restored is None
        
        # Create new session (client fallback)
        new_session_id = await manager.create_session()
        assert new_session_id != old_session_id
        
        # New conversation starts fresh
        new_session = await manager.get_session(new_session_id)
        assert len(new_session.conversation_context) == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_during_active_sessions(self, session_manager):
        """Test cleanup doesn't affect active sessions."""
        manager = SessionManager(timeout_minutes=1)
        
        # Create active sessions
        active1 = await manager.create_session()
        active2 = await manager.create_session()
        
        # Create expired session
        expired = await manager.create_session()
        manager._sessions[expired].last_active = datetime.now() - timedelta(minutes=2)
        
        # Run cleanup
        count = await manager.cleanup_expired_sessions()
        
        assert count == 1
        assert active1 in manager._sessions
        assert active2 in manager._sessions
        assert expired not in manager._sessions
    
    @pytest.mark.asyncio
    async def test_session_stats_accuracy(self, session_manager):
        """Test session statistics reflect actual state."""
        # Create sessions in different states
        connected1 = await session_manager.create_session()
        connected2 = await session_manager.create_session()
        disconnected1 = await session_manager.create_session()
        
        await session_manager.disconnect_session(disconnected1)
        
        stats = await session_manager.get_stats()
        
        assert stats["total_sessions"] == 3
        assert stats["active_sessions"] == 2
        assert stats["disconnected_sessions"] == 1
        assert stats["timeout_minutes"] == 5
