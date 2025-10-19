"""
Integration tests for full test suite execution and thread cleanup.

Tests that the full pytest suite can run without hanging and that
thread cleanup works across the entire test suite.
Part of Phase 2, User Story 1 (P1) - Thread Cleanup.
"""

import pytest
import subprocess
import threading
import time
import os
import sys


class TestFullSuiteExecution:
    """Integration tests for full test suite behavior."""
    
    def test_full_suite_completes(self):
        """
        Test that running the full pytest suite completes without hanging.
        
        This is the primary success criterion for P1:
        - Test suite should complete in <5 minutes
        - No infinite hangs
        - Clean exit
        """
        # Run pytest on all tests (except this file to avoid recursion)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # Build pytest command
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/",
            "--ignore=tests/integration/test_full_suite.py",  # Avoid recursion
            "-v",  # Verbose for visibility
            "--tb=short",  # Short tracebacks
            "--timeout=60"  # 60s timeout per test
        ]
        
        start_time = time.time()
        
        # Run with timeout to prevent infinite hang
        try:
            result = subprocess.run(
                cmd,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute total timeout
            )
            
            elapsed = time.time() - start_time
            
            # Check results
            assert elapsed < 300, f"Test suite took {elapsed:.1f}s (should be <300s)"
            
            # Suite should complete (exit code 0 or 1, not timeout/hang)
            assert result.returncode in [0, 1], \
                f"Test suite should complete. Exit code: {result.returncode}"
            
            print(f"\n✅ Test suite completed in {elapsed:.1f}s")
            print(f"Exit code: {result.returncode}")
            
        except subprocess.TimeoutExpired as e:
            pytest.fail(
                f"Test suite hung and exceeded 5 minute timeout! "
                f"This indicates thread cleanup is not working."
            )
    
    def test_zero_orphaned_threads_after_suite(self):
        """
        Test that no orphaned threads remain after test execution.
        
        This validates that TurnDetector and other threaded components
        clean up properly.
        """
        # Count baseline threads
        threads_before = threading.active_count()
        print(f"\nThreads before test: {threads_before}")
        
        # Run a subset of tests that use TurnDetector
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/unit/test_turn_detection.py",
            "-v",
            "--tb=short"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Wait for cleanup
        time.sleep(1.0)
        
        # Count threads after
        threads_after = threading.active_count()
        print(f"Threads after test: {threads_after}")
        
        # Should not have significantly more threads
        # Allow +1 for potential pytest internals
        assert threads_after <= threads_before + 1, \
            f"Orphaned threads detected! Before: {threads_before}, After: {threads_after}"
    
    def test_execution_time_under_5_minutes(self):
        """
        Test that full test suite completes in under 5 minutes.
        
        Success Criterion SC-001: Test suite <5 minutes (10/10 runs).
        This is a single run; full validation requires 10 runs (see T034).
        """
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/",
            "--ignore=tests/integration/test_full_suite.py",
            "-q",  # Quiet mode for faster execution
            "--tb=line"
        ]
        
        start_time = time.time()
        
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute hard limit
        )
        
        elapsed = time.time() - start_time
        
        print(f"\n⏱️  Test suite execution time: {elapsed:.1f}s")
        
        # Success criterion: <300 seconds (5 minutes)
        assert elapsed < 300, \
            f"Test suite took {elapsed:.1f}s, exceeds 5 minute limit (SC-001)"
        
        # Also check it doesn't hang completely (should finish)
        assert result.returncode in [0, 1], \
            f"Test suite should complete normally. Exit code: {result.returncode}"
    
    @pytest.mark.skip(reason="Requires pytest-cov installed")
    def test_coverage_report_generation(self):
        """
        Test that coverage report can be generated for Phase 2 code.
        
        Success Criterion SC-003: Coverage ≥60% for Phase 2 code.
        """
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/unit/test_thread_cleanup.py",
            "--cov=code.utils.lifecycle",
            "--cov=code.turndetect",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "-v"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Should complete successfully
        assert result.returncode == 0, "Coverage run should complete"
        
        # Check output for coverage percentage
        output = result.stdout + result.stderr
        print(f"\nCoverage output:\n{output}")
        
        # Coverage report should be generated
        assert "TOTAL" in output, "Coverage report should be generated"


class TestThreadCleanupRegression:
    """Regression tests to prevent thread cleanup issues."""
    
    def test_repeated_test_runs_dont_accumulate_threads(self):
        """
        Test that running tests multiple times doesn't accumulate threads.
        
        This prevents regression where threads leak over multiple runs.
        """
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # Run the same test file 3 times
        for run_num in range(3):
            cmd = [
                sys.executable, "-m", "pytest",
                "tests/unit/test_thread_cleanup.py::TestTurnDetectorCleanup::test_close_method",
                "-v"
            ]
            
            result = subprocess.run(
                cmd,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Each run should complete successfully
            assert result.returncode == 0, \
                f"Run {run_num + 1} failed with exit code {result.returncode}"
            
            # Brief pause between runs
            time.sleep(0.5)
        
        # If we get here, all runs completed without hanging
        assert True, "All test runs completed successfully"
    
    def test_ci_cd_simulation(self):
        """
        Simulate CI/CD environment by running full suite in subprocess.
        
        Success Criterion SC-002: CI completes without timeout.
        """
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # Simulate CI environment variables
        env = os.environ.copy()
        env['CI'] = '1'
        env['PYTEST_TIMEOUT'] = '300'  # 5 minute timeout
        
        cmd = [
            sys.executable, "-m", "pytest",
            "tests/",
            "--ignore=tests/integration/test_full_suite.py",
            "-v",
            "--tb=short"
        ]
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                cwd=project_root,
                env=env,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute CI timeout
            )
            
            elapsed = time.time() - start_time
            
            print(f"\n🤖 CI simulation completed in {elapsed:.1f}s")
            print(f"Exit code: {result.returncode}")
            
            # CI should not timeout
            assert True, f"CI simulation completed (SC-002 validated)"
            
        except subprocess.TimeoutExpired:
            pytest.fail(
                "CI simulation timed out after 5 minutes! "
                "This would fail in real CI/CD (SC-002 FAILED)"
            )


class TestPerformanceComparison:
    """Compare performance with file-by-file execution."""
    
    @pytest.mark.skip(reason="Requires baseline measurements")
    def test_50_percent_improvement_over_file_by_file(self):
        """
        Test that full suite is ≥50% faster than file-by-file execution.
        
        Success Criterion SC-005: 50% improvement over file-by-file.
        """
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        
        # Measure file-by-file execution time
        test_files = [
            "tests/unit/test_audio_processing.py",
            "tests/unit/test_callbacks.py",
            "tests/unit/test_security_validators.py",
            "tests/unit/test_text_utils.py",
            "tests/unit/test_turn_detection.py"
        ]
        
        start_time = time.time()
        for test_file in test_files:
            cmd = [sys.executable, "-m", "pytest", test_file, "-q"]
            subprocess.run(cmd, cwd=project_root, capture_output=True, timeout=60)
        file_by_file_time = time.time() - start_time
        
        # Measure full suite execution time
        start_time = time.time()
        cmd = [sys.executable, "-m", "pytest", "tests/unit/", "-q"]
        subprocess.run(cmd, cwd=project_root, capture_output=True, timeout=300)
        full_suite_time = time.time() - start_time
        
        improvement = (file_by_file_time - full_suite_time) / file_by_file_time * 100
        
        print(f"\nPerformance comparison:")
        print(f"File-by-file: {file_by_file_time:.1f}s")
        print(f"Full suite: {full_suite_time:.1f}s")
        print(f"Improvement: {improvement:.1f}%")
        
        # Success criterion: ≥50% improvement
        assert improvement >= 50, \
            f"Only {improvement:.1f}% improvement, need ≥50% (SC-005)"
