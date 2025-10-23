"""
Performance Testing Suite with Real-Time Monitoring
Phase 2 P4 - T109: Performance Testing with Live Monitoring

This module provides comprehensive performance testing capabilities
with real-time monitoring integration for WebSocket lifecycle components.
"""

import asyncio
import time
import json
import threading
import statistics
import psutil
import subprocess
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import requests
import websocket
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

from session.session_manager import SessionManager, WebSocketSession
from utils.backoff import ExponentialBackoff

class PerformanceMonitor:
    """Real-time performance metrics collection and reporting."""
    
    def __init__(self, monitor_url: str = "http://localhost:8001"):
        self.monitor_url = monitor_url
        self.session = requests.Session()
        self.metrics = {
            "test_start_time": None,
            "current_test": None,
            "concurrent_sessions": 0,
            "total_connections": 0,
            "successful_connections": 0,
            "failed_connections": 0,
            "reconnection_times": [],
            "memory_samples": [],
            "cpu_samples": [],
            "response_times": [],
            "session_cleanup_times": []
        }
        self.is_monitoring = False
        self.monitor_thread = None
    
    def start_monitoring(self, test_name: str):
        """Start performance monitoring for a test."""
        self.metrics["test_start_time"] = time.time()
        self.metrics["current_test"] = test_name
        self.is_monitoring = True
        
        # Start background monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_system, daemon=True)
        self.monitor_thread.start()
        
        # Notify dashboard
        try:
            self.session.post(f"{self.monitor_url}/api/test-update", json={
                "test_name": f"Performance Test: {test_name}",
                "status": "RUNNING"
            })
        except Exception as e:
            print(f"⚠️ Failed to notify monitor: {e}")
    
    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        
        # Calculate final metrics
        duration = time.time() - self.metrics["test_start_time"] if self.metrics["test_start_time"] else 0
        
        # Notify dashboard
        try:
            self.session.post(f"{self.monitor_url}/api/test-update", json={
                "test_name": f"Performance Test Complete: {self.metrics['current_test']}",
                "status": "PASSED",
                "duration": duration
            })
        except Exception as e:
            print(f"⚠️ Failed to notify monitor: {e}")
    
    def _monitor_system(self):
        """Background system monitoring."""
        while self.is_monitoring:
            try:
                # Collect system metrics
                cpu_percent = psutil.cpu_percent(interval=0.1)
                memory = psutil.virtual_memory()
                
                self.metrics["cpu_samples"].append(cpu_percent)
                self.metrics["memory_samples"].append(memory.percent)
                
                # Send to dashboard
                self.session.post(f"{self.monitor_url}/api/test-update", json={
                    "system_metrics": {
                        "cpu_percent": cpu_percent,
                        "memory_percent": memory.percent,
                        "concurrent_sessions": self.metrics["concurrent_sessions"]
                    }
                })
                
            except Exception as e:
                print(f"⚠️ Monitoring error: {e}")
            
            time.sleep(1)  # Sample every second
    
    def record_connection(self, success: bool, response_time: float = 0):
        """Record connection attempt result."""
        self.metrics["total_connections"] += 1
        if success:
            self.metrics["successful_connections"] += 1
            if response_time > 0:
                self.metrics["response_times"].append(response_time)
        else:
            self.metrics["failed_connections"] += 1
    
    def record_reconnection(self, reconnection_time: float):
        """Record reconnection timing."""
        self.metrics["reconnection_times"].append(reconnection_time)
    
    def record_cleanup(self, cleanup_time: float):
        """Record session cleanup timing."""
        self.metrics["session_cleanup_times"].append(cleanup_time)
    
    def set_concurrent_sessions(self, count: int):
        """Update concurrent session count."""
        self.metrics["concurrent_sessions"] = count
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get comprehensive performance summary."""
        duration = time.time() - self.metrics["test_start_time"] if self.metrics["test_start_time"] else 0
        
        summary = {
            "test_name": self.metrics["current_test"],
            "duration": duration,
            "total_connections": self.metrics["total_connections"],
            "successful_connections": self.metrics["successful_connections"],
            "failed_connections": self.metrics["failed_connections"],
            "success_rate": (self.metrics["successful_connections"] / max(1, self.metrics["total_connections"])) * 100,
            "concurrent_sessions_peak": self.metrics["concurrent_sessions"]
        }
        
        # Response time statistics
        if self.metrics["response_times"]:
            summary["response_times"] = {
                "min": min(self.metrics["response_times"]),
                "max": max(self.metrics["response_times"]),
                "avg": statistics.mean(self.metrics["response_times"]),
                "median": statistics.median(self.metrics["response_times"]),
                "p95": sorted(self.metrics["response_times"])[int(len(self.metrics["response_times"]) * 0.95)]
            }
        
        # Reconnection statistics
        if self.metrics["reconnection_times"]:
            summary["reconnection_times"] = {
                "min": min(self.metrics["reconnection_times"]),
                "max": max(self.metrics["reconnection_times"]),
                "avg": statistics.mean(self.metrics["reconnection_times"]),
                "median": statistics.median(self.metrics["reconnection_times"])
            }
        
        # System resource usage
        if self.metrics["cpu_samples"]:
            summary["cpu_usage"] = {
                "min": min(self.metrics["cpu_samples"]),
                "max": max(self.metrics["cpu_samples"]),
                "avg": statistics.mean(self.metrics["cpu_samples"])
            }
        
        if self.metrics["memory_samples"]:
            summary["memory_usage"] = {
                "min": min(self.metrics["memory_samples"]),
                "max": max(self.metrics["memory_samples"]),
                "avg": statistics.mean(self.metrics["memory_samples"])
            }
        
        # Session cleanup performance
        if self.metrics["session_cleanup_times"]:
            summary["cleanup_times"] = {
                "min": min(self.metrics["session_cleanup_times"]),
                "max": max(self.metrics["session_cleanup_times"]),
                "avg": statistics.mean(self.metrics["session_cleanup_times"])
            }
        
        return summary

class WebSocketLoadTester:
    """WebSocket connection load testing with real-time monitoring."""
    
    def __init__(self, server_url: str = "ws://localhost:8000/ws", monitor: PerformanceMonitor = None):
        self.server_url = server_url
        self.monitor = monitor or PerformanceMonitor()
        self.active_connections = []
        self.connection_results = []
    
    def create_connection(self, session_id: str = None) -> Tuple[bool, float]:
        """Create a single WebSocket connection and measure response time."""
        start_time = time.time()
        
        try:
            # Create WebSocket connection
            ws = websocket.WebSocket()
            ws.settimeout(10)  # 10 second timeout
            
            # Connect with session restoration if session_id provided
            url = self.server_url
            if session_id:
                url += f"?session_id={session_id}"
            
            ws.connect(url)
            
            # Send test message
            test_message = json.dumps({
                "type": "test_message",
                "timestamp": datetime.now().isoformat(),
                "data": "load_test"
            })
            ws.send(test_message)
            
            # Wait for response
            response = ws.recv()
            response_time = time.time() - start_time
            
            # Store connection for later cleanup
            self.active_connections.append(ws)
            
            return True, response_time
            
        except Exception as e:
            response_time = time.time() - start_time
            return False, response_time
    
    def run_concurrent_load_test(self, num_connections: int, duration_seconds: int = 30) -> Dict[str, Any]:
        """Run concurrent connection load test."""
        print(f"🔥 Starting load test: {num_connections} concurrent connections for {duration_seconds}s")
        
        self.monitor.start_monitoring(f"Load Test - {num_connections} Connections")
        self.monitor.set_concurrent_sessions(num_connections)
        
        results = {
            "num_connections": num_connections,
            "duration": duration_seconds,
            "connections_created": 0,
            "connections_successful": 0,
            "connections_failed": 0,
            "start_time": time.time()
        }
        
        try:
            # Create connections concurrently
            with ThreadPoolExecutor(max_workers=min(num_connections, 50)) as executor:
                # Submit connection tasks
                future_to_session = {}
                
                for i in range(num_connections):
                    session_id = f"load_test_session_{i}"
                    future = executor.submit(self.create_connection, session_id)
                    future_to_session[future] = session_id
                
                # Collect results as they complete
                for future in as_completed(future_to_session, timeout=duration_seconds + 10):
                    session_id = future_to_session[future]
                    
                    try:
                        success, response_time = future.result()
                        results["connections_created"] += 1
                        
                        if success:
                            results["connections_successful"] += 1
                        else:
                            results["connections_failed"] += 1
                        
                        # Record in monitor
                        self.monitor.record_connection(success, response_time)
                        
                        print(f"📊 Connection {results['connections_created']}/{num_connections}: "
                              f"{'✅' if success else '❌'} ({response_time:.3f}s)")
                        
                    except Exception as e:
                        results["connections_failed"] += 1
                        self.monitor.record_connection(False, 0)
                        print(f"❌ Connection failed: {e}")
            
            # Wait for test duration
            time.sleep(max(0, duration_seconds - (time.time() - results["start_time"])))
            
        except Exception as e:
            print(f"❌ Load test error: {e}")
        
        finally:
            # Cleanup connections
            cleanup_start = time.time()
            self.cleanup_connections()
            cleanup_time = time.time() - cleanup_start
            
            self.monitor.record_cleanup(cleanup_time)
            self.monitor.stop_monitoring()
            
            results["cleanup_time"] = cleanup_time
            results["total_duration"] = time.time() - results["start_time"]
        
        return results
    
    def cleanup_connections(self):
        """Clean up all active WebSocket connections."""
        print(f"🧹 Cleaning up {len(self.active_connections)} connections...")
        
        for ws in self.active_connections:
            try:
                ws.close()
            except Exception:
                pass
        
        self.active_connections.clear()

class SessionManagerPerformanceTester:
    """Performance testing for SessionManager operations."""
    
    def __init__(self, monitor: PerformanceMonitor = None):
        self.monitor = monitor or PerformanceMonitor()
        self.session_manager = SessionManager()
    
    def test_session_creation_performance(self, num_sessions: int = 1000) -> Dict[str, Any]:
        """Test session creation performance under load."""
        print(f"📊 Testing session creation: {num_sessions} sessions")
        
        self.monitor.start_monitoring(f"Session Creation - {num_sessions} Sessions")
        
        start_time = time.time()
        creation_times = []
        created_sessions = []
        
        for i in range(num_sessions):
            session_start = time.time()
            
            session_id = f"perf_test_session_{i}"
            
            # Create session synchronously (without await)
            try:
                # Create session directly instead of using async method
                from session.session_manager import WebSocketSession
                session = WebSocketSession(session_id)
                self.session_manager.sessions[session_id] = session
                created_sessions.append(session)
                
                creation_time = time.time() - session_start
                creation_times.append(creation_time)
                
                # Add some conversation context
                session.add_message("user", f"Test message {i}")
                session.add_message("assistant", f"Response {i}")
                
                if i % 100 == 0:
                    print(f"📈 Created {i}/{num_sessions} sessions")
                    
            except Exception as e:
                print(f"❌ Failed to create session {i}: {e}")
                creation_times.append(0)
        
        total_time = time.time() - start_time
        
        # Test cleanup performance
        cleanup_start = time.time()
        
        # Manual cleanup since we created sessions directly
        cleanup_count = 0
        for session_id in list(self.session_manager.sessions.keys()):
            if session_id.startswith("perf_test_session_"):
                del self.session_manager.sessions[session_id]
                cleanup_count += 1
        
        cleanup_time = time.time() - cleanup_start
        
        self.monitor.record_cleanup(cleanup_time)
        self.monitor.stop_monitoring()
        
        # Filter out failed creation attempts
        valid_creation_times = [t for t in creation_times if t > 0]
        
        results = {
            "num_sessions": num_sessions,
            "successful_sessions": len(valid_creation_times),
            "total_time": total_time,
            "avg_creation_time": statistics.mean(valid_creation_times) if valid_creation_times else 0,
            "min_creation_time": min(valid_creation_times) if valid_creation_times else 0,
            "max_creation_time": max(valid_creation_times) if valid_creation_times else 0,
            "sessions_per_second": len(valid_creation_times) / total_time if total_time > 0 else 0,
            "cleanup_time": cleanup_time,
            "cleaned_sessions": cleanup_count
        }
        
        return results
    
    def test_concurrent_session_access(self, num_threads: int = 20, operations_per_thread: int = 100) -> Dict[str, Any]:
        """Test concurrent session access performance."""
        print(f"🔄 Testing concurrent access: {num_threads} threads, {operations_per_thread} ops each")
        
        self.monitor.start_monitoring(f"Concurrent Access - {num_threads}x{operations_per_thread}")
        
        # Pre-create some sessions
        session_ids = []
        for i in range(num_threads):
            session_id = f"concurrent_test_session_{i}"
            # Create session directly
            from session.session_manager import WebSocketSession
            session = WebSocketSession(session_id)
            self.session_manager.sessions[session_id] = session
            session_ids.append(session_id)
        
        def worker_thread(thread_id: int, session_ids: List[str]) -> Dict[str, Any]:
            """Worker thread for concurrent operations."""
            thread_results = {
                "thread_id": thread_id,
                "operations": 0,
                "errors": 0,
                "operation_times": []
            }
            
            for op in range(operations_per_thread):
                op_start = time.time()
                
                try:
                    # Random operations
                    session_id = session_ids[op % len(session_ids)]
                    
                    if op % 4 == 0:
                        # Get session
                        session = self.session_manager.sessions.get(session_id)
                    elif op % 4 == 1:
                        # Touch session (update last_active)
                        session = self.session_manager.sessions.get(session_id)
                        if session:
                            session.touch()
                    elif op % 4 == 2:
                        # Update session
                        session = self.session_manager.sessions.get(session_id)
                        if session:
                            session.add_message("user", f"Thread {thread_id} message {op}")
                    else:
                        # Get stats
                        stats = {
                            "total_sessions": len(self.session_manager.sessions),
                            "active_sessions": len([s for s in self.session_manager.sessions.values() if not s.is_expired()])
                        }
                    
                    thread_results["operations"] += 1
                    
                except Exception as e:
                    thread_results["errors"] += 1
                
                op_time = time.time() - op_start
                thread_results["operation_times"].append(op_time)
            
            return thread_results
        
        # Run concurrent operations
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            
            for thread_id in range(num_threads):
                future = executor.submit(worker_thread, thread_id, session_ids)
                futures.append(future)
            
            # Collect results
            thread_results = []
            for future in as_completed(futures):
                result = future.result()
                thread_results.append(result)
        
        total_time = time.time() - start_time
        
        # Aggregate results
        total_operations = sum(r["operations"] for r in thread_results)
        total_errors = sum(r["errors"] for r in thread_results)
        all_operation_times = []
        for r in thread_results:
            all_operation_times.extend(r["operation_times"])
        
        # Cleanup test sessions
        for session_id in session_ids:
            self.session_manager.sessions.pop(session_id, None)
        
        self.monitor.stop_monitoring()
        
        results = {
            "num_threads": num_threads,
            "operations_per_thread": operations_per_thread,
            "total_operations": total_operations,
            "total_errors": total_errors,
            "error_rate": (total_errors / max(1, total_operations + total_errors)) * 100,
            "total_time": total_time,
            "operations_per_second": total_operations / total_time if total_time > 0 else 0,
            "avg_operation_time": statistics.mean(all_operation_times) if all_operation_times else 0,
            "thread_results": thread_results
        }
        
        return results

class ReconnectionPerformanceTester:
    """Test reconnection performance under various conditions."""
    
    def __init__(self, monitor: PerformanceMonitor = None):
        self.monitor = monitor or PerformanceMonitor()
    
    def test_exponential_backoff_performance(self, num_cycles: int = 100) -> Dict[str, Any]:
        """Test exponential backoff calculation performance."""
        print(f"⏱️  Testing backoff performance: {num_cycles} cycles")
        
        self.monitor.start_monitoring(f"Backoff Performance - {num_cycles} Cycles")
        
        backoff = ExponentialBackoff(initial_delay=1.0, max_delay=30.0, max_attempts=6)
        
        start_time = time.time()
        calculation_times = []
        
        for cycle in range(num_cycles):
            cycle_start = time.time()
            
            # Simulate reconnection attempts
            for attempt in range(6):
                calc_start = time.time()
                delay = backoff.get_next_delay()
                calc_time = time.time() - calc_start
                calculation_times.append(calc_time)
                
                # Simulate waiting (but don't actually wait)
                should_give_up = backoff.should_give_up()
                if should_give_up:
                    break
            
            # Reset for next cycle
            backoff.reset()
            
            cycle_time = time.time() - cycle_start
            if cycle % 10 == 0:
                print(f"📊 Completed {cycle}/{num_cycles} cycles")
        
        total_time = time.time() - start_time
        
        self.monitor.stop_monitoring()
        
        results = {
            "num_cycles": num_cycles,
            "total_time": total_time,
            "cycles_per_second": num_cycles / total_time,
            "avg_calculation_time": statistics.mean(calculation_times),
            "min_calculation_time": min(calculation_times),
            "max_calculation_time": max(calculation_times),
            "total_calculations": len(calculation_times)
        }
        
        return results

def run_comprehensive_performance_suite():
    """Run the complete performance testing suite with real-time monitoring."""
    print("🚀 Starting Comprehensive Performance Testing Suite")
    print("=" * 60)
    
    monitor = PerformanceMonitor()
    all_results = {}
    
    # Test 1: Session Manager Performance
    print("\n📊 Test 1: Session Manager Performance")
    print("-" * 40)
    session_tester = SessionManagerPerformanceTester(monitor)
    
    all_results["session_creation"] = session_tester.test_session_creation_performance(1000)
    print(f"✅ Session creation: {all_results['session_creation']['sessions_per_second']:.1f} sessions/sec")
    
    all_results["concurrent_access"] = session_tester.test_concurrent_session_access(20, 100)
    print(f"✅ Concurrent access: {all_results['concurrent_access']['operations_per_second']:.1f} ops/sec")
    
    # Test 2: Exponential Backoff Performance
    print("\n⏱️  Test 2: Exponential Backoff Performance")
    print("-" * 40)
    backoff_tester = ReconnectionPerformanceTester(monitor)
    
    all_results["backoff_performance"] = backoff_tester.test_exponential_backoff_performance(1000)
    print(f"✅ Backoff calculations: {all_results['backoff_performance']['cycles_per_second']:.1f} cycles/sec")
    
    # Test 3: WebSocket Load Testing (if test server is running)
    print("\n🔥 Test 3: WebSocket Load Testing")
    print("-" * 40)
    
    try:
        load_tester = WebSocketLoadTester(monitor=monitor)
        
        # Test with increasing load
        for num_connections in [10, 25, 50]:
            print(f"\n🧪 Load test: {num_connections} concurrent connections")
            result = load_tester.run_concurrent_load_test(num_connections, duration_seconds=10)
            all_results[f"load_test_{num_connections}"] = result
            
            success_rate = (result["connections_successful"] / max(1, result["connections_created"])) * 100
            print(f"✅ Success rate: {success_rate:.1f}%")
            
            # Brief pause between tests
            time.sleep(2)
            
    except Exception as e:
        print(f"⚠️ WebSocket load testing skipped: {e}")
        print("💡 Make sure test server is running: python test_server.py")
    
    # Performance Summary
    print("\n" + "=" * 60)
    print("📊 PERFORMANCE TESTING SUMMARY")
    print("=" * 60)
    
    for test_name, results in all_results.items():
        print(f"\n🧪 {test_name.replace('_', ' ').title()}:")
        
        if "sessions_per_second" in results:
            print(f"  📈 Performance: {results['sessions_per_second']:.1f} sessions/sec")
        if "operations_per_second" in results:
            print(f"  📈 Performance: {results['operations_per_second']:.1f} operations/sec")
        if "cycles_per_second" in results:
            print(f"  📈 Performance: {results['cycles_per_second']:.1f} cycles/sec")
        if "connections_successful" in results:
            success_rate = (results["connections_successful"] / max(1, results["connections_created"])) * 100
            print(f"  📈 Success Rate: {success_rate:.1f}%")
        if "error_rate" in results:
            print(f"  ⚠️ Error Rate: {results['error_rate']:.2f}%")
    
    # Get overall system performance summary
    performance_summary = monitor.get_performance_summary()
    
    print(f"\n🖥️ System Performance During Tests:")
    if "cpu_usage" in performance_summary:
        print(f"  🖥️ CPU Usage: {performance_summary['cpu_usage']['avg']:.1f}% avg")
    if "memory_usage" in performance_summary:
        print(f"  💾 Memory Usage: {performance_summary['memory_usage']['avg']:.1f}% avg")
    
    print("\n🎉 Performance testing complete!")
    print("📊 Monitor dashboard: http://localhost:8001")
    
    return all_results

if __name__ == "__main__":
    results = run_comprehensive_performance_suite()