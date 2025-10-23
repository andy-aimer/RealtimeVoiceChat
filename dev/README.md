# Development Files

This directory contains all development, testing, and documentation files for the RealtimeVoiceChat project.

## Structure

```
dev/
├── tests/               # All test files (unit and integration)
├── scripts/             # Development and testing scripts
├── specs/               # Development specifications and contracts
├── reports/             # Analysis reports and completion summaries
├── docs/                # Development documentation
├── code_backup/         # Backup of old code structure
├── htmlcov/             # Coverage reports
└── .pytest_cache/       # Pytest cache
```

## Running Tests

From the project root:

```bash
# Run all tests
pytest dev/tests/

# Run unit tests only
pytest dev/tests/unit/

# Run integration tests only
pytest dev/tests/integration/

# Run with coverage
pytest --cov=src --cov-report=html dev/tests/
```

## Development Scripts

- `test_server_monitoring.py` - Monitor server for testing
- `test_monitoring_standalone.py` - Standalone monitoring tests
- `measure_monitoring_overhead.py` - Performance measurement
- `run_tests_separately.py` - Test runner utility

## Usage

All scripts should be run from the project root directory:

```bash
python dev/scripts/test_server_monitoring.py
python dev/scripts/measure_monitoring_overhead.py
```
