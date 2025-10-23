# Contract: SessionManager Interface

**Feature**: Phase 2 Infrastructure Improvements  
**Module**: `code/websocket/session_manager.py`  
**Priority**: P3 (Connection Reliability)

## Purpose

Manage WebSocket session lifecycle with in-memory persistence, automatic cleanup, and reconnection support within configurable timeout window.

---

## Interface Definition

```python
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
import logging

class SessionManager:
    """
    Manages WebSocket session persistence for reconnection support.

    Features:
    - In-memory dict storage (no external database)
    - Automatic session expiration (default 5 minutes)
    - Background cleanup task (removes expired sessions)
    - Thread-safe for concurrent access

    Memory footprint: ~5KB per session, bounded by timeout
    """

    def __init__(self, timeout_minutes: int = 5):
        """
        Initialize session manager.

        Args:
            timeout_minutes: Session expiration timeout (default 5)

        Raises:
            ValueError: If timeout_minutes < 1
        """
        ...

    def create_session(
        self,
        context: Optional[Dict[str, Any]] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """
        Create new WebSocket session.

        Args:
            context: Initial conversation context (default: {})
            client_ip: Client IP address for logging
            user_agent: Client user agent for logging

        Returns:
            str: UUID session_id

        Side effects:
            - Stores session in internal dict
            - Sets connection_state = CONNECTED
            - Sets last_active = now

        Thread safety:
            - Safe for concurrent calls
        """
        ...

    def restore_session(self, session_id: str) -> Optional[WebSocketSession]:
        """
        Restore existing session for reconnection.

        Args:
            session_id: UUID from previous connection

        Returns:
            WebSocketSession: Restored session if valid
            None: If session_id not found or expired

        Behavior:
            - Returns None if session_id not in storage
            - Returns None if last_active > timeout window
            - Updates last_active timestamp on success
            - Resets reconnection_attempts to 0
            - Sets connection_state = CONNECTED

        Side effects:
            - Removes expired session from storage (if applicable)
            - Updates session last_active timestamp

        Thread safety:
            - Safe for concurrent calls
        """
        ...

    def update_session(
        self,
        session_id: str,
        context: Optional[Dict[str, Any]] = None,
        state: Optional[ConnectionState] = None
    ) -> bool:
        """
        Update existing session data.

        Args:
            session_id: Session to update
            context: New conversation context (merges with existing)
            state: New connection state

        Returns:
            bool: True if session updated, False if not found

        Behavior:
            - Updates last_active timestamp
            - Merges context (doesn't replace entirely)
            - Updates state if provided

        Thread safety:
            - Safe for concurrent calls
        """
        ...

    def touch_session(self, session_id: str) -> bool:
        """
        Update last_active timestamp (keepalive).

        Args:
            session_id: Session to touch

        Returns:
            bool: True if session exists, False otherwise

        Use case:
            - Call on every WebSocket message received
            - Prevents premature expiration during active conversation

        Thread safety:
            - Safe for concurrent calls
        """
        ...

    def delete_session(self, session_id: str) -> bool:
        """
        Explicitly remove session from storage.

        Args:
            session_id: Session to delete

        Returns:
            bool: True if session deleted, False if not found

        Use case:
            - User explicitly disconnects (not temporary)
            - Manual cleanup before timeout

        Thread safety:
            - Safe for concurrent calls
        """
        ...

    def cleanup_expired_sessions(self) -> int:
        """
        Remove all sessions exceeding timeout window.

        Returns:
            int: Number of sessions removed

        Behavior:
            - Iterates all sessions
            - Removes if (now - last_active) > timeout
            - Logs INFO for each removed session

        Performance:
            - O(n) where n = active session count
            - Designed for background task (60s interval)

        Thread safety:
            - Safe for concurrent calls
        """
        ...

    def get_session(self, session_id: str) -> Optional[WebSocketSession]:
        """
        Retrieve session without modifying state.

        Args:
            session_id: Session to retrieve

        Returns:
            WebSocketSession: Copy of session data
            None: If session not found

        Behavior:
            - Returns copy (caller can't mutate storage)
            - Does NOT update last_active
            - Does NOT check expiration (use restore_session for that)

        Thread safety:
            - Safe for concurrent calls
        """
        ...

    def list_active_sessions(self) -> List[str]:
        """
        Get list of all active session IDs.

        Returns:
            List[str]: Session IDs currently in storage

        Use case:
            - Health check metrics (session count)
            - Admin dashboard

        Thread safety:
            - Safe for concurrent calls
        """
        ...

    def get_session_count(self) -> int:
        """
        Get count of active sessions.

        Returns:
            int: Number of sessions in storage

        Thread safety:
            - Safe for concurrent calls
        """
        ...
```

---

## Data Structures

### WebSocketSession

```python
from dataclasses import dataclass, field
from enum import Enum

class ConnectionState(str, Enum):
    """WebSocket connection states"""
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    RECONNECTING = "RECONNECTING"
    EXPIRED = "EXPIRED"

@dataclass
class WebSocketSession:
    """WebSocket session data"""

    # Identity
    session_id: str  # UUID v4

    # State
    connection_state: ConnectionState = ConnectionState.CONNECTED
    last_active: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)

    # Reconnection tracking
    reconnection_attempts: int = 0
    last_reconnection_attempt: Optional[datetime] = None

    # Conversation data
    conversation_context: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
```

---

## Behavioral Contracts

### Session Creation

**MUST**:

- Generate unique UUID v4 for session_id
- Initialize conversation_context as empty dict if not provided
- Set connection_state = CONNECTED
- Set last_active and created_at = now
- Store session in internal dict immediately

**MUST NOT**:

- Reuse session_id (UUID collision extremely unlikely)
- Allow None session_id
- Create session if storage limit exceeded (fail fast)

### Session Restoration

**MUST**:

- Return None if session_id not found
- Return None if (now - last_active) > timeout
- Remove expired session from storage before returning None
- Update last_active on successful restoration
- Reset reconnection_attempts to 0
- Set connection_state = CONNECTED

**MUST NOT**:

- Return expired sessions
- Modify conversation_context during restoration
- Raise exceptions for missing sessions (return None)

### Session Expiration

**MUST**:

- Calculate expiration as (now - last_active) > timeout
- Remove expired sessions during cleanup_expired_sessions()
- Log INFO message for each expired session (include session_id)
- Continue cleanup if individual session removal fails

**MUST NOT**:

- Expire sessions based on created_at (use last_active)
- Block cleanup if logging fails
- Raise exceptions from cleanup (log errors only)

### Thread Safety

**MUST**:

- Use threading.Lock for all dict operations
- Release lock before calling external functions (callbacks, logging)
- Handle lock acquisition failures gracefully

**MUST NOT**:

- Hold lock during I/O operations
- Deadlock on recursive calls
- Allow race conditions in cleanup

---

## Error Handling

### Invalid Session ID

```python
# Missing session_id
session = manager.restore_session("nonexistent-uuid")
assert session is None  # No exception raised

# Expired session
session_id = manager.create_session()
time.sleep(301)  # 5 min 1 sec
session = manager.restore_session(session_id)
assert session is None  # Expired
```

### Concurrent Access

```python
# Thread 1: Create session
session_id = manager.create_session()

# Thread 2: Restore session (simultaneously)
session = manager.restore_session(session_id)
assert session is not None  # Thread-safe

# Thread 3: Cleanup (simultaneously)
count = manager.cleanup_expired_sessions()
# No race conditions or crashes
```

### Invalid Configuration

```python
# Invalid timeout
with pytest.raises(ValueError):
    manager = SessionManager(timeout_minutes=0)

with pytest.raises(ValueError):
    manager = SessionManager(timeout_minutes=-5)
```

---

## Performance Guarantees

| Operation                  | Maximum Latency | Notes                               |
| -------------------------- | --------------- | ----------------------------------- |
| create_session()           | 1 ms            | Dict insert + UUID generation       |
| restore_session()          | 5 ms            | Dict lookup + expiration check      |
| update_session()           | 2 ms            | Dict update                         |
| touch_session()            | 1 ms            | Timestamp update only               |
| delete_session()           | 1 ms            | Dict removal                        |
| cleanup_expired_sessions() | O(n)            | n = session count, ~1ms per session |
| get_session_count()        | <1 ms           | Dict size()                         |

**Memory Usage**: ~5KB per session (typical conversation_context)

**Scalability**:

- 100 sessions: 500 KB memory
- 1000 sessions: 5 MB memory (not expected for single-user deployment)
- Cleanup overhead: Negligible for <100 sessions

---

## Integration Examples

### FastAPI WebSocket Handler

```python
# code/server.py
from fastapi import FastAPI, WebSocket, Query
from code.websocket.session_manager import SessionManager

app = FastAPI()
session_manager = SessionManager(timeout_minutes=5)

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: Optional[str] = Query(None)
):
    await websocket.accept()

    # Restore or create session
    if session_id:
        session = session_manager.restore_session(session_id)
        if session:
            logging.info(f"Session restored: {session_id}")
            await websocket.send_json({
                "type": "session_restored",
                "session_id": session_id,
                "context": session.conversation_context
            })
        else:
            logging.warning(f"Session expired or invalid: {session_id}")
            session_id = None

    if not session_id:
        session_id = session_manager.create_session(
            client_ip=websocket.client.host
        )
        logging.info(f"New session created: {session_id}")
        await websocket.send_json({
            "type": "session_created",
            "session_id": session_id
        })

    try:
        while True:
            data = await websocket.receive_json()

            # Touch session on every message (keepalive)
            session_manager.touch_session(session_id)

            # Update conversation context
            if "message" in data:
                session_manager.update_session(
                    session_id,
                    context={"last_message": data["message"]}
                )

            # Handle message...
            await websocket.send_json({"status": "ok"})

    except WebSocketDisconnect:
        # Mark disconnected (session persists for 5 minutes)
        session_manager.update_session(
            session_id,
            state=ConnectionState.DISCONNECTED
        )
        logging.info(f"Session disconnected: {session_id}")
```

### Background Cleanup Task

```python
# code/server.py
import asyncio

async def cleanup_sessions_task():
    """Background task to remove expired sessions every 60 seconds"""
    while True:
        await asyncio.sleep(60)
        try:
            count = session_manager.cleanup_expired_sessions()
            if count > 0:
                logging.info(f"Cleaned up {count} expired sessions")
        except Exception as e:
            logging.error(f"Session cleanup failed: {e}")

@app.on_event("startup")
async def startup_event():
    """Start background tasks on server startup"""
    asyncio.create_task(cleanup_sessions_task())
    logging.info("Session cleanup task started")
```

### Health Check Integration

```python
# code/monitoring/resource_metrics.py
def get_health_status() -> dict:
    """Include session metrics in health check"""
    return {
        "status": "healthy",
        "active_sessions": session_manager.get_session_count(),
        "session_ids": session_manager.list_active_sessions()
    }
```

---

## Testing Contracts

### Unit Tests

```python
def test_session_creation():
    """Verify session creation generates valid UUID"""
    manager = SessionManager()
    session_id = manager.create_session()

    assert isinstance(session_id, str)
    assert len(session_id) == 36  # UUID format

    session = manager.get_session(session_id)
    assert session is not None
    assert session.connection_state == ConnectionState.CONNECTED

def test_session_expiration():
    """Verify sessions expire after timeout"""
    manager = SessionManager(timeout_minutes=1)
    session_id = manager.create_session()

    # Immediately restorable
    session = manager.restore_session(session_id)
    assert session is not None

    # Wait for expiration
    time.sleep(61)

    # Should return None after timeout
    session = manager.restore_session(session_id)
    assert session is None

def test_cleanup_expired_sessions():
    """Verify cleanup removes only expired sessions"""
    manager = SessionManager(timeout_minutes=1)

    # Create 5 sessions
    session_ids = [manager.create_session() for _ in range(5)]
    assert manager.get_session_count() == 5

    # Wait for expiration
    time.sleep(61)

    # Cleanup should remove all 5
    count = manager.cleanup_expired_sessions()
    assert count == 5
    assert manager.get_session_count() == 0

def test_touch_session_prevents_expiration():
    """Verify touch_session resets expiration timer"""
    manager = SessionManager(timeout_minutes=1)
    session_id = manager.create_session()

    # Touch every 30 seconds for 2 minutes
    for _ in range(4):
        time.sleep(30)
        success = manager.touch_session(session_id)
        assert success

    # Session should still be valid (touched within timeout)
    session = manager.restore_session(session_id)
    assert session is not None
```

### Integration Tests

```python
async def test_websocket_reconnection():
    """Verify WebSocket reconnection preserves session"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Connect with WebSocket
        async with client.websocket_connect("/ws") as ws:
            # Receive session_created message
            data = await ws.receive_json()
            assert data["type"] == "session_created"
            session_id = data["session_id"]

            # Send message
            await ws.send_json({"message": "Hello"})

            # Close connection
            await ws.close()

        # Reconnect with same session_id
        async with client.websocket_connect(f"/ws?session_id={session_id}") as ws:
            # Receive session_restored message
            data = await ws.receive_json()
            assert data["type"] == "session_restored"
            assert data["session_id"] == session_id

            # Conversation context preserved
            assert "last_message" in data["context"]
```

---

## Compliance Checklist

✅ **Offline-First**: In-memory storage, no external databases  
✅ **Reliability**: Graceful handling of expired sessions, no exceptions  
✅ **Observability**: Structured logging (INFO for cleanup, session lifecycle)  
✅ **Security**: No hardcoded secrets, session_id validation  
✅ **Maintainability**: Single responsibility (session management only)  
✅ **Testability**: All operations testable without WebSocket (unit tests)

---

**Version**: 1.0  
**Last Updated**: October 19, 2025
