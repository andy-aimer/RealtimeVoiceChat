# 🍓 Raspberry Pi 5 Deployment Guide

Complete step-by-step instructions for deploying RealtimeVoiceChat on Raspberry Pi 5.

## 📋 Prerequisites

### Hardware Requirements

- **Raspberry Pi 5** (4GB or 8GB RAM recommended)
- **High-quality microSD card** (64GB+ Class 10 or better)
- **Official Raspberry Pi 5 Power Supply** (27W USB-C)
- **Ethernet cable** or WiFi connection
- **Optional**: Heat sink/fan for better performance

### Recommended Pi 5 Configuration

- **RAM**: 8GB (recommended) or 4GB (minimum)
- **Storage**: 64GB+ high-speed microSD or NVMe SSD via HAT
- **Cooling**: Active cooling for sustained performance
- **Power**: Official 27W power supply for stability

## 🚀 Step-by-Step Deployment

### Step 1: Prepare Raspberry Pi OS

#### 1.1 Flash Raspberry Pi OS

```bash
# Download Raspberry Pi Imager
# https://www.raspberrypi.com/software/

# Flash 64-bit Raspberry Pi OS (Bookworm) to microSD
# Enable SSH, set username/password, configure WiFi in imager
```

#### 1.2 Initial System Setup

```bash
# SSH into your Pi
ssh pi@your-pi-ip-address

# Update system
sudo apt update && sudo apt upgrade -y

# Install essential packages
sudo apt install -y git curl wget vim htop tree

# Enable all needed interfaces
sudo raspi-config
# Advanced Options > Expand Filesystem
# Interface Options > SSH (Enable)
# Interface Options > I2C (Enable if using sensors)
# Performance Options > GPU Memory Split > 16

# Reboot
sudo reboot
```

### Step 2: Install Python and Dependencies

#### 2.1 Install Python 3.11+

```bash
# Check Python version (should be 3.11+ on Bookworm)
python3 --version

# Install Python development tools
sudo apt install -y python3-pip python3-venv python3-dev build-essential

# Install system dependencies for audio
sudo apt install -y portaudio19-dev libasound2-dev libpulse-dev

# Install additional dependencies
sudo apt install -y ffmpeg libavcodec-extra libsndfile1
```

#### 2.2 Optimize Pi 5 Performance

```bash
# Add to /boot/config.txt for better performance
echo "
# Pi 5 Performance Optimizations
arm_freq=2400
gpu_freq=800
over_voltage=2
temp_limit=75

# Memory split for headless operation
gpu_mem=16

# Enable all CPU cores
force_turbo=1
" | sudo tee -a /boot/config.txt

# Configure memory and swap
sudo dphys-swapfile swapoff
sudo sed -i 's/CONF_SWAPSIZE=100/CONF_SWAPSIZE=2048/' /etc/dphys-swapfile
sudo dphys-swapfile setup
sudo dphys-swapfile swapon

# Reboot to apply changes
sudo reboot
```

### Step 3: Install Docker for ARM64

#### 3.1 Install Docker

```bash
# Install Docker using convenience script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install -y docker-compose

# Restart session to apply group changes
newgrp docker

# Test Docker installation
docker --version
docker-compose --version
```

#### 3.2 Configure Docker for Pi 5

```bash
# Create Docker daemon configuration for Pi optimization
sudo mkdir -p /etc/docker
echo '{
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "experimental": false,
  "live-restore": true
}' | sudo tee /etc/docker/daemon.json

# Restart Docker
sudo systemctl restart docker
sudo systemctl enable docker
```

### Step 4: Deploy RealtimeVoiceChat

#### 4.1 Clone and Setup Project

```bash
# Clone the project
git clone https://github.com/andy-aimer/RealtimeVoiceChat.git
cd RealtimeVoiceChat

# Create Pi-specific environment
python3 -m venv venv_pi5
source venv_pi5/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### 4.2 Create Pi 5 Specific Configuration

```bash
# Create Pi-specific production config
mkdir -p deployment/pi5
```

Create the Pi 5 configuration file:

```bash
cat > deployment/pi5/pi5_config.py << 'EOF'
"""
Raspberry Pi 5 Specific Configuration
Optimized for ARM64 and limited resources
"""

import os
from production.production_config import ProductionConfig

class Pi5Config(ProductionConfig):
    """Pi 5 optimized configuration."""

    def __init__(self):
        # Set Pi-specific defaults before parent init
        self.set_pi5_defaults()
        super().__init__()
        self.apply_pi5_optimizations()

    def set_pi5_defaults(self):
        """Set Pi 5 specific default values."""
        # Resource constraints for Pi 5
        os.environ.setdefault('PROD_MAX_WORKERS', '2')  # Limit workers
        os.environ.setdefault('PROD_MAX_CONNECTIONS', '50')  # Reduce connections
        os.environ.setdefault('PROD_MEMORY_LIMIT', '1GB')  # Memory limit

        # Pi-specific paths
        os.environ.setdefault('PROD_SSL_CERT_PATH', '/home/pi/ssl/server.crt')
        os.environ.setdefault('PROD_SSL_KEY_PATH', '/home/pi/ssl/server.key')
        os.environ.setdefault('PROD_LOG_DIR', '/home/pi/logs/realtimevoicechat')

        # Network settings for Pi
        os.environ.setdefault('PROD_HOST', '0.0.0.0')
        os.environ.setdefault('PROD_PORT', '8000')
        os.environ.setdefault('PROD_SSL_PORT', '8443')

        # Performance tuning
        os.environ.setdefault('PROD_WEBSOCKET_PING_INTERVAL', '30')
        os.environ.setdefault('PROD_WEBSOCKET_PING_TIMEOUT', '10')
        os.environ.setdefault('PROD_RATE_LIMIT_PER_MINUTE', '100')

    def apply_pi5_optimizations(self):
        """Apply Pi 5 specific optimizations."""
        # Audio optimizations for Pi
        self.AUDIO_BUFFER_SIZE = 2048  # Larger buffer for stability
        self.AUDIO_SAMPLE_RATE = 16000  # Lower sample rate
        self.AUDIO_CHANNELS = 1  # Mono for efficiency

        # WebSocket optimizations
        self.WEBSOCKET_COMPRESSION = True  # Enable compression
        self.WEBSOCKET_MAX_MESSAGE_SIZE = 1024 * 512  # 512KB limit

        # Processing optimizations
        self.MAX_CONCURRENT_SESSIONS = 10  # Limit concurrent sessions
        self.THERMAL_THROTTLE_TEMP = 70  # Lower thermal threshold

        # Memory optimizations
        self.ENABLE_MEMORY_MONITORING = True
        self.MEMORY_WARNING_THRESHOLD = 0.8  # 80% memory warning

# Create global instance
pi5_config = Pi5Config()
EOF
```

#### 4.3 Create Pi 5 Docker Configuration

```bash
# Create Pi-specific Dockerfile
cat > deployment/pi5/Dockerfile.pi5 << 'EOF'
# Raspberry Pi 5 optimized Dockerfile
FROM python:3.11-slim-bookworm

# Install system dependencies for Pi 5
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    libasound2-dev \
    libpulse-dev \
    ffmpeg \
    libsndfile1 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/logs /app/ssl

# Set environment for Pi 5
ENV PYTHONPATH=/app
ENV PROD_ENVIRONMENT=pi5
ENV PROD_MAX_WORKERS=2
ENV PROD_MEMORY_LIMIT=1GB

# Expose ports
EXPOSE 8000 8443

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application
CMD ["python", "-m", "uvicorn", "production.production_server:app", "--host", "0.0.0.0", "--port", "8000"]
EOF
```

#### 4.4 Create Pi 5 Docker Compose

```bash
cat > deployment/pi5/docker-compose.pi5.yml << 'EOF'
version: '3.8'

services:
  realtimevoicechat:
    build:
      context: ../..
      dockerfile: deployment/pi5/Dockerfile.pi5
    container_name: realtimevoicechat_pi5
    restart: unless-stopped
    ports:
      - "8000:8000"
      - "8443:8443"
    volumes:
      - ./ssl:/app/ssl:ro
      - ./logs:/app/logs
      - ./data:/app/data
    environment:
      - PROD_ENVIRONMENT=pi5
      - PROD_HOST=0.0.0.0
      - PROD_PORT=8000
      - PROD_SSL_PORT=8443
      - PROD_MAX_WORKERS=2
      - PROD_MAX_CONNECTIONS=50
      - PROD_LOG_LEVEL=INFO
    deploy:
      resources:
        limits:
          memory: 1GB
        reservations:
          memory: 512MB
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  nginx:
    image: nginx:alpine
    container_name: nginx_pi5
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/ssl:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - realtimevoicechat
    deploy:
      resources:
        limits:
          memory: 128MB
        reservations:
          memory: 64MB

  monitoring:
    build:
      context: ../..
      dockerfile: deployment/pi5/Dockerfile.pi5
    container_name: monitoring_pi5
    restart: unless-stopped
    ports:
      - "8001:8001"
    volumes:
      - ./logs:/app/logs:ro
      - ./data:/app/data:ro
    environment:
      - MONITORING_PORT=8001
      - MONITORING_HOST=0.0.0.0
    command: ["python", "monitoring/test_monitor.py"]
    deploy:
      resources:
        limits:
          memory: 256MB
        reservations:
          memory: 128MB

volumes:
  ssl_data:
  logs_data:
  app_data:

networks:
  default:
    driver: bridge
EOF
```

### Step 5: SSL Certificate Setup for Pi 5

#### 5.1 Create Pi-specific SSL Setup

```bash
# Create SSL setup script for Pi
cat > deployment/pi5/setup_ssl_pi5.sh << 'EOF'
#!/bin/bash

# SSL Certificate Setup for Raspberry Pi 5
# Supports self-signed certificates and Let's Encrypt

set -e

PI5_SSL_DIR="/home/pi/ssl"
PROJECT_DIR="/home/pi/RealtimeVoiceChat"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

setup_ssl_directory() {
    print_status "Setting up SSL directory..."
    sudo mkdir -p "$PI5_SSL_DIR"
    sudo chown pi:pi "$PI5_SSL_DIR"
    chmod 700 "$PI5_SSL_DIR"
    print_success "SSL directory created: $PI5_SSL_DIR"
}

generate_self_signed_cert() {
    local domain=${1:-$(hostname).local}

    print_status "Generating self-signed certificate for: $domain"

    # Generate private key
    openssl genrsa -out "$PI5_SSL_DIR/server.key" 2048

    # Generate certificate signing request
    openssl req -new -key "$PI5_SSL_DIR/server.key" -out "$PI5_SSL_DIR/server.csr" -subj "/C=US/ST=State/L=City/O=Organization/CN=$domain"

    # Generate self-signed certificate
    openssl x509 -req -days 365 -in "$PI5_SSL_DIR/server.csr" -signkey "$PI5_SSL_DIR/server.key" -out "$PI5_SSL_DIR/server.crt"

    # Set permissions
    chmod 600 "$PI5_SSL_DIR/server.key"
    chmod 644 "$PI5_SSL_DIR/server.crt"

    print_success "Self-signed certificate generated successfully!"
    print_warning "This certificate is for development/testing only"

    # Clean up CSR
    rm "$PI5_SSL_DIR/server.csr"
}

setup_letsencrypt() {
    local domain=$1
    local email=$2

    if [ -z "$domain" ] || [ -z "$email" ]; then
        print_error "Domain and email are required for Let's Encrypt"
        echo "Usage: $0 --letsencrypt your-domain.com your-email@example.com"
        exit 1
    fi

    print_status "Setting up Let's Encrypt certificate for: $domain"

    # Install certbot
    sudo apt update
    sudo apt install -y certbot

    # Generate certificate
    sudo certbot certonly --standalone --preferred-challenges http \
        --email "$email" --agree-tos --no-eff-email \
        -d "$domain"

    # Copy certificates to our SSL directory
    sudo cp "/etc/letsencrypt/live/$domain/fullchain.pem" "$PI5_SSL_DIR/server.crt"
    sudo cp "/etc/letsencrypt/live/$domain/privkey.pem" "$PI5_SSL_DIR/server.key"

    # Set ownership
    sudo chown pi:pi "$PI5_SSL_DIR/server.crt" "$PI5_SSL_DIR/server.key"
    chmod 644 "$PI5_SSL_DIR/server.crt"
    chmod 600 "$PI5_SSL_DIR/server.key"

    print_success "Let's Encrypt certificate installed successfully!"

    # Setup auto-renewal
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
    print_status "Auto-renewal cron job added"
}

show_help() {
    echo "Pi 5 SSL Certificate Setup"
    echo ""
    echo "Usage:"
    echo "  $0 --self-signed [domain]     Generate self-signed certificate"
    echo "  $0 --letsencrypt domain email Generate Let's Encrypt certificate"
    echo "  $0 --help                     Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 --self-signed              # Use Pi hostname"
    echo "  $0 --self-signed mypi.local   # Custom domain"
    echo "  $0 --letsencrypt mypi.ddns.net me@example.com"
}

main() {
    setup_ssl_directory

    case "${1:-}" in
        --self-signed)
            generate_self_signed_cert "$2"
            ;;
        --letsencrypt)
            setup_letsencrypt "$2" "$3"
            ;;
        --help)
            show_help
            ;;
        *)
            print_status "No arguments provided, generating self-signed certificate"
            generate_self_signed_cert
            ;;
    esac

    # Verify certificates
    if [ -f "$PI5_SSL_DIR/server.crt" ] && [ -f "$PI5_SSL_DIR/server.key" ]; then
        print_success "SSL certificates are ready!"
        echo "Certificate: $PI5_SSL_DIR/server.crt"
        echo "Private Key: $PI5_SSL_DIR/server.key"

        # Show certificate info
        print_status "Certificate information:"
        openssl x509 -in "$PI5_SSL_DIR/server.crt" -text -noout | grep -A 2 "Subject:"
        openssl x509 -in "$PI5_SSL_DIR/server.crt" -text -noout | grep -A 2 "Not Before\|Not After"
    else
        print_error "SSL certificate generation failed!"
        exit 1
    fi
}

main "$@"
EOF

chmod +x deployment/pi5/setup_ssl_pi5.sh
```

### Step 6: Create Pi 5 Deployment Script

#### 6.1 Main Deployment Script

```bash
cat > deployment/pi5/deploy_pi5.sh << 'EOF'
#!/bin/bash

# Raspberry Pi 5 Deployment Script for RealtimeVoiceChat
# Automated production deployment with Pi optimizations

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
PI5_SSL_DIR="/home/pi/ssl"
PI5_LOG_DIR="/home/pi/logs/realtimevoicechat"
PI5_DATA_DIR="/home/pi/data/realtimevoicechat"

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
    echo "║              Raspberry Pi 5 Deployment                     ║"
    echo "║                  RealtimeVoiceChat                          ║"
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

check_prerequisites() {
    print_step "1" "Checking prerequisites..."

    # Check if running on Pi 5
    if ! grep -q "Raspberry Pi 5" /proc/device-tree/model 2>/dev/null; then
        print_warning "This script is optimized for Raspberry Pi 5"
    fi

    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3 first."
        exit 1
    fi

    # Check available memory
    local mem_total=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    local mem_gb=$((mem_total / 1024 / 1024))

    if [ $mem_gb -lt 3 ]; then
        print_warning "Low memory detected ($mem_gb GB). Consider using 4GB+ Pi 5 for better performance."
    else
        print_success "Memory check passed ($mem_gb GB available)"
    fi

    # Check disk space
    local disk_space=$(df / | awk 'NR==2 {print $4}')
    local disk_gb=$((disk_space / 1024 / 1024))

    if [ $disk_gb -lt 5 ]; then
        print_error "Insufficient disk space ($disk_gb GB). Need at least 5GB free space."
        exit 1
    else
        print_success "Disk space check passed ($disk_gb GB available)"
    fi

    print_success "Prerequisites check completed!"
}

setup_directories() {
    print_step "2" "Setting up directories..."

    # Create SSL directory
    mkdir -p "$PI5_SSL_DIR"
    chmod 700 "$PI5_SSL_DIR"

    # Create log directory
    mkdir -p "$PI5_LOG_DIR"
    mkdir -p "$PI5_LOG_DIR/nginx"

    # Create data directory
    mkdir -p "$PI5_DATA_DIR"

    # Create deployment working directory
    mkdir -p "$SCRIPT_DIR/ssl"
    mkdir -p "$SCRIPT_DIR/logs"
    mkdir -p "$SCRIPT_DIR/data"

    # Link directories
    ln -sf "$PI5_SSL_DIR" "$SCRIPT_DIR/ssl"
    ln -sf "$PI5_LOG_DIR" "$SCRIPT_DIR/logs"
    ln -sf "$PI5_DATA_DIR" "$SCRIPT_DIR/data"

    print_success "Directories created successfully!"
}

setup_ssl_certificates() {
    print_step "3" "Setting up SSL certificates..."

    if [ ! -f "$PI5_SSL_DIR/server.crt" ] || [ ! -f "$PI5_SSL_DIR/server.key" ]; then
        print_status "SSL certificates not found. Generating self-signed certificate..."
        "$SCRIPT_DIR/setup_ssl_pi5.sh" --self-signed "$(hostname).local"
    else
        print_success "SSL certificates already exist"
    fi

    # Verify certificates
    if openssl x509 -in "$PI5_SSL_DIR/server.crt" -noout -checkend 86400; then
        print_success "SSL certificates are valid"
    else
        print_warning "SSL certificates are expiring soon or invalid"
    fi
}

optimize_pi5_performance() {
    print_step "4" "Optimizing Pi 5 performance..."

    # Set CPU governor to performance
    if [ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]; then
        echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null
        print_success "CPU governor set to performance mode"
    fi

    # Increase file descriptor limits
    echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
    echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

    # Configure network settings
    echo "net.core.somaxconn = 1024" | sudo tee -a /etc/sysctl.conf
    echo "net.core.netdev_max_backlog = 5000" | sudo tee -a /etc/sysctl.conf
    sudo sysctl -p

    print_success "Pi 5 performance optimization completed"
}

create_nginx_config() {
    print_step "5" "Creating NGINX configuration..."

    cat > "$SCRIPT_DIR/nginx.conf" << 'NGINX_EOF'
events {
    worker_connections 1024;
    use epoll;
}

http {
    upstream app {
        server realtimevoicechat_pi5:8000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    server {
        listen 80;
        server_name _;
        return 301 https://$host$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name _;

        ssl_certificate /etc/ssl/server.crt;
        ssl_certificate_key /etc/ssl/server.key;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        # Security headers
        add_header X-Frame-Options DENY;
        add_header X-Content-Type-Options nosniff;
        add_header X-XSS-Protection "1; mode=block";
        add_header Strict-Transport-Security "max-age=31536000";

        # Rate limiting
        limit_req zone=api burst=20 nodelay;

        location / {
            proxy_pass http://app;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 86400;
        }
    }
}
NGINX_EOF

    print_success "NGINX configuration created"
}

build_and_deploy() {
    print_step "6" "Building and deploying application..."

    cd "$SCRIPT_DIR"

    # Stop any existing containers
    docker-compose -f docker-compose.pi5.yml down 2>/dev/null || true

    # Build and start services
    print_status "Building Docker images (this may take a few minutes on Pi 5)..."
    docker-compose -f docker-compose.pi5.yml build --no-cache

    print_status "Starting services..."
    docker-compose -f docker-compose.pi5.yml up -d

    # Wait for services to start
    print_status "Waiting for services to start..."
    sleep 30

    # Check service health
    local retries=12
    local count=0

    while [ $count -lt $retries ]; do
        if curl -k -f https://localhost/health > /dev/null 2>&1; then
            print_success "Application is running and healthy!"
            break
        fi

        print_status "Waiting for application to start... ($((count + 1))/$retries)"
        sleep 10
        count=$((count + 1))
    done

    if [ $count -eq $retries ]; then
        print_error "Application failed to start properly"
        docker-compose -f docker-compose.pi5.yml logs
        exit 1
    fi
}

setup_systemd_service() {
    print_step "7" "Setting up systemd service..."

    cat > /tmp/realtimevoicechat-pi5.service << 'SERVICE_EOF'
[Unit]
Description=RealtimeVoiceChat on Raspberry Pi 5
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/pi/RealtimeVoiceChat/deployment/pi5
ExecStart=/usr/bin/docker-compose -f docker-compose.pi5.yml up -d
ExecStop=/usr/bin/docker-compose -f docker-compose.pi5.yml down
TimeoutStartSec=0
User=pi
Group=pi

[Install]
WantedBy=multi-user.target
SERVICE_EOF

    sudo mv /tmp/realtimevoicechat-pi5.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable realtimevoicechat-pi5.service

    print_success "Systemd service configured and enabled"
}

setup_monitoring() {
    print_step "8" "Setting up monitoring..."

    # Create monitoring dashboard for Pi 5
    cat > "$SCRIPT_DIR/pi5_monitor.py" << 'MONITOR_EOF'
#!/usr/bin/env python3
"""
Raspberry Pi 5 Monitoring Dashboard
Real-time system monitoring optimized for Pi 5
"""

import time
import json
import psutil
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

class Pi5MonitorHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_dashboard()
        elif self.path == '/api/metrics':
            self.send_metrics()
        else:
            self.send_error(404)

    def send_dashboard(self):
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Pi 5 Monitor - RealtimeVoiceChat</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; background: #f0f0f0; }
                .container { max-width: 1200px; margin: 0 auto; }
                .metric-card { background: white; padding: 20px; margin: 10px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .metric-value { font-size: 2em; font-weight: bold; color: #2196F3; }
                .metric-label { color: #666; margin-top: 5px; }
                .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 15px; }
                .status-good { color: #4CAF50; }
                .status-warning { color: #FF9800; }
                .status-critical { color: #F44336; }
            </style>
            <script>
                function updateMetrics() {
                    fetch('/api/metrics')
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('cpu').textContent = data.cpu_percent + '%';
                            document.getElementById('memory').textContent = data.memory_percent + '%';
                            document.getElementById('temperature').textContent = data.temperature + '°C';
                            document.getElementById('disk').textContent = data.disk_percent + '%';
                            document.getElementById('uptime').textContent = data.uptime;
                            document.getElementById('load').textContent = data.load_avg;
                        });
                }

                setInterval(updateMetrics, 2000);
                updateMetrics();
            </script>
        </head>
        <body>
            <div class="container">
                <h1>🍓 Raspberry Pi 5 Monitor - RealtimeVoiceChat</h1>
                <div class="grid">
                    <div class="metric-card">
                        <div class="metric-value" id="cpu">-</div>
                        <div class="metric-label">CPU Usage</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="memory">-</div>
                        <div class="metric-label">Memory Usage</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="temperature">-</div>
                        <div class="metric-label">CPU Temperature</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="disk">-</div>
                        <div class="metric-label">Disk Usage</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="uptime">-</div>
                        <div class="metric-label">System Uptime</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value" id="load">-</div>
                        <div class="metric-label">Load Average</div>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())

    def send_metrics(self):
        try:
            # Get CPU temperature (Pi 5 specific)
            with open('/sys/class/thermal/thermal_zone0/temp') as f:
                temp = int(f.read()) / 1000.0
        except:
            temp = 0

        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        load_avg = psutil.getloadavg()
        uptime = time.time() - psutil.boot_time()

        metrics = {
            'cpu_percent': round(cpu_percent, 1),
            'memory_percent': round(memory.percent, 1),
            'temperature': round(temp, 1),
            'disk_percent': round(disk.percent, 1),
            'uptime': f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m",
            'load_avg': f"{load_avg[0]:.2f}"
        }

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(metrics).encode())

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8002), Pi5MonitorHandler)
    print("Pi 5 Monitor running on http://localhost:8002")
    server.serve_forever()
MONITOR_EOF

    chmod +x "$SCRIPT_DIR/pi5_monitor.py"

    # Start monitoring in background
    nohup python3 "$SCRIPT_DIR/pi5_monitor.py" > "$PI5_LOG_DIR/monitor.log" 2>&1 &

    print_success "Pi 5 monitoring dashboard started on port 8002"
}

create_management_scripts() {
    print_step "9" "Creating management scripts..."

    # Start script
    cat > "$SCRIPT_DIR/start_pi5.sh" << 'START_EOF'
#!/bin/bash
cd "$(dirname "$0")"
docker-compose -f docker-compose.pi5.yml up -d
echo "RealtimeVoiceChat started on Pi 5"
echo "Access at: https://$(hostname).local or https://$(hostname -I | awk '{print $1}')"
echo "Monitoring: http://$(hostname -I | awk '{print $1}'):8002"
START_EOF

    # Stop script
    cat > "$SCRIPT_DIR/stop_pi5.sh" << 'STOP_EOF'
#!/bin/bash
cd "$(dirname "$0")"
docker-compose -f docker-compose.pi5.yml down
pkill -f pi5_monitor.py
echo "RealtimeVoiceChat stopped on Pi 5"
STOP_EOF

    # Status script
    cat > "$SCRIPT_DIR/status_pi5.sh" << 'STATUS_EOF'
#!/bin/bash
cd "$(dirname "$0")"
echo "=== RealtimeVoiceChat Pi 5 Status ==="
docker-compose -f docker-compose.pi5.yml ps
echo ""
echo "=== System Resources ==="
echo "CPU: $(top -bn1 | grep load | awk '{printf "%.2f%%\n", $(NF-2)*100}')"
echo "Memory: $(free | grep Mem | awk '{printf "%.1f%%\n", $3/$2 * 100.0}')"
echo "Temperature: $(cat /sys/class/thermal/thermal_zone0/temp | awk '{print $1/1000"°C"}')"
echo "Disk: $(df / | tail -1 | awk '{print $5}')"
STATUS_EOF

    # Health check script
    cat > "$SCRIPT_DIR/health_check_pi5.sh" << 'HEALTH_EOF'
#!/bin/bash
echo "🍓 Pi 5 Health Check - RealtimeVoiceChat"
echo "======================================"

# Check SSL certificate
if curl -k -f https://localhost/health > /dev/null 2>&1; then
    echo "✅ HTTPS endpoint healthy"
else
    echo "❌ HTTPS endpoint failed"
fi

# Check monitoring
if curl -f http://localhost:8002/api/metrics > /dev/null 2>&1; then
    echo "✅ Monitoring dashboard healthy"
else
    echo "❌ Monitoring dashboard failed"
fi

# Check Docker containers
echo ""
echo "Container Status:"
docker-compose -f docker-compose.pi5.yml ps

# System health
echo ""
echo "System Health:"
TEMP=$(cat /sys/class/thermal/thermal_zone0/temp | awk '{print $1/1000}')
if (( $(echo "$TEMP > 75" | bc -l) )); then
    echo "⚠️  High temperature: ${TEMP}°C"
else
    echo "✅ Temperature OK: ${TEMP}°C"
fi

MEM_USAGE=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
if (( $(echo "$MEM_USAGE > 90" | bc -l) )); then
    echo "⚠️  High memory usage: ${MEM_USAGE}%"
else
    echo "✅ Memory usage OK: ${MEM_USAGE}%"
fi
HEALTH_EOF

    # Make scripts executable
    chmod +x "$SCRIPT_DIR"/*.sh

    print_success "Management scripts created"
}

print_completion_summary() {
    print_step "10" "Deployment completed successfully!"

    local pi_ip=$(hostname -I | awk '{print $1}')
    local pi_hostname=$(hostname)

    echo ""
    echo -e "${GREEN}${BOLD}🎉 RealtimeVoiceChat is now running on your Raspberry Pi 5!${NC}"
    echo ""
    echo -e "${BLUE}📱 Access URLs:${NC}"
    echo "   • Main App (HTTPS): https://$pi_ip:443 or https://$pi_hostname.local"
    echo "   • Main App (HTTP):  http://$pi_ip:80 (redirects to HTTPS)"
    echo "   • Monitoring:       http://$pi_ip:8001"
    echo "   • Pi 5 Monitor:     http://$pi_ip:8002"
    echo ""
    echo -e "${BLUE}🛠️  Management Commands:${NC}"
    echo "   • Start:       ./deployment/pi5/start_pi5.sh"
    echo "   • Stop:        ./deployment/pi5/stop_pi5.sh"
    echo "   • Status:      ./deployment/pi5/status_pi5.sh"
    echo "   • Health:      ./deployment/pi5/health_check_pi5.sh"
    echo "   • SSL Setup:   ./deployment/pi5/setup_ssl_pi5.sh --help"
    echo ""
    echo -e "${BLUE}📊 Performance Notes:${NC}"
    echo "   • Optimized for Pi 5 ARM64 architecture"
    echo "   • Memory limited to 1GB per container"
    echo "   • CPU governor set to performance mode"
    echo "   • SSL compression enabled for efficiency"
    echo ""
    echo -e "${BLUE}🔧 Next Steps:${NC}"
    echo "   1. Test the application: curl -k https://$pi_ip/health"
    echo "   2. Check monitoring: open http://$pi_ip:8002 in browser"
    echo "   3. Configure domain name if needed"
    echo "   4. Set up port forwarding for external access"
    echo "   5. Consider setting up dynamic DNS for remote access"
    echo ""
    echo -e "${YELLOW}⚠️  Important Security Notes:${NC}"
    echo "   • Currently using self-signed SSL certificate"
    echo "   • For production use, set up proper SSL with Let's Encrypt"
    echo "   • Configure firewall rules for external access"
    echo "   • Change default passwords and API keys"
    echo ""
    echo -e "${BLUE}📖 Documentation:${NC}"
    echo "   • Full guide: deployment/pi5/README_PI5.md"
    echo "   • Production: production/README.md"
    echo "   • Monitoring: monitoring/README.md"
}

main() {
    print_header

    check_prerequisites
    setup_directories
    setup_ssl_certificates
    optimize_pi5_performance
    create_nginx_config
    build_and_deploy
    setup_systemd_service
    setup_monitoring
    create_management_scripts
    print_completion_summary

    print_success "🍓 Raspberry Pi 5 deployment completed successfully!"
}

# Run deployment
main "$@"
EOF

chmod +x deployment/pi5/deploy_pi5.sh
```

### Step 7: Run the Deployment

#### 7.1 Execute Pi 5 Deployment

```bash
# Navigate to project directory
cd ~/RealtimeVoiceChat

# Run the automated Pi 5 deployment
./deployment/pi5/deploy_pi5.sh
```

#### 7.2 Verify Deployment

```bash
# Check application health
./deployment/pi5/health_check_pi5.sh

# Check system status
./deployment/pi5/status_pi5.sh

# View logs if needed
docker-compose -f deployment/pi5/docker-compose.pi5.yml logs
```

### Step 8: Access Your Application

After successful deployment:

1. **Main Application**: `https://your-pi-ip:443`
2. **Monitoring Dashboard**: `http://your-pi-ip:8001`
3. **Pi 5 System Monitor**: `http://your-pi-ip:8002`

### Step 9: Optional Optimizations

#### 9.1 Enable Hardware Acceleration

```bash
# Add to /boot/config.txt for hardware acceleration
echo "
# Hardware acceleration
dtoverlay=vc4-kms-v3d
gpu_mem=128
" | sudo tee -a /boot/config.txt

sudo reboot
```

#### 9.2 Set Up Dynamic DNS (for remote access)

```bash
# Install ddclient for dynamic DNS
sudo apt install -y ddclient

# Configure with your DNS provider
sudo dpkg-reconfigure ddclient
```

#### 9.3 Configure Firewall for External Access

```bash
# Install UFW firewall
sudo apt install -y ufw

# Configure basic rules
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable
```

## 🔧 Troubleshooting

### Common Issues

1. **Memory Issues**: Increase swap or use lighter containers
2. **SSL Certificate Issues**: Check certificate paths and permissions
3. **Performance Issues**: Monitor temperature and CPU usage
4. **Network Issues**: Check firewall and port configurations

### Performance Monitoring

```bash
# Real-time system monitoring
htop

# Check temperature
cat /sys/class/thermal/thermal_zone0/temp

# Monitor Docker resources
docker stats

# Check application logs
docker-compose -f deployment/pi5/docker-compose.pi5.yml logs -f
```

### Maintenance Commands

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Clean Docker images
docker system prune -f

# Restart services
./deployment/pi5/stop_pi5.sh && ./deployment/pi5/start_pi5.sh

# Check SSL certificate expiry
openssl x509 -in /home/pi/ssl/server.crt -noout -dates
```

## 🎉 Congratulations!

Your RealtimeVoiceChat application is now running on Raspberry Pi 5 with:

- ✅ Production-grade security
- ✅ SSL/TLS encryption
- ✅ Real-time monitoring
- ✅ Automatic startup
- ✅ Pi 5 optimizations
- ✅ ARM64 compatibility

The deployment is optimized for Pi 5's ARM64 architecture and includes comprehensive monitoring and management tools.
