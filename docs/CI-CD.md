# CI/CD Documentation

## Overview

This project uses GitHub Actions for automated testing, coverage reporting, code quality checks, and deployment validation.

## Workflows

### 1. **Test Workflow** (`.github/workflows/test.yml`)

**Triggers:** Push to main/develop, Pull Requests  
**Purpose:** Run unit and integration tests across Python 3.10, 3.11, 3.12

**What it does:**

- ✅ Installs system dependencies (portaudio, ffmpeg)
- ✅ Runs unit tests with pytest
- ✅ Runs integration tests (with timeout protection)
- ✅ Uploads test results as artifacts

**Duration:** ~5-10 minutes

---

### 2. **Coverage Workflow** (`.github/workflows/coverage.yml`)

**Triggers:** Push to main/develop, Pull Requests  
**Purpose:** Ensure ≥60% code coverage

**What it does:**

- ✅ Runs tests with coverage measurement
- ✅ Checks 60% coverage threshold
- ✅ Uploads to Codecov (if configured)
- ✅ Comments coverage report on PRs
- ✅ Generates coverage badge

**Duration:** ~5-7 minutes

---

### 3. **Code Quality Workflow** (`.github/workflows/quality.yml`)

**Triggers:** Push to main/develop, Pull Requests  
**Purpose:** Enforce code quality standards

**What it does:**

- ✅ Black formatting check
- ✅ isort import sorting check
- ✅ Flake8 linting
- ✅ 300-line file size limit check
- ✅ MyPy type checking
- ✅ Bandit security scan

**Duration:** ~2-3 minutes

---

### 4. **Monitoring Endpoints Workflow** (`.github/workflows/monitoring.yml`)

**Triggers:** Push/PR affecting monitoring code  
**Purpose:** Validate /health and /metrics endpoints

**What it does:**

- ✅ Runs standalone monitoring tests
- ✅ Starts test server
- ✅ Tests /health endpoint (JSON structure, caching)
- ✅ Tests /metrics endpoint (Prometheus format)
- ✅ Validates HTTP headers
- ✅ Performance benchmarks

**Duration:** ~3-4 minutes

---

### 5. **Pi 5 Validation Workflow** (`.github/workflows/pi5-validation.yml`)

**Triggers:** Push to main, Pull Requests  
**Purpose:** Validate Raspberry Pi 5 constraints

**What it does:**

- ✅ Checks memory usage targets (<50MB)
- ✅ Validates CPU usage (<2%)
- ✅ Tests thermal monitoring graceful fallback
- ✅ Enforces 300-line file size limit
- ✅ Validates offline-first architecture
- ✅ Generates Pi 5 deployment checklist

**Duration:** ~2-3 minutes

---

### 6. **Complete CI/CD Pipeline** (`.github/workflows/ci-cd.yml`)

**Triggers:** Push to main, Pull Requests, Manual  
**Purpose:** Run full validation pipeline

**Stages:**

1. Code Quality → 2. Unit Tests → 3. Integration Tests → 4. Coverage → 5. Monitoring → 6. Security → 7. Pi5 Validation → 8. Report

**Duration:** ~15-20 minutes

---

## Status Badges

Add these to your `README.md`:

```markdown
![Tests](https://github.com/tsr1311/RealtimeVoiceChat/workflows/Tests/badge.svg)
![Coverage](https://github.com/tsr1311/RealtimeVoiceChat/workflows/Coverage/badge.svg)
![Code Quality](https://github.com/tsr1311/RealtimeVoiceChat/workflows/Code%20Quality/badge.svg)
![Monitoring](https://github.com/tsr1311/RealtimeVoiceChat/workflows/Monitoring%20Endpoints/badge.svg)
```

## Local Development

### Run Tests Locally

```bash
# Activate virtual environment
source venv-py312/bin/activate

# Run all tests
pytest tests/ -v

# Run with coverage
pytest --cov=code --cov-report=html tests/

# Run only unit tests
pytest tests/unit/ -v

# Run only integration tests
pytest tests/integration/ -v

# Run specific test file
pytest tests/unit/test_turn_detection.py -v
```

### Code Quality Checks

```bash
# Format code with black
black code/ tests/

# Sort imports with isort
isort code/ tests/

# Lint with flake8
flake8 code/ tests/

# Type check with mypy
mypy code/

# Security scan with bandit
bandit -r code/
```

### Test Monitoring Endpoints

```bash
# Run standalone tests
python test_monitoring_standalone.py

# Start test server
python test_server_monitoring.py

# In another terminal:
curl http://localhost:8000/health | jq
curl http://localhost:8000/metrics
```

## Configuration Files

- **`setup.cfg`** - pytest, coverage, flake8 configuration
- **`pyproject.toml`** - black, isort, mypy, pylint configuration
- **`.github/workflows/*.yml`** - GitHub Actions workflow definitions

## Secrets Configuration

### Required Secrets (Optional)

Add these in GitHub repository settings → Secrets and variables → Actions:

1. **`CODECOV_TOKEN`** (optional)
   - Get from https://codecov.io
   - Enables coverage reporting to Codecov
   - Not required for basic functionality

### How to Add Secrets

1. Go to: `https://github.com/tsr1311/RealtimeVoiceChat/settings/secrets/actions`
2. Click "New repository secret"
3. Add name and value
4. Click "Add secret"

## Workflow Triggers

### Automatic Triggers

- **Push to main/develop:** Runs all workflows
- **Pull Request:** Runs tests, coverage, quality checks
- **Path-based triggers:** Monitoring workflow only runs when monitoring code changes

### Manual Triggers

All workflows support manual triggering via `workflow_dispatch`:

1. Go to Actions tab
2. Select workflow
3. Click "Run workflow"
4. Choose branch
5. Click "Run workflow"

## Best Practices

### Before Committing

```bash
# 1. Format code
black code/ tests/

# 2. Sort imports
isort code/ tests/

# 3. Run tests locally
pytest tests/ -v

# 4. Check coverage
pytest --cov=code --cov-report=term tests/

# 5. Lint
flake8 code/ tests/
```

### Pull Request Checklist

- [ ] All tests pass locally
- [ ] Code coverage ≥60%
- [ ] Code formatted with black
- [ ] Imports sorted with isort
- [ ] No flake8 violations
- [ ] All files ≤300 lines
- [ ] No security issues (bandit)
- [ ] CI/CD checks pass

### Performance Targets

Monitor these in CI logs:

| Metric                   | Target     | Workflow       |
| ------------------------ | ---------- | -------------- |
| Unit test runtime        | <2 min     | test.yml       |
| Integration test runtime | <5 min     | test.yml       |
| Coverage check           | ≥60%       | coverage.yml   |
| Health endpoint latency  | <500ms     | monitoring.yml |
| Metrics endpoint latency | <50ms      | monitoring.yml |
| File size limit          | ≤300 lines | quality.yml    |

## Troubleshooting

### Tests Fail Locally But Pass in CI

- Check Python version (CI uses 3.10, 3.11, 3.12)
- Verify all dependencies installed
- Check for platform-specific issues

### Coverage Below 60%

```bash
# Generate detailed coverage report
pytest --cov=code --cov-report=html tests/
open htmlcov/index.html

# Identify uncovered lines
pytest --cov=code --cov-report=term-missing tests/
```

### Monitoring Tests Fail

```bash
# Check if ports are in use
lsof -i :8000

# Kill existing server
pkill -f test_server_monitoring

# Restart tests
python test_monitoring_standalone.py
```

### File Size Violations

```bash
# Find files over 300 lines
find code/ -name "*.py" -exec wc -l {} \; | awk '$1 > 300 {print}'

# Refactor large files into smaller modules
```

## Continuous Improvement

### Adding New Tests

1. Create test file in appropriate directory
2. Follow naming convention: `test_*.py`
3. Use pytest fixtures from `conftest.py`
4. Run locally before committing
5. Verify CI passes

### Adding New Workflows

1. Create `.github/workflows/new-workflow.yml`
2. Define triggers and jobs
3. Test with `workflow_dispatch` first
4. Monitor execution time
5. Update this documentation

## Support

For CI/CD issues:

1. Check workflow logs in Actions tab
2. Review this documentation
3. Check configuration files
4. Run tests locally to reproduce
5. Open issue with logs and error details

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [pytest Documentation](https://docs.pytest.org/)
- [Codecov Documentation](https://docs.codecov.com/)
- [Black Documentation](https://black.readthedocs.io/)
- [Flake8 Documentation](https://flake8.pycqa.org/)
