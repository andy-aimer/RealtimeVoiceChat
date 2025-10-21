#!/bin/bash

# Quick Pi 5 Setup Script
# Run this script directly on your Raspberry Pi 5

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
    echo "║           Quick Pi 5 Setup - RealtimeVoiceChat             ║"
    echo "║              One-command deployment script                  ║"
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

check_pi5() {
    print_step "1" "Checking Raspberry Pi 5..."
    
    if grep -q "Raspberry Pi 5" /proc/device-tree/model 2>/dev/null; then
        print_success "Running on Raspberry Pi 5"
    else
        print_warning "Not detected as Pi 5 - script will continue but may not be optimized"
    fi
    
    # Check available memory
    local mem_total=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    local mem_gb=$((mem_total / 1024 / 1024))
    print_status "Available memory: ${mem_gb}GB"
    
    if [ $mem_gb -lt 3 ]; then
        print_warning "Consider using 4GB+ Pi 5 for better performance"
    fi
}

update_system() {
    print_step "2" "Updating system packages..."
    
    sudo apt update
    sudo apt upgrade -y
    
    # Install essential packages
    sudo apt install -y git curl wget vim htop tree python3-pip python3-venv build-essential
    
    print_success "System updated successfully"
}

install_docker() {
    print_step "3" "Installing Docker..."
    
    if command -v docker &> /dev/null; then
        print_status "Docker already installed"
    else
        print_status "Installing Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        rm get-docker.sh
    fi
    
    # Install Docker Compose
    if command -v docker-compose &> /dev/null; then
        print_status "Docker Compose already installed"
    else
        sudo apt install -y docker-compose
    fi
    
    print_success "Docker installation completed"
}

optimize_pi5() {
    print_step "4" "Optimizing Pi 5 performance..."
    
    # Performance settings
    if ! grep -q "arm_freq=2400" /boot/config.txt; then
        echo "
# Pi 5 Performance Optimizations
arm_freq=2400
gpu_freq=800
over_voltage=2
temp_limit=75
gpu_mem=16
force_turbo=1
" | sudo tee -a /boot/config.txt
        print_status "Performance settings added to /boot/config.txt"
    fi
    
    # Network optimizations
    if ! grep -q "net.core.somaxconn" /etc/sysctl.conf; then
        echo "net.core.somaxconn = 1024" | sudo tee -a /etc/sysctl.conf
        echo "net.core.netdev_max_backlog = 5000" | sudo tee -a /etc/sysctl.conf
        sudo sysctl -p
    fi
    
    print_success "Pi 5 optimization completed"
}

clone_and_setup() {
    print_step "5" "Cloning RealtimeVoiceChat..."
    
    cd ~
    
    if [ -d "RealtimeVoiceChat" ]; then
        print_status "Repository already exists, updating..."
        cd RealtimeVoiceChat
        git pull
    else
        print_status "Cloning repository..."
        git clone https://github.com/andy-aimer/RealtimeVoiceChat.git
        cd RealtimeVoiceChat
    fi
    
    # Create Python virtual environment
    if [ ! -d "venv_pi5" ]; then
        python3 -m venv venv_pi5
    fi
    
    source venv_pi5/bin/activate
    pip install --upgrade pip
    
    print_success "Repository setup completed"
}

setup_ssl() {
    print_step "6" "Setting up SSL certificates..."
    
    mkdir -p /home/pi/ssl
    chmod 700 /home/pi/ssl
    
    if [ ! -f "/home/pi/ssl/server.crt" ]; then
        print_status "Generating self-signed certificate..."
        
        # Generate private key
        openssl genrsa -out /home/pi/ssl/server.key 2048
        
        # Generate certificate
        openssl req -new -x509 -key /home/pi/ssl/server.key -out /home/pi/ssl/server.crt -days 365 \
            -subj "/C=US/ST=State/L=City/O=Pi5/CN=$(hostname).local"
        
        chmod 600 /home/pi/ssl/server.key
        chmod 644 /home/pi/ssl/server.crt
        
        print_success "Self-signed certificate generated"
    else
        print_status "SSL certificates already exist"
    fi
}

create_deployment_files() {
    print_step "7" "Creating Pi 5 deployment files..."
    
    cd ~/RealtimeVoiceChat
    mkdir -p deployment/pi5
    
    # Create simplified Docker Compose for quick setup
    cat > deployment/pi5/docker-compose.quick.yml << 'EOF'
version: '3.8'

services:
  realtimevoicechat:
    image: python:3.11-slim
    container_name: realtimevoicechat_pi5_quick
    restart: unless-stopped
    working_dir: /app
    ports:
      - "8000:8000"
    volumes:
      - .:/app
      - /home/pi/ssl:/app/ssl:ro
      - /home/pi/logs:/app/logs
    environment:
      - PROD_ENVIRONMENT=pi5
      - PROD_TEST_MODE=true
      - PROD_HOST=0.0.0.0
      - PROD_PORT=8000
      - PYTHONPATH=/app
    command: >
      bash -c "
        apt-get update && 
        apt-get install -y portaudio19-dev libasound2-dev build-essential curl &&
        pip install fastapi uvicorn websockets &&
        python -m uvicorn server:app --host 0.0.0.0 --port 8000
      "
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  monitoring:
    image: python:3.11-slim
    container_name: monitoring_pi5_quick
    restart: unless-stopped
    working_dir: /app
    ports:
      - "8001:8001"
    volumes:
      - .:/app:ro
    environment:
      - MONITORING_PORT=8001
      - PYTHONPATH=/app
    command: >
      bash -c "
        pip install psutil &&
        python monitoring/simple_performance_test.py
      "
EOF

    print_success "Deployment files created"
}

deploy_application() {
    print_step "8" "Deploying application..."
    
    cd ~/RealtimeVoiceChat/deployment/pi5
    
    # Create logs directory
    mkdir -p /home/pi/logs
    
    # Start services
    print_status "Starting Docker services (this may take a few minutes)..."
    newgrp docker << 'DEPLOY_COMMANDS'
docker-compose -f docker-compose.quick.yml down 2>/dev/null || true
docker-compose -f docker-compose.quick.yml up -d
DEPLOY_COMMANDS

    # Wait for services
    print_status "Waiting for services to start..."
    sleep 30
    
    # Check health
    local retries=10
    local count=0
    
    while [ $count -lt $retries ]; do
        if curl -f http://localhost:8000/health > /dev/null 2>&1; then
            print_success "Application is running!"
            break
        fi
        
        print_status "Waiting for application... ($((count + 1))/$retries)"
        sleep 10
        count=$((count + 1))
    done
    
    if [ $count -eq $retries ]; then
        print_warning "Application may still be starting. Check with: docker logs realtimevoicechat_pi5_quick"
    fi
}

create_management_commands() {
    print_step "9" "Creating management commands..."
    
    # Start script
    cat > ~/start_realtimevoicechat.sh << 'EOF'
#!/bin/bash
cd ~/RealtimeVoiceChat/deployment/pi5
docker-compose -f docker-compose.quick.yml up -d
echo "RealtimeVoiceChat started!"
echo "Access at: http://$(hostname -I | awk '{print $1}'):8000"
echo "Monitoring: http://$(hostname -I | awk '{print $1}'):8001"
EOF

    # Stop script
    cat > ~/stop_realtimevoicechat.sh << 'EOF'
#!/bin/bash
cd ~/RealtimeVoiceChat/deployment/pi5
docker-compose -f docker-compose.quick.yml down
echo "RealtimeVoiceChat stopped."
EOF

    # Status script
    cat > ~/status_realtimevoicechat.sh << 'EOF'
#!/bin/bash
echo "=== RealtimeVoiceChat Status ==="
cd ~/RealtimeVoiceChat/deployment/pi5
docker-compose -f docker-compose.quick.yml ps
echo ""
echo "=== Quick Health Check ==="
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Application: Running"
else
    echo "❌ Application: Not responding"
fi

if curl -f http://localhost:8001 > /dev/null 2>&1; then
    echo "✅ Monitoring: Running"
else
    echo "❌ Monitoring: Not responding"
fi

echo ""
echo "=== System Info ==="
echo "Temperature: $(vcgencmd measure_temp 2>/dev/null || echo 'N/A')"
echo "Memory: $(free -h | grep Mem | awk '{print $3"/"$2}')"
echo "Uptime: $(uptime -p)"
EOF

    chmod +x ~/start_realtimevoicechat.sh ~/stop_realtimevoicechat.sh ~/status_realtimevoicechat.sh
    
    print_success "Management commands created in home directory"
}

print_completion() {
    local pi_ip=$(hostname -I | awk '{print $1}')
    
    echo ""
    echo -e "${GREEN}${BOLD}🎉 RealtimeVoiceChat Pi 5 Quick Setup Completed!${NC}"
    echo ""
    echo -e "${BLUE}📱 Access your application:${NC}"
    echo "   • Main App:    http://$pi_ip:8000"
    echo "   • Monitoring:  http://$pi_ip:8001"
    echo ""
    echo -e "${BLUE}🛠️  Management commands:${NC}"
    echo "   • Start:   ~/start_realtimevoicechat.sh"
    echo "   • Stop:    ~/stop_realtimevoicechat.sh"
    echo "   • Status:  ~/status_realtimevoicechat.sh"
    echo ""
    echo -e "${BLUE}🔧 Next steps:${NC}"
    echo "   1. Test: curl http://$pi_ip:8000/health"
    echo "   2. Open browser: http://$pi_ip:8000"
    echo "   3. Check monitoring: http://$pi_ip:8001"
    echo "   4. For full production setup, see: deployment/raspberry_pi5_deployment.md"
    echo ""
    echo -e "${YELLOW}⚠️  Note:${NC} This is a quick setup for testing. For production:"
    echo "   • Run the full deployment script: deployment/pi5/deploy_pi5.sh"
    echo "   • Set up proper SSL certificates"
    echo "   • Configure firewall rules"
    echo ""
    echo -e "${GREEN}🍓 Enjoy your Pi 5 RealtimeVoiceChat!${NC}"
}

main() {
    print_header
    
    check_pi5
    update_system
    install_docker
    optimize_pi5
    clone_and_setup
    setup_ssl
    create_deployment_files
    deploy_application
    create_management_commands
    print_completion
    
    echo ""
    print_success "Setup completed! Restart recommended for all optimizations to take effect."
    echo -e "${BLUE}Restart command: sudo reboot${NC}"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please run this script as a regular user (not root)"
    exit 1
fi

# Run main function
main "$@"