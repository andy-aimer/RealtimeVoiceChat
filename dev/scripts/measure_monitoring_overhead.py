#!/usr/bin/env python3
"""
Measure monitoring overhead by comparing CPU usage before and after enabling monitoring.

This script simulates the Pi 5 overhead measurement by:
1. Measuring baseline CPU with server running but no monitoring calls
2. Measuring CPU with active monitoring endpoint requests
3. Calculating the overhead percentage
"""
import time
import psutil
import requests
import statistics

def measure_cpu_baseline(duration=5):
    """Measure baseline CPU usage without monitoring requests."""
    print(f"📊 Measuring baseline CPU for {duration} seconds...")
    samples = []
    start = time.time()
    while time.time() - start < duration:
        samples.append(psutil.cpu_percent(interval=0.1))
    
    avg_cpu = statistics.mean(samples)
    print(f"  Baseline CPU: {avg_cpu:.2f}%")
    return avg_cpu

def measure_cpu_with_monitoring(duration=5, request_interval=1.0):
    """Measure CPU usage with active monitoring requests."""
    print(f"📊 Measuring CPU with monitoring requests for {duration} seconds...")
    samples = []
    start = time.time()
    last_request = start
    
    while time.time() - start < duration:
        current_time = time.time()
        
        # Make monitoring request at specified interval
        if current_time - last_request >= request_interval:
            try:
                requests.get("http://localhost:8000/health", timeout=1)
                requests.get("http://localhost:8000/metrics", timeout=1)
                last_request = current_time
            except:
                pass  # Ignore request failures
        
        samples.append(psutil.cpu_percent(interval=0.1))
    
    avg_cpu = statistics.mean(samples)
    print(f"  Monitoring CPU: {avg_cpu:.2f}%")
    return avg_cpu

def main():
    print("🔍 Monitoring Overhead Measurement")
    print("=" * 50)
    print()
    
    # Check if server is running
    try:
        response = requests.get("http://localhost:8000/health", timeout=2)
        print(f"✅ Server is running (status: {response.status_code})")
    except:
        print("❌ Server is not running. Please start the server first.")
        print("   Run: cd code && uvicorn server:app")
        return
    
    print()
    
    # Measure baseline
    baseline_cpu = measure_cpu_baseline(duration=10)
    time.sleep(2)  # Brief pause between measurements
    
    # Measure with monitoring (1Hz requests as per spec)
    monitoring_cpu = measure_cpu_with_monitoring(duration=10, request_interval=1.0)
    
    # Calculate overhead
    overhead = monitoring_cpu - baseline_cpu
    overhead_percent = (overhead / baseline_cpu * 100) if baseline_cpu > 0 else 0
    
    print()
    print("📊 Results")
    print("=" * 50)
    print(f"Baseline CPU:    {baseline_cpu:.2f}%")
    print(f"Monitoring CPU:  {monitoring_cpu:.2f}%")
    print(f"Overhead:        {overhead:.2f}% (absolute)")
    print(f"Overhead:        {overhead_percent:.1f}% (relative)")
    print()
    
    # Check against requirement (<2% absolute)
    if overhead < 2.0:
        print(f"✅ PASS: Monitoring overhead ({overhead:.2f}%) is below 2% target")
    else:
        print(f"❌ FAIL: Monitoring overhead ({overhead:.2f}%) exceeds 2% target")
    
    print()
    print("Note: This is a simulation on current hardware.")
    print("Actual Pi 5 hardware may show different results.")

if __name__ == "__main__":
    main()
