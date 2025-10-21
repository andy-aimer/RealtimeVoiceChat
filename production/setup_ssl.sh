#!/bin/bash

# SSL Certificate Generation Script for RealtimeVoiceChat Production
# Generates self-signed certificates for development/testing or prepares for production certificates

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Default configuration
CERT_DIR="$PROJECT_ROOT/ssl"
DOMAIN="localhost"
COUNTRY="US"
STATE="State"
CITY="City"
ORG="RealtimeVoiceChat"
ORG_UNIT="IT"
EMAIL="admin@localhost"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║            SSL Certificate Setup for Production             ║"
    echo "║                  RealtimeVoiceChat                          ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "${GREEN}[STEP]${NC} $1"
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

show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -d, --domain DOMAIN     Domain name for certificate (default: localhost)"
    echo "  -c, --cert-dir DIR      Certificate directory (default: ./ssl)"
    echo "  --production           Generate production-ready certificate request"
    echo "  --letsencrypt          Set up Let's Encrypt certificate"
    echo "  --self-signed          Generate self-signed certificate (default)"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Generate self-signed cert for localhost"
    echo "  $0 -d example.com --production        # Generate CSR for production domain"
    echo "  $0 -d example.com --letsencrypt       # Set up Let's Encrypt certificate"
}

create_cert_dir() {
    print_step "Creating certificate directory: $CERT_DIR"
    mkdir -p "$CERT_DIR"
    chmod 700 "$CERT_DIR"
}

generate_self_signed() {
    print_step "Generating self-signed certificate for $DOMAIN"
    
    # Create OpenSSL configuration
    cat > "$CERT_DIR/cert.conf" << EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
C=$COUNTRY
ST=$STATE
L=$CITY
O=$ORG
OU=$ORG_UNIT
emailAddress=$EMAIL
CN=$DOMAIN

[v3_req]
subjectAltName = @alt_names
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth

[alt_names]
DNS.1 = $DOMAIN
DNS.2 = localhost
DNS.3 = 127.0.0.1
IP.1 = 127.0.0.1
EOF

    # Generate private key
    print_info "Generating private key..."
    openssl genrsa -out "$CERT_DIR/server.key" 2048
    chmod 600 "$CERT_DIR/server.key"
    
    # Generate certificate
    print_info "Generating certificate..."
    openssl req -new -x509 -key "$CERT_DIR/server.key" \
        -out "$CERT_DIR/server.crt" \
        -days 365 \
        -config "$CERT_DIR/cert.conf" \
        -extensions v3_req
    
    chmod 644 "$CERT_DIR/server.crt"
    
    print_info "Self-signed certificate generated successfully!"
    print_warning "Note: Self-signed certificates will show security warnings in browsers"
    print_info "Certificate: $CERT_DIR/server.crt"
    print_info "Private Key: $CERT_DIR/server.key"
}

generate_production_csr() {
    print_step "Generating production certificate signing request (CSR) for $DOMAIN"
    
    # Create OpenSSL configuration for production
    cat > "$CERT_DIR/production.conf" << EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
C=$COUNTRY
ST=$STATE
L=$CITY
O=$ORG
OU=$ORG_UNIT
emailAddress=$EMAIL
CN=$DOMAIN

[v3_req]
subjectAltName = @alt_names
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth

[alt_names]
DNS.1 = $DOMAIN
DNS.2 = www.$DOMAIN
EOF

    # Generate private key
    print_info "Generating private key for production..."
    openssl genrsa -out "$CERT_DIR/production.key" 2048
    chmod 600 "$CERT_DIR/production.key"
    
    # Generate CSR
    print_info "Generating certificate signing request..."
    openssl req -new -key "$CERT_DIR/production.key" \
        -out "$CERT_DIR/production.csr" \
        -config "$CERT_DIR/production.conf"
    
    print_info "Production CSR generated successfully!"
    print_info "Submit this CSR to your Certificate Authority:"
    print_info "CSR File: $CERT_DIR/production.csr"
    print_info "Private Key: $CERT_DIR/production.key (keep this secure!)"
    
    echo ""
    print_info "CSR Content (copy and paste to your CA):"
    echo "----------------------------------------"
    cat "$CERT_DIR/production.csr"
    echo "----------------------------------------"
}

setup_letsencrypt() {
    print_step "Setting up Let's Encrypt certificate for $DOMAIN"
    
    # Check if certbot is installed
    if ! command -v certbot &> /dev/null; then
        print_error "Certbot is not installed. Please install it first:"
        echo "  Ubuntu/Debian: sudo apt-get install certbot"
        echo "  CentOS/RHEL: sudo yum install certbot"
        echo "  macOS: brew install certbot"
        exit 1
    fi
    
    print_warning "Make sure your domain $DOMAIN points to this server's public IP"
    print_warning "Port 80 must be accessible from the internet for domain validation"
    
    read -p "Continue with Let's Encrypt certificate generation? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Let's Encrypt setup cancelled"
        return
    fi
    
    # Generate Let's Encrypt certificate
    print_info "Requesting Let's Encrypt certificate..."
    sudo certbot certonly --standalone \
        --preferred-challenges http \
        -d "$DOMAIN" \
        --email "$EMAIL" \
        --agree-tos \
        --non-interactive
    
    # Copy certificates to our directory
    print_info "Copying certificates to project directory..."
    sudo cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$CERT_DIR/server.crt"
    sudo cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$CERT_DIR/server.key"
    sudo chown "$USER:$USER" "$CERT_DIR/server.crt" "$CERT_DIR/server.key"
    chmod 644 "$CERT_DIR/server.crt"
    chmod 600 "$CERT_DIR/server.key"
    
    print_info "Let's Encrypt certificate setup complete!"
    print_info "Certificate: $CERT_DIR/server.crt"
    print_info "Private Key: $CERT_DIR/server.key"
    
    # Set up auto-renewal
    print_info "Setting up auto-renewal..."
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
    print_info "Auto-renewal cron job added (runs daily at noon)"
}

verify_certificate() {
    if [[ -f "$CERT_DIR/server.crt" ]]; then
        print_step "Verifying certificate..."
        
        print_info "Certificate details:"
        openssl x509 -in "$CERT_DIR/server.crt" -text -noout | grep -E "(Subject:|Issuer:|Not Before:|Not After:)"
        
        print_info "Certificate validation:"
        if openssl x509 -in "$CERT_DIR/server.crt" -noout -checkend 86400; then
            print_info "✅ Certificate is valid and will not expire in the next 24 hours"
        else
            print_warning "⚠️ Certificate will expire within 24 hours or is already expired"
        fi
    fi
}

update_environment_config() {
    print_step "Updating environment configuration..."
    
    ENV_FILE="$PROJECT_ROOT/.env.production"
    
    if [[ -f "$ENV_FILE" ]]; then
        # Update SSL paths in environment file
        sed -i.bak "s|PROD_SSL_CERT_PATH=.*|PROD_SSL_CERT_PATH=$CERT_DIR/server.crt|" "$ENV_FILE"
        sed -i.bak "s|PROD_SSL_KEY_PATH=.*|PROD_SSL_KEY_PATH=$CERT_DIR/server.key|" "$ENV_FILE"
        sed -i.bak "s|PROD_USE_SSL=.*|PROD_USE_SSL=true|" "$ENV_FILE"
        
        print_info "Updated $ENV_FILE with SSL certificate paths"
        print_info "SSL enabled in production configuration"
    else
        print_warning "Environment file not found: $ENV_FILE"
        print_info "Run the production server first to generate the template"
    fi
}

create_docker_ssl_config() {
    print_step "Creating Docker SSL configuration..."
    
    cat > "$PROJECT_ROOT/docker-compose.ssl.yml" << EOF
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8443:8443"
    volumes:
      - ./ssl:/app/ssl:ro
    environment:
      - PROD_USE_SSL=true
      - PROD_SSL_CERT_PATH=/app/ssl/server.crt
      - PROD_SSL_KEY_PATH=/app/ssl/server.key
      - PROD_HOST=0.0.0.0
      - PROD_SSL_PORT=8443
    networks:
      - voicechat_network

networks:
  voicechat_network:
    driver: bridge
EOF

    print_info "Docker SSL configuration created: docker-compose.ssl.yml"
    print_info "Run with: docker-compose -f docker-compose.ssl.yml up"
}

main() {
    print_header
    
    # Parse command line arguments
    MODE="self-signed"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--domain)
                DOMAIN="$2"
                shift 2
                ;;
            -c|--cert-dir)
                CERT_DIR="$2"
                shift 2
                ;;
            --production)
                MODE="production"
                shift
                ;;
            --letsencrypt)
                MODE="letsencrypt"
                shift
                ;;
            --self-signed)
                MODE="self-signed"
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Check dependencies
    if ! command -v openssl &> /dev/null; then
        print_error "OpenSSL is not installed. Please install it first."
        exit 1
    fi
    
    print_info "Domain: $DOMAIN"
    print_info "Certificate directory: $CERT_DIR"
    print_info "Mode: $MODE"
    echo ""
    
    # Create certificate directory
    create_cert_dir
    
    # Generate certificates based on mode
    case $MODE in
        "self-signed")
            generate_self_signed
            ;;
        "production")
            generate_production_csr
            ;;
        "letsencrypt")
            setup_letsencrypt
            ;;
    esac
    
    # Verify and configure
    verify_certificate
    update_environment_config
    create_docker_ssl_config
    
    echo ""
    print_step "Setup complete!"
    
    if [[ $MODE == "self-signed" || $MODE == "letsencrypt" ]]; then
        echo ""
        print_info "Next steps:"
        echo "1. Start the production server:"
        echo "   cd $PROJECT_ROOT"
        echo "   python production/production_server.py"
        echo ""
        echo "2. Access your application:"
        echo "   https://$DOMAIN:8443"
        echo ""
        if [[ $MODE == "self-signed" ]]; then
            print_warning "For self-signed certificates, you'll need to accept the security warning in your browser"
        fi
    fi
}

# Run main function
main "$@"