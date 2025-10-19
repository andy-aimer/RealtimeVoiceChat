# Tasks: Phase 2 Infrastructure Improvements

**Branch**: `002-test-thermal-websocket`  
**Input**: Design documents from `/specs/002-test-thermal-websocket/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Organization**: Tasks are grouped by user story (P1: Thread Cleanup, P2: Thermal Protection, P3: WebSocket Lifecycle) to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1=P1, US2=P2, US3=P3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create directory structure and initialize new modules for Phase 2 features

- [ ] T001 Create `code/utils/` directory for lifecycle management utilities
- [ ] T002 Create `code/monitoring/` directory for thermal monitoring components
- [ ] T003 Create `code/websocket/` directory for session management
- [ ] T004 Create `tests/unit/` directory for Phase 2 unit tests
- [ ] T005 Create `tests/integration/` directory for Phase 2 integration tests
- [ ] T006 Create `code/utils/__init__.py` with module docstring
- [ ] T007 Create `code/monitoring/__init__.py` with module docstring
- [ ] T008 Create `code/websocket/__init__.py` with module docstring

**Checkpoint**: Directory structure ready for Phase 2 implementation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core utilities that user stories depend on (no implementation yet, just foundations)

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T009 Install optional dependencies if needed: `pip install pytest-xdist` (document in README as optional)
- [ ] T010 Review existing `code/turndetect.py` to understand current thread implementation (investigation task)
- [ ] T011 Review existing `code/server.py` WebSocket handler to understand current connection logic (investigation task)
- [ ] T012 Document current Phase 1 test execution behavior (baseline metrics for comparison)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - CI/CD Reliability (Priority: P1) 🎯 MVP

**Goal**: Fix test suite thread cleanup so `pytest tests/` completes in <5 minutes without hanging

**Independent Test**: Run `pytest tests/` and verify completion in <5 minutes with ≥60% coverage

### Implementation for User Story 1

- [ ] T013 [P] [US1] Create `ManagedThread` class in `code/utils/lifecycle.py` with `__init__`, `stop()`, `should_stop()` methods
- [ ] T014 [US1] Add `join()` method with timeout to `ManagedThread` in `code/utils/lifecycle.py`
- [ ] T015 [US1] Add `__enter__` and `__exit__` context manager methods to `ManagedThread` in `code/utils/lifecycle.py`
- [ ] T016 [US1] Add exception handling and logging to `ManagedThread` in `code/utils/lifecycle.py`
- [ ] T017 [US1] Refactor `TurnDetector.__init__` in `code/turndetect.py` to use `ManagedThread` for `text_worker`
- [ ] T018 [US1] Refactor `TurnDetector.__init__` in `code/turndetect.py` to use `ManagedThread` for `silence_worker`
- [ ] T019 [US1] Update `_process_text_queue` method in `code/turndetect.py` to check `should_stop()` in loop
- [ ] T020 [US1] Update `_detect_silence` method in `code/turndetect.py` to check `should_stop()` in loop
- [ ] T021 [US1] Add `close()` method to `TurnDetector` in `code/turndetect.py` that stops and joins threads
- [ ] T022 [US1] Add `__enter__` and `__exit__` methods to `TurnDetector` in `code/turndetect.py` for context manager support
- [ ] T023 [P] [US1] Create unit test file `tests/unit/test_thread_cleanup.py` with test for `ManagedThread.stop()` signal
- [ ] T024 [P] [US1] Add unit test for `ManagedThread.should_stop()` behavior in `tests/unit/test_thread_cleanup.py`
- [ ] T025 [P] [US1] Add unit test for `ManagedThread` context manager in `tests/unit/test_thread_cleanup.py`
- [ ] T026 [P] [US1] Add unit test for `ManagedThread.join()` timeout in `tests/unit/test_thread_cleanup.py`
- [ ] T027 [P] [US1] Add unit test for `TurnDetector.close()` method in `tests/unit/test_thread_cleanup.py`
- [ ] T028 [P] [US1] Add unit test for `TurnDetector` context manager in `tests/unit/test_thread_cleanup.py`
- [ ] T029 [US1] Create integration test file `tests/integration/test_full_suite.py` with test that runs full pytest suite
- [ ] T030 [US1] Add test to verify zero orphaned threads after test completion in `tests/integration/test_full_suite.py`
- [ ] T031 [US1] Add test to verify execution time <5 minutes in `tests/integration/test_full_suite.py`
- [ ] T032 [US1] Add test to verify coverage report generation ≥60% in `tests/integration/test_full_suite.py`
- [ ] T033 [US1] Update existing Phase 1 tests to use `TurnDetector` context manager (refactor existing test fixtures)
- [ ] T034 [US1] Run full test suite 10 times to verify no hanging (validation task - document results)
- [ ] T035 [US1] Generate coverage report and verify ≥60% for Phase 2 code (validation task)
- [ ] T036 [US1] Document pytest-xdist fallback strategy in README.md (if context managers insufficient)

**Checkpoint**: Test suite completes without hanging, coverage ≥60%, zero orphaned threads

**Success Criteria Verified**:

- ✅ SC-001: Test suite <5 minutes (10/10 runs)
- ✅ SC-002: CI completes without timeout
- ✅ SC-003: Coverage ≥60%
- ✅ SC-004: Zero orphaned threads
- ✅ SC-005: 50% improvement over file-by-file

---

## Phase 4: User Story 2 - Hardware Protection (Priority: P2)

**Goal**: Implement thermal workload reduction at 85°C for Raspberry Pi 5 hardware protection

**Independent Test**: Simulate high temperature and verify system reduces workload at 85°C, resumes at 80°C

### Implementation for User Story 2

- [ ] T037 [P] [US2] Create `ThermalState` dataclass in `code/monitoring/thermal_monitor.py` with temperature fields
- [ ] T038 [US2] Add hysteresis logic methods to `ThermalState` in `code/monitoring/thermal_monitor.py` (`should_trigger_protection`, `should_resume_normal`, `update_temperature`)
- [ ] T039 [P] [US2] Create `ThermalMonitor` class in `code/monitoring/thermal_monitor.py` with `__init__` and configuration
- [ ] T040 [US2] Implement `get_temperature()` method in `ThermalMonitor` class in `code/monitoring/thermal_monitor.py` (read from `/sys/class/thermal/thermal_zone0/temp`)
- [ ] T041 [US2] Add platform detection logic to `get_temperature()` in `code/monitoring/thermal_monitor.py` (return -1 on non-Pi)
- [ ] T042 [US2] Implement `check_thermal_protection()` method in `ThermalMonitor` class in `code/monitoring/thermal_monitor.py`
- [ ] T043 [US2] Add callback registration system to `ThermalMonitor` class in `code/monitoring/thermal_monitor.py` (`register_callback` method)
- [ ] T044 [US2] Implement background monitoring thread in `ThermalMonitor` class in `code/monitoring/thermal_monitor.py` (`start_monitoring`, `stop_monitoring`)
- [ ] T045 [US2] Add `get_state()` method to `ThermalMonitor` class in `code/monitoring/thermal_monitor.py`
- [ ] T046 [US2] Add `set_thresholds()` method to `ThermalMonitor` class in `code/monitoring/thermal_monitor.py` for dynamic configuration
- [ ] T047 [US2] Add thermal simulation mode to `ThermalMonitor` for testing in `code/monitoring/thermal_monitor.py` (`_simulate_temperature` method)
- [ ] T048 [US2] Integrate `ThermalMonitor` into `LLMModule` in `code/llm_module.py` (add instance variable, register callback)
- [ ] T049 [US2] Implement `_on_thermal_event` callback in `LLMModule` in `code/llm_module.py` (pause/resume inference)
- [ ] T050 [US2] Add `pause_inference()` method to `LLMModule` in `code/llm_module.py`
- [ ] T051 [US2] Add `resume_inference()` method to `LLMModule` in `code/llm_module.py`
- [ ] T052 [US2] Start thermal monitoring in `LLMModule.__init__` or server startup in `code/server.py`
- [ ] T053 [US2] Update `code/monitoring/resource_metrics.py` to include thermal state in health check
- [ ] T054 [P] [US2] Create unit test file `tests/unit/test_thermal_monitor.py` with test for temperature reading
- [ ] T055 [P] [US2] Add unit test for platform detection (non-Pi returns -1) in `tests/unit/test_thermal_monitor.py`
- [ ] T056 [P] [US2] Add unit test for hysteresis logic (85°C trigger, 80°C resume) in `tests/unit/test_thermal_monitor.py`
- [ ] T057 [P] [US2] Add unit test for callback notification in `tests/unit/test_thermal_monitor.py`
- [ ] T058 [P] [US2] Add unit test for thermal simulation mode in `tests/unit/test_thermal_monitor.py`
- [ ] T059 [P] [US2] Add unit test for threshold configuration in `tests/unit/test_thermal_monitor.py`
- [ ] T060 [US2] Create integration test file `tests/integration/test_thermal_integration.py` with thermal protection workflow test
- [ ] T061 [US2] Add integration test for LLM throttling on thermal trigger in `tests/integration/test_thermal_integration.py`
- [ ] T062 [US2] Add integration test for thermal resume workflow in `tests/integration/test_thermal_integration.py`
- [ ] T063 [US2] Test thermal monitoring on Raspberry Pi 5 hardware (manual validation task - document results)
- [ ] T064 [US2] Test thermal stress with `stress-ng` on Pi 5 (manual validation task - document results)
- [ ] T065 [US2] Add environment variable configuration support in README.md (`THERMAL_TRIGGER_THRESHOLD`, `THERMAL_RESUME_THRESHOLD`, etc.)

**Checkpoint**: Thermal protection triggers at 85°C, resumes at 80°C, integrates with LLM throttling

**Success Criteria Verified**:

- ✅ SC-006: Protection triggers within 10s of 85°C
- ✅ SC-007: Temperature capped at 87°C
- ✅ SC-008: Resumes within 30s of <80°C
- ✅ SC-009: Zero thermal crashes
- ✅ SC-010: Clear notification logs

---

## Phase 5: User Story 3 - Connection Reliability (Priority: P3)

**Goal**: Add WebSocket lifecycle management with automatic reconnection and session persistence

**Independent Test**: Disconnect WebSocket, verify automatic reconnection with session preservation within 10s

### Implementation for User Story 3

- [ ] T066 [P] [US3] Create `ConnectionState` enum in `code/websocket/session_manager.py` (CONNECTED, DISCONNECTED, RECONNECTING, EXPIRED)
- [ ] T067 [P] [US3] Create `WebSocketSession` dataclass in `code/websocket/session_manager.py` with session fields
- [ ] T068 [US3] Add session lifecycle methods to `WebSocketSession` in `code/websocket/session_manager.py` (`is_expired`, `touch`, `mark_disconnected`, `mark_reconnecting`, `mark_connected`)
- [ ] T069 [P] [US3] Create `SessionManager` class in `code/websocket/session_manager.py` with `__init__` and storage dict
- [ ] T070 [US3] Implement `create_session()` method in `SessionManager` class in `code/websocket/session_manager.py`
- [ ] T071 [US3] Implement `restore_session()` method in `SessionManager` class in `code/websocket/session_manager.py`
- [ ] T072 [US3] Implement `update_session()` method in `SessionManager` class in `code/websocket/session_manager.py`
- [ ] T073 [US3] Implement `touch_session()` method in `SessionManager` class in `code/websocket/session_manager.py`
- [ ] T074 [US3] Implement `delete_session()` method in `SessionManager` class in `code/websocket/session_manager.py`
- [ ] T075 [US3] Implement `cleanup_expired_sessions()` method in `SessionManager` class in `code/websocket/session_manager.py`
- [ ] T076 [US3] Implement `get_session()`, `list_active_sessions()`, `get_session_count()` methods in `SessionManager` class in `code/websocket/session_manager.py`
- [ ] T077 [US3] Add threading.Lock for thread safety in `SessionManager` class in `code/websocket/session_manager.py`
- [ ] T078 [US3] Integrate `SessionManager` into `code/server.py` WebSocket handler (instantiate, session creation/restoration)
- [ ] T079 [US3] Update WebSocket connection handler in `code/server.py` to accept `session_id` query parameter
- [ ] T080 [US3] Add session restoration logic on reconnection in `code/server.py` WebSocket handler
- [ ] T081 [US3] Add session touch on every message in `code/server.py` WebSocket handler
- [ ] T082 [US3] Add session update for conversation context in `code/server.py` WebSocket handler
- [ ] T083 [US3] Create background cleanup task in `code/server.py` (async cleanup_sessions_task function)
- [ ] T084 [US3] Start background cleanup task on server startup in `code/server.py` (@app.on_event("startup"))
- [ ] T085 [US3] Update health check endpoint in `code/server.py` to include session count
- [ ] T086 [P] [US3] Create exponential backoff utility in `code/utils/backoff.py` with `ExponentialBackoff` class
- [ ] T087 [US3] Implement client-side WebSocket reconnection logic in `code/static/app.js` (WebSocketClient class)
- [ ] T088 [US3] Add exponential backoff to client reconnection in `code/static/app.js` (1s → 30s, 10 retries)
- [ ] T089 [US3] Add session_id storage and restoration in `code/static/app.js` (localStorage)
- [ ] T090 [US3] Add connection state tracking in `code/static/app.js` (CONNECTED, DISCONNECTED, RECONNECTING)
- [ ] T091 [US3] Add connection status UI in `code/static/index.html` (status indicator element)
- [ ] T092 [US3] Update connection status UI on state changes in `code/static/app.js`
- [ ] T093 [US3] Implement ping/pong health checks in `code/server.py` WebSocket handler (30-second interval)
- [ ] T094 [US3] Add ping/pong response in `code/static/app.js` client
- [ ] T095 [P] [US3] Create unit test file `tests/unit/test_reconnection.py` with test for exponential backoff algorithm
- [ ] T096 [P] [US3] Add unit test for session creation in `tests/unit/test_reconnection.py`
- [ ] T097 [P] [US3] Add unit test for session restoration in `tests/unit/test_reconnection.py`
- [ ] T098 [P] [US3] Add unit test for session expiration in `tests/unit/test_reconnection.py`
- [ ] T099 [P] [US3] Add unit test for session cleanup in `tests/unit/test_reconnection.py`
- [ ] T100 [P] [US3] Add unit test for touch_session preventing expiration in `tests/unit/test_reconnection.py`
- [ ] T101 [US3] Create integration test file `tests/integration/test_websocket_lifecycle.py` with connection test
- [ ] T102 [US3] Add integration test for disconnect/reconnect flow in `tests/integration/test_websocket_lifecycle.py`
- [ ] T103 [US3] Add integration test for session persistence across reconnection in `tests/integration/test_websocket_lifecycle.py`
- [ ] T104 [US3] Add integration test for session expiration after 5 minutes in `tests/integration/test_websocket_lifecycle.py`
- [ ] T105 [US3] Add integration test for reconnection latency (<10s) in `tests/integration/test_websocket_lifecycle.py`
- [ ] T106 [US3] Test WebSocket reconnection in browser (manual validation task - document results)
- [ ] T107 [US3] Test session persistence with network toggle (manual validation task - document results)

**Checkpoint**: WebSocket reconnects automatically, session persists for 5 minutes, conversation context preserved

**Success Criteria Verified**:

- ✅ SC-011: 95% recovery for disconnections <60s
- ✅ SC-012: 100% session preservation <5 min
- ✅ SC-013: Clear error messages
- ✅ SC-014: 90% reconnections <10s
- ✅ SC-015: Zero data loss

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, documentation, and improvements across all user stories

- [ ] T108 [P] Run full test suite 10 times to verify reliability (validation task - document results)
- [ ] T109 [P] Generate final coverage report and verify ≥60% for all Phase 2 code
- [ ] T110 [P] Update README.md with Phase 2 features (thread cleanup, thermal protection, WebSocket reconnection)
- [ ] T111 [P] Update DEPLOYMENT.md with Raspberry Pi 5 thermal configuration instructions
- [ ] T112 [P] Create CHANGELOG.md entry for Phase 2 release
- [ ] T113 [P] Add Phase 2 configuration examples to .env.example file
- [ ] T114 [P] Update quickstart.md with any new testing procedures discovered during implementation
- [ ] T115 Code review: Verify all files <300 lines per constitution
- [ ] T116 Code review: Verify no external service dependencies (offline-first)
- [ ] T117 Code review: Verify proper error handling and logging in all new modules
- [ ] T118 Performance validation: Verify thermal monitoring overhead <0.5% CPU
- [ ] T119 Performance validation: Verify test suite execution time <5 minutes
- [ ] T120 Performance validation: Verify WebSocket reconnection latency <10s (90th percentile)
- [ ] T121 Security validation: Verify no path leaks in error messages
- [ ] T122 Security validation: Verify input validation on temperature thresholds and session IDs
- [ ] T123 Run quickstart.md validation scenarios (all P1, P2, P3 tests)
- [ ] T124 Final integration test: Run full voice chat pipeline with all Phase 2 features active
- [ ] T125 Prepare Phase 2 completion report (similar to PHASE_1_COMPLETE.md)

**Checkpoint**: All success criteria met, documentation complete, ready for merge

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1/P1 (Phase 3)**: Depends on Foundational completion - Can proceed independently
- **User Story 2/P2 (Phase 4)**: Depends on Foundational completion - Can proceed independently (parallel with US1)
- **User Story 3/P3 (Phase 5)**: Depends on Foundational completion - Can proceed independently (parallel with US1, US2)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1 - Thread Cleanup)**: No dependencies on other stories - Highest priority, blocking for CI/CD
- **User Story 2 (P2 - Thermal Protection)**: No dependencies on other stories - Independent hardware protection feature
- **User Story 3 (P3 - WebSocket Lifecycle)**: No dependencies on other stories - Independent connection reliability feature

### Within Each User Story

**User Story 1 (Thread Cleanup)**:

1. Create ManagedThread class (T013-T016)
2. Refactor TurnDetector to use ManagedThread (T017-T022)
3. Add unit tests (T023-T028) - can run parallel
4. Add integration tests (T029-T032)
5. Validation (T033-T036)

**User Story 2 (Thermal Protection)**:

1. Create ThermalState and ThermalMonitor (T037-T047)
2. Integrate with LLMModule (T048-T052)
3. Update health checks (T053)
4. Add unit tests (T054-T059) - can run parallel
5. Add integration tests (T060-T062)
6. Hardware validation (T063-T065)

**User Story 3 (WebSocket Lifecycle)**:

1. Create SessionManager (T066-T077)
2. Integrate with server (T078-T085)
3. Add exponential backoff utility (T086)
4. Update client-side code (T087-T094)
5. Add unit tests (T095-T100) - can run parallel
6. Add integration tests (T101-T105)
7. Manual validation (T106-T107)

### Parallel Opportunities

**Phase 1 (Setup)**: All tasks T001-T008 can run in parallel (different directories)

**Phase 2 (Foundational)**: Tasks T010-T012 can run in parallel (investigation tasks)

**Phase 3 (US1)**:

- T013 (ManagedThread) can be independent
- T023-T028 (unit tests) can run in parallel after T013-T022 complete

**Phase 4 (US2)**:

- T037 (ThermalState) independent
- T039 (ThermalMonitor class shell) independent
- T054-T059 (unit tests) can run in parallel after T037-T047 complete

**Phase 5 (US3)**:

- T066-T067 (data structures) can run in parallel
- T086 (backoff utility) independent
- T095-T100 (unit tests) can run in parallel after T066-T086 complete

**Phase 6 (Polish)**: Tasks T108-T114 can run in parallel (documentation), T115-T122 can run in parallel (validation)

**Cross-Story Parallelism**: After Phase 2 (Foundational) completes, all three user stories (Phase 3, 4, 5) can proceed in parallel with separate team members

---

## Parallel Example: All User Stories Together

```bash
# After Foundational phase (T001-T012) completes, launch all user stories in parallel:

# Developer A: User Story 1 (Thread Cleanup)
Task T013: "Create ManagedThread class in code/utils/lifecycle.py"
Task T017: "Refactor TurnDetector in code/turndetect.py"

# Developer B: User Story 2 (Thermal Protection)
Task T037: "Create ThermalState in code/monitoring/thermal_monitor.py"
Task T039: "Create ThermalMonitor in code/monitoring/thermal_monitor.py"

# Developer C: User Story 3 (WebSocket Lifecycle)
Task T066: "Create ConnectionState in code/websocket/session_manager.py"
Task T069: "Create SessionManager in code/websocket/session_manager.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only - P1 Thread Cleanup)

1. Complete Phase 1: Setup (T001-T008)
2. Complete Phase 2: Foundational (T009-T012)
3. Complete Phase 3: User Story 1 (T013-T036)
4. **STOP and VALIDATE**:
   - Run full test suite 10 times
   - Verify <5 minutes execution
   - Verify ≥60% coverage
   - Verify zero orphaned threads
5. Deploy/merge if ready (unblocks CI/CD immediately)

**Value Delivered**: CI/CD pipelines can run, automated testing enabled, development velocity improved

### Incremental Delivery (Add P2 and P3)

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 (P1) → Test independently → **Merge to main** (MVP - CI/CD unblocked!)
3. Add User Story 2 (P2) → Test independently → Merge to main (Hardware protection enabled)
4. Add User Story 3 (P3) → Test independently → Merge to main (Connection reliability improved)
5. Complete Phase 6 (Polish) → Final validation → Phase 2 complete!

### Parallel Team Strategy

With multiple developers available:

1. Team completes Setup + Foundational together (T001-T012)
2. Once Foundational is done:
   - **Developer A**: User Story 1 (P1) - Thread Cleanup (T013-T036)
   - **Developer B**: User Story 2 (P2) - Thermal Protection (T037-T065)
   - **Developer C**: User Story 3 (P3) - WebSocket Lifecycle (T066-T107)
3. Each developer completes and tests their story independently
4. Team merges stories one by one (P1 → P2 → P3)
5. Team completes Polish phase together (T108-T125)

**Timeline**: 3-4 weeks total (1 week per story if serial, 1-2 weeks if parallel with 3 developers)

---

## Task Summary

**Total Tasks**: 125 tasks

**Breakdown by Phase**:

- Phase 1 (Setup): 8 tasks
- Phase 2 (Foundational): 4 tasks
- Phase 3 (User Story 1 - P1): 24 tasks
- Phase 4 (User Story 2 - P2): 29 tasks
- Phase 5 (User Story 3 - P3): 42 tasks
- Phase 6 (Polish): 18 tasks

**Breakdown by User Story**:

- User Story 1 (P1 - Thread Cleanup): 24 tasks
- User Story 2 (P2 - Thermal Protection): 29 tasks
- User Story 3 (P3 - WebSocket Lifecycle): 42 tasks
- Infrastructure/Setup: 12 tasks
- Polish/Validation: 18 tasks

**Parallelizable Tasks**: 47 tasks marked with [P] (37.6% of total)

**Parallel Opportunities**:

- Within Setup: 8 tasks can run in parallel
- Within Foundational: 3 investigation tasks in parallel
- Within User Story 1: 6 unit tests in parallel
- Within User Story 2: 6 unit tests in parallel
- Within User Story 3: 6 unit tests + data structures in parallel
- Within Polish: 7 documentation + 8 validation tasks in parallel
- **Cross-Story**: All 3 user stories can proceed in parallel (95 tasks across US1/US2/US3)

**Independent Test Criteria**:

- **US1**: Run `pytest tests/` - completes <5 min, ≥60% coverage, zero orphaned threads
- **US2**: Simulate 85°C temperature - system reduces workload, logs CRITICAL, resumes at 80°C
- **US3**: Disconnect WebSocket - client reconnects within 10s, session restored, context preserved

**Suggested MVP Scope**: User Story 1 (P1) only - Unblocks CI/CD immediately (24 tasks, ~3-5 days)

---

## Notes

- All tasks follow strict checklist format: `- [ ] [ID] [P?] [Story?] Description with file path`
- [P] tasks = different files, no dependencies, can run in parallel
- [Story] label (US1/US2/US3) maps task to specific user story for traceability
- Each user story is independently completable and testable
- Tests are included per specification requirement for ≥60% coverage
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies
- Constitution compliance: All new files will be <300 lines (verified in T115)
- Offline-first: No external service dependencies (verified in T116)
- Performance targets: Verified in T118-T120
