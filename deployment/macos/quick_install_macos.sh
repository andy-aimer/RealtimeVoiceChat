#!/bin/bash

# macOS Quick Installation Script for RealtimeVoiceChat
# Automated setup for macOS development and production

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m'

print_header() {
    echo -e "${BLUE}${BOLD}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║            macOS Quick Install - RealtimeVoiceChat         ║"
    echo "║              One-command setup for macOS                    ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "${BLUE}${BOLD}[STEP $1]${NC} $2"
}

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_macos() {
    print_step "1" "Checking macOS compatibility..."
    
    if [[ "$OSTYPE" != "darwin"* ]]; then
        print_error "This script is designed for macOS only"
        exit 1
    fi
    
    # Check macOS version
    local macos_version=$(sw_vers -productVersion)
    local major_version=$(echo $macos_version | cut -d. -f1)
    
    if [ "$major_version" -lt 10 ]; then
        print_error "macOS 10.15 or later is required. Current version: $macos_version"
        exit 1
    fi
    
    print_success "Running on macOS $macos_version"
    
    # Check architecture
    local arch=$(uname -m)
    if [ "$arch" = "arm64" ]; then
        print_status "Apple Silicon (M1/M2/M3) detected"
        HOMEBREW_PREFIX="/opt/homebrew"
    else
        print_status "Intel Mac detected"
        HOMEBREW_PREFIX="/usr/local"
    fi
}

install_xcode_tools() {
    print_step "2" "Installing Xcode Command Line Tools..."
    
    if xcode-select -p &>/dev/null; then
        print_status "Xcode Command Line Tools already installed"
    else
        print_status "Installing Xcode Command Line Tools..."
        xcode-select --install
        
        # Wait for installation to complete
        print_status "Please complete the Xcode installation dialog, then press Enter to continue..."
        read -p "Press Enter when installation is complete..."
        
        if xcode-select -p &>/dev/null; then
            print_success "Xcode Command Line Tools installed successfully"
        else
            print_error "Xcode Command Line Tools installation failed"
            exit 1
        fi
    fi
}

install_homebrew() {
    print_step "3" "Installing Homebrew..."
    
    if command -v brew &>/dev/null; then
        print_status "Homebrew already installed"
        brew update
    else
        print_status "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        # Add Homebrew to PATH
        echo "eval \"($HOMEBREW_PREFIX/bin/brew shellenv)\"" >> ~/.zprofile
        eval "$($HOMEBREW_PREFIX/bin/brew shellenv)"
        
        if command -v brew &>/dev/null; then
            print_success "Homebrew installed successfully"
        else
            print_error "Homebrew installation failed"
            exit 1
        fi
    fi
}

install_dependencies() {
    print_step "4" "Installing system dependencies..."
    
    print_status "Installing Python 3.11..."
    brew install python@3.11
    
    print_status "Installing audio dependencies..."
    brew install portaudio ffmpeg
    
    print_status "Installing additional tools..."
    brew install wget curl git jq
    
    print_success "System dependencies installed"
}

setup_project() {
    print_step "5" "Setting up RealtimeVoiceChat project..."
    
    cd ~
    
    if [ -d "RealtimeVoiceChat" ]; then
        print_status "Project directory already exists, updating..."
        cd RealtimeVoiceChat
        git pull
    else
        print_status "Cloning RealtimeVoiceChat repository..."
        git clone https://github.com/andy-aimer/RealtimeVoiceChat.git
        cd RealtimeVoiceChat
    fi
    
    PROJECT_DIR=$(pwd)
    print_success "Project setup in: $PROJECT_DIR"
}

create_virtual_environment() {
    print_step "6" "Creating Python virtual environment..."
    
    cd "$PROJECT_DIR"
    
    if [ -d "venv_macos" ]; then
        print_status "Virtual environment already exists"
    else
        python3.11 -m venv venv_macos
        print_success "Virtual environment created"
    fi
    
    source venv_macos/bin/activate
    pip install --upgrade pip
    
    print_status "Installing Python dependencies..."
    pip install -r requirements.txt
    
    print_success "Python environment setup complete"
}

setup_ssl_certificates() {
    print_step "7" "Setting up SSL certificates..."
    
    SSL_DIR="$HOME/ssl"
    mkdir -p "$SSL_DIR"
    
    if [ ! -f "$SSL_DIR/server.crt" ] || [ ! -f "$SSL_DIR/server.key" ]; then
        print_status "Generating self-signed SSL certificate..."
        
        openssl req -x509 -newkey rsa:2048 -keyout "$SSL_DIR/server.key" -out "$SSL_DIR/server.crt" -days 365 -nodes \
            -subj "/C=US/ST=California/L=Cupertino/O=RealtimeVoiceChat/CN=localhost"
        
        chmod 600 "$SSL_DIR/server.key"
        chmod 644 "$SSL_DIR/server.crt"
        
        print_success "SSL certificates generated in $SSL_DIR"
    else
        print_status "SSL certificates already exist"
    fi
}

create_macos_config() {
    print_step "8" "Creating macOS-specific configuration..."
    
    mkdir -p "$PROJECT_DIR/deployment/macos"
    
    # Create macOS configuration file
    cat > "$PROJECT_DIR/deployment/macos/macos_config.py" << 'EOF'
"""
macOS-specific configuration for RealtimeVoiceChat
Optimized for macOS development and production
"""

import os
import platform
from pathlib import Path

class MacOSConfig:
    """Configuration optimized for macOS."""
    
    def __init__(self):
        self.setup_macos_defaults()
    
    def setup_macos_defaults(self):
        """Set macOS-specific defaults."""
        # macOS paths
        home_dir = Path.home()
        
        # SSL configuration
        os.environ.setdefault('PROD_SSL_CERT_PATH', str(home_dir / 'ssl' / 'server.crt'))
        os.environ.setdefault('PROD_SSL_KEY_PATH', str(home_dir / 'ssl' / 'server.key'))
        
        # Log directory
        log_dir = home_dir / 'Library' / 'Logs' / 'RealtimeVoiceChat'
        log_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault('PROD_LOG_DIR', str(log_dir))
        
        # macOS-specific settings
        os.environ.setdefault('PROD_HOST', '0.0.0.0')
        os.environ.setdefault('PROD_PORT', '8000')
        os.environ.setdefault('PROD_SSL_PORT', '8443')
        
        # Performance settings for macOS
        import psutil
        cpu_count = psutil.cpu_count()
        os.environ.setdefault('PROD_MAX_WORKERS', str(min(cpu_count, 8)))
        os.environ.setdefault('PROD_MAX_CONNECTIONS', '200')
        
        # Audio settings
        os.environ.setdefault('AUDIO_SAMPLE_RATE', '44100')  # macOS prefers 44.1kHz
        os.environ.setdefault('AUDIO_BUFFER_SIZE', '1024')
        
        # macOS security
        os.environ.setdefault('PROD_RATE_LIMIT_PER_MINUTE', '300')
        
    def get_system_info(self):
        """Get macOS system information."""
        return {
            'platform': platform.platform(),
            'processor': platform.processor(),
            'architecture': platform.architecture(),
            'machine': platform.machine(),
            'python_version': platform.python_version(),
            'macos_version': platform.mac_ver()[0]
        }

# Create global instance
macos_config = MacOSConfig()
EOF

    print_success "macOS configuration created"
}

create_management_scripts() {
    print_step "9" "Creating management scripts..."
    
    # Start script
    cat > "$PROJECT_DIR/start_macos.sh" << EOF
#!/bin/bash
cd "$PROJECT_DIR"
source venv_macos/bin/activate
export PROD_ENVIRONMENT=macos
python src/server.py
EOF

    # Start with SSL script
    cat > "$PROJECT_DIR/start_macos_ssl.sh" << EOF
#!/bin/bash
cd "$PROJECT_DIR"
source venv_macos/bin/activate
export PROD_ENVIRONMENT=macos
export PROD_USE_SSL=true
python production/production_server.py
EOF

    # Monitoring script
    cat > "$PROJECT_DIR/start_monitoring_macos.sh" << EOF
#!/bin/bash
cd "$PROJECT_DIR"
source venv_macos/bin/activate
python monitoring/test_monitor.py &
echo "Monitoring started on http://localhost:8001"
EOF

    # Status script
    cat > "$PROJECT_DIR/status_macos.sh" << 'EOF'
#!/bin/bash
echo "=== RealtimeVoiceChat macOS Status ==="
echo "Project Directory: $PWD"
echo ""

# Check if virtual environment exists
if [ -d "venv_macos" ]; then
    echo "✅ Virtual Environment: Ready"
else
    echo "❌ Virtual Environment: Missing"
fi

# Check if SSL certificates exist
if [ -f "$HOME/ssl/server.crt" ] && [ -f "$HOME/ssl/server.key" ]; then
    echo "✅ SSL Certificates: Ready"
else
    echo "❌ SSL Certificates: Missing"
fi

# Check if server is running
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "✅ Server (HTTP): Running on port 8000"
else
    echo "⚪ Server (HTTP): Not running"
fi

if lsof -ti:8443 > /dev/null 2>&1; then
    echo "✅ Server (HTTPS): Running on port 8443"
else
    echo "⚪ Server (HTTPS): Not running"
fi

# Check monitoring
if lsof -ti:8001 > /dev/null 2>&1; then
    echo "✅ Monitoring: Running on port 8001"
else
    echo "⚪ Monitoring: Not running"
fi

echo ""
echo "=== System Information ==="
echo "macOS Version: $(sw_vers -productVersion)"
echo "Architecture: $(uname -m)"
echo "Python Version: $(python3.11 --version 2>/dev/null || echo 'Not found')"
echo "Available Memory: $(vm_stat | head -1)"
EOF

    # Make scripts executable
    chmod +x "$PROJECT_DIR"/*.sh
    
    print_success "Management scripts created"
}

setup_aliases() {
    print_step "10" "Setting up convenient aliases..."
    
    # Add aliases to shell profile
    SHELL_PROFILE=""
    if [ -f ~/.zshrc ]; then
        SHELL_PROFILE=~/.zshrc
    elif [ -f ~/.bash_profile ]; then
        SHELL_PROFILE=~/.bash_profile
    else
        SHELL_PROFILE=~/.zprofile
        touch $SHELL_PROFILE
    fi
    
    # Check if aliases already exist
    if ! grep -q "RealtimeVoiceChat aliases" "$SHELL_PROFILE"; then
        cat >> "$SHELL_PROFILE" << EOF

# RealtimeVoiceChat aliases
alias rtvc="cd $PROJECT_DIR && source venv_macos/bin/activate"
alias start-rtvc="cd $PROJECT_DIR && ./start_macos.sh"
alias start-rtvc-ssl="cd $PROJECT_DIR && ./start_macos_ssl.sh"
alias start-rtvc-monitor="cd $PROJECT_DIR && ./start_monitoring_macos.sh"
alias status-rtvc="cd $PROJECT_DIR && ./status_macos.sh"
alias logs-rtvc="tail -f ~/Library/Logs/RealtimeVoiceChat/*.log"
EOF
        print_success "Aliases added to $SHELL_PROFILE"
    else
        print_status "Aliases already exist in $SHELL_PROFILE"
    fi
}

test_installation() {
    print_step "11" "Testing installation..."
    
    cd "$PROJECT_DIR"
    source venv_macos/bin/activate
    
    # Test Python imports
    print_status "Testing Python dependencies..."
    python -c "
import fastapi
import uvicorn
import websockets
import sounddevice
print('✅ All Python dependencies imported successfully')
"
    
    # Test audio system
    print_status "Testing audio system..."
    python -c "
import sounddevice as sd
devices = sd.query_devices()
print(f'✅ Audio system working - {len(devices)} devices found')
print(f'Default device: {sd.default.device}')
"
    
    # Test SSL certificates
    print_status "Testing SSL certificates..."
    if [ -f "$HOME/ssl/server.crt" ] && [ -f "$HOME/ssl/server.key" ]; then
        openssl x509 -in "$HOME/ssl/server.crt" -text -noout | grep -A 2 "Subject:"
        print_success "SSL certificates are valid"
    else
        print_error "SSL certificates not found"
    fi
    
    print_success "Installation test completed"
}

print_completion() {
    local mac_ip=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}')
    
    echo ""
    echo -e "${GREEN}${BOLD}🎉 RealtimeVoiceChat macOS Installation Complete!${NC}"
    echo ""
    echo -e "${BLUE}📱 Quick Start Commands:${NC}"
    echo "   • Activate env:    rtvc"
    echo "   • Start app:       start-rtvc"
    echo "   • Start with SSL:  start-rtvc-ssl"
    echo "   • Start monitor:   start-rtvc-monitor"
    echo "   • Check status:    status-rtvc"
    echo ""
    echo -e "${BLUE}🌐 Access URLs:${NC}"
    echo "   • Local HTTP:      http://localhost:8000"
    echo "   • Local HTTPS:     https://localhost:8443"
    echo "   • Network access:  http://$mac_ip:8000"
    echo "   • Monitoring:      http://localhost:8001"
    echo ""
    echo -e "${BLUE}📁 Project Location:${NC}"
    echo "   • Project:         $PROJECT_DIR"
    echo "   • SSL certs:       $HOME/ssl/"
    echo "   • Logs:            $HOME/Library/Logs/RealtimeVoiceChat/"
    echo ""
    echo -e "${BLUE}🚀 Next Steps:${NC}"
    echo "   1. Restart your terminal or run: source $SHELL_PROFILE"
    echo "   2. Test: start-rtvc"
    echo "   3. Open: http://localhost:8000"
    echo "   4. Check monitor: http://localhost:8001"
    echo ""
    echo -e "${GREEN}Enjoy your macOS RealtimeVoiceChat! 🍎🎉${NC}"
}

main() {
    print_header
    
    check_macos
    install_xcode_tools
    install_homebrew
    install_dependencies
    setup_project
    create_virtual_environment
    setup_ssl_certificates
    create_macos_config
    create_management_scripts
    setup_aliases
    test_installation
    print_completion
    
    print_success "macOS installation completed successfully!"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please run this script as a regular user (not root)"
    exit 1
fi

# Run main function
main "$@"