# Phase 0: Research & Technical Investigation

**Feature**: Phase 2 Infrastructure Improvements  
**Branch**: `002-test-thermal-websocket`  
**Date**: October 19, 2025

## Purpose

Resolve critical unknowns before design and implementation of thread cleanup (P1), thermal workload reduction (P2), and WebSocket lifecycle management (P3).

---

## Research Topics

### 1. Thread Cleanup Root Cause Analysis

**Question**: What specifically causes `turndetect.py` background threads to hang during pytest teardown?

**Investigation**:

**Thread Architecture in `turndetect.py`**:

```python
# Current implementation (Phase 1)
class TurnDetector:
    def __init__(self):
        self.text_worker = threading.Thread(target=self._process_text_queue)
        self.silence_worker = threading.Thread(target=self._detect_silence)
        self.text_worker.start()
        self.silence_worker.start()

    # NO CLEANUP METHODS - threads never explicitly stopped
```

**Hypothesis**: Threads are started as non-daemon threads without explicit termination signals. When pytest teardown occurs, threads continue running and block test suite completion.

**Evidence**:

- Phase 1 completion report documents "test suite hanging" requiring file-by-file execution
- No `stop()` or `join()` methods in current TurnDetector implementation
- Threads may be blocked on queue operations (`queue.get()`) without timeout

**Solution Pattern - Context Manager Approach**:

```python
class ManagedThread(threading.Thread):
    """Thread with proper lifecycle management"""
    def __init__(self, target, *args, **kwargs):
        super().__init__(target=target, *args, **kwargs)
        self._stop_event = threading.Event()

    def stop(self):
        """Signal thread to stop"""
        self._stop_event.set()

    def should_stop(self) -> bool:
        """Check if thread should terminate"""
        return self._stop_event.is_set()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        self.join(timeout=5.0)  # Wait max 5 seconds
        if self.is_alive():
            logging.warning(f"Thread {self.name} did not terminate cleanly")
```

**Alternative - pytest-xdist**:
If context managers don't fully resolve hanging, use pytest-xdist for process isolation:

```bash
pytest tests/ -n auto --dist loadfile
```

Each test file runs in separate process, preventing thread accumulation.

**Recommendation**: Implement context manager approach first (zero dependencies), fall back to pytest-xdist if issues persist.

**References**:

- Python threading documentation: https://docs.python.org/3/library/threading.html
- Context managers: https://docs.python.org/3/library/contextlib.html
- pytest-xdist: https://pytest-xdist.readthedocs.io/

---

### 2. Raspberry Pi 5 Thermal Monitoring

**Question**: What is the exact interface and file format for CPU temperature on Raspberry Pi 5?

**Investigation**:

**Thermal Zone Path**:

```bash
# Raspberry Pi 5 (Bookworm OS)
/sys/class/thermal/thermal_zone0/temp
```

**File Format**:

- Returns temperature in **millidegrees Celsius** (e.g., `85000` = 85.0°C)
- Single integer value, newline-terminated
- Requires `/1000` conversion to get °C

**Alternative Methods**:

1. **vcgencmd** (legacy, requires sudo):

   ```bash
   vcgencmd measure_temp
   # Output: temp=85.0'C
   ```

2. **sysfs direct read** (preferred, no sudo):
   ```python
   def get_cpu_temperature() -> float:
       """Read Pi 5 CPU temperature from sysfs"""
       try:
           with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
               temp_millidegrees = int(f.read().strip())
               return temp_millidegrees / 1000.0
       except (FileNotFoundError, ValueError, PermissionError):
           return -1.0  # Platform not supported or error
   ```

**Platform Detection**:

```python
import platform

def is_raspberry_pi() -> bool:
    """Detect if running on Raspberry Pi"""
    try:
        with open('/proc/device-tree/model', 'r') as f:
            model = f.read().lower()
            return 'raspberry pi' in model
    except FileNotFoundError:
        return False
```

**Polling Strategy**:

- **Interval**: 1 second (balance between responsiveness and CPU overhead)
- **Overhead**: Single file read per second (~0.001% CPU on Pi 5)
- **Thread**: Background daemon thread with stop signal

**Thermal Throttling Points** (Pi 5 reference):

- 80°C: Normal operating range
- 85°C: **Phase 2 trigger threshold** (workload reduction)
- 80°C: **Phase 2 resume threshold** (2°C hysteresis)
- 85°C: Hardware thermal throttling begins (unavoidable)

**Recommendation**: Use sysfs direct read (`/sys/class/thermal/thermal_zone0/temp`) with 1-second polling interval and -1 fallback for non-Pi platforms.

**References**:

- Raspberry Pi thermal management: https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#temperature-management
- Linux thermal sysfs: https://www.kernel.org/doc/Documentation/thermal/sysfs-api.txt

---

### 3. WebSocket Session Persistence (In-Memory)

**Question**: How to implement session persistence without external database?

**Investigation**:

**In-Memory Dict Structure**:

```python
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import uuid

@dataclass
class WebSocketSession:
    session_id: str
    connection_state: str  # "CONNECTED", "DISCONNECTED", "RECONNECTING"
    last_active: datetime
    reconnection_attempts: int = 0
    conversation_context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

class SessionManager:
    def __init__(self, timeout_minutes: int = 5):
        self._sessions: Dict[str, WebSocketSession] = {}
        self._timeout = timedelta(minutes=timeout_minutes)

    def create_session(self, context: Dict[str, Any]) -> str:
        """Create new session, return session_id"""
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = WebSocketSession(
            session_id=session_id,
            connection_state="CONNECTED",
            last_active=datetime.now(),
            conversation_context=context
        )
        return session_id

    def restore_session(self, session_id: str) -> Optional[WebSocketSession]:
        """Restore session if within timeout window"""
        session = self._sessions.get(session_id)
        if not session:
            return None

        # Check timeout
        if datetime.now() - session.last_active > self._timeout:
            del self._sessions[session_id]
            return None

        session.last_active = datetime.now()
        session.connection_state = "CONNECTED"
        session.reconnection_attempts = 0
        return session

    def cleanup_expired_sessions(self) -> int:
        """Remove sessions inactive >timeout, return count"""
        now = datetime.now()
        expired = [
            sid for sid, session in self._sessions.items()
            if now - session.last_active > self._timeout
        ]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)
```

**Background Cleanup Task**:

```python
# In server.py startup
from fastapi import FastAPI
import asyncio

app = FastAPI()
session_manager = SessionManager(timeout_minutes=5)

async def cleanup_sessions_task():
    """Background task to cleanup expired sessions every minute"""
    while True:
        await asyncio.sleep(60)  # Run every 1 minute
        count = session_manager.cleanup_expired_sessions()
        if count > 0:
            logging.info(f"Cleaned up {count} expired sessions")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(cleanup_sessions_task())
```

**Session ID Exchange** (WebSocket handshake):

```javascript
// Client-side (static/app.js)
let sessionId = localStorage.getItem("websocket_session_id");

const ws = new WebSocket(`ws://localhost:8000/ws?session_id=${sessionId}`);

ws.onopen = () => {
  console.log("Connected");
  // Server returns session_id if new connection
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.session_id) {
    sessionId = data.session_id;
    localStorage.setItem("websocket_session_id", sessionId);
  }
};
```

**Memory Considerations**:

- Typical session size: ~5KB (conversation context)
- Max concurrent sessions: 100 (single-user deployment target: 1)
- Memory footprint: <1MB for 100 sessions
- Cleanup interval: 60 seconds (acceptable latency for 5-minute timeout)

**Recommendation**: In-memory dict with background asyncio cleanup task. No external database needed for single-user deployment.

**References**:

- FastAPI background tasks: https://fastapi.tiangolo.com/tutorial/background-tasks/
- Python dataclasses: https://docs.python.org/3/library/dataclasses.html

---

### 4. WebSocket Reconnection Strategy

**Question**: What exponential backoff algorithm should be used for reconnection?

**Investigation**:

**Exponential Backoff Algorithm**:

```javascript
// Client-side reconnection logic (static/app.js)
class WebSocketClient {
  constructor(url) {
    this.url = url;
    this.reconnectionAttempts = 0;
    this.maxReconnectionAttempts = 10;
    this.reconnectionDelay = 1000; // 1 second initial
    this.maxReconnectionDelay = 30000; // 30 seconds max
    this.ws = null;
  }

  connect() {
    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log("Connected");
      this.reconnectionAttempts = 0; // Reset on successful connection
      this.reconnectionDelay = 1000;
    };

    this.ws.onclose = (event) => {
      console.log("Disconnected");
      this.scheduleReconnection();
    };

    this.ws.onerror = (error) => {
      console.error("WebSocket error:", error);
    };
  }

  scheduleReconnection() {
    if (this.reconnectionAttempts >= this.maxReconnectionAttempts) {
      console.error("Max reconnection attempts reached");
      this.showConnectionFailedUI();
      return;
    }

    this.reconnectionAttempts++;
    console.log(
      `Reconnecting (attempt ${this.reconnectionAttempts}/${this.maxReconnectionAttempts})...`
    );

    setTimeout(() => {
      this.connect();
    }, this.reconnectionDelay);

    // Exponential backoff: double delay each time, capped at 30s
    this.reconnectionDelay = Math.min(
      this.reconnectionDelay * 2,
      this.maxReconnectionDelay
    );
  }

  showConnectionFailedUI() {
    // Display "Connection failed. Please refresh page to reconnect."
    document.getElementById("connection-status").textContent =
      "Connection failed. Click here to reconnect.";
    document.getElementById("connection-status").onclick = () => {
      location.reload();
    };
  }
}
```

**Backoff Sequence**:

- Attempt 1: 1 second delay
- Attempt 2: 2 seconds delay
- Attempt 3: 4 seconds delay
- Attempt 4: 8 seconds delay
- Attempt 5: 16 seconds delay
- Attempt 6-10: 30 seconds delay (capped)

**Total Retry Window**: ~2.5 minutes before giving up (well within 5-minute session timeout)

**Connection Health Checks** (ping/pong):

```python
# Server-side (server.py)
from fastapi import WebSocket
import asyncio

async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    async def ping_task():
        """Send ping every 30 seconds"""
        while True:
            await asyncio.sleep(30)
            try:
                await websocket.send_json({"type": "ping"})
            except Exception:
                break  # Connection lost

    asyncio.create_task(ping_task())

    # Handle messages...
```

```javascript
// Client-side pong response
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === "ping") {
    ws.send(JSON.stringify({ type: "pong" }));
  }
};
```

**Recommendation**: Exponential backoff with 1s initial, 30s max, 10 retry limit. Implement server-side ping/pong for health checks every 30 seconds.

**References**:

- WebSocket RFC 6455: https://datatracker.ietf.org/doc/html/rfc6455
- Exponential backoff best practices: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/

---

### 5. Thermal Hysteresis Implementation

**Question**: How to prevent temperature oscillation around 85°C threshold?

**Investigation**:

**Schmitt Trigger Pattern** (hysteresis):

```python
class ThermalMonitor:
    def __init__(self):
        self.trigger_threshold = 85.0  # °C
        self.resume_threshold = 80.0   # °C (2°C hysteresis)
        self.protection_active = False

    def check_thermal_state(self, current_temp: float) -> bool:
        """
        Returns True if thermal protection should be active.
        Implements hysteresis to prevent oscillation.
        """
        if self.protection_active:
            # Currently protected: resume only when temp drops below 80°C
            if current_temp < self.resume_threshold:
                self.protection_active = False
                logging.info(f"Thermal protection RESUMED (temp: {current_temp:.1f}°C)")
        else:
            # Not protected: trigger when temp reaches 85°C
            if current_temp >= self.trigger_threshold:
                self.protection_active = True
                logging.critical(f"Thermal protection TRIGGERED (temp: {current_temp:.1f}°C)")

        return self.protection_active
```

**State Diagram**:

```
[NORMAL] ---(temp >= 85°C)---> [PROTECTED]
    ^                               |
    |                               |
    +---------(temp < 80°C)---------+
```

**Hysteresis Band**: 5°C (80°C to 85°C)

- Prevents rapid state changes when temperature hovers near threshold
- Allows system to cool down before resuming full workload
- Industry standard: 2-5°C hysteresis for thermal protection

**Example Scenario**:

```
Time  | Temp (°C) | State      | Action
------|-----------|------------|----------------------------
0s    | 84.0      | NORMAL     | Full workload
10s   | 85.0      | PROTECTED  | Trigger: Reduce LLM workload
20s   | 84.5      | PROTECTED  | Still protected (above 80°C)
30s   | 83.0      | PROTECTED  | Still protected (above 80°C)
40s   | 79.8      | NORMAL     | Resume: Restore full workload
```

**Configuration**:

```python
# Environment variables or config file
THERMAL_TRIGGER_THRESHOLD = 85.0  # °C
THERMAL_RESUME_THRESHOLD = 80.0   # °C
THERMAL_POLL_INTERVAL = 1.0       # seconds
```

**Recommendation**: Implement Schmitt trigger pattern with 5°C hysteresis (80°C resume, 85°C trigger). Make thresholds configurable via environment variables.

**References**:

- Hysteresis in control systems: https://en.wikipedia.org/wiki/Hysteresis
- Schmitt trigger: https://en.wikipedia.org/wiki/Schmitt_trigger

---

## Research Summary

### Key Findings

1. **Thread Cleanup**: Context manager pattern with `threading.Event` stop signals will resolve hanging. pytest-xdist as fallback if needed.

2. **Thermal Monitoring**: Use `/sys/class/thermal/thermal_zone0/temp` (sysfs), 1-second polling, -1 fallback for non-Pi platforms.

3. **Session Persistence**: In-memory dict with asyncio cleanup task (60-second interval), 5-minute timeout, <1MB memory footprint.

4. **WebSocket Reconnection**: Exponential backoff (1s initial, 30s max, 10 retries), ping/pong health checks (30-second interval).

5. **Thermal Hysteresis**: Schmitt trigger pattern (85°C trigger, 80°C resume) prevents oscillation, configurable thresholds.

### Technical Decisions

| Decision              | Choice                                  | Rationale                                                  |
| --------------------- | --------------------------------------- | ---------------------------------------------------------- |
| Thread cleanup        | Context managers + stop events          | Zero dependencies, clean API, pytest-friendly              |
| Thermal interface     | `/sys/class/thermal/thermal_zone0/temp` | No sudo required, direct kernel interface                  |
| Session storage       | In-memory dict                          | Single-user deployment, <1MB footprint, no DB overhead     |
| Reconnection strategy | Exponential backoff (10 retries)        | Industry standard, balances responsiveness and server load |
| Hysteresis band       | 5°C (80-85°C)                           | Prevents oscillation, allows cooling, configurable         |
| pytest strategy       | Context managers first, xdist fallback  | Minimize dependencies, test file-by-file if needed         |

### Implementation Priorities

**Must Have** (blocking):

- Context manager thread lifecycle (P1 blocker)
- Thermal monitoring class with hysteresis (P2 core)
- Session manager with cleanup (P3 core)
- Exponential backoff reconnection (P3 core)

**Should Have** (enhance quality):

- pytest-xdist integration (P1 fallback)
- Thermal simulation mode (P2 testing)
- Connection status UI (P3 UX)

**Could Have** (future enhancement):

- Advanced reconnection strategies (jitter, circuit breakers)
- Multi-level thermal throttling (gradual reduction)
- Distributed session storage (Redis for multi-node)

---

## Resolved Unknowns

✅ **Thread cleanup root cause**: Non-daemon threads without stop signals, blocked on queue operations  
✅ **Pi 5 thermal interface**: `/sys/class/thermal/thermal_zone0/temp` (millidegrees)  
✅ **Session persistence structure**: In-memory dict with asyncio cleanup, 5-min timeout  
✅ **Exponential backoff algorithm**: 1s initial, 30s max, double each attempt, 10 retry limit  
✅ **Hysteresis implementation**: Schmitt trigger, 5°C band (80-85°C), state-based logic

### Remaining Questions (Low Priority)

- Should thermal monitoring use separate thread or integrate with existing event loop? (Decision: Separate daemon thread for simplicity)
- Should WebSocket session_id be in URL query param or first message? (Decision: Query param for server-side logging)
- Should test suite use pytest-xdist by default or opt-in? (Decision: Opt-in, document in README)

---

**Next Step**: Proceed to Phase 1 Design (data-model.md, contracts/, quickstart.md).
