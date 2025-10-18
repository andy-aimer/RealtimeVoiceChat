# Implementation Tasks: Phase 1 Foundation

**Feature:** 001-phase-1-foundation  
**Branch:** `001-phase-1-foundation`  
**Date:** 2025-10-18

---

## Overview

This document breaks down the Phase 1 Foundation feature into executable tasks organized by user story. Each task follows the format: `- [ ] [TaskID] [P?] [Story?] Description with file path`

**Task Count Summary:**

- Phase 1 (Setup): 7 tasks
- Phase 2 (Foundational): 5 tasks
- Phase 3 (US1 - Testing Infrastructure): 10 tasks
- Phase 4 (US2 - Health & Monitoring): 9 tasks
- Phase 5 (US3 - Security Basics): 6 tasks
- Phase 6 (Polish): 5 tasks
- **Total: 42 tasks**

**Parallel Opportunities:** 28 parallelizable tasks identified (marked with [P])

---

## User Story Mapping

From `spec.md`, we have three primary goals that map to user stories:

- **US1**: Testing Infrastructure - Achieve 60% code coverage with unit and integration tests
- **US2**: Health & Monitoring - Implement edge-optimized health checks and resource metrics for Pi 5
- **US3**: Security Baseline - Add input validation and optional authentication

---

## Phase 1: Setup & Project Initialization

**Goal:** Set up project dependencies and testing infrastructure foundation.

**Tasks:**

- [ ] T001 Install pytest and testing dependencies in requirements.txt
- [ ] T002 Install psutil for system metrics monitoring in requirements.txt
- [ ] T003 Create tests/ directory structure (tests/unit/, tests/integration/)
- [ ] T004 Create tests/**init**.py package initializer
- [ ] T005 Create code/monitoring/ directory for Pi 5 monitoring modules
- [ ] T006 Create code/middleware/ directory for logging and optional auth
- [ ] T007 Create code/security/ directory for validators and optional auth

**Validation:** All directories exist, dependencies installed, `pytest --version` succeeds.

---

## Phase 2: Foundational Infrastructure

**Goal:** Implement shared infrastructure needed by all user stories (blocking prerequisites).

**Tasks:**

- [ ] T008 [P] Create pytest configuration in tests/conftest.py with fixtures for async tests, HTTP client, and mock data
- [ ] T009 [P] Implement structured JSON logging in code/middleware/logging.py (max 100 lines)
- [ ] T010 [P] Integrate JSON logging middleware into code/server.py FastAPI app
- [ ] T011 [P] Create code/exceptions.py with custom exception hierarchy (RealtimeVoiceChatException base class)
- [ ] T012 [P] Update code/server.py to import and use custom exceptions for error handling

**Validation:**

- `pytest tests/conftest.py` succeeds
- Logging middleware outputs valid JSON
- Custom exceptions importable

**Independent Test Criteria:**

- JSON logs can be parsed with `jq`
- FastAPI server starts with logging middleware active
- Custom exceptions can be raised and caught

---

## Phase 3: US1 - Testing Infrastructure

**User Story:** As a developer, I want comprehensive testing infrastructure so I can validate system behavior with 60% code coverage and ensure <1.8s pipeline latency on Pi 5.

**Success Criteria:**

- [ ] All unit tests pass with ≥60% code coverage
- [ ] Integration tests validate full pipeline latency <1.8s on Pi 5
- [ ] Integration tests verify clean interruption handling (no zombie processes)
- [ ] Test suite execution time: <5 minutes total

**Tasks:**

- [ ] T013 [P] [US1] Create tests/unit/test_turn_detection.py with tests for TurnDetection class pause calculation logic
- [ ] T014 [P] [US1] Create tests/unit/test_audio_processing.py with tests for AudioProcessor audio processing functions
- [ ] T015 [P] [US1] Create tests/unit/test_text_utils.py with tests for TextSimilarity and TextContext helpers
- [ ] T016 [P] [US1] Create tests/unit/test_callbacks.py with tests for TranscriptionCallbacks state management
- [ ] T017 [US1] Create tests/integration/test_pipeline_e2e.py with full STT→LLM→TTS pipeline test using custom timing code (time.perf_counter)
- [ ] T018 [US1] Implement warmup run in test_pipeline_e2e.py to load models before actual latency test
- [ ] T019 [US1] Add <1.8s latency assertion in test_pipeline_e2e.py with detailed failure message showing actual latency
- [ ] T020 [US1] Create tests/integration/test_interruption_handling.py with mid-generation cancellation test
- [ ] T021 [US1] Add zombie process detection in test_interruption_handling.py to verify clean cleanup
- [ ] T022 [US1] Run pytest with coverage: `pytest tests/ --cov=code --cov-report=term` and verify ≥60% coverage

**Dependencies:**

- Requires Phase 2 (conftest.py fixtures)
- US1 tasks are internally parallelizable (T013-T016 can run concurrently)

**Parallel Execution Example:**

```bash
# Run all unit tests in parallel
pytest tests/unit/ -n auto

# Run integration tests sequentially (they test full pipeline)
pytest tests/integration/test_pipeline_e2e.py
pytest tests/integration/test_interruption_handling.py
```

**Independent Test Criteria:**

- Unit tests can run independently without server
- Integration tests validate full pipeline with actual components
- Coverage report shows ≥60% for code/ directory
- Test suite completes in <5 minutes

---

## Phase 4: US2 - Health & Monitoring

**User Story:** As a system operator, I want health checks and resource metrics so I can monitor Pi 5 system status and detect CPU throttling before performance degrades.

**Success Criteria:**

- [ ] `/health` endpoint returns component status (200 if healthy, 503 if degraded)
- [ ] `/metrics` endpoint exposes resource metrics in Prometheus plain text format
- [ ] Monitoring overhead: <2% CPU, <50MB RAM on Pi 5
- [ ] CPU temperature monitoring works on Pi 5, returns -1 on unsupported platforms

**Tasks:**

- [ ] T023 [P] [US2] Implement check_audio_processor() async function in code/health_checks.py (max 100 lines total for file)
- [ ] T024 [P] [US2] Implement check_llm_backend() async function in code/health_checks.py
- [ ] T025 [P] [US2] Implement check_tts_engine() async function in code/health_checks.py
- [ ] T026 [P] [US2] Implement check_system_resources() async function in code/health_checks.py with RAM/CPU/swap thresholds
- [ ] T027 [US2] Add GET /health endpoint to code/server.py with async health checks, 5s timeout per component, parallel execution
- [ ] T028 [P] [US2] Implement get_cpu_temperature() in code/metrics.py with platform-specific detection (vcgencmd for Pi 5, -1 fallback)
- [ ] T029 [P] [US2] Implement get_metrics() in code/metrics.py returning Prometheus plain text format (max 80 lines total for file)
- [ ] T030 [US2] Add GET /metrics endpoint to code/server.py returning Prometheus format with 1Hz cached metrics
- [ ] T031 [US2] Create code/monitoring/pi5_monitor.py with Pi 5 specific resource monitoring and 75°C/80°C temperature alerts

**Dependencies:**

- Requires Phase 2 (logging middleware)
- T023-T026 must complete before T027
- T028-T029 must complete before T030

**Parallel Execution Example:**

```bash
# Implement all health check functions in parallel (different functions)
# T023, T024, T025, T026 - independent functions in same file

# Implement metrics functions in parallel with health checks
# T028, T029 - independent from health checks
```

**Independent Test Criteria:**

- `/health` endpoint accessible, returns valid JSON
- Component checks work independently (can mock components)
- `/metrics` endpoint returns valid Prometheus format parseable by prometheus_client
- CPU temperature returns valid float (not None/NaN)
- Monitoring adds <2% CPU overhead (measure with psutil before/after)

---

## Phase 5: US3 - Security Basics

**User Story:** As a security-conscious user, I want input validation and optional authentication so my system is protected from crashes and unauthorized access based on deployment scenario.

**Success Criteria:**

- [ ] Input validation prevents malformed JSON from crashing server
- [ ] Structured logs output valid JSON for all log levels
- [ ] Security middleware adds <10ms latency per request
- [ ] Optional auth/rate-limiting can be enabled via config

**Tasks:**

- [ ] T032 [P] [US3] Create ValidationError Pydantic model in code/security/validators.py (max 80 lines total for file)
- [ ] T033 [P] [US3] Create WebSocketMessage Pydantic model in code/security/validators.py with type validation (audio/text/control)
- [ ] T034 [P] [US3] Create TextData Pydantic model in code/security/validators.py with text sanitization (5000 char max, prompt injection detection)
- [ ] T035 [P] [US3] Implement validate_message() function in code/security/validators.py returning tuple[bool, List[ValidationError]]
- [ ] T036 [US3] Integrate validate_message() into WebSocket handler in code/server.py with error response on validation failure
- [ ] T037 [US3] Add error sanitization to all exception handlers in code/server.py to prevent system path leaks

**Dependencies:**

- Requires Phase 2 (custom exceptions)
- T032-T035 must complete before T036
- T037 depends on T011 (exception hierarchy)

**Parallel Execution Example:**

```bash
# All Pydantic models can be implemented in parallel (T032-T035)
# Different classes in same file, no dependencies
```

**Independent Test Criteria:**

- Validation rejects messages with invalid type
- Validation rejects text >5000 characters
- Validation logs warning for prompt injection attempts
- WebSocket handler returns error JSON on validation failure
- Error messages don't contain system paths (test with intentional errors)

---

## Phase 6: Polish & Cross-Cutting Concerns

**Goal:** Final integration, documentation, and verification on Pi 5 hardware.

**Tasks:**

- [ ] T038 Run full test suite with coverage: `pytest tests/ -v --cov=code --cov-report=html --cov-report=term`
- [ ] T039 Verify all files comply with 300 line limit: `find code tests -name "*.py" -exec wc -l {} \; | awk '$1 > 300'`
- [ ] T040 Test health and metrics endpoints manually: `curl http://localhost:8000/health | jq` and `curl http://localhost:8000/metrics`
- [ ] T041 Measure monitoring overhead on Pi 5 using psutil before/after, verify <2% CPU increase
- [ ] T042 Generate final coverage report and verify ≥60%: `pytest --cov=code --cov-report=html && open htmlcov/index.html`

**Validation:**

- All tests pass
- Coverage ≥60%
- All files ≤300 lines
- Endpoints return valid responses
- Monitoring overhead <2% on Pi 5

---

## Dependencies & Execution Order

### Story Completion Order

```
Phase 1 (Setup) → Phase 2 (Foundational) → [US1, US2, US3 in parallel] → Phase 6 (Polish)
```

**Story Independence:**

- ✅ **US1 (Testing)** is independent - can be implemented first or in parallel with US2/US3
- ✅ **US2 (Health & Monitoring)** is independent - can be implemented in parallel with US1/US3
- ✅ **US3 (Security)** is independent - can be implemented in parallel with US1/US2

**Critical Path:**

1. Phase 1 (Setup) - 1 day
2. Phase 2 (Foundational) - 1 day
3. Longest story: US1 (Testing) - 3-4 days
4. Phase 6 (Polish) - 1 day

**Total Timeline:** 6-7 days with parallelization (vs 8-12 days sequential)

### Task Dependencies Graph

```
T001-T007 (Setup)
    ↓
T008 (conftest) → T013-T022 (US1 tests)
    ↓
T009-T010 (Logging) → T023-T031 (US2 monitoring)
    ↓
T011-T012 (Exceptions) → T032-T037 (US3 validation)
    ↓
T038-T042 (Polish)
```

---

## Parallel Execution Strategies

### Strategy 1: By User Story (Recommended)

```bash
# Team of 3 developers
Developer 1: US1 (Testing Infrastructure) - T013-T022
Developer 2: US2 (Health & Monitoring) - T023-T031
Developer 3: US3 (Security Basics) - T032-T037

# All work in parallel after Phase 2 completes
# Merge independently, resolve conflicts in Phase 6
```

### Strategy 2: By Layer

```bash
# Horizontal slicing
Phase 1: Setup (1 developer, 1 day)
Phase 2: Foundational (1 developer, 1 day)
Phase 3-5: All 28 [P] tasks distributed across team
Phase 6: Integration (1 developer, 1 day)
```

### Strategy 3: Solo Developer

```bash
# Implement in priority order
Day 1: T001-T012 (Setup + Foundational)
Day 2-3: T023-T031 (US2 - Health & Monitoring - highest business value)
Day 4-5: T032-T037 (US3 - Security - required for all deployments)
Day 6-7: T013-T022 (US1 - Testing - validation)
Day 8: T038-T042 (Polish)
```

---

## Implementation Strategy

### MVP Scope (Minimum Viable Product)

**Goal:** Get basic monitoring working first for immediate value.

**MVP = US2 (Health & Monitoring) only:**

- T001-T012 (Setup + Foundational)
- T023-T031 (US2 tasks)
- T038, T040 (Basic validation)

**Timeline:** 3-4 days  
**Deliverable:** Working `/health` and `/metrics` endpoints on Pi 5

### Incremental Delivery Plan

1. **Sprint 1 (Days 1-4):** MVP - US2 (Health & Monitoring)

   - Immediate value: Can monitor Pi 5 in production
   - Deploy to Pi 5, gather real metrics

2. **Sprint 2 (Days 5-7):** US3 (Security Basics)

   - Add input validation
   - Prevents crashes from malformed input
   - Deploy update to Pi 5

3. **Sprint 3 (Days 8-10):** US1 (Testing Infrastructure)

   - Add comprehensive tests
   - Validate 60% coverage
   - Ensure <1.8s pipeline latency

4. **Sprint 4 (Days 11-12):** Polish & Documentation
   - Final integration
   - Performance verification
   - Documentation updates

---

## Testing Strategy

### Unit Tests (US1)

**Files to test:**

- `code/turndetect.py` → `tests/unit/test_turn_detection.py`
- `code/audio_module.py` → `tests/unit/test_audio_processing.py`
- `code/text_similarity.py`, `code/text_context.py` → `tests/unit/test_text_utils.py`
- `code/transcribe.py` (callbacks) → `tests/unit/test_callbacks.py`

**Test count target:** ~15 unit tests total

### Integration Tests (US1)

**Files:**

- `tests/integration/test_pipeline_e2e.py` - Full pipeline with actual components
- `tests/integration/test_interruption_handling.py` - User interrupt handling

**Test count target:** 2 integration tests (may have multiple assertions each)

### Contract Tests (US2, US3)

**Endpoints to test:**

- GET `/health` - Returns 200/503, valid JSON
- GET `/metrics` - Returns Prometheus format
- WebSocket validation - Rejects invalid messages

**Test count target:** ~5-7 contract tests

### Coverage Target

- **Minimum:** 60% overall coverage
- **Critical paths:** 80%+ coverage for health checks, metrics, validation
- **Skip coverage:** Static config files, **init**.py files

---

## Constitution Compliance Checklist

### Principle 0: Offline-First

- [ ] All monitoring works without network (US2)
- [ ] psutil used for local metrics only (US2)
- [ ] No cloud API calls in health/metrics/validation (US2, US3)

### Principle 1: Reliability

- [ ] Health checks have 5s timeout per component (US2)
- [ ] Async execution prevents blocking (US2)
- [ ] Input validation prevents crashes (US3)

### Principle 2: Observability

- [ ] JSON structured logging implemented (Phase 2)
- [ ] Health endpoint with component status (US2)
- [ ] Metrics endpoint with 4 core metrics (US2)
- [ ] <2% CPU overhead on Pi 5 (US2)

### Principle 3: Security

- [ ] Input validation required for all (US3)
- [ ] Error sanitization prevents path leaks (US3)
- [ ] Optional auth/rate-limiting documented (US3)

### Principle 4: Maintainability

- [ ] All files ≤300 lines (verified in T039)
- [ ] Clear file organization by concern (Phase 1)
- [ ] Explicit imports, no wildcards (All phases)

### Principle 5: Testability

- [ ] 60% coverage achieved (US1, verified in T042)
- [ ] Unit tests for business logic (US1)
- [ ] Integration tests for critical paths (US1)
- [ ] Test suite <5 minutes (US1)

---

## Performance Validation Checklist

### Latency Targets

- [ ] Pipeline E2E: <1.8s (test_pipeline_e2e.py)
- [ ] Health check: <500ms (manual curl test)
- [ ] Metrics endpoint: <50ms (manual curl test)
- [ ] Validation overhead: <10ms per message (benchmark test)

### Resource Targets (Pi 5)

- [ ] Monitoring CPU overhead: <2% (T041)
- [ ] Monitoring RAM overhead: <50MB (T041)
- [ ] CPU temperature: <75°C normal, <80°C max (T031)
- [ ] Test suite runtime: <5 minutes (T038)

---

## Risk Mitigation Tasks

### Risk: psutil overhead on Pi 5

**Mitigation:**

- Limit polling to 1Hz (implemented in T030)
- Cache metric values for 1 second (implemented in T030)
- Measure actual overhead (validated in T041)

### Risk: Test flakiness on Pi 5

**Mitigation:**

- Use longer timeouts on Pi 5 (implemented in T017-T019)
- Warmup run before latency test (implemented in T018)
- Increase timeout thresholds in conftest.py (T008)

### Risk: CPU temp unavailable on dev machines

**Mitigation:**

- Platform-specific detection (implemented in T028)
- Graceful fallback to -1 (implemented in T028)
- Log warning once (implemented in T028)

---

## Completion Criteria

### Definition of Done (per User Story)

**US1 (Testing):**

- ✅ All unit tests pass
- ✅ Integration tests validate <1.8s latency
- ✅ Coverage ≥60%
- ✅ Test suite runs in <5 minutes

**US2 (Monitoring):**

- ✅ `/health` endpoint returns 200/503 correctly
- ✅ `/metrics` endpoint returns valid Prometheus format
- ✅ CPU temperature monitoring works on Pi 5
- ✅ Monitoring overhead <2% CPU

**US3 (Security):**

- ✅ Input validation rejects malformed messages
- ✅ Validation logs prompt injection attempts
- ✅ Error messages don't leak system paths
- ✅ Validation adds <10ms latency

### Feature Complete Criteria

- ✅ All 42 tasks completed
- ✅ All constitution principles satisfied
- ✅ All performance targets met on Pi 5
- ✅ Documentation updated (CLAUDE.md, README)
- ✅ Ready for Phase 2 (Refactoring)

---

## Tools & Commands

### Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=code --cov-report=html --cov-report=term

# Run specific story tests
pytest tests/unit/ -v  # US1 unit tests
pytest tests/integration/ -v  # US1 integration tests

# Start server
python code/server.py

# Check endpoints
curl http://localhost:8000/health | jq
curl http://localhost:8000/metrics
```

### Validation

```bash
# Check file line counts
find code tests -name "*.py" -exec wc -l {} \; | awk '$1 > 300 {print}'

# Validate JSON logs
tail -f logs/app.log | jq

# Parse Prometheus metrics
curl http://localhost:8000/metrics | grep system_cpu_temperature_celsius
```

### Pi 5 Deployment

```bash
# Copy to Pi 5
scp -r RealtimeVoiceChat pi@raspberrypi.local:~/

# SSH and test
ssh pi@raspberrypi.local
cd ~/RealtimeVoiceChat
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
python code/server.py
```

---

**Generated:** 2025-10-18  
**Status:** Ready for implementation  
**Next Step:** Begin Phase 1 (Setup) with T001-T007
