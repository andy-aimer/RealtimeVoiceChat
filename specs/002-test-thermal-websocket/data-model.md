# Phase 1 Design: Data Model

**Feature**: Phase 2 Infrastructure Improvements  
**Branch**: `002-test-thermal-websocket`  
**Date**: October 19, 2025

## Purpose

Define data structures, state management, and entity relationships for thread lifecycle management (P1), thermal monitoring (P2), and WebSocket session persistence (P3).

---

## Entity Definitions

### 1. ThermalState (P2: Thermal Monitoring)

**Module**: `code/monitoring/thermal_monitor.py`

**Purpose**: Track CPU temperature and thermal protection state with hysteresis logic.

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

@dataclass
class ThermalState:
    """Raspberry Pi 5 thermal monitoring state"""

    # Current readings
    current_temp: float  # Celsius, -1 if unavailable
    last_checked: datetime = field(default_factory=datetime.now)

    # Thresholds (configurable)
    trigger_threshold: float = 85.0  # °C - activate protection
    resume_threshold: float = 80.0   # °C - deactivate protection (hysteresis)

    # State flags
    protection_active: bool = False  # True when workload reduction active
    platform_supported: bool = True  # False on non-Pi platforms

    # Statistics
    trigger_count: int = 0  # Number of times protection triggered
    max_temp_observed: float = 0.0  # Historical max temperature

    def should_trigger_protection(self) -> bool:
        """Check if protection should activate (Schmitt trigger upper threshold)"""
        return self.current_temp >= self.trigger_threshold

    def should_resume_normal(self) -> bool:
        """Check if protection should deactivate (Schmitt trigger lower threshold)"""
        return self.current_temp < self.resume_threshold

    def update_temperature(self, new_temp: float) -> bool:
        """Update temperature, return True if state changed"""
        self.current_temp = new_temp
        self.last_checked = datetime.now()
        self.max_temp_observed = max(self.max_temp_observed, new_temp)

        old_state = self.protection_active

        if self.protection_active:
            # Currently protected: check for resume condition
            if self.should_resume_normal():
                self.protection_active = False
        else:
            # Not protected: check for trigger condition
            if self.should_trigger_protection():
                self.protection_active = True
                self.trigger_count += 1

        return old_state != self.protection_active  # True if state changed
```

**Relationships**:

- Read by: `ThermalMonitor` (polling loop)
- Consumed by: `LLMModule` (workload throttling), `AudioProcessor` (TTS pausing)
- Logged by: `monitoring/resource_metrics.py` (health check integration)

**State Transitions**:

```
┌─────────────────────────────────────────────────┐
│ NORMAL (protection_active = False)              │
│ - Full LLM inference rate                       │
│ - TTS processing active                         │
└───────────┬─────────────────────────────────────┘
            │
            │ temp >= 85.0°C (trigger)
            │
            ▼
┌─────────────────────────────────────────────────┐
│ PROTECTED (protection_active = True)            │
│ - Reduced LLM inference rate OR paused          │
│ - TTS synthesis paused OR queued                │
└───────────┬─────────────────────────────────────┘
            │
            │ temp < 80.0°C (resume)
            │
            ▼
         [NORMAL]
```

**Configuration**:

```python
# Environment variables or config file
THERMAL_TRIGGER_THRESHOLD = 85.0  # °C
THERMAL_RESUME_THRESHOLD = 80.0   # °C
THERMAL_POLL_INTERVAL = 1.0       # seconds
THERMAL_ENABLED = True            # Master enable/disable
```

---

### 2. WebSocketSession (P3: Connection Reliability)

**Module**: `code/websocket/session_manager.py`

**Purpose**: Persist conversation state during temporary disconnections, enable reconnection within timeout window.

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

class ConnectionState(str, Enum):
    """WebSocket connection states"""
    CONNECTED = "CONNECTED"          # Active connection
    DISCONNECTED = "DISCONNECTED"    # Connection lost, within timeout
    RECONNECTING = "RECONNECTING"    # Client attempting reconnection
    EXPIRED = "EXPIRED"              # Session timeout exceeded

@dataclass
class WebSocketSession:
    """Session state for WebSocket connections"""

    # Identity
    session_id: str  # UUID v4

    # Connection state
    connection_state: ConnectionState = ConnectionState.CONNECTED
    last_active: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)

    # Reconnection tracking
    reconnection_attempts: int = 0  # Client-side retry count
    last_reconnection_attempt: Optional[datetime] = None

    # Conversation context (persisted across reconnections)
    conversation_context: Dict[str, Any] = field(default_factory=dict)
    # Example context:
    # {
    #     "conversation_history": [...],  # Recent messages
    #     "user_preferences": {...},      # Voice settings, language
    #     "last_audio_timestamp": 123.45  # For resuming playback
    # }

    # Metadata
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None

    def is_expired(self, timeout_minutes: int = 5) -> bool:
        """Check if session has exceeded timeout window"""
        from datetime import timedelta
        timeout = timedelta(minutes=timeout_minutes)
        return datetime.now() - self.last_active > timeout

    def touch(self) -> None:
        """Update last_active timestamp (keepalive)"""
        self.last_active = datetime.now()

    def mark_disconnected(self) -> None:
        """Mark session as disconnected"""
        self.connection_state = ConnectionState.DISCONNECTED
        self.touch()

    def mark_reconnecting(self) -> None:
        """Mark session as attempting reconnection"""
        self.connection_state = ConnectionState.RECONNECTING
        self.reconnection_attempts += 1
        self.last_reconnection_attempt = datetime.now()

    def mark_connected(self) -> None:
        """Mark session as successfully connected/reconnected"""
        self.connection_state = ConnectionState.CONNECTED
        self.reconnection_attempts = 0
        self.last_reconnection_attempt = None
        self.touch()
```

**Relationships**:

- Managed by: `SessionManager` (in-memory dict storage)
- Created by: WebSocket connection handler (`server.py`)
- Restored by: Client reconnection with session_id query param
- Cleaned up by: Background asyncio task (60-second interval)

**Lifecycle**:

```
┌─────────────────────────────────────────────────┐
│ CREATE (new WebSocket connection)               │
│ - Generate UUID session_id                      │
│ - Initialize conversation_context = {}          │
└───────────┬─────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────┐
│ CONNECTED                                       │
│ - Active bidirectional communication            │
│ - Touch last_active on each message             │
└───────────┬─────────────────────────────────────┘
            │
            │ Network disconnection / server restart
            │
            ▼
┌─────────────────────────────────────────────────┐
│ DISCONNECTED                                    │
│ - Session preserved in memory                   │
│ - Wait for reconnection (5-min timeout)         │
└───────────┬─────────────────────────────────────┘
            │
            │ Client reconnects with session_id
            │
            ▼
┌─────────────────────────────────────────────────┐
│ RECONNECTING                                    │
│ - Validate session_id exists                    │
│ - Check timeout window                          │
└───────────┬─────────────────────────────────────┘
            │
            │ Restore success
            │
            ▼
         [CONNECTED]
            │
            │ 5-min timeout OR explicit close
            │
            ▼
┌─────────────────────────────────────────────────┐
│ EXPIRED                                         │
│ - Remove from SessionManager                    │
│ - Conversation context lost                     │
└─────────────────────────────────────────────────┘
```

**Storage**:

```python
# In-memory storage structure (SessionManager)
class SessionManager:
    def __init__(self):
        self._sessions: Dict[str, WebSocketSession] = {}
        # Example:
        # {
        #     "a1b2c3d4-...": WebSocketSession(...),
        #     "e5f6g7h8-...": WebSocketSession(...)
        # }
```

---

### 3. ThreadLifecycle (P1: Thread Cleanup)

**Module**: `code/utils/lifecycle.py`

**Purpose**: Provide clean abstraction for thread lifecycle management with explicit stop signals and context manager support.

```python
import threading
import logging
from typing import Optional, Callable
from contextlib import contextmanager

class ManagedThread(threading.Thread):
    """Thread with explicit lifecycle management and stop signaling"""

    def __init__(self, target: Callable, name: Optional[str] = None,
                 daemon: bool = False, *args, **kwargs):
        super().__init__(target=self._wrap_target(target), name=name,
                        daemon=daemon, *args, **kwargs)
        self._stop_event = threading.Event()
        self._target = target
        self._logger = logging.getLogger(f"ManagedThread.{name or 'unnamed'}")

    def _wrap_target(self, target: Callable) -> Callable:
        """Wrap target function to handle stop event"""
        def wrapper(*args, **kwargs):
            try:
                return target(*args, **kwargs)
            except Exception as e:
                self._logger.error(f"Thread {self.name} crashed: {e}")
                raise
        return wrapper

    def stop(self) -> None:
        """Signal thread to stop gracefully"""
        self._logger.info(f"Stopping thread {self.name}")
        self._stop_event.set()

    def should_stop(self) -> bool:
        """Check if thread should terminate (poll from within thread)"""
        return self._stop_event.is_set()

    def join(self, timeout: Optional[float] = 5.0) -> bool:
        """
        Wait for thread to terminate.
        Returns True if thread stopped cleanly, False if timeout.
        """
        super().join(timeout=timeout)
        if self.is_alive():
            self._logger.warning(
                f"Thread {self.name} did not stop within {timeout}s timeout"
            )
            return False
        self._logger.info(f"Thread {self.name} stopped cleanly")
        return True

    def __enter__(self):
        """Context manager entry: start thread"""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit: stop and join thread"""
        self.stop()
        self.join(timeout=5.0)
        return False  # Don't suppress exceptions
```

**Usage Example** (Refactored TurnDetector):

```python
# Before (Phase 1 - thread leakage)
class TurnDetector:
    def __init__(self):
        self.text_worker = threading.Thread(target=self._process_text)
        self.silence_worker = threading.Thread(target=self._detect_silence)
        self.text_worker.start()
        self.silence_worker.start()
    # NO CLEANUP

# After (Phase 2 - proper lifecycle)
from code.utils.lifecycle import ManagedThread

class TurnDetector:
    def __init__(self):
        self.text_worker = ManagedThread(
            target=self._process_text,
            name="text_processor"
        )
        self.silence_worker = ManagedThread(
            target=self._detect_silence,
            name="silence_detector"
        )
        self.text_worker.start()
        self.silence_worker.start()

    def _process_text(self):
        """Worker loop with stop signal checking"""
        while not self.text_worker.should_stop():
            try:
                # Use timeout to allow periodic stop checking
                item = self.text_queue.get(timeout=0.1)
                # Process item...
            except queue.Empty:
                continue

    def close(self):
        """Explicit cleanup method"""
        self.text_worker.stop()
        self.silence_worker.stop()
        self.text_worker.join(timeout=5.0)
        self.silence_worker.join(timeout=5.0)

    def __enter__(self):
        """Context manager support for tests"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Automatic cleanup in context manager"""
        self.close()
```

**Test Usage** (pytest fixture):

```python
import pytest

@pytest.fixture
def turn_detector():
    """Fixture with automatic cleanup"""
    with TurnDetector() as detector:
        yield detector
    # Cleanup happens automatically in __exit__

def test_turn_detection(turn_detector):
    # Test logic...
    pass
# Threads cleaned up after test completes
```

---

## Relationships Between Entities

### ThermalState → LLMModule Integration

```python
# code/llm_module.py (modified)
from code.monitoring.thermal_monitor import ThermalMonitor

class LLMModule:
    def __init__(self):
        self.thermal_monitor = ThermalMonitor()
        self.thermal_monitor.register_callback(self._on_thermal_event)

    def _on_thermal_event(self, state: ThermalState):
        """Handle thermal protection state changes"""
        if state.protection_active:
            logging.critical(
                f"THERMAL PROTECTION: Pausing LLM inference (temp: {state.current_temp:.1f}°C)"
            )
            self.pause_inference()
        else:
            logging.info(
                f"THERMAL RESUME: Resuming LLM inference (temp: {state.current_temp:.1f}°C)"
            )
            self.resume_inference()
```

### WebSocketSession → FastAPI WebSocket Handler

```python
# code/server.py (modified)
from fastapi import WebSocket, Query
from code.websocket.session_manager import SessionManager, WebSocketSession

session_manager = SessionManager(timeout_minutes=5)

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: Optional[str] = Query(None)
):
    await websocket.accept()

    # Restore existing session or create new
    if session_id:
        session = session_manager.restore_session(session_id)
        if session:
            logging.info(f"Session {session_id} restored")
        else:
            logging.warning(f"Session {session_id} expired or invalid")
            session_id = None

    if not session_id:
        session_id = session_manager.create_session(context={})
        logging.info(f"New session created: {session_id}")
        await websocket.send_json({"type": "session_created", "session_id": session_id})

    # ... handle messages ...
```

### ManagedThread → TurnDetector Integration

```python
# code/turndetect.py (modified)
from code.utils.lifecycle import ManagedThread

class TurnDetector:
    def __init__(self):
        self.text_worker = ManagedThread(target=self._process_text, name="text_worker")
        self.silence_worker = ManagedThread(target=self._detect_silence, name="silence_worker")

    def _process_text(self):
        """Worker with stop signal checking"""
        while not self.text_worker.should_stop():
            # Process with timeout to allow stop signal checks
            ...

    def close(self):
        """Explicit cleanup"""
        self.text_worker.stop()
        self.silence_worker.stop()
        self.text_worker.join()
        self.silence_worker.join()
```

---

## Data Flow Diagrams

### Thermal Monitoring Flow

```
┌─────────────────────┐
│ ThermalMonitor      │
│ (polling loop)      │
└──────────┬──────────┘
           │ Every 1 second
           │
           ▼
┌─────────────────────┐
│ Read temperature    │
│ /sys/class/thermal/ │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ ThermalState        │
│ .update_temperature │
└──────────┬──────────┘
           │ State changed?
           │
           ▼
┌─────────────────────┐
│ Notify callbacks    │
│ (LLM, TTS, Metrics) │
└─────────────────────┘
```

### WebSocket Reconnection Flow

```
┌─────────────────────┐
│ Client: Disconnect  │
│ (network loss)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Store session_id    │
│ localStorage        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Exponential backoff │
│ 1s, 2s, 4s, 8s...   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Reconnect with      │
│ session_id param    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Server: Restore     │
│ WebSocketSession    │
└──────────┬──────────┘
           │ Within 5-min timeout?
           │
           ▼
┌─────────────────────┐
│ Resume conversation │
│ (context preserved) │
└─────────────────────┘
```

### Thread Lifecycle Flow

```
┌─────────────────────┐
│ Test starts         │
│ (pytest fixture)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ with TurnDetector() │
│ __enter__           │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Threads start       │
│ (ManagedThread)     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Test executes       │
│ (business logic)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Test completes      │
│ __exit__ called     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Threads stop()      │
│ Threads join()      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Cleanup complete    │
│ (no orphaned)       │
└─────────────────────┘
```

---

## Configuration Schema

### Environment Variables

```bash
# Thermal monitoring (P2)
THERMAL_ENABLED=true                    # Master enable/disable
THERMAL_TRIGGER_THRESHOLD=85.0          # °C - activate protection
THERMAL_RESUME_THRESHOLD=80.0           # °C - deactivate protection
THERMAL_POLL_INTERVAL=1.0               # seconds
THERMAL_SIMULATION_MODE=false           # For testing without Pi 5

# WebSocket sessions (P3)
WEBSOCKET_SESSION_TIMEOUT_MINUTES=5     # Session expiration
WEBSOCKET_PING_INTERVAL_SECONDS=30      # Health check ping
WEBSOCKET_MAX_RECONNECTION_ATTEMPTS=10  # Client-side retry limit

# Thread lifecycle (P1)
THREAD_STOP_TIMEOUT_SECONDS=5.0         # Max wait for thread termination
THREAD_LOG_LEVEL=INFO                   # DEBUG for troubleshooting
```

### Configuration File (Optional)

```python
# code/config/phase2_config.py
from pydantic import BaseSettings

class Phase2Config(BaseSettings):
    """Phase 2 infrastructure configuration"""

    # Thermal
    thermal_enabled: bool = True
    thermal_trigger_threshold: float = 85.0
    thermal_resume_threshold: float = 80.0
    thermal_poll_interval: float = 1.0
    thermal_simulation_mode: bool = False

    # WebSocket
    websocket_session_timeout_minutes: int = 5
    websocket_ping_interval_seconds: int = 30
    websocket_max_reconnection_attempts: int = 10

    # Thread lifecycle
    thread_stop_timeout_seconds: float = 5.0
    thread_log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_prefix = ""
```

---

## Memory Footprint Estimates

| Entity                 | Size (bytes) | Max Count | Total Memory |
| ---------------------- | ------------ | --------- | ------------ |
| ThermalState           | ~200         | 1         | 200 bytes    |
| WebSocketSession       | ~5KB         | 100       | 500 KB       |
| ManagedThread overhead | ~1KB         | 10        | 10 KB        |
| **Total**              |              |           | **~510 KB**  |

**Analysis**: Negligible memory impact (<1MB) for single-user deployment. Session cleanup ensures bounded memory growth.

---

## Validation Checklist

✅ **ThermalState**: Implements hysteresis logic (5°C band)  
✅ **WebSocketSession**: Supports reconnection within 5-minute window  
✅ **ManagedThread**: Provides stop signal and context manager API  
✅ **Relationships**: Clear integration points with existing modules  
✅ **Configuration**: All thresholds configurable via environment variables  
✅ **Memory**: Bounded memory growth with cleanup mechanisms

---

**Next Step**: Generate API contracts (contracts/) and quickstart guide (quickstart.md).
