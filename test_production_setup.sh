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
