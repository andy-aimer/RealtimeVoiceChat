#!/usr/bin/env python3
"""
macOS Installation Verification Script
Tests that all components work correctly on macOS
"""

import sys
import platform
import subprocess
import os
from pathlib import Path

def print_status(message, status="INFO"):
    colors = {
        "INFO": "\033[34m",    # Blue
        "SUCCESS": "\033[32m", # Green
        "WARNING": "\033[33m", # Yellow
        "ERROR": "\033[31m",   # Red
    }
    reset = "\033[0m"
    print(f"{colors.get(status, '')}{status}: {message}{reset}")

def check_macos():
    """Verify we're running on macOS."""
    if platform.system() != "Darwin":
        print_status("This verification script is designed for macOS only", "ERROR")
        return False
    
    version = platform.mac_ver()[0]
    print_status(f"Running on macOS {version}", "SUCCESS")
    return True

def check_python():
    """Check Python version."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print_status(f"Python {version.major}.{version.minor}.{version.micro} ✓", "SUCCESS")
        return True
    else:
        print_status(f"Python {version.major}.{version.minor}.{version.micro} - Recommend 3.11+", "WARNING")
        return True

def check_homebrew():
    """Check if Homebrew is installed."""
    try:
        result = subprocess.run(['brew', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip().split('\n')[0]
            print_status(f"Homebrew installed: {version}", "SUCCESS")
            return True
    except FileNotFoundError:
        print_status("Homebrew not found - install with quick setup script", "WARNING")
        return False

def check_dependencies():
    """Check key Python dependencies."""
    dependencies = [
        'fastapi',
        'uvicorn',
        'websockets',
        'sounddevice',
        'numpy',
        'torch'
    ]
    
    missing = []
    for dep in dependencies:
        try:
            __import__(dep)
            print_status(f"✓ {dep}", "SUCCESS")
        except ImportError:
            missing.append(dep)
            print_status(f"✗ {dep}", "ERROR")
    
    if missing:
        print_status(f"Missing dependencies: {', '.join(missing)}", "ERROR")
        return False
    return True

def check_audio():
    """Test audio system."""
    try:
        import sounddevice as sd
        devices = sd.query_devices()
        default_device = sd.default.device
        
        print_status(f"Audio system working - {len(devices)} devices found", "SUCCESS")
        print_status(f"Default device: {default_device}", "INFO")
        
        # Check for input devices
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        if input_devices:
            print_status(f"Input devices available: {len(input_devices)}", "SUCCESS")
        else:
            print_status("No input devices found", "WARNING")
        
        return True
    except Exception as e:
        print_status(f"Audio system error: {e}", "ERROR")
        return False

def check_ssl_certs():
    """Check SSL certificate setup."""
    ssl_dir = Path.home() / 'ssl'
    cert_file = ssl_dir / 'server.crt'
    key_file = ssl_dir / 'server.key'
    
    if cert_file.exists() and key_file.exists():
        print_status("SSL certificates found", "SUCCESS")
        
        # Check certificate validity
        try:
            result = subprocess.run([
                'openssl', 'x509', '-in', str(cert_file), '-noout', '-checkend', '86400'
            ], capture_output=True)
            
            if result.returncode == 0:
                print_status("SSL certificates are valid", "SUCCESS")
            else:
                print_status("SSL certificates are expiring or invalid", "WARNING")
        except Exception as e:
            print_status(f"Could not verify SSL certificates: {e}", "WARNING")
        
        return True
    else:
        print_status("SSL certificates not found in ~/ssl/", "WARNING")
        print_status("Run: deployment/macos/quick_install_macos.sh to set up", "INFO")
        return False

def check_project_structure():
    """Verify project files exist."""
    required_files = [
        'src/server.py',
        'deployment/macos/quick_install_macos.sh',
        'deployment/macos_installation.md',
        'requirements.txt'
    ]
    
    missing = []
    for file_path in required_files:
        if Path(file_path).exists():
            print_status(f"✓ {file_path}", "SUCCESS")
        else:
            missing.append(file_path)
            print_status(f"✗ {file_path}", "ERROR")
    
    if missing:
        print_status("Some project files are missing", "WARNING")
        return False
    return True

def test_server_import():
    """Test that the server can be imported."""
    try:
        sys.path.append(str(Path.cwd() / 'src'))
        import server
        print_status("Server module imports successfully", "SUCCESS")
        return True
    except Exception as e:
        print_status(f"Server import failed: {e}", "ERROR")
        return False

def check_network_ports():
    """Check if required ports are available."""
    import socket
    
    ports = [8000, 8001, 8443]
    for port in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        
        if result != 0:
            print_status(f"Port {port} available", "SUCCESS")
        else:
            print_status(f"Port {port} in use", "WARNING")

def main():
    print("🍎 macOS RealtimeVoiceChat Verification")
    print("=" * 40)
    
    checks = [
        ("macOS Platform", check_macos),
        ("Python Version", check_python),
        ("Homebrew", check_homebrew),
        ("Project Structure", check_project_structure),
        ("Python Dependencies", check_dependencies),
        ("Audio System", check_audio),
        ("SSL Certificates", check_ssl_certs),
        ("Server Import", test_server_import),
        ("Network Ports", check_network_ports),
    ]
    
    results = []
    for name, check_func in checks:
        print(f"\n{name}:")
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print_status(f"Check failed with error: {e}", "ERROR")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 40)
    print("📊 Verification Summary:")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print_status("🎉 All checks passed! Your macOS setup is ready.", "SUCCESS")
        print("\nNext steps:")
        print("1. Start the server: python src/server.py")
        print("2. Open browser: http://localhost:8000")
        print("3. Start monitoring: python monitoring/test_monitor.py")
    else:
        print_status("⚠️ Some checks failed. See details above.", "WARNING")
        print("\nTo fix issues:")
        print("1. Run the quick setup: deployment/macos/quick_install_macos.sh")
        print("2. Install missing dependencies: pip install -r requirements.txt")
        print("3. Check the full guide: deployment/macos_installation.md")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)