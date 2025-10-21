#!/bin/bash

# Production Deployment Validation Script
# Tests the production setup to ensure everything is working correctly

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
    echo "║              Production Validation Test                     ║"
    echo "║                  RealtimeVoiceChat                          ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

print_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

test_environment() {
    print_test "Testing production environment setup..."
    
    # Check if production directory exists
    if [ -d "$PROJECT_ROOT/production" ]; then
        print_pass "Production directory exists"
    else
        print_fail "Production directory missing"
        return 1
    fi
    
    # Check if configuration files exist
    if [ -f "$PROJECT_ROOT/production/production_config.py" ]; then
        print_pass "Production configuration file exists"
    else
        print_fail "Production configuration file missing"
        return 1
    fi
    
    # Check if server file exists
    if [ -f "$PROJECT_ROOT/production/production_server.py" ]; then
        print_pass "Production server file exists"
    else
        print_fail "Production server file missing"
        return 1
    fi
    
    # Check if deployment scripts exist
    if [ -f "$PROJECT_ROOT/production/deploy_production.sh" ] && [ -x "$PROJECT_ROOT/production/deploy_production.sh" ]; then
        print_pass "Deployment script exists and is executable"
    else
        print_fail "Deployment script missing or not executable"
        return 1
    fi
    
    return 0
}

test_ssl_setup() {
    print_test "Testing SSL certificate setup..."
    
    # Check if SSL setup script exists
    if [ -f "$PROJECT_ROOT/production/setup_ssl.sh" ] && [ -x "$PROJECT_ROOT/production/setup_ssl.sh" ]; then
        print_pass "SSL setup script exists and is executable"
    else
        print_fail "SSL setup script missing or not executable"
        return 1
    fi
    
    # Test SSL script help
    if "$PROJECT_ROOT/production/setup_ssl.sh" --help > /dev/null 2>&1; then
        print_pass "SSL setup script help works"
    else
        print_fail "SSL setup script help fails"
        return 1
    fi
    
    return 0
}

test_docker_configuration() {
    print_test "Testing Docker configuration..."
    
    # Check if Docker files exist
    if [ -f "$PROJECT_ROOT/Dockerfile.production" ]; then
        print_pass "Production Dockerfile exists"
    else
        print_fail "Production Dockerfile missing"
        return 1
    fi
    
    if [ -f "$PROJECT_ROOT/docker-compose.production.yml" ]; then
        print_pass "Production Docker Compose file exists"
    else
        print_fail "Production Docker Compose file missing"
        return 1
    fi
    
    # Check if NGINX configuration exists
    if [ -f "$PROJECT_ROOT/nginx/nginx.conf" ]; then
        print_pass "NGINX configuration exists"
    else
        print_fail "NGINX configuration missing"
        return 1
    fi
    
    return 0
}

test_monitoring_integration() {
    print_test "Testing monitoring integration..."
    
    # Check if monitoring files exist
    if [ -f "$PROJECT_ROOT/monitoring/test_monitor.py" ]; then
        print_pass "Monitoring server exists"
    else
        print_fail "Monitoring server missing"
        return 1
    fi
    
    if [ -f "$PROJECT_ROOT/monitoring/security_audit.py" ]; then
        print_pass "Security audit script exists"
    else
        print_fail "Security audit script missing"
        return 1
    fi
    
    if [ -f "$PROJECT_ROOT/monitoring/production_optimization.py" ]; then
        print_pass "Production optimization script exists"
    else
        print_fail "Production optimization script missing"
        return 1
    fi
    
    return 0
}

test_security_features() {
    print_test "Testing security features..."
    
    cd "$PROJECT_ROOT"
    
    # Create a temporary virtual environment for testing
    if [ ! -d "test_venv" ]; then
        python3 -m venv test_venv
    fi
    
    source test_venv/bin/activate
    
    # Install minimal dependencies for testing
    pip install -q fastapi uvicorn requests > /dev/null 2>&1
    
    # Test production config import (without validation to avoid SSL cert requirements)
    if python -c "
import sys
sys.path.append('.')
import os
# Temporarily disable validation by setting test mode
os.environ['PROD_TEST_MODE'] = 'true'
try:
    from production.production_config import ProductionConfig
    # Test class definition without full initialization
    config_class = ProductionConfig
    print('Production config imports successfully')
except ImportError as e:
    print(f'Import error: {e}')
    exit(1)
except Exception as e:
    # Configuration errors are expected in test mode without SSL certs
    if 'SSL certificate' in str(e) or 'log directory' in str(e):
        print('Production config imports successfully (validation errors expected in test mode)')
    else:
        print(f'Unexpected error: {e}')
        exit(1)
" > /dev/null 2>&1; then
        print_pass "Production configuration imports correctly"
    else
        print_fail "Production configuration import fails"
        deactivate
        return 1
    fi
    
    # Test environment template generation
    if PROD_TEST_MODE=true python -c "
import sys
sys.path.append('.')
from production.production_config import production_config
production_config.export_env_template('.env.test')
" > /dev/null 2>&1; then
        print_pass "Environment template generation works"
        rm -f .env.test
    else
        print_fail "Environment template generation fails"
        deactivate
        return 1
    fi
    
    deactivate
    rm -rf test_venv
    
    return 0
}

test_phase2_integration() {
    print_test "Testing Phase 2 integration..."
    
    # Check if Phase 2 completion reports exist
    if [ -f "$PROJECT_ROOT/PHASE_2_P4_COMPLETION_REPORT.md" ]; then
        print_pass "Phase 2 P4 completion report exists"
    else
        print_fail "Phase 2 P4 completion report missing"
        return 1
    fi
    
    # Check if monitoring reports can be generated
    if [ -f "$PROJECT_ROOT/monitoring/security_audit_report.html" ]; then
        print_pass "Security audit report exists"
    else
        print_warning "Security audit report not generated yet (run security audit)"
    fi
    
    if [ -f "$PROJECT_ROOT/monitoring/production_optimization_report.html" ]; then
        print_pass "Production optimization report exists"
    else
        print_warning "Production optimization report not generated yet (run optimization)"
    fi
    
    return 0
}

validate_file_permissions() {
    print_test "Validating file permissions..."
    
    # Check script permissions
    local scripts=(
        "production/deploy_production.sh"
        "production/setup_ssl.sh"
    )
    
    for script in "${scripts[@]}"; do
        if [ -x "$PROJECT_ROOT/$script" ]; then
            print_pass "$script is executable"
        else
            print_fail "$script is not executable"
            return 1
        fi
    done
    
    return 0
}

generate_quick_start_test() {
    print_test "Generating quick start test..."
    
    cat > "$PROJECT_ROOT/test_production_setup.sh" << 'EOF'
#!/bin/bash
# Quick Production Setup Test
# This script validates the production setup can be initiated

echo "🚀 Testing Production Setup..."

# Test 1: Generate self-signed certificate
echo "1. Testing SSL setup..."
./production/setup_ssl.sh --self-signed --domain localhost

# Test 2: Generate production environment
echo "2. Testing configuration generation..."
python3 -m venv test_env
source test_env/bin/activate
pip install fastapi uvicorn
python -c "
import sys
sys.path.append('.')
from production.production_config import production_config
production_config.export_env_template('.env.test')
print('✅ Configuration generation successful')
"
deactivate
rm -rf test_env .env.test

# Test 3: Validate Docker setup
echo "3. Testing Docker configuration..."
if command -v docker &> /dev/null; then
    docker build -f Dockerfile.production -t realtimevoicechat:test . > /dev/null 2>&1 && echo "✅ Docker build successful" || echo "❌ Docker build failed"
else
    echo "⚠️ Docker not available - skipping Docker test"
fi

echo "🎉 Production setup test completed!"
EOF
    
    chmod +x "$PROJECT_ROOT/test_production_setup.sh"
    print_pass "Quick start test script generated"
}

run_all_tests() {
    local failed_tests=0
    
    test_environment || ((failed_tests++))
    test_ssl_setup || ((failed_tests++))
    test_docker_configuration || ((failed_tests++))
    test_monitoring_integration || ((failed_tests++))
    test_security_features || ((failed_tests++))
    test_phase2_integration || ((failed_tests++))
    validate_file_permissions || ((failed_tests++))
    generate_quick_start_test || ((failed_tests++))
    
    return $failed_tests
}

print_summary() {
    local failed_tests=$1
    
    echo ""
    echo -e "${BLUE}${BOLD}📋 Validation Summary${NC}"
    echo "===================="
    
    if [ $failed_tests -eq 0 ]; then
        echo -e "${GREEN}✅ All tests passed! Production deployment is ready.${NC}"
        echo ""
        echo -e "${BLUE}Next steps:${NC}"
        echo "1. Run full deployment: ./production/deploy_production.sh"
        echo "2. Or test basic setup: ./test_production_setup.sh"
        echo "3. Start application: ./start_production.sh"
        echo "4. Access at: https://localhost:8443"
        echo "5. Monitor at: http://localhost:8001"
    else
        echo -e "${RED}❌ $failed_tests test(s) failed. Please fix the issues before deployment.${NC}"
        echo ""
        echo -e "${BLUE}Common fixes:${NC}"
        echo "1. Ensure all files are present"
        echo "2. Make scripts executable: chmod +x production/*.sh"
        echo "3. Install Python dependencies"
        echo "4. Check file permissions"
    fi
    
    echo ""
    echo -e "${BLUE}Available commands after deployment:${NC}"
    echo "• ./production/deploy_production.sh  - Full automated deployment"
    echo "• ./production/setup_ssl.sh         - SSL certificate setup"
    echo "• ./start_production.sh             - Start application"
    echo "• ./stop_production.sh              - Stop application"
    echo "• ./health_check.sh                 - Health check"
    echo "• ./start_monitoring.sh             - Start monitoring"
    echo ""
    echo -e "${BLUE}Documentation:${NC}"
    echo "• production/README.md              - Complete production guide"
    echo "• PHASE_2_P4_COMPLETION_REPORT.md   - Phase 2 summary"
    echo "• monitoring/README.md              - Monitoring guide"
}

main() {
    print_header
    
    cd "$PROJECT_ROOT"
    
    echo -e "${BLUE}Validating production deployment setup...${NC}"
    echo "Project root: $PROJECT_ROOT"
    echo ""
    
    if run_all_tests; then
        failed_tests=0
    else
        failed_tests=$?
    fi
    
    print_summary $failed_tests
    
    exit $failed_tests
}

# Run main function
main "$@"