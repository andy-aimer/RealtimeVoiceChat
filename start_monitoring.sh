#!/bin/bash

# Real-Time Test Monitoring Setup Script
# Phase 2 P4 - Polish & Validation

echo "🖥️  Setting up Real-Time Test Monitoring Dashboard"
echo "=================================================="

# Check if we're in the right directory
if [ ! -f "code/server.py" ]; then
    echo "❌ Error: Please run this script from the RealtimeVoiceChat directory"
    exit 1
fi

# Create monitoring directory if it doesn't exist
mkdir -p monitoring/static

echo "📦 Installing additional dependencies..."

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "🔄 Activating virtual environment..."
    source venv/bin/activate
fi

# Install monitoring dependencies
pip install psutil requests

echo "🚀 Starting monitoring dashboard..."

# Start the monitoring dashboard in the background
cd monitoring
python test_monitor.py &
MONITOR_PID=$!

echo "📊 Monitor PID: $MONITOR_PID"
echo "🌐 Dashboard URL: http://localhost:8001"
echo "💚 Health Check: http://localhost:8001/health"

# Wait a moment for the dashboard to start
sleep 3

# Check if dashboard is running
if curl -s http://localhost:8001/health > /dev/null; then
    echo "✅ Monitoring dashboard is running!"
    echo ""
    echo "🎯 Next Steps:"
    echo "1. Open http://localhost:8001 in your browser"
    echo "2. Run tests with: python monitoring/test_runner.py"
    echo "3. Watch real-time progress in the dashboard!"
    echo ""
    echo "⏹️  To stop the monitor: kill $MONITOR_PID"
else
    echo "❌ Failed to start monitoring dashboard"
    kill $MONITOR_PID 2>/dev/null
    exit 1
fi

# Save PID for later cleanup
echo $MONITOR_PID > monitoring/.monitor.pid

echo "🎉 Real-time test monitoring is ready!"
echo "📖 Open http://localhost:8001 to view the dashboard"