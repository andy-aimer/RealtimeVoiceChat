"""
Session management for WebSocket connections.

Implements session lifecycle tracking, conversation context persistence,
and automatic cleanup for expired sessions per Phase 2 P3 specification.

Key Features:
- Binary connection state (CONNECTED/DISCONNECTED per clarifications)
- 5-minute session timeout with automatic cleanup
- Conversation context preservation (last 5 minutes)
- Thread-safe session operations
- Background cleanup task integration
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
import uuid
import asyncio
import threading
from collections import deque
import logging

logger = logging.getLogger(__name__)



class ConnectionState(str, Enum):
    """
    WebSocket connection states (binary state machine per clarification).
    
    Per spec clarification (2025-10-20): Binary state for Phase 2 simplicity.
    """
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"


@dataclass
class WebSocketSession:
    """
    Represents a WebSocket session with connection state and conversation context.
    
    Attributes:
        session_id: Unique session identifier (UUID)
        connection_state: Current connection state (CONNECTED/DISCONNECTED)
        reconnection_attempts: Client-side reconnection attempt counter
        last_active: Timestamp of last activity (for timeout calculation)
        conversation_context: Recent messages (timestamp-indexed, last 5 min)
        created_at: Session creation timestamp
        user_id: Optional user identifier (for future auth support)
    
    Lifecycle:
        DISCONNECTED → CONNECTED (on initial connection)
        CONNECTED → DISCONNECTED (on disconnect)
        DISCONNECTED → CONNECTED (on reconnection within timeout)
        DISCONNECTED → EXPIRED (after 5 minute timeout)
    """
    session_id: str
    connection_state: ConnectionState = ConnectionState.DISCONNECTED
    reconnection_attempts: int = 0
    last_active: datetime = field(default_factory=datetime.now)
    conversation_context: deque = field(default_factory=lambda: deque(maxlen=100))
    created_at: datetime = field(default_factory=datetime.now)
    user_id: Optional[str] = None
    
    def is_expired(self, timeout_minutes: int = 5) -> bool:
        """
        Check if session has exceeded timeout window.
        
        Args:
            timeout_minutes: Session timeout in minutes (default: 5)
            
        Returns:
            True if session is expired, False otherwise
        """
        elapsed = datetime.now() - self.last_active
        return elapsed > timedelta(minutes=timeout_minutes)
    
    def touch(self):
        """Update last_active timestamp to prevent expiration."""
        self.last_active = datetime.now()
    
    def mark_connected(self):
        """Mark session as connected, reset reconnection attempts."""
        self.connection_state = ConnectionState.CONNECTED
        self.reconnection_attempts = 0
        self.touch()
    
    def mark_disconnected(self):
        """Mark session as disconnected, preserve data for reconnection."""
        self.connection_state = ConnectionState.DISCONNECTED
        self.touch()
    
    def add_message(self, role: str, content: str):
        """
        Add message to conversation context with timestamp.
        
        Args:
            role: Message role ("user" or "assistant")
            content: Message content text
        """
        message = {
            "timestamp": datetime.now(),
            "role": role,
            "content": content
        }
        self.conversation_context.append(message)
        self.touch()
    
    def get_recent_context(self, window_minutes: int = 5) -> List[Dict[str, Any]]:
        """
        Get conversation messages from last N minutes.
        
        Args:
            window_minutes: Time window in minutes (default: 5)
            
        Returns:
            List of messages within time window
        """
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        return [
            msg for msg in self.conversation_context
            if msg["timestamp"] > cutoff
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize session to dictionary for JSON responses.
        
        Returns:
            Dictionary representation of session state
        """
        return {
            "session_id": self.session_id,
            "connection_state": self.connection_state.value,
            "reconnection_attempts": self.reconnection_attempts,
            "last_active": self.last_active.isoformat(),
            "created_at": self.created_at.isoformat(),
            "message_count": len(self.conversation_context),
            "user_id": self.user_id
        }


class SessionManager:
    """
    Manages WebSocket session lifecycle with automatic cleanup.
    
    Features:
    - In-memory session storage (per constitution's offline-first principle)
    - Thread-safe operations via asyncio.Lock
    - Background cleanup task (60-second interval)
    - Session persistence for 5 minutes after disconnection
    
    Usage:
        manager = SessionManager(timeout_minutes=5)
        await manager.start_cleanup_task()
        
        # On connection
        session_id = await manager.create_session()
        
        # On reconnection
        session = await manager.restore_session(session_id)
        
        # On disconnect
        await manager.disconnect_session(session_id)
        
        # On shutdown
        await manager.stop_cleanup_task()
    """
    
    def __init__(self, timeout_minutes: int = 5, cleanup_interval: int = 60):
        """
        Initialize session manager.
        
        Args:
            timeout_minutes: Session expiration timeout (default: 5)
            cleanup_interval: Seconds between cleanup runs (default: 60)
        """
        self._sessions: Dict[str, WebSocketSession] = {}
        self._timeout_minutes = timeout_minutes
        self._cleanup_interval = cleanup_interval
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        self._running = False
    
    async def create_session(self, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Create new session with unique ID.
        
        Args:
            context: Optional initial conversation context
            
        Returns:
            session_id (UUID string)
        """
        session_id = str(uuid.uuid4())
        
        async with self._lock:
            session = WebSocketSession(session_id=session_id)
            if context:
                # Initialize with existing context if provided
                for msg in context.get("messages", []):
                    session.add_message(msg.get("role", "user"), msg.get("content", ""))
            
            session.mark_connected()
            self._sessions[session_id] = session
        
        logger.info(f"Session created", extra={
            "event_type": "session_created",
            "session_id": session_id
        })
        
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[WebSocketSession]:
        """
        Retrieve session if it exists and is not expired.
        
        Args:
            session_id: Session identifier
            
        Returns:
            WebSocketSession if found and valid, None otherwise
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            
            if not session:
                return None
            
            if session.is_expired(self._timeout_minutes):
                # Session expired, remove it
                del self._sessions[session_id]
                logger.info(f"Session expired on retrieval", extra={
                    "event_type": "session_expired",
                    "session_id": session_id
                })
                return None
            
            return session
    
    async def restore_session(self, session_id: str) -> Optional[WebSocketSession]:
        """
        Restore disconnected session on reconnection.
        
        Args:
            session_id: Session identifier from client
            
        Returns:
            WebSocketSession if found and valid, None if expired or not found
        """
        session = await self.get_session(session_id)
        
        if session:
            async with self._lock:
                session.mark_connected()
            
            logger.info(f"Session restored", extra={
                "event_type": "session_restored",
                "session_id": session_id,
                "context_messages": len(session.conversation_context)
            })
        
        return session
    
    async def disconnect_session(self, session_id: str):
        """
        Mark session as disconnected, preserve data for reconnection.
        
        Args:
            session_id: Session identifier
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.mark_disconnected()
                
                logger.info(f"Session disconnected", extra={
                    "event_type": "session_disconnected",
                    "session_id": session_id
                })
    
    async def touch_session(self, session_id: str):
        """
        Update session last_active timestamp to prevent expiration.
        
        Args:
            session_id: Session identifier
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.touch()
    
    async def update_session(self, session_id: str, role: str, content: str):
        """
        Add message to session conversation context.
        
        Args:
            session_id: Session identifier
            role: Message role ("user" or "assistant")
            content: Message content
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.add_message(role, content)
    
    async def delete_session(self, session_id: str):
        """
        Immediately remove session (manual cleanup).
        
        Args:
            session_id: Session identifier
        """
        async with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                
                logger.info(f"Session deleted", extra={
                    "event_type": "session_deleted",
                    "session_id": session_id
                })
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Remove sessions inactive for longer than timeout.
        
        Returns:
            Number of sessions cleaned up
        """
        async with self._lock:
            expired = [
                sid for sid, session in self._sessions.items()
                if session.is_expired(self._timeout_minutes)
            ]
            
            for sid in expired:
                del self._sessions[sid]
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions", extra={
                "event_type": "sessions_cleaned",
                "count": len(expired)
            })
        
        return len(expired)
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get session manager statistics.
        
        Returns:
            Dictionary with session counts and stats
        """
        async with self._lock:
            total = len(self._sessions)
            active = sum(1 for s in self._sessions.values() 
                        if s.connection_state == ConnectionState.CONNECTED)
            disconnected = sum(1 for s in self._sessions.values()
                             if s.connection_state == ConnectionState.DISCONNECTED)
        
        return {
            "total_sessions": total,
            "active_sessions": active,
            "disconnected_sessions": disconnected,
            "timeout_minutes": self._timeout_minutes
        }
    
    async def _cleanup_loop(self):
        """Background task that periodically cleans up expired sessions."""
        logger.info(f"Session cleanup task started (interval: {self._cleanup_interval}s)")
        
        while self._running:
            try:
                await asyncio.sleep(self._cleanup_interval)
                
                if self._running:  # Check again after sleep
                    count = await self.cleanup_expired_sessions()
                    
            except asyncio.CancelledError:
                logger.info("Session cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in session cleanup loop: {e}", exc_info=True)
    
    async def start_cleanup_task(self):
        """Start background cleanup task."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._running = True
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Session cleanup task initialized")
    
    async def stop_cleanup_task(self):
        """Stop background cleanup task."""
        self._running = False
        
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Session cleanup task stopped")
