# 🍎 macOS Installation Guide - RealtimeVoiceChat

Complete installation and deployment instructions specifically for macOS systems.

## 📋 Prerequisites

### System Requirements

- **macOS**: 10.15 Catalina or later (macOS 13+ recommended)
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 5GB free space
- **Internet**: Required for dependencies and real-time features

### Required Software

- **Xcode Command Line Tools** (for compilation)
- **Homebrew** (package manager)
- **Python 3.11+** (via Homebrew)
- **Git** (usually pre-installed)

## 🚀 Quick Start (5 minutes)

### One-Command Installation

```bash
curl -sSL https://raw.githubusercontent.com/andy-aimer/RealtimeVoiceChat/main/deployment/macos/quick_install_macos.sh | bash
```

### Manual Installation

#### Step 1: Install Xcode Command Line Tools

```bash
# Install Xcode Command Line Tools
xcode-select --install

# Verify installation
xcode-select -p
# Should output: /Applications/Xcode.app/Contents/Developer
```

#### Step 2: Install Homebrew (if not already installed)

```bash
# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Add Homebrew to PATH (for Apple Silicon Macs)
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"

# Verify installation
brew --version
```

#### Step 3: Install Python and Dependencies

```bash
# Install Python 3.11 via Homebrew
brew install python@3.11

# Install audio dependencies
brew install portaudio ffmpeg

# Install system dependencies
brew install wget curl git
```

#### Step 4: Clone and Setup Project

```bash
# Clone the repository
git clone https://github.com/andy-aimer/RealtimeVoiceChat.git
cd RealtimeVoiceChat

# Create virtual environment
python3.11 -m venv venv_macos
source venv_macos/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install Python dependencies
pip install -r requirements.txt
```

#### Step 5: Configure for macOS

```bash
# Create macOS-specific configuration
mkdir -p deployment/macos
```

## 🔧 macOS-Specific Configuration

### Audio Configuration

```bash
# macOS uses different audio drivers
# Check audio devices
python -c "
import sounddevice as sd
print('Available audio devices:')
print(sd.query_devices())
"

# Set default audio device (if needed)
export AUDIO_DEVICE_INDEX=0  # Adjust as needed
```

### Security Settings

```bash
# Allow microphone access for Terminal/iTerm
# System Preferences > Security & Privacy > Privacy > Microphone
# Add Terminal.app or iTerm.app

# For camera access (if using video features)
# System Preferences > Security & Privacy > Privacy > Camera
# Add your terminal application
```

### SSL Certificate Setup

```bash
# Create SSL directory
mkdir -p ~/ssl

# Generate self-signed certificate for development
openssl req -x509 -newkey rsa:2048 -keyout ~/ssl/server.key -out ~/ssl/server.crt -days 365 -nodes \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Set proper permissions
chmod 600 ~/ssl/server.key
chmod 644 ~/ssl/server.crt
```

## 🎯 Deployment Options

### Option 1: Development Server (Recommended)

```bash
cd RealtimeVoiceChat
source venv_macos/bin/activate

# Start development server
python src/server.py

# Access application
open http://localhost:8000
```

### Option 2: Production Server

```bash
# Use production configuration
PROD_ENVIRONMENT=macos python production/production_server.py

# Access with SSL
open https://localhost:8443
```

### Option 3: Docker Deployment (requires Docker Desktop)

```bash
# Install Docker Desktop for Mac
brew install --cask docker

# Start Docker Desktop and wait for it to be ready

# Build and run with Docker
docker-compose -f deployment/macos/docker-compose.macos.yml up -d

# Access application
open http://localhost:8000
```

## 📊 Monitoring Setup

### Start Monitoring Dashboard

```bash
# Start monitoring in background
python monitoring/test_monitor.py &

# Access monitoring dashboard
open http://localhost:8001
```

### System Monitoring (macOS-specific)

```bash
# Monitor CPU temperature (requires additional tools)
brew install osx-cpu-temp
osx-cpu-temp

# Monitor system resources
brew install htop
htop

# Monitor memory usage
vm_stat

# Monitor disk usage
df -h
```

## 🛡️ Security Configuration

### Firewall Setup

```bash
# Enable macOS firewall
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --setglobalstate on

# Allow specific ports (optional for local development)
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/bin/python3.11
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp /usr/bin/python3.11
```

### Privacy Settings

```bash
# Check microphone permissions
tccutil reset Microphone

# For production, consider code signing
# codesign --force --sign - ./venv_macos/bin/python
```

## 📱 Application Access

### Local Development

- **Main Application**: http://localhost:8000
- **Monitoring Dashboard**: http://localhost:8001
- **Health Check**: http://localhost:8000/health

### Production with SSL

- **Main Application**: https://localhost:8443
- **Monitoring Dashboard**: https://localhost:8001
- **Health Check**: https://localhost:8443/health

### Network Access (from other devices)

```bash
# Find your Mac's IP address
ifconfig | grep "inet " | grep -v 127.0.0.1

# Access from other devices on same network
# http://YOUR_MAC_IP:8000
```

## 🧪 Testing Installation

### Quick Health Check

```bash
cd RealtimeVoiceChat
source venv_macos/bin/activate

# Test basic functionality
python -c "
import src.server
import requests
print('✅ Dependencies loaded successfully')
"

# Test audio system
python -c "
import sounddevice as sd
print('✅ Audio system working')
print(f'Default device: {sd.default.device}')
"

# Test WebSocket connection
python -c "
import websockets
import asyncio
print('✅ WebSocket support available')
"
```

### Run Test Suite

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific macOS tests
python -m pytest tests/unit/test_macos_compatibility.py -v
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Audio Device Not Found

```bash
# List available audio devices
python -c "import sounddevice as sd; print(sd.query_devices())"

# Set specific audio device
export PORTAUDIO_DEVICE_INDEX=1  # Adjust number as needed
```

#### 2. SSL Certificate Issues

```bash
# Regenerate certificates
rm ~/ssl/server.*
openssl req -x509 -newkey rsa:2048 -keyout ~/ssl/server.key -out ~/ssl/server.crt -days 365 -nodes \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
```

#### 3. Port Already in Use

```bash
# Find process using port 8000
lsof -ti:8000

# Kill process if needed
kill -9 $(lsof -ti:8000)
```

#### 4. Permission Denied Errors

```bash
# Fix virtual environment permissions
chmod -R 755 venv_macos/

# Fix SSL certificate permissions
chmod 600 ~/ssl/server.key
chmod 644 ~/ssl/server.crt
```

#### 5. Python Module Import Errors

```bash
# Ensure virtual environment is activated
source venv_macos/bin/activate

# Reinstall requirements
pip install --force-reinstall -r requirements.txt

# Check Python path
python -c "import sys; print(sys.path)"
```

### Performance Optimization

#### CPU and Memory

```bash
# Monitor CPU usage
top -pid $(pgrep -f "python.*server")

# Monitor memory usage
ps -o pid,vsz,rss,comm -p $(pgrep -f "python.*server")

# Optimize for macOS
export OMP_NUM_THREADS=4  # Adjust based on your Mac's cores
export VECLIB_MAXIMUM_THREADS=4
```

#### Network Optimization

```bash
# Increase connection limits (if needed)
sudo sysctl -w kern.ipc.somaxconn=1024
sudo sysctl -w net.inet.tcp.msl=1000
```

## 🚀 Production Deployment on macOS

### Using systemd Alternative (launchd)

```bash
# Create LaunchAgent plist
cat > ~/Library/LaunchAgents/com.realtimevoicechat.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.realtimevoicechat</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/$(whoami)/RealtimeVoiceChat/venv_macos/bin/python</string>
        <string>/Users/$(whoami)/RealtimeVoiceChat/src/server.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/$(whoami)/RealtimeVoiceChat</string>
    <key>KeepAlive</key>
    <true/>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/$(whoami)/Library/Logs/realtimevoicechat.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/$(whoami)/Library/Logs/realtimevoicechat.error.log</string>
</dict>
</plist>
EOF

# Load the service
launchctl load ~/Library/LaunchAgents/com.realtimevoicechat.plist

# Start the service
launchctl start com.realtimevoicechat

# Check status
launchctl list | grep realtimevoicechat
```

### SSL with Real Domain (Optional)

```bash
# For production with real domain, use Let's Encrypt
brew install certbot

# Generate certificate (requires domain pointing to your Mac)
sudo certbot certonly --standalone -d yourdomain.com

# Copy certificates
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ~/ssl/server.crt
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ~/ssl/server.key
```

## 📚 Additional Resources

### macOS-Specific Features

- **Spotlight Integration**: Application is searchable in Spotlight
- **Activity Monitor**: Monitor resource usage
- **Console.app**: View detailed logs
- **Network Utility**: Test network connectivity

### Development Tools

```bash
# Install useful development tools
brew install --cask visual-studio-code
brew install --cask iterm2
brew install --cask docker
brew install jq wget curl
```

### Environment Management

```bash
# Add to ~/.zprofile for automatic environment setup
echo 'export PATH="/opt/homebrew/bin:$PATH"' >> ~/.zprofile
echo 'alias rtvc="cd ~/RealtimeVoiceChat && source venv_macos/bin/activate"' >> ~/.zprofile
echo 'alias start-rtvc="cd ~/RealtimeVoiceChat && source venv_macos/bin/activate && python src/server.py"' >> ~/.zprofile

# Reload shell configuration
source ~/.zprofile
```

## 🎉 Success!

Your RealtimeVoiceChat is now ready to run on macOS with:

✅ **Native macOS Support**: Optimized for Apple hardware  
✅ **Audio Integration**: Works with built-in mic and speakers  
✅ **Security Compliance**: Follows macOS security guidelines  
✅ **Performance Optimization**: Tuned for macOS system calls  
✅ **Easy Management**: Simple start/stop commands  
✅ **Development Ready**: Perfect for testing and development

### Quick Start Commands

```bash
# Start application
rtvc && python src/server.py

# Access application
open http://localhost:8000

# View monitoring
open http://localhost:8001
```

**Enjoy your macOS RealtimeVoiceChat deployment!** 🍎🎉
