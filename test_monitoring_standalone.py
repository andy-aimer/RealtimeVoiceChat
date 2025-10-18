#!/usr/bin/env python3
"""
Standalone test script for monitoring endpoints.
Tests /health and /metrics without starting full server.
"""

import asyncio
import logging
import sys
import os

# Add code directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

# Setup basic logging
logging.basicConfig(level=logging.INFO)

async def test_health_checks():
    """Test health check functions directly"""
    print("\n" + "="*60)
    print("TESTING HEALTH CHECKS")
    print("="*60 + "\n")
    
    try:
        from health_checks import (
            check_audio_processor,
            check_llm_backend,
            check_tts_engine,
            check_system_resources
        )
        
        # Test audio processor check
        print("1. Testing Audio Processor Check...")
        try:
            result = await check_audio_processor()
            print(f"   ✓ Status: {result['status']}")
            print(f"   Component: {result['component']}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Test LLM backend check
        print("\n2. Testing LLM Backend Check...")
        try:
            result = await check_llm_backend()
            print(f"   ✓ Status: {result['status']}")
            print(f"   Component: {result['component']}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Test TTS engine check
        print("\n3. Testing TTS Engine Check...")
        try:
            result = await check_tts_engine()
            print(f"   ✓ Status: {result['status']}")
            print(f"   Component: {result['component']}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Test system resources check
        print("\n4. Testing System Resources Check...")
        try:
            result = await check_system_resources()
            print(f"   ✓ Status: {result['status']}")
            print(f"   Component: {result['component']}")
            if 'details' in result:
                print(f"   Details: {result['details']}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
            
    except ImportError as e:
        print(f"Failed to import health_checks: {e}")
        return False
    
    return True

def test_metrics():
    """Test metrics collection"""
    print("\n" + "="*60)
    print("TESTING METRICS COLLECTION")
    print("="*60 + "\n")
    
    try:
        from metrics import get_metrics, get_cpu_temperature
        
        # Test CPU temperature
        print("1. Testing CPU Temperature...")
        try:
            temp = get_cpu_temperature()
            if temp == -1:
                print(f"   ℹ Temperature monitoring not available on this platform")
            else:
                print(f"   ✓ CPU Temperature: {temp}°C")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Test metrics collection
        print("\n2. Testing Metrics Collection...")
        try:
            metrics = get_metrics()
            print(f"   ✓ Metrics output ({len(metrics)} bytes):")
            print("\n" + "-"*60)
            print(metrics)
            print("-"*60)
        except Exception as e:
            print(f"   ✗ Error: {e}")
            
    except ImportError as e:
        print(f"Failed to import metrics: {e}")
        return False
    
    return True

def test_pi5_monitor():
    """Test Pi 5 specific monitoring"""
    print("\n" + "="*60)
    print("TESTING PI5 MONITORING")
    print("="*60 + "\n")
    
    try:
        from monitoring.pi5_monitor import check_cpu_temperature_status, get_resource_status
        
        # Test CPU temperature status
        print("1. Testing CPU Temperature Status Check...")
        try:
            status, message = check_cpu_temperature_status()
            print(f"   ✓ Status: {status}")
            print(f"   Message: {message}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Test resource status
        print("\n2. Testing Resource Status Check...")
        try:
            status = get_resource_status()
            print(f"   ✓ Overall Status: {status['status']}")
            print(f"   Temperature: {status['temperature']['value']}°C ({status['temperature']['status']})")
            print(f"   Memory Available: {status['memory']['available_gb']:.2f}GB ({status['memory']['status']})")
            print(f"   Swap Used: {status['swap']['used_gb']:.2f}GB ({status['swap']['status']})")
        except Exception as e:
            print(f"   ✗ Error: {e}")
            
    except ImportError as e:
        print(f"Failed to import pi5_monitor: {e}")
        return False
    
    return True

def test_exceptions():
    """Test custom exception hierarchy"""
    print("\n" + "="*60)
    print("TESTING EXCEPTION HIERARCHY")
    print("="*60 + "\n")
    
    try:
        from exceptions import (
            RealtimeVoiceChatException,
            ValidationError,
            HealthCheckError,
            MonitoringError,
            SecurityViolation
        )
        
        print("1. Testing Exception Creation...")
        
        # Test ValidationError
        try:
            err = ValidationError("Invalid input", field="data.message")
            print(f"   ✓ ValidationError created: {err}")
            print(f"     Code: {err.code}")
            print(f"     to_dict(): {err.to_dict()}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Test HealthCheckError
        try:
            err = HealthCheckError("Component failed", component="audio_processor")
            print(f"\n   ✓ HealthCheckError created: {err}")
            print(f"     Code: {err.code}")
            print(f"     to_dict(): {err.to_dict()}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        # Test MonitoringError
        try:
            err = MonitoringError("Metrics collection failed")
            print(f"\n   ✓ MonitoringError created: {err}")
            print(f"     Code: {err.code}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
            
    except ImportError as e:
        print(f"Failed to import exceptions: {e}")
        return False
    
    return True

async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("MONITORING ENDPOINTS - STANDALONE TEST")
    print("="*60)
    
    results = []
    
    # Test health checks (async)
    results.append(await test_health_checks())
    
    # Test metrics (sync)
    results.append(test_metrics())
    
    # Test Pi 5 monitoring (sync)
    results.append(test_pi5_monitor())
    
    # Test exceptions (sync)
    results.append(test_exceptions())
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(results)
    total = len(results)
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
