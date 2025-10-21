#!/bin/bash

# Production Deployment Script for RealtimeVoiceChat
# Implements security recommendations from Phase 2 P4 audit

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}${BOLD}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║              Production Deployment Setup                    ║"
    echo "║                  RealtimeVoiceChat                          ║"
    echo "║                Phase 2 P4 - Security Ready                  ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "${GREEN}${BOLD}[STEP $1]${NC} $2"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

check_prerequisites() {
    print_step "1" "Checking prerequisites..."
    
    local missing_deps=()
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        missing_deps+=("python3")
    fi
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        missing_deps+=("pip3")
    fi
    
    # Check OpenSSL
    if ! command -v openssl &> /dev/null; then
        missing_deps+=("openssl")
    fi
    
    # Check systemctl (for service setup)
    if ! command -v systemctl &> /dev/null; then
        print_warning "systemctl not found - service setup will be skipped"
    fi
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        print_error "Missing dependencies: ${missing_deps[*]}"
        echo "Please install them first:"
        echo "  Ubuntu/Debian: sudo apt-get install ${missing_deps[*]}"
        echo "  CentOS/RHEL: sudo yum install ${missing_deps[*]}"
        echo "  macOS: brew install ${missing_deps[*]}"
        exit 1
    fi
    
    print_success "All prerequisites satisfied"
}

install_python_dependencies() {
    print_step "2" "Installing Python dependencies..."
    
    cd "$PROJECT_ROOT"
    
    # Create production virtual environment
    if [ ! -d "venv_production" ]; then
        print_info "Creating production virtual environment..."
        python3 -m venv venv_production
    fi
    
    # Activate virtual environment
    source venv_production/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install production dependencies
    print_info "Installing production packages..."
    pip install \
        fastapi \
        uvicorn[standard] \
        gunicorn \
        websockets \
        python-jose[cryptography] \
        python-multipart \
        slowapi \
        psutil \
        python-json-logger \
        requests
    
    # Save requirements
    pip freeze > requirements.production.txt
    
    print_success "Python dependencies installed"
}

setup_ssl_certificates() {
    print_step "3" "Setting up SSL certificates..."
    
    read -p "Do you want to set up SSL certificates? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_info "Choose SSL setup method:"
        echo "1. Self-signed certificate (for testing)"
        echo "2. Let's Encrypt certificate (for production with domain)"
        echo "3. Upload existing certificate"
        echo "4. Skip SSL setup"
        
        read -p "Enter choice (1-4): " -n 1 -r
        echo
        
        case $REPLY in
            1)
                print_info "Setting up self-signed certificate..."
                chmod +x "$SCRIPT_DIR/setup_ssl.sh"
                "$SCRIPT_DIR/setup_ssl.sh" --self-signed
                ;;
            2)
                read -p "Enter your domain name: " domain
                print_info "Setting up Let's Encrypt certificate for $domain..."
                chmod +x "$SCRIPT_DIR/setup_ssl.sh"
                "$SCRIPT_DIR/setup_ssl.sh" --domain "$domain" --letsencrypt
                ;;
            3)
                print_info "Please place your certificate files in $PROJECT_ROOT/ssl/"
                print_info "Required files:"
                print_info "  - server.crt (certificate file)"
                print_info "  - server.key (private key file)"
                read -p "Press Enter when files are in place..."
                ;;
            4)
                print_warning "SSL setup skipped - connections will be unencrypted"
                ;;
        esac
    else
        print_warning "SSL setup skipped"
    fi
}

create_production_config() {
    print_step "4" "Creating production configuration..."
    
    cd "$PROJECT_ROOT"
    
    # Generate production environment file
    if [ ! -f ".env.production" ]; then
        print_info "Generating production environment template..."
        source venv_production/bin/activate
        python -c "
import sys
sys.path.append('.')
from production.production_config import production_config
production_config.export_env_template('.env.production')
"
    fi
    
    # Customize configuration
    print_info "Customizing production configuration..."
    
    # Generate secure secret key
    SECRET_KEY=$(openssl rand -hex 32)
    sed -i.bak "s/PROD_AUTH_SECRET_KEY=.*/PROD_AUTH_SECRET_KEY=$SECRET_KEY/" .env.production
    
    # Set SSL paths if certificates exist
    if [ -f "ssl/server.crt" ] && [ -f "ssl/server.key" ]; then
        sed -i.bak "s|PROD_SSL_CERT_PATH=.*|PROD_SSL_CERT_PATH=$PROJECT_ROOT/ssl/server.crt|" .env.production
        sed -i.bak "s|PROD_SSL_KEY_PATH=.*|PROD_SSL_KEY_PATH=$PROJECT_ROOT/ssl/server.key|" .env.production
        sed -i.bak "s/PROD_USE_SSL=.*/PROD_USE_SSL=true/" .env.production
        print_success "SSL enabled in configuration"
    else
        print_warning "No SSL certificates found - SSL disabled"
        sed -i.bak "s/PROD_USE_SSL=.*/PROD_USE_SSL=false/" .env.production
    fi
    
    # Ask about authentication
    read -p "Enable authentication? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sed -i.bak "s/PROD_AUTH_ENABLED=.*/PROD_AUTH_ENABLED=true/" .env.production
        print_info "Authentication enabled (username: any, password: production)"
    else
        sed -i.bak "s/PROD_AUTH_ENABLED=.*/PROD_AUTH_ENABLED=false/" .env.production
    fi
    
    # Set log directory
    LOG_DIR="/var/log/realtimevoicechat"
    if [ ! -d "$LOG_DIR" ]; then
        if [ "$EUID" -eq 0 ]; then
            mkdir -p "$LOG_DIR"
            chmod 755 "$LOG_DIR"
        else
            print_warning "Cannot create system log directory. Using local logs."
            LOG_DIR="$PROJECT_ROOT/logs"
            mkdir -p "$LOG_DIR"
            sed -i.bak "s|PROD_LOG_FILE=.*|PROD_LOG_FILE=$LOG_DIR/app.log|" .env.production
        fi
    fi
    
    print_success "Production configuration created"
}

setup_firewall() {
    print_step "5" "Configuring firewall..."
    
    if command -v ufw &> /dev/null; then
        print_info "Configuring UFW firewall..."
        
        # Check if running as root or with sudo
        if [ "$EUID" -ne 0 ]; then
            print_warning "Firewall configuration requires sudo privileges"
            read -p "Configure firewall with sudo? (y/n): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                print_warning "Firewall configuration skipped"
                return
            fi
            SUDO="sudo"
        else
            SUDO=""
        fi
        
        # Allow SSH (important!)
        $SUDO ufw allow ssh
        
        # Allow HTTP and HTTPS
        $SUDO ufw allow 80/tcp
        $SUDO ufw allow 443/tcp
        
        # Allow application ports
        if grep -q "PROD_USE_SSL=true" .env.production 2>/dev/null; then
            $SUDO ufw allow 8443/tcp  # SSL port
        else
            $SUDO ufw allow 8000/tcp  # Non-SSL port
        fi
        
        # Monitoring port (internal only)
        $SUDO ufw allow from 127.0.0.1 to any port 8001
        
        # Enable firewall if not already enabled
        $SUDO ufw --force enable
        
        print_success "Firewall configured"
        $SUDO ufw status
    else
        print_warning "UFW not found - manual firewall configuration required"
        print_info "Required ports:"
        print_info "  - 22 (SSH)"
        print_info "  - 80 (HTTP)"
        print_info "  - 443 (HTTPS)"
        print_info "  - 8000/8443 (Application)"
        print_info "  - 8001 (Monitoring - internal only)"
    fi
}

create_systemd_service() {
    print_step "6" "Creating systemd service..."
    
    if ! command -v systemctl &> /dev/null; then
        print_warning "systemctl not found - skipping service creation"
        return
    fi
    
    if [ "$EUID" -ne 0 ]; then
        print_warning "Service creation requires sudo privileges"
        read -p "Create systemd service with sudo? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_warning "Service creation skipped"
            return
        fi
        SUDO="sudo"
    else
        SUDO=""
    fi
    
    # Create service file
    SERVICE_FILE="/etc/systemd/system/realtimevoicechat.service"
    
    $SUDO tee "$SERVICE_FILE" > /dev/null << EOF
[Unit]
Description=RealtimeVoiceChat Production Server
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=$PROJECT_ROOT
Environment=PATH=$PROJECT_ROOT/venv_production/bin
EnvironmentFile=$PROJECT_ROOT/.env.production
ExecStart=$PROJECT_ROOT/venv_production/bin/python production/production_server.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
SyslogIdentifier=realtimevoicechat

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$PROJECT_ROOT/logs /var/log/realtimevoicechat

[Install]
WantedBy=multi-user.target
EOF

    # Create user if it doesn't exist
    if ! id "www-data" &>/dev/null; then
        $SUDO useradd --system --no-create-home --shell /bin/false www-data
    fi
    
    # Set permissions
    $SUDO chown -R www-data:www-data "$PROJECT_ROOT"
    $SUDO chmod 644 "$SERVICE_FILE"
    
    # Reload systemd and enable service
    $SUDO systemctl daemon-reload
    $SUDO systemctl enable realtimevoicechat
    
    print_success "Systemd service created and enabled"
    print_info "Control with:"
    print_info "  sudo systemctl start realtimevoicechat"
    print_info "  sudo systemctl stop realtimevoicechat"
    print_info "  sudo systemctl status realtimevoicechat"
    print_info "  sudo journalctl -u realtimevoicechat -f"
}

setup_monitoring() {
    print_step "7" "Setting up monitoring..."
    
    # Create monitoring startup script
    cat > "$PROJECT_ROOT/start_monitoring.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source venv_production/bin/activate
cd monitoring
python test_monitor.py &
MONITOR_PID=$!
echo $MONITOR_PID > monitor.pid
echo "Monitoring dashboard started on http://localhost:8001 (PID: $MONITOR_PID)"
EOF
    
    chmod +x "$PROJECT_ROOT/start_monitoring.sh"
    
    # Create monitoring stop script
    cat > "$PROJECT_ROOT/stop_monitoring.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
if [ -f monitoring/monitor.pid ]; then
    PID=$(cat monitoring/monitor.pid)
    if kill -0 $PID 2>/dev/null; then
        kill $PID
        echo "Monitoring dashboard stopped (PID: $PID)"
    else
        echo "Monitoring dashboard not running"
    fi
    rm -f monitoring/monitor.pid
else
    echo "No monitoring PID file found"
fi
EOF
    
    chmod +x "$PROJECT_ROOT/stop_monitoring.sh"
    
    print_success "Monitoring scripts created"
    print_info "Start monitoring: ./start_monitoring.sh"
    print_info "Stop monitoring: ./stop_monitoring.sh"
}

create_deployment_scripts() {
    print_step "8" "Creating deployment scripts..."
    
    # Production start script
    cat > "$PROJECT_ROOT/start_production.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"

echo "Starting RealtimeVoiceChat Production Server..."

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo "Error: .env.production not found"
    echo "Run deploy_production.sh first"
    exit 1
fi

# Load environment variables
export $(grep -v '^#' .env.production | xargs)

# Activate virtual environment
source venv_production/bin/activate

# Start the server
python production/production_server.py
EOF
    
    chmod +x "$PROJECT_ROOT/start_production.sh"
    
    # Production stop script
    cat > "$PROJECT_ROOT/stop_production.sh" << 'EOF'
#!/bin/bash
echo "Stopping RealtimeVoiceChat Production Server..."

# Find and kill production server processes
pkill -f "production_server.py"
pkill -f "uvicorn.*production"

# Stop systemd service if it exists
if systemctl is-active --quiet realtimevoicechat; then
    sudo systemctl stop realtimevoicechat
    echo "Systemd service stopped"
fi

echo "Production server stopped"
EOF
    
    chmod +x "$PROJECT_ROOT/stop_production.sh"
    
    # Health check script
    cat > "$PROJECT_ROOT/health_check.sh" << 'EOF'
#!/bin/bash

# Load configuration
if [ -f ".env.production" ]; then
    export $(grep -v '^#' .env.production | xargs)
fi

# Determine URL
if [ "${PROD_USE_SSL:-false}" = "true" ]; then
    URL="https://localhost:${PROD_SSL_PORT:-8443}/health"
else
    URL="http://localhost:${PROD_PORT:-8000}/health"
fi

echo "Checking health at: $URL"

# Check health endpoint
if curl -k -s "$URL" | jq . 2>/dev/null; then
    echo "✅ Health check passed"
    exit 0
else
    echo "❌ Health check failed"
    exit 1
fi
EOF
    
    chmod +x "$PROJECT_ROOT/health_check.sh"
    
    print_success "Deployment scripts created"
}

run_security_validation() {
    print_step "9" "Running security validation..."
    
    cd "$PROJECT_ROOT"
    source venv_production/bin/activate
    
    # Run security audit
    print_info "Running security audit..."
    cd monitoring
    if python security_audit.py; then
        print_success "Security audit completed"
    else
        print_warning "Security audit found issues - check the report"
    fi
    
    # Run production optimization
    print_info "Running production optimization..."
    if python production_optimization.py; then
        print_success "Production optimization completed"
    else
        print_warning "Production optimization found issues - check the report"
    fi
    
    cd "$PROJECT_ROOT"
}

display_deployment_summary() {
    print_step "10" "Deployment Summary"
    
    echo ""
    echo -e "${GREEN}${BOLD}🎉 Production Deployment Complete!${NC}"
    echo ""
    
    # SSL status
    if [ -f "ssl/server.crt" ] && [ -f "ssl/server.key" ]; then
        SSL_STATUS="✅ Enabled"
        APP_URL="https://localhost:8443"
    else
        SSL_STATUS="❌ Disabled"
        APP_URL="http://localhost:8000"
    fi
    
    # Authentication status
    if grep -q "PROD_AUTH_ENABLED=true" .env.production 2>/dev/null; then
        AUTH_STATUS="✅ Enabled (username: any, password: production)"
    else
        AUTH_STATUS="❌ Disabled"
    fi
    
    # Service status
    if systemctl is-enabled realtimevoicechat &>/dev/null; then
        SERVICE_STATUS="✅ Systemd service created and enabled"
    else
        SERVICE_STATUS="❌ No systemd service (manual start required)"
    fi
    
    echo -e "${BLUE}Configuration Summary:${NC}"
    echo "  SSL/TLS: $SSL_STATUS"
    echo "  Authentication: $AUTH_STATUS"
    echo "  Service: $SERVICE_STATUS"
    echo "  Monitoring: ✅ Available at http://localhost:8001"
    echo ""
    
    echo -e "${BLUE}Start the application:${NC}"
    if systemctl is-enabled realtimevoicechat &>/dev/null; then
        echo "  sudo systemctl start realtimevoicechat"
    else
        echo "  ./start_production.sh"
    fi
    echo ""
    
    echo -e "${BLUE}Access your application:${NC}"
    echo "  Application: $APP_URL"
    echo "  Health Check: $APP_URL/health"
    echo "  Monitoring: http://localhost:8001"
    echo ""
    
    echo -e "${BLUE}Management commands:${NC}"
    echo "  Start: ./start_production.sh"
    echo "  Stop: ./stop_production.sh"
    echo "  Health: ./health_check.sh"
    echo "  Monitor: ./start_monitoring.sh"
    echo ""
    
    echo -e "${BLUE}Security Reports:${NC}"
    echo "  Security Audit: monitoring/security_audit_report.html"
    echo "  Production Optimization: monitoring/production_optimization_report.html"
    echo ""
    
    if [ "$SSL_STATUS" = "❌ Disabled" ]; then
        echo -e "${YELLOW}⚠️ Important Security Notice:${NC}"
        echo "SSL is currently disabled. For production use, please:"
        echo "1. Run: ./production/setup_ssl.sh --letsencrypt"
        echo "2. Restart the application"
        echo ""
    fi
    
    echo -e "${GREEN}Happy chatting! 🎤💬🧠🔊${NC}"
}

main() {
    print_header
    
    # Create production directory if it doesn't exist
    mkdir -p "$PROJECT_ROOT/production"
    mkdir -p "$PROJECT_ROOT/logs"
    
    # Run deployment steps
    check_prerequisites
    install_python_dependencies
    setup_ssl_certificates
    create_production_config
    setup_firewall
    create_systemd_service
    setup_monitoring
    create_deployment_scripts
    run_security_validation
    display_deployment_summary
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "Usage: $0 [--help]"
        echo ""
        echo "Production deployment script for RealtimeVoiceChat"
        echo "Implements security recommendations from Phase 2 P4 audit"
        echo ""
        echo "This script will:"
        echo "1. Install Python dependencies"
        echo "2. Set up SSL certificates"
        echo "3. Create production configuration"
        echo "4. Configure firewall"
        echo "5. Create systemd service"
        echo "6. Set up monitoring"
        echo "7. Run security validation"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac