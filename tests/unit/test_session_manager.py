"""
Unit tests for WebSocket session management.

Tests the SessionManager, WebSocketSession, and ConnectionState classes
used for maintaining conversation context during reconnections.

Phase 2 P3 Tasks: T096-T100
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from src.session.session_manager import (
    ConnectionState,
    WebSocketSession,
    SessionManager
)


class TestConnectionState:
    """Test ConnectionState enum."""
    
    def test_connection_states_exist(self):
        """Test all expected connection states are defined."""
        assert hasattr(ConnectionState, 'CONNECTED')
        assert hasattr(ConnectionState, 'DISCONNECTED')
    
    def test_connection_state_values(self):
        """Test connection state string values."""
        assert ConnectionState.CONNECTED.value == "CONNECTED"
        assert ConnectionState.DISCONNECTED.value == "DISCONNECTED"
    
    def test_connection_state_equality(self):
        """Test connection state equality comparison."""
        state1 = ConnectionState.CONNECTED
        state2 = ConnectionState.CONNECTED
        state3 = ConnectionState.DISCONNECTED
        
        assert state1 == state2
        assert state1 != state3


class TestWebSocketSession:
    """Test WebSocketSession dataclass."""
    
    def test_session_initialization(self):
        """Test session initialization with required fields."""
        session = WebSocketSession(session_id="test-123")
        
        assert session.session_id == "test-123"
        assert session.connection_state == ConnectionState.DISCONNECTED
        assert session.reconnection_attempts == 0
        assert isinstance(session.last_active, datetime)
        assert isinstance(session.created_at, datetime)
        assert len(session.conversation_context) == 0
        assert session.user_id is None
    
    def test_session_with_custom_values(self):
        """Test session initialization with custom values."""
        now = datetime.now()
        session = WebSocketSession(
            session_id="test-456",
            connection_state=ConnectionState.CONNECTED,
            reconnection_attempts=3,
            user_id="user-789"
        )
        
        assert session.session_id == "test-456"
        assert session.connection_state == ConnectionState.CONNECTED
        assert session.reconnection_attempts == 3
        assert session.user_id == "user-789"
    
    def test_is_expired_not_expired(self):
        """Test is_expired returns False for active session."""
        session = WebSocketSession(session_id="test-123")
        
        assert not session.is_expired(timeout_minutes=5)
    
    def test_is_expired_after_timeout(self):
        """Test is_expired returns True after timeout."""
        session = WebSocketSession(session_id="test-123")
        
        # Manually set last_active to 6 minutes ago
        session.last_active = datetime.now() - timedelta(minutes=6)
        
        assert session.is_expired(timeout_minutes=5)
    
    def test_is_expired_custom_timeout(self):
        """Test is_expired with custom timeout."""
        session = WebSocketSession(session_id="test-123")
        
        # Set last_active to 2 minutes ago
        session.last_active = datetime.now() - timedelta(minutes=2)
        
        # Should be expired with 1-minute timeout
        assert session.is_expired(timeout_minutes=1)
        
        # Should not be expired with 5-minute timeout
        assert not session.is_expired(timeout_minutes=5)
    
    def test_touch_updates_last_active(self):
        """Test touch updates last_active timestamp."""
        session = WebSocketSession(session_id="test-123")
        
        old_time = session.last_active
        
        # Wait a tiny bit to ensure time difference
        asyncio.run(asyncio.sleep(0.01))
        
        session.touch()
        
        assert session.last_active > old_time
    
    def test_mark_connected(self):
        """Test mark_connected updates state and resets attempts."""
        session = WebSocketSession(session_id="test-123")
        session.reconnection_attempts = 5
        session.connection_state = ConnectionState.DISCONNECTED
        
        old_time = session.last_active
        asyncio.run(asyncio.sleep(0.01))
        
        session.mark_connected()
        
        assert session.connection_state == ConnectionState.CONNECTED
        assert session.reconnection_attempts == 0
        assert session.last_active > old_time
    
    def test_mark_disconnected(self):
        """Test mark_disconnected updates state and touches session."""
        session = WebSocketSession(session_id="test-123")
        session.connection_state = ConnectionState.CONNECTED
        
        old_time = session.last_active
        asyncio.run(asyncio.sleep(0.01))
        
        session.mark_disconnected()
        
        assert session.connection_state == ConnectionState.DISCONNECTED
        assert session.last_active > old_time
    
    def test_add_message_user(self):
        """Test adding user message to conversation context."""
        session = WebSocketSession(session_id="test-123")
        
        session.add_message("user", "Hello, how are you?")
        
        assert len(session.conversation_context) == 1
        msg = session.conversation_context[0]
        assert msg["role"] == "user"
        assert msg["content"] == "Hello, how are you?"
        assert isinstance(msg["timestamp"], datetime)
    
    def test_add_message_assistant(self):
        """Test adding assistant message to conversation context."""
        session = WebSocketSession(session_id="test-123")
        
        session.add_message("assistant", "I'm doing well, thank you!")
        
        assert len(session.conversation_context) == 1
        msg = session.conversation_context[0]
        assert msg["role"] == "assistant"
        assert msg["content"] == "I'm doing well, thank you!"
    
    def test_add_multiple_messages(self):
        """Test adding multiple messages maintains order."""
        session = WebSocketSession(session_id="test-123")
        
        session.add_message("user", "Message 1")
        session.add_message("assistant", "Message 2")
        session.add_message("user", "Message 3")
        
        assert len(session.conversation_context) == 3
        assert session.conversation_context[0]["content"] == "Message 1"
        assert session.conversation_context[1]["content"] == "Message 2"
        assert session.conversation_context[2]["content"] == "Message 3"
    
    def test_conversation_context_deque_limit(self):
        """Test conversation context respects maxlen (100 messages)."""
        session = WebSocketSession(session_id="test-123")
        
        # Add 150 messages
        for i in range(150):
            session.add_message("user", f"Message {i}")
        
        # Should only keep last 100
        assert len(session.conversation_context) == 100
        
        # First message should be #50 (0-49 dropped)
        assert session.conversation_context[0]["content"] == "Message 50"
        assert session.conversation_context[-1]["content"] == "Message 149"
    
    def test_get_recent_context_all_recent(self):
        """Test get_recent_context returns all messages within window."""
        session = WebSocketSession(session_id="test-123")
        
        session.add_message("user", "Message 1")
        session.add_message("assistant", "Message 2")
        session.add_message("user", "Message 3")
        
        recent = session.get_recent_context(window_minutes=5)
        
        assert len(recent) == 3
        assert recent[0]["content"] == "Message 1"
        assert recent[2]["content"] == "Message 3"
    
    def test_get_recent_context_excludes_old(self):
        """Test get_recent_context excludes old messages."""
        session = WebSocketSession(session_id="test-123")
        
        # Add old message
        session.add_message("user", "Old message")
        old_msg = session.conversation_context[0]
        old_msg["timestamp"] = datetime.now() - timedelta(minutes=10)
        
        # Add recent messages
        session.add_message("user", "Recent message 1")
        session.add_message("assistant", "Recent message 2")
        
        recent = session.get_recent_context(window_minutes=5)
        
        # Should only include recent messages
        assert len(recent) == 2
        assert all("Recent" in msg["content"] for msg in recent)
    
    def test_get_recent_context_custom_window(self):
        """Test get_recent_context with custom time window."""
        session = WebSocketSession(session_id="test-123")
        
        # Add message 2 minutes ago
        session.add_message("user", "2 min ago")
        msg1 = session.conversation_context[0]
        msg1["timestamp"] = datetime.now() - timedelta(minutes=2)
        
        # Add recent message
        session.add_message("user", "Just now")
        
        # 1-minute window: should only get recent message
        recent_1min = session.get_recent_context(window_minutes=1)
        assert len(recent_1min) == 1
        assert recent_1min[0]["content"] == "Just now"
        
        # 5-minute window: should get both messages
        recent_5min = session.get_recent_context(window_minutes=5)
        assert len(recent_5min) == 2
    
    def test_to_dict_serialization(self):
        """Test to_dict serialization for JSON responses."""
        session = WebSocketSession(session_id="test-789")
        session.mark_connected()
        session.reconnection_attempts = 2
        session.add_message("user", "Test message")
        session.user_id = "user-123"
        
        data = session.to_dict()
        
        assert data["session_id"] == "test-789"
        assert data["connection_state"] == "CONNECTED"
        assert data["reconnection_attempts"] == 2
        assert data["message_count"] == 1
        assert data["user_id"] == "user-123"
        assert isinstance(data["last_active"], str)  # ISO format
        assert isinstance(data["created_at"], str)


class TestSessionManager:
    """Test SessionManager class."""
    
    @pytest.mark.asyncio
    async def test_manager_initialization(self):
        """Test SessionManager initialization."""
        manager = SessionManager(timeout_minutes=5, cleanup_interval=60)
        
        assert manager._timeout_minutes == 5
        assert manager._cleanup_interval == 60
        assert len(manager._sessions) == 0
        assert manager._cleanup_task is None
        assert not manager._running
    
    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test creating a new session (T096)."""
        manager = SessionManager()
        
        session_id = await manager.create_session()
        
        # Verify UUID format (36 characters with dashes)
        assert len(session_id) == 36
        assert session_id.count('-') == 4
        
        # Verify session exists and is connected
        session = await manager.get_session(session_id)
        assert session is not None
        assert session.session_id == session_id
        assert session.connection_state == ConnectionState.CONNECTED
    
    @pytest.mark.asyncio
    async def test_create_session_with_context(self):
        """Test creating session with initial context."""
        manager = SessionManager()
        
        initial_context = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"}
            ]
        }
        
        session_id = await manager.create_session(context=initial_context)
        session = await manager.get_session(session_id)
        
        assert len(session.conversation_context) == 2
        assert session.conversation_context[0]["content"] == "Hello"
        assert session.conversation_context[1]["content"] == "Hi there"
    
    @pytest.mark.asyncio
    async def test_get_session_existing(self):
        """Test retrieving existing session."""
        manager = SessionManager()
        
        session_id = await manager.create_session()
        retrieved = await manager.get_session(session_id)
        
        assert retrieved is not None
        assert retrieved.session_id == session_id
    
    @pytest.mark.asyncio
    async def test_get_session_nonexistent(self):
        """Test retrieving nonexistent session returns None."""
        manager = SessionManager()
        
        session = await manager.get_session("nonexistent-id")
        
        assert session is None
    
    @pytest.mark.asyncio
    async def test_get_session_expired(self):
        """Test retrieving expired session returns None (T098)."""
        manager = SessionManager(timeout_minutes=1)
        
        session_id = await manager.create_session()
        
        # Manually expire the session
        session = manager._sessions[session_id]
        session.last_active = datetime.now() - timedelta(minutes=2)
        
        # Should return None and delete expired session
        retrieved = await manager.get_session(session_id)
        
        assert retrieved is None
        assert session_id not in manager._sessions
    
    @pytest.mark.asyncio
    async def test_restore_session_valid(self):
        """Test restoring valid disconnected session (T097)."""
        manager = SessionManager()
        
        # Create and disconnect session
        session_id = await manager.create_session()
        await manager.disconnect_session(session_id)
        
        # Add some context
        await manager.update_session(session_id, "user", "Test message")
        
        # Restore session
        restored = await manager.restore_session(session_id)
        
        assert restored is not None
        assert restored.session_id == session_id
        assert restored.connection_state == ConnectionState.CONNECTED
        assert len(restored.conversation_context) == 1
    
    @pytest.mark.asyncio
    async def test_restore_session_expired(self):
        """Test restoring expired session returns None."""
        manager = SessionManager(timeout_minutes=1)
        
        session_id = await manager.create_session()
        
        # Expire the session
        session = manager._sessions[session_id]
        session.last_active = datetime.now() - timedelta(minutes=2)
        
        # Attempt to restore
        restored = await manager.restore_session(session_id)
        
        assert restored is None
    
    @pytest.mark.asyncio
    async def test_restore_session_nonexistent(self):
        """Test restoring nonexistent session returns None."""
        manager = SessionManager()
        
        restored = await manager.restore_session("nonexistent-id")
        
        assert restored is None
    
    @pytest.mark.asyncio
    async def test_disconnect_session(self):
        """Test disconnecting session preserves data."""
        manager = SessionManager()
        
        session_id = await manager.create_session()
        await manager.update_session(session_id, "user", "Test message")
        
        await manager.disconnect_session(session_id)
        
        session = await manager.get_session(session_id)
        assert session is not None
        assert session.connection_state == ConnectionState.DISCONNECTED
        assert len(session.conversation_context) == 1
    
    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_session(self):
        """Test disconnecting nonexistent session doesn't raise error."""
        manager = SessionManager()
        
        # Should not raise exception
        await manager.disconnect_session("nonexistent-id")
    
    @pytest.mark.asyncio
    async def test_touch_session(self):
        """Test touching session prevents expiration (T100)."""
        manager = SessionManager(timeout_minutes=1)
        
        session_id = await manager.create_session()
        
        # Get initial last_active time
        session = manager._sessions[session_id]
        initial_time = session.last_active
        
        # Wait and touch
        await asyncio.sleep(0.1)
        await manager.touch_session(session_id)
        
        # Verify last_active updated
        assert session.last_active > initial_time
        
        # Session should not be expired
        assert not session.is_expired(timeout_minutes=1)
    
    @pytest.mark.asyncio
    async def test_touch_nonexistent_session(self):
        """Test touching nonexistent session doesn't raise error."""
        manager = SessionManager()
        
        # Should not raise exception
        await manager.touch_session("nonexistent-id")
    
    @pytest.mark.asyncio
    async def test_update_session(self):
        """Test updating session with messages."""
        manager = SessionManager()
        
        session_id = await manager.create_session()
        
        await manager.update_session(session_id, "user", "Hello")
        await manager.update_session(session_id, "assistant", "Hi there")
        
        session = await manager.get_session(session_id)
        assert len(session.conversation_context) == 2
        assert session.conversation_context[0]["content"] == "Hello"
        assert session.conversation_context[1]["content"] == "Hi there"
    
    @pytest.mark.asyncio
    async def test_update_nonexistent_session(self):
        """Test updating nonexistent session doesn't raise error."""
        manager = SessionManager()
        
        # Should not raise exception
        await manager.update_session("nonexistent-id", "user", "Test")
    
    @pytest.mark.asyncio
    async def test_delete_session(self):
        """Test deleting session."""
        manager = SessionManager()
        
        session_id = await manager.create_session()
        
        await manager.delete_session(session_id)
        
        # Session should no longer exist
        session = await manager.get_session(session_id)
        assert session is None
        assert session_id not in manager._sessions
    
    @pytest.mark.asyncio
    async def test_delete_nonexistent_session(self):
        """Test deleting nonexistent session doesn't raise error."""
        manager = SessionManager()
        
        # Should not raise exception
        await manager.delete_session("nonexistent-id")
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self):
        """Test cleaning up expired sessions (T099)."""
        manager = SessionManager(timeout_minutes=1)
        
        # Create 3 sessions
        id1 = await manager.create_session()
        id2 = await manager.create_session()
        id3 = await manager.create_session()
        
        # Expire 2 sessions
        manager._sessions[id1].last_active = datetime.now() - timedelta(minutes=2)
        manager._sessions[id2].last_active = datetime.now() - timedelta(minutes=2)
        
        # Run cleanup
        count = await manager.cleanup_expired_sessions()
        
        assert count == 2
        assert id1 not in manager._sessions
        assert id2 not in manager._sessions
        assert id3 in manager._sessions
    
    @pytest.mark.asyncio
    async def test_cleanup_no_expired_sessions(self):
        """Test cleanup with no expired sessions."""
        manager = SessionManager()
        
        await manager.create_session()
        await manager.create_session()
        
        count = await manager.cleanup_expired_sessions()
        
        assert count == 0
        assert len(manager._sessions) == 2
    
    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test retrieving session statistics."""
        manager = SessionManager(timeout_minutes=5)
        
        # Create sessions in different states
        id1 = await manager.create_session()  # Connected
        id2 = await manager.create_session()  # Connected
        id3 = await manager.create_session()  # Will disconnect
        
        await manager.disconnect_session(id3)
        
        stats = await manager.get_stats()
        
        assert stats["total_sessions"] == 3
        assert stats["active_sessions"] == 2
        assert stats["disconnected_sessions"] == 1
        assert stats["timeout_minutes"] == 5
    
    @pytest.mark.asyncio
    async def test_get_stats_empty(self):
        """Test statistics with no sessions."""
        manager = SessionManager()
        
        stats = await manager.get_stats()
        
        assert stats["total_sessions"] == 0
        assert stats["active_sessions"] == 0
        assert stats["disconnected_sessions"] == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_task_lifecycle(self):
        """Test starting and stopping cleanup task."""
        manager = SessionManager(cleanup_interval=1)
        
        # Start cleanup task
        await manager.start_cleanup_task()
        
        assert manager._running
        assert manager._cleanup_task is not None
        assert not manager._cleanup_task.done()
        
        # Stop cleanup task
        await manager.stop_cleanup_task()
        
        assert not manager._running
        assert manager._cleanup_task.done()
    
    @pytest.mark.asyncio
    async def test_cleanup_task_runs_periodically(self):
        """Test cleanup task runs at specified interval."""
        manager = SessionManager(timeout_minutes=1, cleanup_interval=1)
        
        # Create expired session
        session_id = await manager.create_session()
        manager._sessions[session_id].last_active = datetime.now() - timedelta(minutes=2)
        
        # Start cleanup task
        await manager.start_cleanup_task()
        
        # Wait for cleanup to run (slightly longer than interval)
        await asyncio.sleep(1.2)
        
        # Session should be cleaned up
        assert session_id not in manager._sessions
        
        # Stop cleanup task
        await manager.stop_cleanup_task()
    
    @pytest.mark.asyncio
    async def test_multiple_sessions_concurrent_operations(self):
        """Test concurrent operations on multiple sessions."""
        manager = SessionManager()
        
        # Create multiple sessions concurrently
        session_ids = await asyncio.gather(
            manager.create_session(),
            manager.create_session(),
            manager.create_session()
        )
        
        # Update sessions concurrently
        await asyncio.gather(
            manager.update_session(session_ids[0], "user", "Message 1"),
            manager.update_session(session_ids[1], "user", "Message 2"),
            manager.update_session(session_ids[2], "user", "Message 3")
        )
        
        # Verify all sessions exist with correct data
        for i, sid in enumerate(session_ids):
            session = await manager.get_session(sid)
            assert session is not None
            assert len(session.conversation_context) == 1
            assert session.conversation_context[0]["content"] == f"Message {i+1}"


class TestSessionManagerThreadSafety:
    """Test SessionManager thread safety with asyncio.Lock."""
    
    @pytest.mark.asyncio
    async def test_concurrent_session_creation(self):
        """Test creating sessions concurrently."""
        manager = SessionManager()
        
        # Create 10 sessions concurrently
        tasks = [manager.create_session() for _ in range(10)]
        session_ids = await asyncio.gather(*tasks)
        
        # All session IDs should be unique
        assert len(session_ids) == 10
        assert len(set(session_ids)) == 10
        
        # All sessions should exist
        assert len(manager._sessions) == 10
    
    @pytest.mark.asyncio
    async def test_concurrent_updates_same_session(self):
        """Test updating same session concurrently."""
        manager = SessionManager()
        
        session_id = await manager.create_session()
        
        # Update session concurrently
        tasks = [
            manager.update_session(session_id, "user", f"Message {i}")
            for i in range(20)
        ]
        await asyncio.gather(*tasks)
        
        # All messages should be added
        session = await manager.get_session(session_id)
        assert len(session.conversation_context) == 20
    
    @pytest.mark.asyncio
    async def test_concurrent_cleanup_and_access(self):
        """Test concurrent cleanup and session access."""
        manager = SessionManager(timeout_minutes=1)
        
        # Create sessions
        id1 = await manager.create_session()
        id2 = await manager.create_session()
        
        # Expire one session
        manager._sessions[id1].last_active = datetime.now() - timedelta(minutes=2)
        
        # Run cleanup and access concurrently
        cleanup_task = manager.cleanup_expired_sessions()
        access_task = manager.get_session(id2)
        
        count, session = await asyncio.gather(cleanup_task, access_task)
        
        assert count == 1  # One session cleaned
        assert session is not None  # Other session accessible
