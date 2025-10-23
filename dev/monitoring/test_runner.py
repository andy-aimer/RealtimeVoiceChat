"""
Enhanced Test Runner with Real-Time Monitoring Integration
Phase 2 P4 - Polish & Validation

This module runs tests with real-time progress reporting to the monitoring dashboard.
"""

import subprocess
import json
import time
import re
import requests
import threading
from pathlib import Path
import argparse
from typing import List, Dict, Any

class MonitoredTestRunner:
    """Test runner that reports progress to the monitoring dashboard."""
    
    def __init__(self, monitor_url: str = "http://localhost:8001"):
        self.monitor_url = monitor_url
        self.session = requests.Session()
        self.current_test = None
        
    def notify_start(self, test_command: str, total_tests: int = 103):
        """Notify monitor that tests are starting."""
        try:
            response = self.session.post(f"{self.monitor_url}/api/start-tests")
            print(f"✅ Monitor notified: Test run started")
        except Exception as e:
            print(f"⚠️ Failed to notify monitor: {e}")
    
    def notify_progress(self, test_name: str, status: str, duration: float = 0):
        """Notify monitor of test progress."""
        try:
            data = {
                "test_name": test_name,
                "status": status,
                "duration": duration
            }
            response = self.session.post(f"{self.monitor_url}/api/test-update", json=data)
        except Exception as e:
            print(f"⚠️ Failed to update monitor: {e}")
    
    def notify_coverage(self, coverage_percent: float):
        """Notify monitor of coverage update."""
        try:
            data = {"coverage": coverage_percent}
            response = self.session.post(f"{self.monitor_url}/api/test-update", json=data)
        except Exception as e:
            print(f"⚠️ Failed to update coverage: {e}")
    
    def notify_finish(self, coverage_percent: float = 0.0):
        """Notify monitor that tests are complete."""
        try:
            data = {"coverage": coverage_percent}
            response = self.session.post(f"{self.monitor_url}/api/finish-tests", json=data)
            print(f"✅ Monitor notified: Test run finished")
        except Exception as e:
            print(f"⚠️ Failed to notify monitor finish: {e}")
    
    def parse_pytest_output(self, line: str) -> Dict[str, Any]:
        """Parse pytest output line for test information."""
        result = {}
        
        # Match test execution lines
        # Example: "tests/test_backoff.py::TestBackoff::test_init PASSED [  1%]"
        test_pattern = r'([^:]+::[^:]+::[^\s]+)\s+(PASSED|FAILED|SKIPPED|ERROR)\s*(?:\[\s*(\d+)%\])?'
        match = re.search(test_pattern, line)
        
        if match:
            result['test_name'] = match.group(1)
            result['status'] = match.group(2)
            if match.group(3):
                result['progress_percent'] = int(match.group(3))
        
        # Match coverage information
        coverage_pattern = r'TOTAL\s+\d+\s+\d+\s+(\d+)%'
        coverage_match = re.search(coverage_pattern, line)
        if coverage_match:
            result['coverage'] = float(coverage_match.group(1))
        
        return result
    
    def run_tests_with_monitoring(self, test_paths: List[str], coverage: bool = True):
        """Run tests with real-time monitoring."""
        print("🖥️  Starting monitored test execution...")
        print(f"📊 Monitor dashboard: {self.monitor_url}")
        print("=" * 60)
        
        # Build pytest command
        cmd = ["python", "-m", "pytest", "-v"]
        
        if coverage:
            cmd.extend(["--cov=src", "--cov-report=term-missing", "--cov-report=html"])
        
        cmd.extend(test_paths)
        
        print(f"🚀 Command: {' '.join(cmd)}")
        print("=" * 60)
        
        # Notify monitor of start
        self.notify_start(' '.join(cmd), 103)
        
        # Run tests with real-time output parsing
        start_time = time.time()
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            test_count = 0
            final_coverage = 0.0
            
            # Process output line by line
            for line in process.stdout:
                print(line.rstrip())  # Print to console for user
                
                # Parse line for test information
                parsed = self.parse_pytest_output(line)
                
                if 'test_name' in parsed:
                    test_count += 1
                    self.notify_progress(
                        parsed['test_name'],
                        parsed['status']
                    )
                    print(f"📊 Test #{test_count}: {parsed['test_name']} - {parsed['status']}")
                
                if 'coverage' in parsed:
                    final_coverage = parsed['coverage']
                    self.notify_coverage(final_coverage)
                    print(f"📈 Coverage: {final_coverage}%")
            
            # Wait for process to complete
            return_code = process.wait()
            duration = time.time() - start_time
            
            print("=" * 60)
            print(f"✅ Test execution completed in {duration:.2f}s")
            print(f"📊 Return code: {return_code}")
            print(f"📈 Final coverage: {final_coverage}%")
            
            # Notify monitor of completion
            self.notify_finish(final_coverage)
            
            return return_code == 0
            
        except Exception as e:
            print(f"❌ Test execution failed: {e}")
            self.notify_finish(0.0)
            return False
    
    def run_reliability_test(self, test_paths: List[str], iterations: int = 10):
        """Run tests multiple times to check reliability."""
        print(f"🔄 Starting reliability test: {iterations} iterations")
        print("=" * 60)
        
        results = []
        
        for i in range(iterations):
            print(f"\n🧪 Iteration {i + 1}/{iterations}")
            print("-" * 40)
            
            start_time = time.time()
            success = self.run_tests_with_monitoring(test_paths, coverage=(i == 0))
            duration = time.time() - start_time
            
            results.append({
                'iteration': i + 1,
                'success': success,
                'duration': duration
            })
            
            if not success:
                print(f"❌ Iteration {i + 1} failed!")
            else:
                print(f"✅ Iteration {i + 1} passed in {duration:.2f}s")
        
        # Summary
        print("\n" + "=" * 60)
        print("📊 RELIABILITY TEST SUMMARY")
        print("=" * 60)
        
        successful = sum(1 for r in results if r['success'])
        success_rate = (successful / iterations) * 100
        avg_duration = sum(r['duration'] for r in results) / iterations
        
        print(f"✅ Success Rate: {successful}/{iterations} ({success_rate:.1f}%)")
        print(f"⏱️  Average Duration: {avg_duration:.2f}s")
        print(f"📈 Min Duration: {min(r['duration'] for r in results):.2f}s")
        print(f"📉 Max Duration: {max(r['duration'] for r in results):.2f}s")
        
        if success_rate >= 95:
            print("🎉 RELIABILITY TEST PASSED (≥95% success rate)")
        else:
            print("⚠️ RELIABILITY TEST NEEDS ATTENTION (<95% success rate)")
        
        return results

def main():
    parser = argparse.ArgumentParser(description="Run tests with real-time monitoring")
    parser.add_argument("--monitor-url", default="http://localhost:8001", 
                       help="Monitor dashboard URL")
    parser.add_argument("--reliability", type=int, default=0,
                       help="Run reliability test with N iterations")
    parser.add_argument("--no-coverage", action="store_true",
                       help="Skip coverage analysis")
    parser.add_argument("tests", nargs="*", default=[
        "tests/unit/test_backoff.py",
        "tests/unit/test_session_manager.py", 
        "tests/integration/test_websocket_lifecycle.py"
    ], help="Test paths to run")
    
    args = parser.parse_args()
    
    runner = MonitoredTestRunner(args.monitor_url)
    
    print("🖥️  Monitored Test Runner - Phase 2 P4")
    print(f"📊 Monitor URL: {args.monitor_url}")
    print(f"🧪 Test paths: {args.tests}")
    print("=" * 60)
    
    if args.reliability > 0:
        results = runner.run_reliability_test(args.tests, args.reliability)
        return all(r['success'] for r in results)
    else:
        return runner.run_tests_with_monitoring(args.tests, not args.no_coverage)

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)