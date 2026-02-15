# Deployment Guide

Quick guide for deploying Server Systems with Docker.

## Prerequisites

- Docker & Docker Compose installed
- Domain with DNS configured (for production)
- SSH access to server

## Quick Start (Development)

```bash
# Start development server with hot reload
docker-compose -f docker-compose.dev.yml up

# Access at http://localhost:5000
```

## Production Deployment

### 1. Initial Setup

```bash
# Clone repository
git clone <repo-url> /opt/server-systems
cd /opt/server-systems

# Create environment file
cp .env.example .env
# Edit .env with your secrets
```

### 2. SSL Certificates

```bash
# Create ssl directory
mkdir -p ssl

# Option A: Let's Encrypt (recommended)
certbot certonly --standalone -d your-domain.com
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/key.pem

# Option B: Self-signed (development only)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ssl/key.pem -out ssl/cert.pem
```

### 3. Start Services

```bash
# Build and start
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SECRET_KEY` | Flask secret key (32+ chars) | ✅ |
| `IP_HASH_SALT` | Salt for IP hashing | ✅ |
| `DISCORD_WEBHOOK_URL` | Discord notifications | ❌ |

## Useful Commands

```bash
# Restart services
docker-compose restart

# Stop everything
docker-compose down

# Update to latest
git pull
docker-compose build
docker-compose up -d

# View logs
docker-compose logs -f web

# Execute command in container
docker-compose exec web python scripts/backup.py
```

## Backups

```bash
# Manual backup
docker-compose exec web python scripts/backup.py

# Restore
docker-compose exec web python scripts/restore.py --list
docker-compose exec web python scripts/restore.py --database backups/<file>
```

## Health Check

```bash
curl http://localhost:8000/api/health
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Container won't start | Check logs: `docker-compose logs web` |
| Port already in use | Change port in docker-compose.yml |
| Database errors | Check data directory permissions |
| SSL errors | Verify cert.pem and key.pem exist in ssl/ |
