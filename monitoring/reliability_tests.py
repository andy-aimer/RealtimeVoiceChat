"""
Reliability Testing Suite with Real-Time Monitoring
Phase 2 P4 - T109: Performance Testing with Live Monitoring

This module provides reliability testing for the WebSocket lifecycle components
to ensure consistent performance under various conditions.
"""

import time
import statistics
import json
import sys
import os
from typing import Dict, List, Any

# Add src and monitoring directories to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))
sys.path.insert(0, os.path.dirname(__file__))

from performance_tests import PerformanceMonitor, SessionManagerPerformanceTester, ReconnectionPerformanceTester
from test_runner import MonitoredTestRunner

class ReliabilityTester:
    """Comprehensive reliability testing with statistical analysis."""
    
    def __init__(self, monitor_url: str = "http://localhost:8001"):
        self.monitor = PerformanceMonitor(monitor_url)
        self.test_runner = MonitoredTestRunner(monitor_url)
    
    def run_reliability_suite(self, iterations: int = 20) -> Dict[str, Any]:
        """Run comprehensive reliability testing suite."""
        print(f"🔄 Starting Reliability Testing Suite - {iterations} iterations")
        print("=" * 60)
        
        self.monitor.start_monitoring(f"Reliability Suite - {iterations} Iterations")
        
        suite_results = {
            "iterations": iterations,
            "start_time": time.time(),
            "test_results": [],
            "session_performance": [],
            "backoff_performance": [],
            "unit_test_results": []
        }
        
        for iteration in range(1, iterations + 1):
            print(f"\n🧪 Iteration {iteration}/{iterations}")
            print("-" * 40)
            
            iteration_start = time.time()
            iteration_results = {
                "iteration": iteration,
                "start_time": iteration_start,
                "tests": {}
            }
            
            try:
                # Test 1: Unit Test Reliability
                print("📋 Running unit tests...")
                unit_start = time.time()
                unit_success = self.test_runner.run_tests_with_monitoring([
                    "tests/unit/test_backoff.py",
                    "tests/unit/test_session_manager.py"
                ], coverage=False)
                unit_duration = time.time() - unit_start
                
                iteration_results["tests"]["unit_tests"] = {
                    "success": unit_success,
                    "duration": unit_duration
                }
                suite_results["unit_test_results"].append(unit_success)
                
                # Test 2: Session Manager Performance
                print("📊 Testing session manager performance...")
                session_tester = SessionManagerPerformanceTester(self.monitor)
                session_result = session_tester.test_session_creation_performance(100)  # Smaller load for reliability
                
                iteration_results["tests"]["session_performance"] = session_result
                suite_results["session_performance"].append(session_result["sessions_per_second"])
                
                # Test 3: Backoff Performance
                print("⏱️  Testing backoff performance...")
                backoff_tester = ReconnectionPerformanceTester(self.monitor)
                backoff_result = backoff_tester.test_exponential_backoff_performance(100)  # Smaller load
                
                iteration_results["tests"]["backoff_performance"] = backoff_result
                suite_results["backoff_performance"].append(backoff_result["cycles_per_second"])
                
                iteration_results["success"] = unit_success
                iteration_results["duration"] = time.time() - iteration_start
                
                print(f"✅ Iteration {iteration}: "
                      f"Unit Tests: {'✅' if unit_success else '❌'}, "
                      f"Sessions: {session_result['sessions_per_second']:.1f}/s, "
                      f"Backoff: {backoff_result['cycles_per_second']:.1f}/s")
                
            except Exception as e:
                print(f"❌ Iteration {iteration} failed: {e}")
                iteration_results["success"] = False
                iteration_results["error"] = str(e)
                iteration_results["duration"] = time.time() - iteration_start
                
                # Record failed metrics
                suite_results["unit_test_results"].append(False)
                suite_results["session_performance"].append(0)
                suite_results["backoff_performance"].append(0)
            
            suite_results["test_results"].append(iteration_results)
            
            # Brief pause between iterations
            time.sleep(1)
        
        suite_results["total_duration"] = time.time() - suite_results["start_time"]
        
        self.monitor.stop_monitoring()
        
        # Calculate reliability statistics
        self._calculate_reliability_stats(suite_results)
        
        return suite_results
    
    def _calculate_reliability_stats(self, results: Dict[str, Any]):
        """Calculate comprehensive reliability statistics."""
        # Unit test reliability
        unit_successes = sum(1 for result in results["unit_test_results"] if result)
        unit_reliability = (unit_successes / len(results["unit_test_results"])) * 100
        
        # Performance consistency
        session_perf = [p for p in results["session_performance"] if p > 0]
        backoff_perf = [p for p in results["backoff_performance"] if p > 0]
        
        results["reliability_stats"] = {
            "unit_test_reliability": unit_reliability,
            "successful_iterations": unit_successes,
            "failed_iterations": len(results["unit_test_results"]) - unit_successes,
            "session_performance_stats": {
                "mean": statistics.mean(session_perf) if session_perf else 0,
                "stdev": statistics.stdev(session_perf) if len(session_perf) > 1 else 0,
                "min": min(session_perf) if session_perf else 0,
                "max": max(session_perf) if session_perf else 0,
                "coefficient_of_variation": (statistics.stdev(session_perf) / statistics.mean(session_perf)) * 100 if len(session_perf) > 1 and statistics.mean(session_perf) > 0 else 0
            },
            "backoff_performance_stats": {
                "mean": statistics.mean(backoff_perf) if backoff_perf else 0,
                "stdev": statistics.stdev(backoff_perf) if len(backoff_perf) > 1 else 0,
                "min": min(backoff_perf) if backoff_perf else 0,
                "max": max(backoff_perf) if backoff_perf else 0,
                "coefficient_of_variation": (statistics.stdev(backoff_perf) / statistics.mean(backoff_perf)) * 100 if len(backoff_perf) > 1 and statistics.mean(backoff_perf) > 0 else 0
            }
        }
    
    def run_stress_reliability_test(self, duration_minutes: int = 10) -> Dict[str, Any]:
        """Run extended stress testing for reliability assessment."""
        print(f"🔥 Starting Stress Reliability Test - {duration_minutes} minutes")
        print("=" * 60)
        
        self.monitor.start_monitoring(f"Stress Test - {duration_minutes}min")
        
        end_time = time.time() + (duration_minutes * 60)
        stress_results = {
            "duration_minutes": duration_minutes,
            "start_time": time.time(),
            "test_cycles": 0,
            "successful_cycles": 0,
            "failed_cycles": 0,
            "performance_samples": []
        }
        
        cycle = 0
        while time.time() < end_time:
            cycle += 1
            cycle_start = time.time()
            
            print(f"🔄 Stress cycle {cycle} (remaining: {int((end_time - time.time()) / 60)}min)")
            
            try:
                # Quick session manager test
                session_tester = SessionManagerPerformanceTester(self.monitor)
                session_result = session_tester.test_session_creation_performance(50)
                
                # Quick backoff test
                backoff_tester = ReconnectionPerformanceTester(self.monitor)
                backoff_result = backoff_tester.test_exponential_backoff_performance(50)
                
                cycle_duration = time.time() - cycle_start
                
                stress_results["test_cycles"] += 1
                stress_results["successful_cycles"] += 1
                stress_results["performance_samples"].append({
                    "cycle": cycle,
                    "session_perf": session_result["sessions_per_second"],
                    "backoff_perf": backoff_result["cycles_per_second"],
                    "duration": cycle_duration
                })
                
                print(f"✅ Cycle {cycle}: "
                      f"Sessions: {session_result['sessions_per_second']:.1f}/s, "
                      f"Backoff: {backoff_result['cycles_per_second']:.1f}/s")
                
            except Exception as e:
                print(f"❌ Cycle {cycle} failed: {e}")
                stress_results["test_cycles"] += 1
                stress_results["failed_cycles"] += 1
                
                stress_results["performance_samples"].append({
                    "cycle": cycle,
                    "session_perf": 0,
                    "backoff_perf": 0,
                    "duration": time.time() - cycle_start,
                    "error": str(e)
                })
            
            # Brief pause between cycles
            time.sleep(2)
        
        stress_results["total_duration"] = time.time() - stress_results["start_time"]
        stress_results["reliability_percentage"] = (stress_results["successful_cycles"] / stress_results["test_cycles"]) * 100
        
        # Calculate performance degradation over time
        successful_samples = [s for s in stress_results["performance_samples"] if s["session_perf"] > 0]
        if len(successful_samples) >= 2:
            first_half = successful_samples[:len(successful_samples)//2]
            second_half = successful_samples[len(successful_samples)//2:]
            
            first_half_avg = statistics.mean([s["session_perf"] for s in first_half])
            second_half_avg = statistics.mean([s["session_perf"] for s in second_half])
            
            stress_results["performance_degradation"] = {
                "first_half_avg": first_half_avg,
                "second_half_avg": second_half_avg,
                "degradation_percent": ((first_half_avg - second_half_avg) / first_half_avg) * 100 if first_half_avg > 0 else 0
            }
        
        self.monitor.stop_monitoring()
        
        return stress_results

def generate_reliability_report(results: Dict[str, Any], output_file: str = "reliability_report.json"):
    """Generate comprehensive reliability report."""
    print("\n" + "=" * 60)
    print("📊 RELIABILITY TESTING REPORT")
    print("=" * 60)
    
    if "reliability_stats" in results:
        stats = results["reliability_stats"]
        
        print(f"\n🧪 Test Reliability:")
        print(f"  ✅ Success Rate: {stats['unit_test_reliability']:.1f}%")
        print(f"  🔄 Successful Iterations: {stats['successful_iterations']}")
        print(f"  ❌ Failed Iterations: {stats['failed_iterations']}")
        
        print(f"\n📊 Session Manager Performance:")
        session_stats = stats["session_performance_stats"]
        print(f"  📈 Average: {session_stats['mean']:.1f} sessions/sec")
        print(f"  📉 Std Dev: {session_stats['stdev']:.2f}")
        print(f"  🎯 Consistency (CV): {session_stats['coefficient_of_variation']:.1f}%")
        print(f"  📏 Range: {session_stats['min']:.1f} - {session_stats['max']:.1f}")
        
        print(f"\n⏱️  Backoff Performance:")
        backoff_stats = stats["backoff_performance_stats"]
        print(f"  📈 Average: {backoff_stats['mean']:.1f} cycles/sec")
        print(f"  📉 Std Dev: {backoff_stats['stdev']:.2f}")
        print(f"  🎯 Consistency (CV): {backoff_stats['coefficient_of_variation']:.1f}%")
        print(f"  📏 Range: {backoff_stats['min']:.1f} - {backoff_stats['max']:.1f}")
        
        # Reliability assessment
        print(f"\n🎯 RELIABILITY ASSESSMENT:")
        if stats["unit_test_reliability"] >= 95:
            print("  🟢 EXCELLENT: >95% test reliability")
        elif stats["unit_test_reliability"] >= 90:
            print("  🟡 GOOD: 90-95% test reliability")
        else:
            print("  🔴 NEEDS ATTENTION: <90% test reliability")
        
        if session_stats["coefficient_of_variation"] <= 10:
            print("  🟢 EXCELLENT: <10% performance variation")
        elif session_stats["coefficient_of_variation"] <= 20:
            print("  🟡 GOOD: 10-20% performance variation")
        else:
            print("  🔴 NEEDS ATTENTION: >20% performance variation")
    
    # Handle stress test results
    if "reliability_percentage" in results:
        print(f"\n🔥 Stress Test Results:")
        print(f"  🔄 Reliability: {results['reliability_percentage']:.1f}%")
        print(f"  ⏱️  Duration: {results['duration_minutes']} minutes")
        print(f"  🧪 Test Cycles: {results['test_cycles']}")
        
        if "performance_degradation" in results:
            deg = results["performance_degradation"]
            print(f"  📉 Performance Degradation: {deg['degradation_percent']:.1f}%")
    
    print(f"\n💾 Saving detailed report to: {output_file}")
    
    # Save detailed results to JSON
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print("🎉 Reliability testing complete!")

def main():
    """Main reliability testing function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run reliability tests with real-time monitoring")
    parser.add_argument("--iterations", type=int, default=10, help="Number of reliability iterations")
    parser.add_argument("--stress-duration", type=int, default=5, help="Stress test duration in minutes")
    parser.add_argument("--monitor-url", default="http://localhost:8001", help="Monitor dashboard URL")
    parser.add_argument("--report-file", default="reliability_report.json", help="Output report file")
    
    args = parser.parse_args()
    
    tester = ReliabilityTester(args.monitor_url)
    
    print("🔄 Phase 2 P4 - T109: Reliability Testing with Live Monitoring")
    print(f"📊 Monitor URL: {args.monitor_url}")
    print(f"🧪 Iterations: {args.iterations}")
    print(f"🔥 Stress Duration: {args.stress_duration} minutes")
    print("=" * 60)
    
    # Run reliability suite
    reliability_results = tester.run_reliability_suite(args.iterations)
    
    # Run stress test
    print(f"\n🔥 Running stress reliability test...")
    stress_results = tester.run_stress_reliability_test(args.stress_duration)
    
    # Combine results
    combined_results = {
        "reliability_suite": reliability_results,
        "stress_test": stress_results,
        "test_timestamp": time.time(),
        "test_configuration": {
            "iterations": args.iterations,
            "stress_duration_minutes": args.stress_duration,
            "monitor_url": args.monitor_url
        }
    }
    
    # Generate report
    generate_reliability_report(reliability_results, args.report_file)
    
    return combined_results

if __name__ == "__main__":
    results = main()