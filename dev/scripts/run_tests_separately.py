#!/usr/bin/env python3
"""
Workaround script to run pytest tests file-by-file to avoid thread cleanup issues.

Usage:
    python run_tests_separately.py
    python run_tests_separately.py --coverage
"""
import subprocess
import sys
from pathlib import Path
import argparse

def run_test_file(filepath, with_coverage=False):
    """Run a single test file and return results."""
    cmd = ["python", "-m", "pytest", str(filepath), "-q", "--tb=short"]
    if with_coverage:
        cmd.extend(["--cov=code", "--cov-append"])
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def main():
    parser = argparse.ArgumentParser(description="Run pytest tests file-by-file")
    parser.add_argument("--coverage", action="store_true", help="Collect coverage data")
    args = parser.parse_args()
    
    # Find all test files
    test_dir = Path("tests")
    test_files = sorted(test_dir.rglob("test_*.py"))
    
    if not test_files:
        print("❌ No test files found")
        return 1
    
    print(f"🧪 Running {len(test_files)} test files separately...")
    print()
    
    total_passed = 0
    total_failed = 0
    failed_files = []
    
    # Remove existing coverage data if running with coverage
    if args.coverage:
        subprocess.run(["coverage", "erase"], capture_output=True)
    
    for test_file in test_files:
        relative_path = test_file
        print(f"Testing {relative_path}...", end=" ", flush=True)
        
        returncode, stdout, stderr = run_test_file(test_file, args.coverage)
        
        # Parse output to extract pass/fail counts
        if returncode == 0:
            # Extract count from output like "42 passed in 0.68s"
            if "passed" in stdout:
                try:
                    count = int(stdout.split()[0])
                    total_passed += count
                    print(f"✅ {count} passed")
                except:
                    print("✅ passed")
            else:
                print("✅ passed")
        else:
            # Extract counts from output like "2 failed, 41 passed"
            if "failed" in stdout:
                try:
                    parts = stdout.split()
                    for i, part in enumerate(parts):
                        if part == "failed,":
                            failed = int(parts[i-1])
                            total_failed += failed
                        if part == "passed":
                            passed = int(parts[i-1])
                            total_passed += passed
                    print(f"⚠️  {failed} failed, {passed} passed")
                    failed_files.append(str(relative_path))
                except:
                    print("❌ failed")
                    failed_files.append(str(relative_path))
            else:
                print("❌ failed")
                failed_files.append(str(relative_path))
    
    print()
    print("=" * 60)
    print(f"📊 Total Results:")
    print(f"   ✅ Passed: {total_passed}")
    print(f"   ❌ Failed: {total_failed}")
    print(f"   📁 Test files: {len(test_files)}")
    
    if failed_files:
        print()
        print("Failed files:")
        for f in failed_files:
            print(f"   - {f}")
    
    if args.coverage:
        print()
        print("📈 Generating coverage report...")
        subprocess.run(["coverage", "report", "--include=code/*"])
        subprocess.run(["coverage", "html"])
        print("   HTML report: htmlcov/index.html")
    
    print("=" * 60)
    
    return 1 if total_failed > 0 else 0

if __name__ == "__main__":
    sys.exit(main())
