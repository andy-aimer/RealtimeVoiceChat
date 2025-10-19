# Feature Specification: Phase 2 Infrastructure Improvements

**Feature Branch**: `002-test-thermal-websocket`  
**Created**: October 19, 2025  
**Status**: Draft  
**Input**: User description: "Phase 2: Fix test suite thread cleanup, implement thermal workload reduction, and add WebSocket lifecycle testing"

## User Scenarios & Testing _(mandatory)_

### User Story 1 - CI/CD Reliability (Priority: P1)

As a **developer**, I want the test suite to execute completely without hanging so that I can run automated CI/CD pipelines and verify code quality before merging.

**Why this priority**: Blocking issue that prevents automated testing and CI/CD pipeline execution. Currently requires manual workarounds to run tests file-by-file. This is the highest priority as it impacts development velocity and code quality assurance.

**Independent Test**: Can be fully tested by running `pytest tests/` and verifying all tests complete successfully in under 5 minutes without hanging. Delivers immediate value by enabling automated CI/CD.

**Acceptance Scenarios**:

1. **Given** a clean repository with all test dependencies installed, **When** developer runs `pytest tests/` from command line, **Then** all tests execute to completion without hanging within 5 minutes
2. **Given** GitHub Actions CI workflow is triggered, **When** tests run in CI environment, **Then** test job completes successfully and reports pass/fail status
3. **Given** test suite has completed, **When** developer reviews coverage report, **Then** coverage metrics are accurately calculated and reported (≥60% target)

---

### User Story 2 - Hardware Protection (Priority: P2)

As a **Raspberry Pi 5 user**, I want the system to automatically reduce workload when CPU temperature exceeds safe thresholds so that my hardware is protected from thermal damage and throttling.

**Why this priority**: Protects expensive hardware from thermal damage and prevents performance degradation from CPU throttling. Important for long-running deployments on Raspberry Pi 5 but not blocking for development.

**Independent Test**: Can be fully tested by simulating high temperature conditions (or actual load testing on Pi 5) and verifying system reduces workload at 85°C threshold. Delivers value by protecting hardware during extended use.

**Acceptance Scenarios**:

1. **Given** system is running on Raspberry Pi 5 with CPU temperature at 84°C, **When** temperature rises to 85°C, **Then** system reduces LLM workload or pauses TTS processing and logs CRITICAL warning
2. **Given** system has triggered thermal protection at 85°C, **When** CPU temperature drops below 80°C, **Then** system resumes normal operation and logs INFO recovery message
3. **Given** system is running on non-Pi platform (macOS/Windows), **When** thermal workload reduction feature is active, **Then** system gracefully handles absence of temperature monitoring without errors

---

### User Story 3 - Connection Reliability (Priority: P3)

As a **user of the voice chat system**, I want WebSocket connections to handle disconnections and reconnections gracefully so that temporary network issues don't disrupt my conversation experience.

**Why this priority**: Improves user experience for internet-connected deployments but less critical for offline/local use cases. Deferred from Phase 1 and represents an enhancement rather than core functionality.

**Independent Test**: Can be fully tested by simulating network disconnections during active sessions and verifying automatic reconnection with session persistence. Delivers value by improving reliability for remote users.

**Acceptance Scenarios**:

1. **Given** an active WebSocket connection, **When** network connection is lost temporarily, **Then** client automatically attempts reconnection with exponential backoff
2. **Given** WebSocket disconnected during TTS playback, **When** connection is restored, **Then** session state is recovered and audio playback resumes or gracefully stops
3. **Given** server restarts while clients are connected, **When** server comes back online, **Then** existing clients detect disconnection and reconnect automatically

---

### Edge Cases

- What happens when thread cleanup is triggered during active audio processing?
- How does system handle rapid temperature fluctuations around the 85°C threshold (oscillation)?
- What happens when WebSocket reconnection fails after maximum retry attempts?
- How does system handle thread cleanup during pytest teardown when threads are blocked on I/O?
- What happens when CPU temperature monitoring becomes unavailable mid-session?
- How does system behave when multiple WebSocket disconnections occur simultaneously?

## Requirements _(mandatory)_

### Functional Requirements

#### Thread Cleanup (P1)

- **FR-001**: System MUST properly terminate all background threads in `turndetect.py` when test teardown occurs
- **FR-002**: Test suite MUST execute all tests sequentially without thread accumulation between test runs
- **FR-003**: System MUST implement proper lifecycle management for `TurnDetector` class with explicit cleanup methods
- **FR-004**: Test suite MUST complete execution of all tests in under 5 minutes on development hardware
- **FR-005**: System MUST generate complete coverage report (≥60% target) after successful test suite execution

#### Thermal Workload Reduction (P2)

- **FR-006**: System MUST monitor CPU temperature continuously on Raspberry Pi 5 platforms
- **FR-007**: System MUST trigger workload reduction when CPU temperature reaches 85°C threshold
- **FR-008**: Workload reduction actions MUST include one or more of: reducing LLM inference rate, pausing TTS synthesis, or queuing responses
- **FR-009**: System MUST log CRITICAL alert when thermal protection is triggered, including timestamp and current temperature
- **FR-010**: System MUST automatically resume normal operation when CPU temperature drops below 80°C (hysteresis to prevent oscillation)
- **FR-011**: System MUST gracefully handle platforms where CPU temperature monitoring is unavailable (return -1, no errors)
- **FR-012**: Thermal thresholds MUST be configurable via environment variables or configuration file

#### WebSocket Lifecycle (P3)

- **FR-013**: Client MUST detect WebSocket disconnection within 5 seconds of connection loss
- **FR-014**: Client MUST automatically attempt reconnection using exponential backoff strategy (initial: 1s, max: 30s)
- **FR-015**: System MUST implement maximum retry limit of 10 attempts before requiring manual reconnection
- **FR-016**: System MUST persist session state during temporary disconnections (session ID, conversation context)
- **FR-017**: Server MUST maintain session data for 5 minutes after disconnection to allow reconnection
- **FR-018**: System MUST provide clear user feedback during disconnection, reconnection, and connection failure states
- **FR-019**: System MUST implement connection health checks (ping/pong) every 30 seconds to detect stale connections

### Key Entities _(include if feature involves data)_

- **TurnDetector**: Audio processing component with background threads requiring lifecycle management

  - Attributes: text_worker thread, silence_worker thread, state management
  - Relationships: Used by TranscriptionCallbacks, must be properly cleaned up in tests

- **ThermalMonitor**: Monitors CPU temperature and triggers protective actions

  - Attributes: current_temperature, threshold_temperature (85°C), hysteresis_temperature (80°C), protection_active flag
  - Relationships: Reads from Pi5Monitor, controls LLMModule and AudioProcessor

- **WebSocketSession**: Manages client connection lifecycle
  - Attributes: session_id, connection_state, reconnection_attempts, last_active_timestamp
  - Relationships: Associated with conversation context, manages connection to server

## Success Criteria _(mandatory)_

### Measurable Outcomes

#### Thread Cleanup Success (P1)

- **SC-001**: Test suite completes full execution in under 5 minutes without hanging (100% success rate across 10 consecutive runs)
- **SC-002**: GitHub Actions CI pipeline completes test jobs successfully without timeouts (30-minute timeout not reached)
- **SC-003**: Coverage report is generated automatically with ≥60% code coverage across all modules
- **SC-004**: Zero orphaned threads remain after test suite completion (verified via process inspection)
- **SC-005**: Test suite execution time improves by at least 50% compared to file-by-file workaround (current: ~8-10 minutes → target: <5 minutes)

#### Thermal Protection Success (P2)

- **SC-006**: System triggers thermal protection within 10 seconds of CPU temperature reaching 85°C on Raspberry Pi 5
- **SC-007**: System prevents CPU temperature from exceeding 87°C during sustained workload (2°C margin of safety)
- **SC-008**: System resumes normal operation within 30 seconds of temperature dropping below 80°C threshold
- **SC-009**: Zero thermal-related system crashes or hardware damage occur during stress testing
- **SC-010**: Users receive clear notification when thermal protection is active (log message visible in console/UI)

#### WebSocket Reliability Success (P3)

- **SC-011**: System successfully recovers from 95% of temporary network disconnections (under 60 seconds) without user intervention
- **SC-012**: Session data is preserved during reconnection for 100% of disconnections under 5 minutes
- **SC-013**: Users experience graceful degradation with clear error messages for reconnection failures (no silent failures)
- **SC-014**: Reconnection attempt succeeds within 10 seconds for 90% of connection restorations
- **SC-015**: Zero data loss or corruption occurs during disconnect/reconnect cycles (conversation context preserved)

## Assumptions

- Phase 1 Foundation has been completed and merged to main branch
- All Phase 1 infrastructure (health checks, metrics, security validation) remains functional
- Raspberry Pi 5 is the target platform for thermal monitoring, but system must work on all platforms
- Thread cleanup issue in `turndetect.py` is caused by background threads not being properly terminated
- WebSocket reconnection logic will be implemented client-side (JavaScript) with server-side session management
- Thermal workload reduction is sufficient at 85°C and does not require immediate shutdown
- Test suite hanging is reproducible and can be fixed through proper lifecycle management
- Development environment has access to Raspberry Pi 5 hardware for thermal testing (or can use thermal simulation)

## Dependencies

### Technical Dependencies

- Python threading library (`threading` module)
- Context managers (`contextlib`) for resource management
- pytest-xdist (optional) for test isolation and parallel execution
- WebSocket protocol standards (RFC 6455)
- Raspberry Pi 5 thermal monitoring interfaces (`/sys/class/thermal/`, `vcgencmd`)

### External Dependencies

- Phase 1 completion: All Phase 1 infrastructure must be functional
- Hardware access: Raspberry Pi 5 for thermal testing (or thermal simulation capability)
- Network simulation tools: For testing WebSocket disconnection scenarios

## Constraints

- Must maintain backward compatibility with Phase 1 codebase
- Must not increase monitoring overhead beyond Phase 1 target (<2% CPU)
- Must preserve all Phase 1 functionality while adding new features
- Thread cleanup must not impact real-time audio processing performance
- Thermal protection must have minimal latency (<1 second from threshold to action)
- WebSocket reconnection must not create memory leaks or resource exhaustion
- All code files must remain under 300-line limit per constitution
- Solution must work offline (no external service dependencies for core functionality)

## Out of Scope

- Advanced circuit breaker patterns (deferred to future phase)
- Distributed tracing and observability (deferred to future phase)
- Multi-node WebSocket load balancing (single-server deployment only)
- Automated thermal stress testing on real hardware (manual testing acceptable)
- WebSocket compression or advanced performance optimizations
- Thread pool management or async refactoring of existing code
- GPU temperature monitoring (CPU only for Phase 2)
- Automated recovery from hardware failures
- WebSocket message queuing during disconnection (simple reconnection only)

## Risks & Mitigations

| Risk                                                           | Impact | Likelihood | Mitigation                                                                                                        |
| -------------------------------------------------------------- | ------ | ---------- | ----------------------------------------------------------------------------------------------------------------- |
| Thread cleanup solution doesn't fully resolve hanging          | High   | Medium     | Implement pytest-xdist for process isolation as fallback; add comprehensive thread lifecycle tests                |
| Thermal protection triggers too aggressively (false positives) | Medium | Medium     | Implement 2°C hysteresis (80°C resume, 85°C trigger); make thresholds configurable                                |
| WebSocket reconnection logic creates memory leaks              | High   | Low        | Implement strict session timeout (5 minutes); add memory profiling tests; use weak references for session storage |
| Cannot reproduce thread hanging in test environment            | High   | Low        | Document exact reproduction steps from Phase 1; use thread dumps and profiling to identify blocking calls         |
| Raspberry Pi 5 thermal testing unavailable                     | Medium | Medium     | Use thermal simulation or CPU stress testing; validate on actual hardware before release                          |
| WebSocket reconnection conflicts with existing error handling  | Medium | Medium     | Review Phase 1 error handling code; ensure new logic integrates cleanly; add integration tests                    |

## Open Questions

1. Should thermal workload reduction be gradual (multiple levels) or binary (on/off)?
   - **Initial decision**: Binary on/off at 85°C for simplicity; can enhance later
2. What should be the maximum WebSocket session persistence time?
   - **Initial decision**: 5 minutes based on industry standards for session timeout
3. Should thread cleanup use context managers, explicit cleanup methods, or both?
   - **Initial decision**: Both - context managers for test convenience, explicit cleanup for production use
