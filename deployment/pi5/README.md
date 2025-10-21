# 🍓 Raspberry Pi 5 Quick Start Guide

## Two-Minute Deployment

### Option 1: Super Quick Setup (Recommended for Testing)

**On your Raspberry Pi 5, run this single command:**

```bash
curl -sSL https://raw.githubusercontent.com/andy-aimer/RealtimeVoiceChat/main/deployment/pi5/quick_setup_pi5.sh | bash
```

Or if you have the repository locally:

```bash
# Clone the repository
git clone https://github.com/andy-aimer/RealtimeVoiceChat.git
cd RealtimeVoiceChat

# Run quick setup
./deployment/pi5/quick_setup_pi5.sh
```

**What this does:**

- ✅ Installs Docker and dependencies
- ✅ Optimizes Pi 5 performance settings
- ✅ Sets up SSL certificates
- ✅ Deploys the application
- ✅ Creates management scripts

**Access after setup:**

- **Main App**: `http://your-pi-ip:8000`
- **Monitoring**: `http://your-pi-ip:8001`

### Option 2: Full Production Setup

For a complete production deployment with all security features:

```bash
# Follow the complete guide
cat deployment/raspberry_pi5_deployment.md

# Or use the production deployment script
./deployment/pi5/deploy_pi5.sh
```

## 🎯 What You Get

### 🚀 **Performance Optimized for Pi 5**

- ARM64 Docker containers
- Memory-limited (1GB) containers
- CPU governor optimization
- Thermal management

### 🛡️ **Security Features**

- SSL/TLS encryption
- Rate limiting
- Security headers
- Firewall integration

### 📊 **Monitoring**

- Real-time system metrics
- Pi 5 temperature monitoring
- Memory and CPU usage
- Container health checks

### 🔧 **Easy Management**

- One-command start/stop
- Automatic startup on boot
- Health monitoring
- Log management

## 🛠️ Management Commands

After deployment, use these commands:

```bash
# Start the application
~/start_realtimevoicechat.sh

# Stop the application
~/stop_realtimevoicechat.sh

# Check status
~/status_realtimevoicechat.sh

# View logs
docker logs realtimevoicechat_pi5_quick
```

## 🔍 Troubleshooting

### Common Issues

**Application won't start:**

```bash
# Check container status
docker ps -a

# View logs
docker logs realtimevoicechat_pi5_quick

# Restart services
~/stop_realtimevoicechat.sh && ~/start_realtimevoicechat.sh
```

**High temperature:**

```bash
# Check temperature
vcgencmd measure_temp

# Add cooling or reduce CPU frequency in /boot/config.txt
```

**Memory issues:**

```bash
# Check memory usage
free -h

# Restart to clear memory
sudo reboot
```

### Performance Tips

1. **Use Class 10+ MicroSD card** or NVMe SSD
2. **Enable active cooling** for sustained performance
3. **Use 8GB Pi 5** for better performance
4. **Monitor temperature** - throttling starts at 80°C

## 📈 Next Steps

### For Development

- Access the web interface at `http://your-pi-ip:8000`
- Check monitoring dashboard at `http://your-pi-ip:8001`
- Customize configuration in `deployment/pi5/pi5_config.py`

### For Production

- Set up proper domain name and SSL certificates
- Configure firewall rules for external access
- Set up dynamic DNS for remote access
- Enable automatic updates

### For Advanced Features

- Multi-user support
- Mobile app integration
- Cloud synchronization
- Advanced analytics

## 🎉 Enjoy Your Pi 5 Deployment!

Your RealtimeVoiceChat is now running on Raspberry Pi 5 with enterprise-grade features optimized for ARM64 architecture.

For questions or issues, check the full documentation in `deployment/raspberry_pi5_deployment.md`.
