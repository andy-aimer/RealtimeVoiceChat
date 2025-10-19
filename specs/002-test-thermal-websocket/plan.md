# Implementation Plan: Phase 2 Infrastructure Improvements

**Branch**: `002-test-thermal-websocket` | **Date**: October 19, 2025 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-test-thermal-websocket/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Fix critical test suite thread cleanup in `turndetect.py` (P1), implement thermal workload reduction at 85°C for Raspberry Pi 5 hardware protection (P2), and add WebSocket lifecycle management with automatic reconnection (P3). Technical approach: context managers for thread lifecycle, CPU temperature monitoring via `/sys/class/thermal/`, client-side exponential backoff reconnection with 5-minute session persistence.

## Technical Context

**Language/Version**: Python 3.12 (3.10+ required)  
**Primary Dependencies**: FastAPI, WebSockets, threading, contextlib, pytest (pytest-xdist optional)  
**Storage**: In-memory dict-based session storage (5-minute timeout)  
**Testing**: pytest with coverage reporting (≥60% target for Phase 2)  
**Target Platform**: Raspberry Pi 5 (8GB RAM) primary, macOS/Linux development secondary  
**Project Type**: Single project (Python server application with WebSocket frontend)  
**Performance Goals**: Test suite <5 minutes, thermal response <10 seconds, WebSocket reconnection <10 seconds (90th percentile)  
**Constraints**: <2% CPU monitoring overhead, <300 lines per file, offline-first (no external services), thermal protection latency <1 second  
**Scale/Scope**: Single-user deployment, 43 existing Phase 1 tests + new Phase 2 tests, 3 new features (thread cleanup, thermal, WebSocket)

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

### Principle 0: Offline-First Architecture ✅ PASS

- **Thread cleanup**: No external dependencies, pure Python threading
- **Thermal monitoring**: Local `/sys/class/thermal/` reads, no cloud APIs
- **WebSocket**: Client-side reconnection logic, no external services
- **Verdict**: All features maintain 100% offline capability

### Principle 1: Reliability First ✅ PASS

- **Thread cleanup**: Context managers ensure proper teardown, no silent thread leaks
- **Thermal monitoring**: Graceful fallback when temperature unavailable (return -1)
- **WebSocket**: Exponential backoff (10 retry limit), clear error states, session persistence
- **Logging**: CRITICAL for thermal triggers, INFO for recovery, structured error context
- **Verdict**: All features implement graceful failure handling and comprehensive logging

### Principle 2: Observability (Edge-Optimized) ✅ PASS

- **Monitoring overhead**: Thermal polling <0.5% CPU (1-second intervals)
- **Test metrics**: Coverage reporting integrated (≥60% target)
- **WebSocket**: Connection state tracking, health checks (30s ping/pong)
- **Logging**: JSON-structured logs for thermal events, thread lifecycle, reconnection attempts
- **Verdict**: Observability appropriate for Pi 5 edge deployment, minimal overhead

### Principle 3: Security (Deployment-Dependent) ✅ PASS

- **Personal/offline use**: Basic input validation only (temperature thresholds, session IDs)
- **Error sanitization**: No path leaks in thread cleanup errors
- **No authentication changes**: WebSocket security unchanged from Phase 1
- **Verdict**: Security posture appropriate for personal/offline deployment target

### Principle 4: Maintainability ✅ PASS

- **File organization**: New modules under existing structure (code/monitoring/, code/utils/)
- **Line limits**: All new files <300 lines (ThermalMonitor ~150 lines, WebSocketManager ~200 lines)
- **Single responsibility**: TurnDetector cleanup, ThermalMonitor, WebSocketSession (separate concerns)
- **Documentation**: Inline docstrings, module-level README updates
- **Verdict**: Maintains Phase 1 modular architecture, adheres to file size limits

### Principle 5: Testability ✅ PASS

- **Coverage target**: ≥60% for Phase 2 code (personal deployment standard)
- **Unit tests**: Thread lifecycle, thermal threshold logic, reconnection backoff algorithm
- **Integration tests**: Full test suite execution (<5 min), thermal simulation, WebSocket disconnect/reconnect
- **Critical paths**: Thread cleanup during pytest teardown, thermal protection trigger/resume, session persistence
- **Verdict**: Test strategy appropriate for personal deployment, critical paths covered

### Constitution Verdict: ✅ ALL PRINCIPLES SATISFIED

**No complexity violations.** Feature adheres to all constitutional principles without exceptions. Proceed to Phase 0 research.

## Project Structure

### Documentation (this feature)

```
specs/002-test-thermal-websocket/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (to be created)
├── data-model.md        # Phase 1 output (to be created)
├── quickstart.md        # Phase 1 output (to be created)
├── contracts/           # Phase 1 output (to be created)
├── checklists/          # Validation artifacts
│   └── requirements.md  # Spec quality checklist (14/14 PASS)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
code/
├── server.py                      # [EXISTS] FastAPI server, WebSocket routes
├── turndetect.py                  # [MODIFY] Add context manager lifecycle for thread cleanup
├── audio_module.py                # [EXISTS] Audio processing callbacks
├── llm_module.py                  # [MODIFY] Add thermal throttling integration
├── speech_pipeline_manager.py    # [EXISTS] Orchestrates STT→LLM→TTS pipeline
├── transcribe.py                  # [EXISTS] RealtimeSTT integration
├── monitoring/                    # [NEW DIRECTORY]
│   ├── __init__.py
│   ├── thermal_monitor.py         # [NEW] Raspberry Pi 5 CPU temperature monitoring
│   └── resource_metrics.py        # [EXISTS from Phase 1] Extend with thermal metrics
├── utils/                         # [NEW DIRECTORY]
│   ├── __init__.py
│   ├── lifecycle.py               # [NEW] Context managers for thread cleanup
│   └── backoff.py                 # [NEW] Exponential backoff utilities
├── websocket/                     # [NEW DIRECTORY]
│   ├── __init__.py
│   ├── session_manager.py         # [NEW] Session persistence (5-min timeout)
│   └── reconnection.py            # [NEW] Client reconnection state machine
├── static/
│   ├── app.js                     # [MODIFY] Add WebSocket reconnection logic
│   ├── index.html                 # [MODIFY] Add connection status UI
│   └── [pcmWorkletProcessor.js, ttsPlaybackProcessor.js] # [UNCHANGED]
└── [other existing files unchanged]

tests/
├── unit/                          # [NEW DIRECTORY]
│   ├── test_thread_cleanup.py     # [NEW] TurnDetector lifecycle tests
│   ├── test_thermal_monitor.py    # [NEW] Temperature threshold and hysteresis tests
│   └── test_reconnection.py       # [NEW] Exponential backoff algorithm tests
├── integration/                   # [NEW DIRECTORY]
│   ├── test_full_suite.py         # [NEW] Verify pytest completes <5 min
│   ├── test_thermal_integration.py # [NEW] Thermal protection with LLM/TTS
│   └── test_websocket_lifecycle.py # [NEW] Disconnect/reconnect scenarios
└── [Phase 1 tests remain in tests/ root - to be organized later]

docker/
├── Dockerfile                     # [EXISTS] Standard Linux deployment
└── Dockerfile.pi5                 # [EXISTS from Phase 1] ARM64 Raspberry Pi 5
```

**Structure Decision**: Single project Python server application. New directories for `monitoring/`, `utils/`, and `websocket/` modules maintain Phase 1's flat `code/` structure while organizing Phase 2 features. Tests split into `unit/` and `integration/` subdirectories for clarity (Phase 1 tests remain in root `tests/` to avoid regression). Client-side changes isolated to `static/app.js` and `static/index.html`.

---

## Phase 0: Research (Outline & Unknowns)

_See [research.md](./research.md) for detailed technical investigation._

### Critical Unknowns Identified

1. **Thread Cleanup Root Cause**: What specifically causes `turndetect.py` threads to hang during pytest teardown?
2. **Raspberry Pi 5 Thermal Interface**: What is the exact file path and format for CPU temperature on Pi 5?
3. **WebSocket Session Persistence**: How to store session state without external database (in-memory structure)?
4. **Test Isolation Strategy**: Is pytest-xdist required or can context managers solve thread leakage?
5. **Thermal Hysteresis Logic**: How to prevent oscillation when temperature fluctuates around 85°C threshold?

### Research Deliverables (research.md)

- Python threading lifecycle investigation (daemon threads, `join()`, context managers)
- Raspberry Pi 5 thermal monitoring documentation (`/sys/class/thermal/thermal_zone0/temp`)
- WebSocket reconnection patterns (exponential backoff algorithms, session token strategies)
- pytest plugin analysis (pytest-xdist for process isolation, fixtures for cleanup)
- Hysteresis implementation patterns (Schmitt trigger logic, state machines)

---

## Phase 1: Design (Data Model, Contracts, Quickstart)

_See design artifacts in this directory for detailed specifications._

### Data Model (data-model.md)

**ThermalState** (monitoring/thermal_monitor.py):

```python
@dataclass
class ThermalState:
    current_temp: float          # Celsius
    threshold_temp: float = 85.0  # Trigger protection
    resume_temp: float = 80.0     # Hysteresis lower bound
    protection_active: bool = False
    last_checked: datetime
```

**WebSocketSession** (websocket/session_manager.py):

```python
@dataclass
class WebSocketSession:
    session_id: str              # UUID
    connection_state: ConnectionState  # CONNECTED, DISCONNECTED, RECONNECTING
    last_active: datetime
    reconnection_attempts: int = 0
    conversation_context: Dict[str, Any]  # Preserve across reconnections
```

**ThreadLifecycle** (utils/lifecycle.py):

```python
class ManagedThread(threading.Thread):
    """Context manager wrapper for proper thread cleanup"""
    def __enter__(self) -> 'ManagedThread': ...
    def __exit__(self, exc_type, exc_val, exc_tb) -> None: ...
    def stop(self) -> None: ...  # Signal thread to terminate
```

### API Contracts (contracts/)

**ThermalMonitor Interface** (contracts/thermal_monitor.md):

```python
class ThermalMonitor:
    def get_temperature() -> float:
        """Returns CPU temp in Celsius or -1 if unavailable"""

    def check_thermal_protection() -> bool:
        """Returns True if protection triggered (≥85°C)"""

    def register_throttle_callback(callback: Callable[[float], None]) -> None:
        """Register function to call when thermal protection triggers"""
```

**WebSocket Session Manager** (contracts/websocket_session.md):

```python
class SessionManager:
    def create_session(session_id: str, context: Dict) -> WebSocketSession:
        """Create new session with 5-min timeout"""

    def restore_session(session_id: str) -> Optional[WebSocketSession]:
        """Restore session if within timeout window"""

    def cleanup_expired_sessions() -> int:
        """Remove sessions inactive >5 minutes, return count removed"""
```

### Quickstart (quickstart.md)

**Thread Cleanup Testing**:

```bash
# Before fix: Test suite hangs
pytest tests/ --timeout=300  # Times out after 5 minutes

# After fix: Test suite completes
pytest tests/ --cov=code --cov-report=html
# Expected: <5 minutes, ≥60% coverage, all tests pass
```

**Thermal Protection Demo** (Raspberry Pi 5 only):

```bash
# Generate CPU load to trigger thermal protection
stress-ng --cpu 4 --timeout 60s &
python -m code.monitoring.thermal_monitor --simulate
# Expected: CRITICAL log at 85°C, INFO log at 80°C resume
```

**WebSocket Reconnection**:

```bash
# Start server
python code/server.py

# In browser console (disconnect network, then reconnect):
# Expected: "Reconnecting (attempt 1/10)..." → "Connected" within 10s
```

---

## Phase 2: Implementation Tasks

_See [tasks.md](./tasks.md) for detailed task breakdown (created by /speckit.tasks command)._

### High-Level Implementation Sequence

**Sprint 1: Thread Cleanup (P1)** - Unblock CI/CD

1. Investigate `turndetect.py` thread lifecycle with profiling
2. Implement `ManagedThread` context manager in `utils/lifecycle.py`
3. Refactor `TurnDetector` to use context manager
4. Add unit tests for thread cleanup (100% coverage target)
5. Verify full test suite execution <5 minutes

**Sprint 2: Thermal Protection (P2)** - Hardware safety

1. Implement `ThermalMonitor` class with Pi 5 interface
2. Add temperature polling loop (1-second intervals)
3. Implement hysteresis logic (85°C trigger, 80°C resume)
4. Integrate thermal throttling callbacks into `llm_module.py`
5. Add thermal protection tests (unit + integration)

**Sprint 3: WebSocket Lifecycle (P3)** - Connection reliability

1. Implement `SessionManager` with in-memory dict storage
2. Add session expiration cleanup (5-minute timeout)
3. Implement client-side reconnection logic (`static/app.js`)
4. Add exponential backoff with 10-retry limit
5. Add connection status UI (`static/index.html`)
6. Test disconnect/reconnect scenarios (integration tests)

**Sprint 4: Integration & Validation**

1. Run full test suite 10 times (verify no hangs)
2. Thermal stress testing on Pi 5 (or simulation)
3. WebSocket disconnect testing (network simulation)
4. Coverage validation (≥60% target)
5. Update documentation (README, deployment guides)

---

## Success Verification

### Acceptance Criteria Mapping

**P1: Thread Cleanup**

- ✅ SC-001: Test suite completes in <5 minutes (10/10 runs)
- ✅ SC-002: GitHub Actions CI completes without timeout
- ✅ SC-003: Coverage report generated (≥60%)
- ✅ SC-004: Zero orphaned threads after test completion
- ✅ SC-005: 50% improvement over file-by-file execution time

**P2: Thermal Protection**

- ✅ SC-006: Protection triggers within 10s of 85°C
- ✅ SC-007: Temperature capped at 87°C during load
- ✅ SC-008: Resumes within 30s of dropping below 80°C
- ✅ SC-009: Zero thermal crashes during stress testing
- ✅ SC-010: Clear notification logs (CRITICAL/INFO)

**P3: WebSocket Reliability**

- ✅ SC-011: 95% recovery rate for disconnections <60s
- ✅ SC-012: 100% session preservation for disconnections <5 min
- ✅ SC-013: Clear error messages for reconnection failures
- ✅ SC-014: 90% reconnections succeed within 10s
- ✅ SC-015: Zero data loss during disconnect/reconnect

### Testing Strategy

**Unit Tests** (≥60% coverage target):

- `test_thread_cleanup.py`: ManagedThread lifecycle, stop signals, context manager behavior
- `test_thermal_monitor.py`: Temperature reading, threshold logic, hysteresis, platform fallback
- `test_reconnection.py`: Exponential backoff algorithm, retry limits, backoff timing

**Integration Tests**:

- `test_full_suite.py`: Verify full pytest execution <5 minutes, coverage generation
- `test_thermal_integration.py`: Thermal trigger → LLM throttle → resume workflow
- `test_websocket_lifecycle.py`: Disconnect → reconnect → session restore → conversation continuity

**Manual Testing** (Raspberry Pi 5 required):

- Thermal stress testing with `stress-ng` (verify 85°C trigger, 80°C resume)
- Long-running conversation test (verify no thread leaks over 30 minutes)
- Network disconnection scenarios (Wi-Fi toggle, router reboot)

---

## Risk Mitigation

### High-Impact Risks

**Risk**: Thread cleanup doesn't fully resolve pytest hanging

- **Mitigation**: Implement pytest-xdist as fallback for process isolation
- **Fallback**: Document file-by-file execution strategy, add Makefile target

**Risk**: Cannot reproduce thermal conditions in development (no Pi 5)

- **Mitigation**: Implement thermal simulation mode with configurable temperature
- **Validation**: Defer hardware validation to Pi 5 owner testing

**Risk**: WebSocket reconnection creates memory leaks

- **Mitigation**: Implement strict 5-minute session timeout, add memory profiling tests
- **Monitoring**: Track session dict size in health check metrics

### Medium-Impact Risks

**Risk**: Thermal protection triggers too frequently (false positives)

- **Mitigation**: Implement 2°C hysteresis (80°C resume, 85°C trigger)
- **Configuration**: Make thresholds configurable via environment variables

**Risk**: WebSocket reconnection conflicts with Phase 1 error handling

- **Mitigation**: Review Phase 1 WebSocket code before implementation
- **Testing**: Add integration tests for error scenario compatibility

---

## Dependencies & Blockers

### Must Have Before Starting

- ✅ Phase 1 completion and merge to main (COMPLETED)
- ✅ Phase 2 specification validated (14/14 checklist items PASS)
- ✅ Constitution check passed (all 6 principles satisfied)

### Nice to Have

- ⏳ Raspberry Pi 5 hardware access (for thermal validation)
- ⏳ Network simulation tools (for WebSocket testing)

### External Dependencies

- Python threading library (stdlib, no installation)
- pytest-xdist (optional, install if needed: `pip install pytest-xdist`)
- stress-ng (optional, for thermal testing: `sudo apt install stress-ng`)

---

## Timeline Estimate

**Sprint 1 (Thread Cleanup)**: 3-5 days

- Investigation: 1 day
- Implementation: 2 days
- Testing: 1-2 days

**Sprint 2 (Thermal Protection)**: 4-6 days

- Implementation: 2-3 days
- Integration: 1-2 days
- Testing: 1 day

**Sprint 3 (WebSocket Lifecycle)**: 5-7 days

- Backend: 2-3 days
- Frontend: 2-3 days
- Testing: 1 day

**Sprint 4 (Integration & Validation)**: 2-3 days

**Total Estimate**: 14-21 days (3-4 weeks)

---

## Open Questions (Resolved During Planning)

1. ~~Should thermal workload reduction be gradual or binary?~~
   - **Decision**: Binary on/off at 85°C for simplicity (can enhance later)
2. ~~What should be the maximum WebSocket session persistence time?~~
   - **Decision**: 5 minutes (industry standard for session timeout)
3. ~~Should thread cleanup use context managers, explicit cleanup, or both?~~

   - **Decision**: Both - context managers for test convenience, explicit cleanup for production

4. ~~Is pytest-xdist required or optional?~~

   - **Decision**: Optional - try context managers first, use pytest-xdist as fallback

5. ~~How to test thermal protection without Raspberry Pi 5 hardware?~~
   - **Decision**: Implement thermal simulation mode with configurable temperature

---

**Next Step**: Execute `/speckit.tasks` command to generate detailed task breakdown in `tasks.md`.
