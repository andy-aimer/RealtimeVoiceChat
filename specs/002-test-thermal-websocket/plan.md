# Implementation Plan: Phase 2 Infrastructure Improvements

**Branch**: `002-test-thermal-websocket` | **Date**: 2025-10-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-test-thermal-websocket/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Phase 2 enhances RealtimeVoiceChat's infrastructure reliability with three priorities:

1. **P1 - Thread Cleanup**: Fix test suite hanging by implementing proper lifecycle management for background threads in TurnDetector
2. **P2 - Thermal Protection**: Add CPU temperature monitoring with automatic workload reduction at 85°C to protect Raspberry Pi 5 hardware
3. **P3 - WebSocket Lifecycle**: Implement graceful reconnection handling with exponential backoff and 5-minute session persistence

Technical approach: Context managers for resource cleanup, background monitoring thread with hysteresis for thermal protection, binary WebSocket state machine (CONNECTED/DISCONNECTED) with structured JSON logging for observability.

## Technical Context

**Language/Version**: Python 3.13  
**Primary Dependencies**: FastAPI, pytest, python-json-logger, psutil (for thermal monitoring)  
**Storage**: In-memory dict for session storage (5-minute timeout)  
**Testing**: pytest (60% coverage target), pytest-timeout for thread cleanup validation  
**Target Platform**: Raspberry Pi 5 (primary), macOS/Linux/Windows (dev platforms)  
**Project Type**: Web (FastAPI backend + JavaScript WebSocket client)  
**Performance Goals**: Test suite <5min, thermal detection <10s, reconnection <10s (90%), <1s thermal action latency  
**Constraints**: <2% monitoring overhead, <300 lines per file, offline-capable, backward compatible with Phase 1  
**Scale/Scope**: Single user, 3 priority levels (P1/P2/P3), ~15 new tests, 4-6 new modules

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

| Principle                | Requirement                        | Status  | Evidence/Plan                                                                                                                                               |
| ------------------------ | ---------------------------------- | ------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **0. Offline-First**     | 100% offline capable               | ✅ PASS | All features work offline: thread cleanup is local, thermal monitoring uses local sensors, WebSocket is for local/network connections (no cloud dependency) |
| **1. Reliability First** | Graceful failure handling, retries | ✅ PASS | Thermal protection prevents crashes, WebSocket reconnection with exponential backoff, thread cleanup prevents test hangs                                    |
| **2. Observability**     | Health checks + resource metrics   | ✅ PASS | Structured JSON logging (FR-009b), thermal state in health checks, WebSocket events logged                                                                  |
| **3. Security**          | Personal: validation only          | ✅ PASS | Personal deployment - input validation already in Phase 1, error sanitization maintained                                                                    |
| **4. Maintainability**   | <300 lines/file, SRP               | ✅ PASS | New modules: thermal_monitor.py, websocket_session.py, managed_thread.py - each <300 lines, single responsibility                                           |
| **5. Testability**       | 60% coverage minimum               | ✅ PASS | ~15 new tests planned: unit (ThermalMonitor, ManagedThread), integration (WebSocket lifecycle, thermal protection), thread cleanup validation               |

**Overall**: ✅ **PASS** - No violations. All Phase 2 features align with constitution principles.

## Project Structure

### Documentation (this feature)

```
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```
src/
├── monitoring/
│   └── thermal_monitor.py          # NEW: P2 - CPU temp monitoring with hysteresis
├── infrastructure/
│   └── managed_thread.py            # NEW: P1 - Thread lifecycle wrapper
├── session/
│   └── websocket_session.py         # NEW: P3 - Session state manager (CONNECTED/DISCONNECTED)
├── server.py                         # MODIFIED: P3 - Session persistence hooks
├── turndetect.py                     # MODIFIED: P1 - Use ManagedThread for cleanup
├── llm_module.py                     # MODIFIED: P2 - Thermal protection integration
├── audio_module.py                   # MODIFIED: P2 - TTS pause on thermal trigger
└── logsetup.py                       # MODIFIED: P2/P3 - Add JSON formatter

code/static/
├── app.js                            # MODIFIED: P3 - WebSocket reconnection logic, P2 - Thermal UI indicator
└── index.html                        # MODIFIED: P2 - Thermal warning banner placeholder

tests/
├── unit/
│   ├── test_thermal_monitor.py       # NEW: P2 - Thermal logic unit tests
│   ├── test_managed_thread.py        # NEW: P1 - Thread lifecycle tests
│   └── test_websocket_session.py     # NEW: P3 - Session state tests
├── integration/
│   ├── test_thread_cleanup.py        # NEW: P1 - Full test suite execution validation
│   ├── test_thermal_integration.py   # NEW: P2 - End-to-end thermal protection
│   └── test_websocket_lifecycle.py   # NEW: P3 - Reconnection scenarios
└── conftest.py                       # MODIFIED: P1 - Thread leak detection fixtures

.specify/
└── memory/
    └── copilot-instructions.md       # UPDATED: Phase 2 tech stack additions
```

**Structure Decision**: Web application structure (backend Python + frontend JavaScript). Using existing `src/` and `code/static/` directories. New modules follow constitution's <300 lines/file limit and SRP (thermal monitoring, thread management, session management are separate concerns).

## Complexity Tracking

_No violations - this section intentionally left empty._

Phase 2 implementation adheres to all constitution principles without requiring exceptions or complexity justifications.
