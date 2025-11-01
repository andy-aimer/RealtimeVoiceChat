# Tasks: Replace RealtimeTTS with Piper TTS

**Input**: Design documents from `/specs/001-replace-piper-tts/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/tts-api.yaml, quickstart.md

**Tests**: Tests are NOT explicitly requested in this specification. Test tasks are omitted per instructions.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths assume single project structure per plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency migration from RealtimeTTS to Piper TTS

- [x] T001 Update requirements.txt to remove RealtimeTTS dependencies (realtimetts[kokoro,coqui,orpheus]==0.5.5)
- [x] T002 Add Piper TTS dependencies to requirements.txt (piper-tts>=1.2.0, onnxruntime>=1.16.0, aiofiles>=23.0.0)
- [x] T003 Create Piper voice model directory structure at src/models/piper/
- [x] T004 Create voice profile configuration file at config/voice_profiles.json
- [x] T005 Create TTS configuration file template at config/tts_config.json

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core Piper TTS infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Download Piper voice model: en_US-lessac-medium.onnx and config to src/models/piper/
- [ ] T007 Download Piper voice model: en_US-amy-medium.onnx and config to src/models/piper/
- [ ] T008 Download Piper voice model: en_GB-alan-medium.onnx and config to src/models/piper/
- [ ] T009 Create PiperTTSEngine class in src/audio_module.py with initialization and model loading methods
- [ ] T010 Implement voice profile loading from ONNX models in src/audio_module.py
- [ ] T011 Create VoiceProfile data class in src/audio_module.py matching data-model.md schema
- [ ] T012 Create TTSEngineConfig data class in src/audio_module.py matching data-model.md schema
- [ ] T013 Implement ONNX runtime provider configuration for CPU execution in src/audio_module.py
- [ ] T014 Create voice migration mapping (RealtimeTTS to Piper) in config/tts_config.json
- [ ] T015 Implement configuration loading for Piper settings in src/audio_module.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Voice Response with Piper TTS (Priority: P1) 🎯 MVP

**Goal**: Replace RealtimeTTS engines with Piper TTS for all voice responses, maintaining audio quality and <2s latency for messages under 200 characters

**Independent Test**: Send text message through chat interface and verify audio response is generated using Piper TTS with acceptable quality and timing

### Implementation for User Story 1

- [ ] T016 [US1] Implement synchronous text synthesis method (synthesize) in PiperTTSEngine class in src/audio_module.py
- [ ] T017 [US1] Implement streaming synthesis method (synthesize_streaming) using async generators in src/audio_module.py
- [ ] T018 [US1] Create AudioOutputStream data class in src/audio_module.py matching data-model.md schema
- [ ] T019 [US1] Create TTSRequest data class in src/audio_module.py matching data-model.md schema
- [ ] T020 [US1] Implement audio chunk generation with metadata (sample_rate, duration_ms, chunk_index) in src/audio_module.py
- [ ] T021 [US1] Update server.py to initialize PiperTTSEngine instead of RealtimeTTS engines
- [ ] T022 [US1] Replace RealtimeTTS engine calls with PiperTTSEngine.synthesize() in src/audio_module.py
- [ ] T023 [US1] Implement TTS request queuing to handle multiple rapid messages in src/audio_module.py
- [ ] T024 [US1] Add audio streaming output to maintain real-time delivery in src/audio_module.py
- [ ] T025 [US1] Verify audio format compatibility (PCM, sample rate) with existing audio pipeline in src/audio_module.py
- [ ] T026 [US1] Implement latency monitoring (track processing_time_ms) in PiperTTSEngine in src/audio_module.py
- [ ] T027 [US1] Add logging for TTS synthesis operations (INFO level) in src/audio_module.py

**Checkpoint**: At this point, User Story 1 should be fully functional - all voice responses use Piper TTS with streaming

---

## Phase 4: User Story 2 - Voice Configuration Options (Priority: P2)

**Goal**: Enable users to select from available Piper TTS voices to customize chat experience, replacing RealtimeTTS engine selection

**Independent Test**: Access voice settings, switch between available Piper voices, verify audio output reflects selected voice characteristics

### Implementation for User Story 2

- [ ] T028 [P] [US2] Implement GET /tts/voices endpoint in src/server.py per contracts/tts-api.yaml
- [ ] T029 [P] [US2] Implement GET /tts/config endpoint in src/server.py per contracts/tts-api.yaml
- [ ] T030 [US2] Implement PATCH /tts/config endpoint to update default_voice in src/server.py per contracts/tts-api.yaml
- [ ] T031 [US2] Create get_available_voices() method in PiperTTSEngine returning VoiceProfile list in src/audio_module.py
- [ ] T032 [US2] Create set_voice() method in PiperTTSEngine for runtime voice switching in src/audio_module.py
- [ ] T033 [US2] Implement voice preference persistence to config/tts_config.json in src/audio_module.py
- [ ] T034 [US2] Add voice profile validation (ensure voice_id exists) in PiperTTSEngine in src/audio_module.py
- [ ] T035 [US2] Migrate legacy RealtimeTTS voice preferences using migration mapping in src/audio_module.py
- [ ] T036 [US2] Update frontend voice selection UI to display Piper voices from /tts/voices endpoint in code/static/app.js
- [ ] T037 [US2] Implement voice change notification to update current_voice without restart in src/audio_module.py
- [ ] T038 [US2] Add logging for voice configuration changes (INFO level) in src/audio_module.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently - voice selection functional

---

## Phase 5: User Story 3 - Performance Monitoring and Fallbacks (Priority: P3)

**Goal**: Enable system administrators to monitor TTS performance metrics and ensure graceful handling of Piper TTS failures with appropriate fallbacks

**Independent Test**: Monitor system logs during TTS operations and intentionally trigger failure conditions to verify fallback behavior

### Implementation for User Story 3

- [ ] T039 [P] [US3] Implement GET /tts/health endpoint in src/server.py per contracts/tts-api.yaml
- [ ] T040 [P] [US3] Create TTS metrics tracking class (TTSMetrics) in src/audio_module.py
- [ ] T041 [US3] Implement health check method in PiperTTSEngine (models_loaded, memory_usage, last_synthesis_ms) in src/audio_module.py
- [ ] T042 [US3] Add memory usage monitoring for loaded ONNX models in src/audio_module.py
- [ ] T043 [US3] Implement TTS success/failure rate tracking in TTSMetrics in src/audio_module.py
- [ ] T044 [US3] Add graceful error handling for missing model files in PiperTTSEngine initialization in src/audio_module.py
- [ ] T045 [US3] Implement retry logic (single retry) for corrupted audio generation in src/audio_module.py
- [ ] T046 [US3] Create fallback mechanism to simple TTS (src/tts_simple.py) when Piper fails in src/audio_module.py
- [ ] T047 [US3] Add comprehensive error logging (ERROR level) for TTS failures in src/audio_module.py
- [ ] T048 [US3] Implement exception handling to prevent TTS errors from crashing application in src/server.py
- [ ] T049 [US3] Add TTS processing time metrics to response logs in src/audio_module.py
- [ ] T050 [US3] Create error response format matching contracts/tts-api.yaml schemas in src/server.py

**Checkpoint**: All user stories should now be independently functional - monitoring and reliability features complete

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories, production readiness

- [ ] T051 [P] Update Dockerfile to include Piper model downloads during build
- [ ] T052 [P] Update docker-compose.yml with Piper-specific environment variables
- [ ] T053 Update requirements.production.txt with Piper dependencies
- [ ] T054 Add Pi 5 optimization settings (thread_count=3, CPU provider) to config/tts_config.json
- [ ] T055 [P] Update README.md with Piper TTS installation and configuration instructions
- [ ] T056 [P] Create migration guide documentation for existing RealtimeTTS deployments
- [ ] T057 Remove unused RealtimeTTS import statements from src/audio_module.py
- [ ] T058 Remove unused RealtimeTTS import statements from src/server.py
- [ ] T059 Clean up old RealtimeTTS configuration references in config files
- [ ] T060 Verify all API endpoints match contracts/tts-api.yaml specifications
- [ ] T061 Run validation tests from quickstart.md (synthesis, streaming, performance)
- [ ] T062 Verify memory usage meets <100MB additional usage requirement
- [ ] T063 Validate TTS latency meets <2s requirement for <200 character messages
- [ ] T064 Test voice model lazy loading to optimize memory usage
- [ ] T065 Verify offline operation (no network calls after model download)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Integrates with US1 but independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Builds on US1 monitoring but independently testable

### Within Each User Story

**User Story 1 (Core TTS Replacement)**:

- T016-T017 (synthesis methods) must complete before T022 (replace RealtimeTTS calls)
- T018-T019 (data classes) must complete before T020 (audio chunk generation)
- T021 (server initialization) must complete before T022 (replace engine calls)
- T023-T025 (streaming/queueing/format) can proceed after T022
- T026-T027 (monitoring/logging) are independent enhancements

**User Story 2 (Voice Selection)**:

- T028-T029 (GET endpoints) are independent and can run in parallel [P]
- T031 (get available voices) must complete before T028 endpoint can return data
- T032 (voice switching) must complete before T030 (PATCH config endpoint)
- T033-T035 (persistence/validation/migration) can proceed in parallel after T032
- T036 (frontend UI) depends on T028 endpoint being ready
- T037-T038 (notifications/logging) are final enhancements

**User Story 3 (Monitoring & Fallbacks)**:

- T039-T040 (health endpoint and metrics class) can run in parallel [P]
- T041-T043 (health check/memory/tracking) depend on T040 metrics class
- T044-T048 (error handling/retry/fallback) can proceed in parallel after T041
- T049-T050 (response logging/error formats) are final enhancements

### Parallel Opportunities

- **Setup Phase**: All dependency update tasks (T001-T005) can be done by different team members
- **Foundational Phase**: Model downloads (T006-T008) can run in parallel, data classes (T011-T012) can run in parallel
- **User Story 2**: Endpoint implementations (T028-T030) marked [P] can run in parallel
- **User Story 3**: Health endpoint and metrics class (T039-T040) marked [P] can run in parallel
- **Polish Phase**: Documentation tasks (T051-T052, T055-T056) marked [P] can run in parallel
- **Different user stories** can be worked on in parallel by different team members after Foundational phase

---

## Parallel Example: User Story 1

```bash
# After foundational phase, these tasks can start in parallel:
Task T016: "Implement synchronous text synthesis method in src/audio_module.py"
Task T017: "Implement streaming synthesis method in src/audio_module.py"
Task T018: "Create AudioOutputStream data class in src/audio_module.py"
Task T019: "Create TTSRequest data class in src/audio_module.py"

# After T016-T019 complete, these can proceed:
Task T020: "Implement audio chunk generation in src/audio_module.py"
Task T021: "Update server.py to initialize PiperTTSEngine"
```

---

## Parallel Example: User Story 2

```bash
# These endpoint implementations can run in parallel (marked [P]):
Task T028: "Implement GET /tts/voices endpoint in src/server.py"
Task T029: "Implement GET /tts/config endpoint in src/server.py"

# These persistence tasks can run in parallel after voice switching is ready:
Task T033: "Implement voice preference persistence in src/audio_module.py"
Task T034: "Add voice profile validation in src/audio_module.py"
Task T035: "Migrate legacy RealtimeTTS preferences in src/audio_module.py"
```

---

## Parallel Example: User Story 3

```bash
# These can start in parallel (marked [P]):
Task T039: "Implement GET /tts/health endpoint in src/server.py"
Task T040: "Create TTS metrics tracking class in src/audio_module.py"

# After metrics class exists, these error handling tasks can proceed in parallel:
Task T044: "Add graceful error handling for missing models in src/audio_module.py"
Task T045: "Implement retry logic for corrupted audio in src/audio_module.py"
Task T046: "Create fallback mechanism to simple TTS in src/audio_module.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T015) - CRITICAL foundation
3. Complete Phase 3: User Story 1 (T016-T027)
4. **STOP and VALIDATE**: Test voice responses work with Piper TTS
5. Deploy/demo if ready - core functionality complete

**MVP Scope**: This provides complete Piper TTS integration replacing RealtimeTTS with streaming voice responses. Users get functional voice chat with Piper TTS, meeting the core requirement.

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready (T001-T015)
2. Add User Story 1 → Test independently → Deploy/Demo (T016-T027) - **MVP!**
3. Add User Story 2 → Test independently → Deploy/Demo (T028-T038) - Voice customization
4. Add User Story 3 → Test independently → Deploy/Demo (T039-T050) - Monitoring & reliability
5. Polish & finalize → Production ready (T051-T065)

Each story adds value without breaking previous stories. Can stop at any checkpoint.

### Parallel Team Strategy

With multiple developers:

1. **Team completes Setup + Foundational together** (T001-T015)
2. **Once Foundational is done:**
   - Developer A: User Story 1 (T016-T027) - Core TTS replacement
   - Developer B: User Story 2 (T028-T038) - Voice configuration
   - Developer C: User Story 3 (T039-T050) - Monitoring & fallbacks
3. Stories complete and integrate independently
4. Team reconvenes for Polish phase (T051-T065)

---

## Task Summary

- **Total Tasks**: 65
- **Setup Phase**: 5 tasks
- **Foundational Phase**: 10 tasks (BLOCKING)
- **User Story 1 (P1)**: 12 tasks - Core Piper TTS integration
- **User Story 2 (P2)**: 11 tasks - Voice configuration and selection
- **User Story 3 (P3)**: 12 tasks - Monitoring and fallback handling
- **Polish Phase**: 15 tasks - Production readiness and optimization

### Parallel Opportunities Identified

- **5 tasks** marked [P] for parallel execution within user stories
- **3 user stories** can be developed in parallel after Foundational phase
- **Multiple polish tasks** can be done in parallel in final phase

### Independent Test Criteria

- **User Story 1**: Send text message, verify Piper TTS audio response with <2s latency
- **User Story 2**: Switch voices in settings, verify audio output reflects selected voice
- **User Story 3**: Monitor logs during operation, trigger failures, verify graceful fallbacks

### MVP Recommendation

**Suggested MVP Scope**: Setup + Foundational + User Story 1 (T001-T027)

This provides complete Piper TTS replacement with streaming audio, meeting the primary requirement to "remove realtimetts and replace with piper TTS" while maintaining voice chat functionality.

---

## Format Validation ✓

All tasks follow the required checklist format:

- ✓ Checkbox format: `- [ ]`
- ✓ Task ID: Sequential (T001-T065)
- ✓ [P] marker: Applied to 5 parallelizable tasks
- ✓ [Story] label: Applied to all User Story phase tasks (US1, US2, US3)
- ✓ Description: Includes exact file paths and clear actions
- ✓ No story labels in Setup, Foundational, or Polish phases

Tasks are immediately executable - each includes specific file paths and actions that an LLM can complete without additional context.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Tests omitted per specification (not explicitly requested)
- Maintains backward compatibility with existing audio pipeline interface
- Offline-first architecture preserved (no cloud API dependencies)
- Performance targets: <2s TTS generation, <100MB additional memory
