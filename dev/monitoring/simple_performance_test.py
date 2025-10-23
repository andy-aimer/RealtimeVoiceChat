#!/usr/bin/env python3
"""
Simple Performance Test Runner
Phase 2 P4 - T109: Performance Testing with Live Monitoring
"""

import sys
import os
import time
import traceback

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src'))

def test_imports():
    """Test that all required modules can be imported."""
    print("🔍 Testing imports...")
    
    try:
        from session.session_manager import SessionManager, WebSocketSession
        print("✅ Session manager imported successfully")
    except Exception as e:
        print(f"❌ Failed to import session manager: {e}")
        return False
    
    try:
        from utils.backoff import ExponentialBackoff
        print("✅ Exponential backoff imported successfully")
    except Exception as e:
        print(f"❌ Failed to import backoff: {e}")
        return False
    
    try:
        import requests
        print("✅ Requests imported successfully")
    except Exception as e:
        print(f"❌ Failed to import requests: {e}")
        return False
    
    try:
        import psutil
        print("✅ PSUtil imported successfully")
    except Exception as e:
        print(f"❌ Failed to import psutil: {e}")
        return False
    
    return True

def test_session_creation():
    """Test basic session creation performance."""
    print("\n📊 Testing Session Creation Performance...")
    
    try:
        from session.session_manager import SessionManager, WebSocketSession
        
        manager = SessionManager()
        
        start_time = time.time()
        num_sessions = 100
        
        for i in range(num_sessions):
            session_id = f"test_session_{i}"
            session = WebSocketSession(session_id)
            manager._sessions[session_id] = session  # Use private attribute
            
            # Add test messages
            session.add_message("user", f"Test message {i}")
            session.add_message("assistant", f"Response {i}")
            
            if i % 20 == 0:
                print(f"  📈 Created {i}/{num_sessions} sessions")
        
        total_time = time.time() - start_time
        sessions_per_second = num_sessions / total_time
        
        print(f"✅ Created {num_sessions} sessions in {total_time:.3f}s")
        print(f"📊 Performance: {sessions_per_second:.1f} sessions/second")
        
        # Cleanup
        manager._sessions.clear()
        
        return True
        
    except Exception as e:
        print(f"❌ Session creation test failed: {e}")
        traceback.print_exc()
        return False

def test_backoff_performance():
    """Test exponential backoff performance."""
    print("\n⏱️ Testing Exponential Backoff Performance...")
    
    try:
        from utils.backoff import ExponentialBackoff
        
        backoff = ExponentialBackoff(initial_delay=1.0, max_delay=30.0, max_attempts=6)
        
        start_time = time.time()
        num_cycles = 1000
        
        for cycle in range(num_cycles):
            # Simulate reconnection attempts
            for attempt in range(6):
                delay = backoff.next_delay()  # Use correct method name
                should_give_up = backoff.should_give_up()
                if should_give_up:
                    break
            
            # Reset for next cycle
            backoff.reset()
            
            if cycle % 200 == 0:
                print(f"  📈 Completed {cycle}/{num_cycles} cycles")
        
        total_time = time.time() - start_time
        cycles_per_second = num_cycles / total_time
        
        print(f"✅ Completed {num_cycles} backoff cycles in {total_time:.3f}s")
        print(f"📊 Performance: {cycles_per_second:.1f} cycles/second")
        
        return True
        
    except Exception as e:
        print(f"❌ Backoff performance test failed: {e}")
        traceback.print_exc()
        return False

def test_monitor_connection():
    """Test connection to monitoring dashboard."""
    print("\n🖥️ Testing Monitor Connection...")
    
    try:
        import requests
        
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            print("✅ Monitor dashboard is responding")
            
            # Test sending update
            update_data = {
                "test_name": "Simple Performance Test",
                "status": "RUNNING"
            }
            
            update_response = requests.post(
                "http://localhost:8001/api/test-update", 
                json=update_data,
                timeout=5
            )
            
            if update_response.status_code == 200:
                print("✅ Monitor update API is working")
                return True
            else:
                print(f"⚠️ Monitor update failed: {update_response.status_code}")
                return False
        else:
            print(f"❌ Monitor dashboard not responding: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"⚠️ Monitor connection failed: {e}")
        print("💡 Make sure monitoring dashboard is running: python monitoring/test_monitor.py")
        return False

def run_simple_performance_suite():
    """Run a simplified performance test suite."""
    print("🚀 Simple Performance Testing Suite")
    print("=" * 50)
    
    # Test imports
    if not test_imports():
        print("\n❌ Import test failed. Cannot proceed.")
        return False
    
    # Test monitor connection
    monitor_working = test_monitor_connection()
    
    # Test session creation
    session_test = test_session_creation()
    
    # Test backoff performance
    backoff_test = test_backoff_performance()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 PERFORMANCE TEST SUMMARY")
    print("=" * 50)
    
    tests_passed = sum([session_test, backoff_test])
    total_tests = 2
    
    print(f"✅ Tests Passed: {tests_passed}/{total_tests}")
    print(f"🖥️ Monitor Connection: {'✅' if monitor_working else '❌'}")
    
    if tests_passed == total_tests:
        print("🎉 All performance tests passed!")
        return True
    else:
        print("⚠️ Some performance tests failed.")
        return False

if __name__ == "__main__":
    success = run_simple_performance_suite()
    sys.exit(0 if success else 1)