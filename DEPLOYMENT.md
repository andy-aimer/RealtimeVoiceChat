# Deployment Guide

This document provides comprehensive deployment instructions for the RealtimeVoiceChat application.

## 🚀 Quick Deployment

### Docker (Recommended)

The fastest way to deploy the application is using Docker:

```bash
# Clone the repository
git clone https://github.com/andy-aimer/RealtimeVoiceChat.git
cd RealtimeVoiceChat

# Build and run production image
docker build -f Dockerfile -t realtimevoicechat:production .
docker run --gpus all -p 8000:8000 realtimevoicechat:production
```

### Docker Compose

For a complete deployment with monitoring and load balancing:

```bash
# Production deployment with all services
docker-compose -f docker-compose.production.yml up -d

# Verify services are running
docker-compose -f docker-compose.production.yml ps
```

## 📁 Optimized Project Structure

The codebase has been reorganized for production deployment:

```
RealtimeVoiceChat/
├── src/                     # 🎯 Production application code
├── dev/                     # 🔧 Development files (excluded from Docker)
├── deployment/              # 🚀 Production configurations
├── .github/workflows/       # 🔄 CI/CD pipelines
├── docker-compose.yml       # Development environment
├── Dockerfile              # 📦 Production Docker image
└── requirements.txt        # Production dependencies only
```

**Key Benefits:**

- ✅ **Smaller Docker images** (dev files excluded)
- ✅ **Faster builds** (optimized layer caching)
- ✅ **Cleaner structure** (production vs development separation)
- ✅ **Better security** (no test files in production)

## 🐳 Docker Configuration

### Production Dockerfile Features

- **Multi-stage build** for smaller final images
- **CUDA 12.1 support** for GPU acceleration
- **Model pre-downloading** for faster startup
- **Non-root user** for security
- **Optimized Python dependencies** with caching

### Build Arguments

```bash
# Custom Whisper model
docker build --build-arg WHISPER_MODEL=medium.en -t realtimevoicechat .

# Available models: tiny, base, small, medium, large
```

## 🔧 Configuration

### Environment Variables

Required environment variables:

```bash
# Production settings
MAX_AUDIO_QUEUE_SIZE=50
LOG_LEVEL=INFO
WHISPER_MODEL=base.en
RUNNING_IN_DOCKER=true

# GPU settings (if available)
NVIDIA_VISIBLE_DEVICES=all
CUDA_HOME=/usr/local/cuda

# Cache directories
HF_HOME=/home/appuser/.cache/huggingface
TORCH_HOME=/home/appuser/.cache/torch
```

### Volume Mounts

For persistent caching and logs:

```bash
docker run -v /host/cache:/home/appuser/.cache \
           -v /host/logs:/app/logs \
           -p 8000:8000 realtimevoicechat:production
```

## 🎯 Hardware Deployment Targets

### Raspberry Pi 5 (Primary Target)

Optimized for Pi 5 deployment:

```bash
# Pi 5 specific constraints
Memory usage: <50MB for monitoring
CPU overhead: <2%
Response time: <500ms for health checks
Temperature monitoring: 75°C warning, 80°C critical
```

Deployment command:

```bash
docker run -d --name voicechat \
           --restart unless-stopped \
           -p 8000:8000 \
           -v /opt/voicechat/cache:/home/appuser/.cache \
           realtimevoicechat:production
```

### GPU Servers

For CUDA-enabled deployment:

```bash
# GPU deployment
docker run -d --name voicechat-gpu \
           --gpus all \
           --restart unless-stopped \
           -p 8000:8000 \
           -e NVIDIA_VISIBLE_DEVICES=all \
           realtimevoicechat:production
```

## 📊 Production Monitoring

### Health Checks

The application provides comprehensive health monitoring:

```bash
# Health endpoint
curl http://localhost:8000/health

# Metrics (Prometheus format)
curl http://localhost:8000/metrics

# System information
curl http://localhost:8000/system
```

### Performance Targets

- **Health endpoint:** <500ms (p95)
- **Metrics endpoint:** <50ms (p99)
- **Memory usage:** <50MB for monitoring
- **CPU overhead:** <2% on Pi 5

## 🔒 Production Security

### Security Features

- ✅ **Non-root container execution**
- ✅ **Minimal attack surface** (no dev tools)
- ✅ **Input validation** and sanitization
- ✅ **Rate limiting** built-in
- ✅ **No sensitive data logging**

### Recommended Security Settings

```bash
# Run with read-only filesystem
docker run --read-only --tmpfs /tmp \
           -p 8000:8000 realtimevoicechat:production

# Limit resources
docker run --memory=2g --cpus=2 \
           -p 8000:8000 realtimevoicechat:production
```

## 🚦 CI/CD Integration

The project includes production-ready CI/CD:

1. **Quality Gates:** Code formatting, linting, security scanning
2. **Testing:** Multi-Python version testing (3.10-3.12)
3. **Coverage:** 60% minimum requirement with trending
4. **Performance:** Endpoint validation and benchmarking
5. **Pi5 Validation:** Hardware-specific constraint checking
6. **Deployment:** Automated Docker builds and registry pushes

### GitHub Actions Workflows

- `ci-cd.yml` - Main orchestration pipeline
- `test.yml` - Multi-platform testing
- `coverage.yml` - Coverage enforcement
- `quality.yml` - Code quality checks
- `monitoring.yml` - Performance validation
- `pi5-validation.yml` - Hardware optimization

## 🔍 Troubleshooting

### Common Issues

1. **GPU not detected:**

   ```bash
   # Check NVIDIA runtime
   docker run --gpus all nvidia/cuda:12.1-base-ubuntu22.04 nvidia-smi
   ```

2. **Memory issues on Pi 5:**

   ```bash
   # Monitor memory usage
   docker stats voicechat
   ```

3. **Audio device access:**
   ```bash
   # Add device permissions
   docker run --device=/dev/snd -p 8000:8000 realtimevoicechat:production
   ```

### Logs and Debugging

```bash
# View container logs
docker logs voicechat

# Real-time log monitoring
docker logs -f voicechat

# Enter container for debugging
docker exec -it voicechat /bin/bash
```

## 📈 Scaling and Performance

### Horizontal Scaling

Use Docker Compose for load balancing:

```yaml
version: "3.8"
services:
  app:
    image: realtimevoicechat:production
    deploy:
      replicas: 3
    ports:
      - "8000-8002:8000"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```

### Performance Optimization

1. **Model caching:** Pre-download models in Docker image
2. **Memory limits:** Set appropriate container limits
3. **CPU affinity:** Pin containers to specific cores
4. **Storage:** Use SSD for model cache directories

## 🆘 Support

For deployment issues:

1. Check the [GitHub Issues](https://github.com/andy-aimer/RealtimeVoiceChat/issues)
2. Review CI/CD pipeline results
3. Consult the main README.md for general usage
4. Check dev/docs/ for development information

---

**Version:** 1.0.0  
**Last Updated:** October 2025  
**Deployment Target:** Production Ready
