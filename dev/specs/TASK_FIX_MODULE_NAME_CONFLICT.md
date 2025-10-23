# Task: Fix Module Name Conflict (Rename `code/` → `src/`)

**Priority**: High (blocks pytest execution)  
**Type**: Infrastructure / Technical Debt  
**Estimated Effort**: 2-3 hours  
**Branch**: Create new branch `fix-module-name-conflict`  
**Related**: Phase 2 P1 validation blocked by this issue

---

## Problem Statement

The project's `code/` directory shadows Python's standard library `code` module, preventing pytest from running:

```
AttributeError: module 'code' has no attribute 'InteractiveConsole'
(consider renaming '/Users/Tom/dev-projects/RealtimeVoiceChat/code/__init__.py'
since it has the same name as the standard library module named 'code')
```

**Impact**:

- ❌ Cannot run pytest test suite
- ❌ Cannot generate coverage reports
- ❌ Cannot validate Phase 2 implementation with pytest
- ❌ Blocks CI/CD pipeline setup

**Root Cause**:
When pytest initializes its debugger (pdb), it tries to import the stdlib `code.InteractiveConsole` class. However, Python finds the project's `code/` directory first, which doesn't have this class, causing the import to fail.

---

## Proposed Solution

Rename `code/` directory to `src/` (following Python best practices).

**Benefits**:

- ✅ Fixes pytest import issue
- ✅ Follows Python packaging conventions
- ✅ More explicit (src = source code)
- ✅ No stdlib conflicts

**Alternatives Considered**:

- `app/` - Good, but less conventional for libraries
- `realtimevoicechat/` - Too long, redundant with repo name
- Keep `code/` and use pytest config - Doesn't fully solve the issue

---

## Implementation Checklist

### Phase 1: Directory Rename (30 minutes)

- [ ] Create new branch: `git checkout -b fix-module-name-conflict`
- [ ] Rename directory: `git mv code src`
- [ ] Verify git tracked the rename: `git status`
- [ ] Commit rename: `git commit -m "Rename code/ to src/ to fix stdlib conflict"`

### Phase 2: Update Imports (60 minutes)

Update all Python files that import from `code.*`:

**Server Files**:

- [ ] `src/server.py` - Update internal imports if any
- [ ] `src/llm_module.py` - Update internal imports if any
- [ ] `src/audio_module.py` - Update internal imports if any
- [ ] `src/turndetect.py` - Update: `from code.utils.lifecycle` → `from src.utils.lifecycle`
- [ ] `src/speech_pipeline_manager.py` - Check for internal imports
- [ ] `src/transcribe.py` - Check for internal imports
- [ ] Other files in `src/` - Search for `from code.` or `import code.`

**Test Files**:

- [ ] `tests/unit/test_thread_cleanup.py` - Update: `from code.utils.lifecycle` → `from src.utils.lifecycle`
- [ ] `tests/unit/test_thread_cleanup.py` - Update: `from code.turndetect` → `from src.turndetect`
- [ ] `tests/unit/test_turn_detection.py` - Update all `code.*` imports
- [ ] `tests/unit/test_audio_processing.py` - Update all `code.*` imports
- [ ] `tests/unit/test_callbacks.py` - Update all `code.*` imports
- [ ] `tests/unit/test_security_validators.py` - Update all `code.*` imports
- [ ] `tests/unit/test_text_utils.py` - Update all `code.*` imports
- [ ] `tests/integration/test_pipeline_e2e.py` - Update all `code.*` imports
- [ ] `tests/integration/test_interruption_handling.py` - Update all `code.*` imports
- [ ] `tests/integration/test_full_suite.py` - Update validation script paths
- [ ] `tests/conftest.py` - Update: `from code.turndetect` → `from src.turndetect`

**Validation Scripts**:

- [ ] `specs/002-test-thermal-websocket/validate_mvp.py` - Update coverage paths
- [ ] `specs/002-test-thermal-websocket/direct_test_managed_thread.py` - Update: `from code.utils` → `from src.utils`

### Phase 3: Update Configuration (15 minutes)

- [ ] `README.md` - Update any references to `code/` directory
- [ ] `DEPLOYMENT.md` - Update any deployment paths
- [ ] `.gitignore` - Check if any `code/` specific entries exist
- [ ] `docker-compose.yml` - Update volume mounts if any
- [ ] `Dockerfile` - Update COPY commands if any
- [ ] `entrypoint.sh` - Update paths if any
- [ ] `requirements.txt` - No changes needed (external deps only)

### Phase 4: Update Documentation (15 minutes)

- [ ] `specs/002-test-thermal-websocket/plan.md` - Update file paths in examples
- [ ] `specs/002-test-thermal-websocket/research.md` - Update file paths
- [ ] `specs/002-test-thermal-websocket/data-model.md` - Update file paths
- [ ] `specs/002-test-thermal-websocket/contracts/*.md` - Update file paths
- [ ] `specs/002-test-thermal-websocket/quickstart.md` - Update examples
- [ ] `specs/002-test-thermal-websocket/tasks.md` - Update file paths in task descriptions
- [ ] `specs/002-test-thermal-websocket/BASELINE_TEST_BEHAVIOR.md` - Update examples
- [ ] `specs/002-test-thermal-websocket/PHASE_2_P1_MVP_COMPLETE.md` - Update file paths
- [ ] `specs/002-test-thermal-websocket/VALIDATION_RESULTS.md` - Update recommendation
- [ ] Any other spec files referencing `code/`

### Phase 5: Testing & Validation (30 minutes)

- [ ] Run direct test: `python3 specs/002-test-thermal-websocket/direct_test_managed_thread.py`
  - Expected: ✅ All tests pass
- [ ] Try pytest: `python3 -m pytest --collect-only`
  - Expected: ✅ No AttributeError, should collect tests
- [ ] Run unit tests: `pytest tests/unit/test_thread_cleanup.py -v`
  - Expected: ✅ All 15 tests pass
- [ ] Run integration tests: `pytest tests/integration/test_full_suite.py -v`
  - Expected: ✅ All tests pass or collect without errors
- [ ] Run full suite: `pytest tests/ -v`
  - Expected: ✅ All tests execute without hanging
- [ ] Run with coverage: `pytest tests/ --cov=src --cov-report=term-missing`
  - Expected: ✅ Coverage report generated
- [ ] Run validation script: `python3 specs/002-test-thermal-websocket/validate_mvp.py`
  - Expected: ✅ All validations pass

### Phase 6: Commit & Merge (15 minutes)

- [ ] Review all changes: `git diff`
- [ ] Stage all changes: `git add -A`
- [ ] Commit: `git commit -m "Update imports after code/ → src/ rename"`
- [ ] Push branch: `git push origin fix-module-name-conflict`
- [ ] Create PR: "Fix module name conflict (rename code/ to src/)"
- [ ] Verify CI passes (if configured)
- [ ] Merge to main
- [ ] Update Phase 2 branch: `git checkout 002-test-thermal-websocket && git merge main`

---

## Search & Replace Commands

**For efficiency, use these commands:**

### Find all imports to update:

```bash
# Find all files importing from code.*
grep -r "from code\." . --include="*.py" | grep -v ".git"
grep -r "import code\." . --include="*.py" | grep -v ".git"

# Count occurrences
grep -r "from code\." . --include="*.py" | grep -v ".git" | wc -l
```

### Automated replacement (use carefully):

```bash
# Dry run first - see what would change
find . -name "*.py" -type f -not -path "./.git/*" -exec grep -l "from code\." {} \;

# Replace all occurrences
find . -name "*.py" -type f -not -path "./.git/*" -exec sed -i '' 's/from code\./from src\./g' {} \;
find . -name "*.py" -type f -not -path "./.git/*" -exec sed -i '' 's/import code\./import src\./g' {} \;

# Verify changes
git diff
```

### Update documentation:

```bash
# Find markdown files with code/ references
grep -r "code/" specs/ --include="*.md" | grep -v ".git"

# Replace in markdown (be selective - some might be code blocks)
find specs/ -name "*.md" -type f -exec sed -i '' 's|code/|src/|g' {} \;
```

---

## Testing Strategy

### Pre-Rename Baseline:

```bash
# Document current state
python3 -m pytest --collect-only 2>&1 | tee pre-rename-pytest.log
python3 specs/002-test-thermal-websocket/direct_test_managed_thread.py 2>&1 | tee pre-rename-direct.log
```

### Post-Rename Validation:

```bash
# Should work now
python3 -m pytest --collect-only  # Should list all tests
python3 -m pytest tests/unit/test_thread_cleanup.py -v  # Should pass
python3 -m pytest tests/ -v  # Should run full suite
```

---

## Risk Assessment

**Low Risk**:

- Purely mechanical change (rename + find-replace)
- Git tracks renames, so history preserved
- Can be validated completely before merge
- Easy to revert if needed

**Potential Issues**:

- ⚠️ Absolute imports might need updating (unlikely)
- ⚠️ Deployment scripts might reference `code/` paths
- ⚠️ Docker volumes might need path updates

**Mitigation**:

- Test on branch before merging
- Keep Phase 2 branch separate until validated
- Run full test suite to catch any missed imports

---

## Success Criteria

✅ **pytest runs successfully**:

```bash
$ python3 -m pytest --collect-only
# No AttributeError about code.InteractiveConsole
# All tests collected successfully
```

✅ **Full test suite executes**:

```bash
$ pytest tests/ -v
# All tests run (pass/fail doesn't matter yet, just that they run)
# No import errors
# No "module 'code' has no attribute" errors
```

✅ **Coverage report generates**:

```bash
$ pytest tests/ --cov=src --cov-report=html
# htmlcov/ directory created
# Coverage report shows Phase 2 code
```

✅ **Validation script passes**:

```bash
$ python3 specs/002-test-thermal-websocket/validate_mvp.py
# Results: 4/4 validations passed
# ✅ ALL VALIDATIONS PASSED
```

---

## Post-Completion Actions

After this task is complete:

1. **Update Phase 2 P1 documentation**:

   - Mark pytest validation as ✅ COMPLETE
   - Update VALIDATION_RESULTS.md with full pytest results
   - Re-run 10-iteration test for SC-001

2. **Enable CI/CD**:

   - Add pytest to GitHub Actions
   - Configure coverage reporting
   - Set up automatic test runs on PRs

3. **Resume Phase 2 work**:
   - P2: Thermal Protection can now use pytest
   - P3: WebSocket Lifecycle can now use pytest
   - All future tests can use pytest normally

---

## References

- **Python Packaging Guide**: https://packaging.python.org/en/latest/tutorials/packaging-projects/
  - Recommends `src/` layout for projects
- **pytest Documentation**: https://docs.pytest.org/
  - No conflicts with `src/` directory name
- **Issue Context**: `specs/002-test-thermal-websocket/BASELINE_TEST_BEHAVIOR.md`
- **Validation Results**: `specs/002-test-thermal-websocket/VALIDATION_RESULTS.md`

---

## Timeline Estimate

- **Preparation**: 15 min (understand scope, create branch)
- **Rename**: 5 min (git mv command)
- **Update Imports**: 60 min (find-replace with verification)
- **Update Config**: 15 min (docker, docs)
- **Update Documentation**: 15 min (spec files)
- **Testing**: 30 min (run all validations)
- **Commit & Review**: 15 min (final checks, PR)

**Total**: ~2.5 hours for careful, thorough implementation

---

## Appendix: Example Import Updates

### Before (broken):

```python
# tests/unit/test_thread_cleanup.py
from code.utils.lifecycle import ManagedThread
from code.turndetect import TurnDetection

# src/turndetect.py
from code.utils.lifecycle import ManagedThread
```

### After (working):

```python
# tests/unit/test_thread_cleanup.py
from src.utils.lifecycle import ManagedThread
from src.turndetect import TurnDetection

# src/turndetect.py
from src.utils.lifecycle import ManagedThread
```

### Documentation Update:

```markdown
# Before

File: `code/utils/lifecycle.py`

# After

File: `src/utils/lifecycle.py`
```

---

**Created**: October 19, 2025  
**Priority**: High  
**Estimated Completion**: 2-3 hours  
**Blocks**: Full pytest suite execution, CI/CD setup  
**Unblocks**: Phase 2 P2, P3, and all future testing
