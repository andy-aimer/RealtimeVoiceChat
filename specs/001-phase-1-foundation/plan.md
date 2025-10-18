# Implementation Plan: Phase 1 Foundation

**Branch**: `001-phase-1-foundation` | **Date**: 2025-10-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-phase-1-foundation/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Establish foundational testing, monitoring, and security infrastructure for RealtimeVoiceChat. Implements pytest testing framework with 60% coverage target, edge-optimized health/metrics endpoints for Pi 5 resource monitoring, and input validation to prevent crashes. Uses custom timing code for latency validation (<1.8s pipeline target), Prometheus plain text format for metrics, and async health checks with timeout protection. All monitoring works 100% offline with <2% CPU overhead.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: FastAPI, pytest 7.4.3, pytest-asyncio 0.21.1, httpx 0.25.0, psutil 5.9.6  
**Storage**: In-memory dict-based session storage (no external databases)  
**Testing**: pytest with async support, custom timing code for latency validation  
**Target Platform**: Raspberry Pi 5 (8GB RAM, ARM64) + macOS/Linux for development  
**Project Type**: single (monolithic Python web application)  
**Performance Goals**:

- Pipeline latency: <1.8s total (STT + LLM + TTS)
- Monitoring overhead: <2% CPU, <50MB RAM
- Health check latency: <500ms (p99)
- Test coverage: 60% minimum
  **Constraints**:
- 100% offline operation (no cloud dependencies)
- Edge-optimized monitoring (minimal overhead on Pi 5)
- CPU temperature monitoring critical (75°C target, 80°C throttle)
- Max 300 lines per file (maintainability principle)
  **Scale/Scope**:
- Single-user personal deployment
- ~350 lines of new code (health_checks.py, metrics.py, validators.py)
- 8 new test files (~15-17 tests total)
- 2-week implementation timeline

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

### Principle 0: Offline-First Architecture

✅ **PASS** - All monitoring components (health checks, metrics, validation) operate without network dependencies. Uses psutil for local system metrics, no cloud API calls. Python library dependencies (pytest, psutil, FastAPI) are acceptable; external service dependencies (cloud APIs, remote databases) are not allowed for personal/offline deployment.

### Principle 1: Reliability First

✅ **PASS** - Health checks have 5s timeout protection. Async execution prevents event loop blocking. Retry strategy (3 attempts, 2s/4s/8s backoff) documented for future phases.

### Principle 2: Observability (Edge-Optimized)

✅ **PASS** - Implements edge-optimized monitoring:

- Health endpoint with component status (audio, llm, tts, system)
- 4 lightweight metrics (memory, CPU %, CPU temp, swap)
- Prometheus format for future tooling compatibility
- <2% CPU overhead target (1Hz polling)
- Pi 5 CPU temperature monitoring critical for throttling detection

### Principle 3: Security (Deployment-Dependent)

✅ **PASS** - Appropriate security for deployment scenarios:

- **Required for all:** Input validation (1MB max message, 5000 char max text, prompt injection detection)
- **Required for all:** Error sanitization (no system path leaks)
- **Optional for internet-exposed:** API key auth, rate limiting (5 conn/IP, 100 msg/min)
- Follows deployment-dependent principle correctly

### Principle 4: Maintainability

✅ **PASS** - Strict file size compliance:

- health_checks.py: ~100 lines (4 async functions)
- metrics.py: ~80 lines (temperature detection + metrics formatting)
- validators.py: ~80 lines (Pydantic models)
- All files well under 300 line limit

### Principle 5: Testability

✅ **PASS** - Achieves 60% coverage target:

- Unit tests for turn detection, audio, text utils, callbacks (~15 tests)
- Integration tests for pipeline E2E + interruption handling (2 tests)
- Custom timing code for latency validation
- Test execution time: 2.5-3.5 min (under 5 min limit)

**Overall Gate Status**: ✅ **APPROVED** - All 6 principles satisfied, no violations requiring justification.

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
code/
├── health_checks.py           # NEW: Component health check functions (async, parallel execution)
├── metrics.py                 # NEW: System metrics collection (Prometheus format)
├── server.py                  # MODIFIED: Add /health and /metrics endpoints
├── monitoring/
│   └── pi5_monitor.py        # NEW: Pi 5 specific resource monitoring
├── middleware/
│   └── logging.py            # NEW: Structured JSON logging middleware
├── security/
│   └── validators.py         # NEW: Input validation (required for all deployments, log-only prompt injection detection)
└── [existing modules: audio_module.py, llm_module.py, etc.]

tests/
├── __init__.py               # NEW: Test package init
├── conftest.py               # NEW: Pytest fixtures and configuration
├── unit/
│   ├── test_turn_detection.py      # NEW: Turn detection logic tests
│   ├── test_audio_processing.py    # NEW: Audio processor tests
│   ├── test_text_utils.py          # NEW: Text similarity/context tests
│   └── test_callbacks.py           # NEW: Callback state management tests
└── integration/
    ├── test_pipeline_e2e.py        # NEW: Full pipeline latency test
    └── test_interruption_handling.py # NEW: User interrupt test
```

**Structure Decision**: Single project structure (Option 1) chosen because:

- Monolithic Python application (no frontend/backend split)
- All code in `code/` directory (existing structure)
- New test directory at repository root following pytest conventions
- Monitoring and security modules organized by concern under `code/`
- Maintains compatibility with existing codebase organization

## Complexity Tracking

_No violations detected - all constitution principles satisfied. This section intentionally left empty._
