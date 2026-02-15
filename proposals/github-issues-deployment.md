# 🚀 Deployment & Infrastructure

## Issue 24: Create Docker Configuration ✅

**Labels:** `infrastructure`, `deployment`, `priority:medium`, `enhancement`  
**Status:** ✅ **IMPLEMENTED**

**Description:**
Containerize the application for easier deployment, better consistency across environments, and simplified scaling.

**Implemented Files:**
- `Dockerfile` - Production image with gunicorn, non-root user, health check
- `Dockerfile.dev` - Development image with hot reload
- `docker-compose.yml` - Production compose (Redis commented out as optional)
- `docker-compose.dev.yml` - Development compose with volume mounts
- `.dockerignore` - Excludes unnecessary files from build
- `.env.example` - Environment variable template

**Tasks:**
- [x] Create production Dockerfile
  ```dockerfile
  # Dockerfile
  FROM python:3.11-slim
  
  # Install system dependencies
  RUN apt-get update && apt-get install -y \
      gcc \
      && rm -rf /var/lib/apt/lists/*
  
  # Create app user (security best practice)
  RUN useradd -m -u 1000 appuser
  
  WORKDIR /app
  
  # Install Python dependencies
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  
  # Copy application code
  COPY --chown=appuser:appuser . .
  
  # Switch to non-root user
  USER appuser
  
  # Expose port
  EXPOSE 8000
  
  # Health check
  HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
      CMD curl -f http://localhost:8000/health || exit 1
  
  # Run with gunicorn
  CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "--access-logfile", "-", "run:app"]
  ```
- [x] Create development Dockerfile
  ```dockerfile
  # Dockerfile.dev
  FROM python:3.11-slim
  
  WORKDIR /app
  
  # Install dev dependencies
  RUN pip install debugpy
  
  COPY requirements.txt .
  RUN pip install -r requirements.txt
  
  COPY . .
  
  # Development server with hot reload
  CMD ["flask", "run", "--host=0.0.0.0", "--debug"]
  ```
- [x] Create docker-compose.yml (Redis commented out)
  ```yaml
  version: '3.8'
  
  services:
    web:
      build: .
      ports:
        - "8000:8000"
      environment:
        - SECRET_KEY=${SECRET_KEY}
        - IP_HASH_SALT=${IP_HASH_SALT}
        - DISCORD_WEBHOOK_URL=${DISCORD_WEBHOOK_URL}
        - REDIS_URL=redis://redis:6379/0
      volumes:
        - ./data:/app/data
        - ./logs:/app/logs
      depends_on:
        - redis
      restart: unless-stopped
    
    redis:
      image: redis:7-alpine
      ports:
        - "6379:6379"
      volumes:
        - redis_data:/data
      restart: unless-stopped
    
    nginx:
      image: nginx:alpine
      ports:
        - "80:80"
        - "443:443"
      volumes:
        - ./nginx.conf:/etc/nginx/nginx.conf:ro
        - ./ssl:/etc/nginx/ssl:ro
      depends_on:
        - web
      restart: unless-stopped
  
  volumes:
    redis_data:
  ```
- [x] Create .dockerignore
  ```
  __pycache__
  *.pyc
  .git
  .env
  .venv
  venv/
  .pytest_cache
  .coverage
  htmlcov/
  logs/
  *.log
  ```
- [x] Add docker documentation (docs/deployment/README.md)
  ```markdown
  # Docker Deployment
  
  ## Development
  ```bash
  docker-compose -f docker-compose.dev.yml up
  ```
  
  ## Production
  ```bash
  docker-compose up -d
  ```
  ```
- [ ] Test container builds (manual)
- [ ] Optimize image size (optional, multi-stage builds)

**Estimated Effort:** 3-4 hours ✅ **COMPLETED**

**Benefits:**
- Consistent deployment environment
- Easy local development setup
- Simplified scaling

---

## Issue 25: Set up CI/CD Pipeline ✅

**Labels:** `infrastructure`, `deployment`, `priority:high`, `automation`  
**Status:** ✅ **IMPLEMENTED**

**Implemented Files:**
- `.github/workflows/test.yml` - Run tests and linting on push/PR
- `.github/workflows/build.yml` - Build Docker image on version tags
- `.github/workflows/deploy.yml` - SSH deploy after successful build

**Description:**
Automate testing, building, and deployment with GitHub Actions.

**Tasks:**
- [ ] Create test workflow
  ```yaml
  # .github/workflows/test.yml
  name: Tests
  
  on:
    push:
      branches: [main, develop]
    pull_request:
      branches: [main]
  
  jobs:
    test:
      runs-on: ubuntu-latest
      
      steps:
        - uses: actions/checkout@v4
        
        - name: Set up Python
          uses: actions/setup-python@v4
          with:
            python-version: '3.11'
            cache: 'pip'
        
        - name: Install dependencies
          run: |
            pip install -r requirements.txt
            pip install pytest pytest-cov
        
        - name: Run tests
          run: pytest --cov=app --cov-report=xml
        
        - name: Upload coverage
          uses: codecov/codecov-action@v3
          with:
            file: ./coverage.xml
        
        - name: Run linting
          run: |
            pip install flake8 black mypy
            flake8 app/
            black --check app/
            mypy app/
  ```
- [ ] Create build workflow
  ```yaml
  # .github/workflows/build.yml
  name: Build Docker Image
  
  on:
    push:
      tags:
        - 'v*'
  
  jobs:
    build:
      runs-on: ubuntu-latest
      
      steps:
        - uses: actions/checkout@v4
        
        - name: Set up Docker Buildx
          uses: docker/setup-buildx-action@v3
        
        - name: Login to Docker Hub
          uses: docker/login-action@v3
          with:
            username: ${{ secrets.DOCKER_USERNAME }}
            password: ${{ secrets.DOCKER_PASSWORD }}
        
        - name: Build and push
          uses: docker/build-push-action@v5
          with:
            context: .
            push: true
            tags: |
              youruser/server-systems:latest
              youruser/server-systems:${{ github.ref_name }}
            cache-from: type=registry,ref=youruser/server-systems:latest
            cache-to: type=inline
  ```
- [ ] Create deployment workflow
  ```yaml
  # .github/workflows/deploy.yml
  name: Deploy to Production
  
  on:
    workflow_run:
      workflows: ["Build Docker Image"]
      types:
        - completed
  
  jobs:
    deploy:
      runs-on: ubuntu-latest
      if: ${{ github.event.workflow_run.conclusion == 'success' }}
      
      steps:
        - name: Deploy to server
          uses: appleboy/ssh-action@master
          with:
            host: ${{ secrets.DEPLOY_HOST }}
            username: ${{ secrets.DEPLOY_USER }}
            key: ${{ secrets.DEPLOY_KEY }}
            script: |
              cd /opt/server-systems
              docker-compose pull
              docker-compose up -d
              docker-compose logs -f --tail=100
  ```
- [ ] Add status badges to README
  ```markdown
  ![Tests](https://github.com/user/repo/workflows/Tests/badge.svg)
  ![Coverage](https://codecov.io/gh/user/repo/branch/main/graph/badge.svg)
  ```
- [ ] Document CI/CD process

**Estimated Effort:** 4-5 hours

**Benefits:**
- Automated testing
- Consistent builds
- Fast deployments
- Reduced human error

---

## Issue 26: Create Production Nginx Configuration ✅

**Labels:** `infrastructure`, `deployment`, `priority:high`, `security`  
**Status:** ✅ **IMPLEMENTED**

**Implemented Files:**
- `nginx.conf` - Full production config with SSL, gzip, rate limiting, security headers, static file serving

**Description:**
Set up nginx as reverse proxy with SSL, caching, and security headers.

**Tasks:**
- [x] Create nginx.conf
  ```nginx
  # nginx.conf
  user nginx;
  worker_processes auto;
  error_log /var/log/nginx/error.log warn;
  pid /var/run/nginx.pid;
  
  events {
      worker_connections 1024;
  }
  
  http {
      include /etc/nginx/mime.types;
      default_type application/octet-stream;
      
      # Logging
      log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for" '
                      'rt=$request_time';
      
      access_log /var/log/nginx/access.log main;
      
      # Performance
      sendfile on;
      tcp_nopush on;
      tcp_nodelay on;
      keepalive_timeout 65;
      types_hash_max_size 2048;
      
      # Compression
      gzip on;
      gzip_vary on;
      gzip_proxied any;
      gzip_comp_level 6;
      gzip_types text/plain text/css text/xml text/javascript 
                 application/json application/javascript application/xml+rss;
      
      # Rate limiting
      limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
      limit_req_zone $binary_remote_addr zone=api:10m rate=30r/s;
      limit_req_zone $binary_remote_addr zone=login:10m rate=5r/m;
      
      # Upstream
      upstream flask_app {
          server web:8000 max_fails=3 fail_timeout=30s;
      }
      
      # HTTP -> HTTPS redirect
      server {
          listen 80;
          server_name your-domain.com;
          return 301 https://$server_name$request_uri;
      }
      
      # HTTPS server
      server {
          listen 443 ssl http2;
          server_name your-domain.com;
          
          # SSL configuration
          ssl_certificate /etc/nginx/ssl/cert.pem;
          ssl_certificate_key /etc/nginx/ssl/key.pem;
          ssl_protocols TLSv1.2 TLSv1.3;
          ssl_ciphers HIGH:!aNULL:!MD5;
          ssl_prefer_server_ciphers on;
          ssl_session_cache shared:SSL:10m;
          ssl_session_timeout 10m;
          
          # Security headers
          add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
          add_header X-Frame-Options "DENY" always;
          add_header X-Content-Type-Options "nosniff" always;
          add_header X-XSS-Protection "1; mode=block" always;
          add_header Referrer-Policy "strict-origin-when-cross-origin" always;
          
          # Static files (aggressive caching)
          location /static/ {
              alias /app/static/;
              expires 1y;
              add_header Cache-Control "public, immutable";
              access_log off;
          }
          
          # API endpoints
          location /api/ {
              limit_req zone=api burst=10 nodelay;
              proxy_pass http://flask_app;
              proxy_set_header Host $host;
              proxy_set_header X-Real-IP $remote_addr;
              proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
              proxy_set_header X-Forwarded-Proto $scheme;
          }
          
          # Login endpoint (strict rate limit)
          location /api/admin/session {
              limit_req zone=login burst=2 nodelay;
              proxy_pass http://flask_app;
              proxy_set_header Host $host;
              proxy_set_header X-Real-IP $remote_addr;
              proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          }
          
          # Default location
          location / {
              limit_req zone=general burst=20 nodelay;
              proxy_pass http://flask_app;
              proxy_set_header Host $host;
              proxy_set_header X-Real-IP $remote_addr;
              proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
              proxy_set_header X-Forwarded-Proto $scheme;
              
              # WebSocket support (if needed)
              proxy_http_version 1.1;
              proxy_set_header Upgrade $http_upgrade;
              proxy_set_header Connection "upgrade";
          }
      }
  }
  ```
- [ ] Set up Let's Encrypt SSL
  ```bash
  certbot certonly --nginx -d your-domain.com
  ```
- [ ] Add SSL renewal cron job
  ```bash
  0 0 * * * certbot renew --quiet
  ```
- [ ] Test nginx config
  ```bash
  nginx -t
  ```
- [ ] Document nginx setup

**Estimated Effort:** 3-4 hours ✅ **COMPLETED**

**Benefits:**
- SSL/TLS encryption
- Better performance (caching, compression)
- Additional security layer
- Professional setup

---

## Issue 27: Set up Monitoring and Alerting

**Labels:** `monitoring`, `infrastructure`, `priority:medium`, `observability`

**Description:**
Implement comprehensive monitoring with Prometheus and Grafana, plus alerting for critical issues.

**Tasks:**
- [ ] Add Prometheus exporter
  ```python
  # Install prometheus_client
  pip install prometheus-client
  
  # app/monitoring.py
  from prometheus_client import Counter, Histogram, Gauge, generate_latest
  
  REQUEST_COUNT = Counter(
      'http_requests_total',
      'Total HTTP requests',
      ['method', 'endpoint', 'status']
  )
  
  REQUEST_DURATION = Histogram(
      'http_request_duration_seconds',
      'HTTP request duration',
      ['method', 'endpoint']
  )
  
  ACTIVE_SESSIONS = Gauge(
      'active_admin_sessions',
      'Number of active admin sessions'
  )
  
  @app.route('/metrics')
  def metrics():
      return generate_latest()
  ```
- [ ] Add Prometheus to docker-compose
  ```yaml
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    restart: unless-stopped
  
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=changeme
    volumes:
      - grafana_data:/var/lib/grafana
    restart: unless-stopped
  ```
- [ ] Create Prometheus config
  ```yaml
  # prometheus.yml
  global:
    scrape_interval: 15s
    evaluation_interval: 15s
  
  scrape_configs:
    - job_name: 'server-systems'
      static_configs:
        - targets: ['web:8000']
  ```
- [ ] Create Grafana dashboard
  - Request rate by endpoint
  - Response time percentiles
  - Error rate
  - Active sessions
  - Database query count
  - Memory/CPU usage
- [ ] Set up alerts
  ```yaml
  # alerts.yml
  groups:
    - name: server_systems
      interval: 30s
      rules:
        - alert: HighErrorRate
          expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
          for: 5m
          annotations:
            summary: "High error rate detected"
        
        - alert: SlowResponse
          expr: http_request_duration_seconds{quantile="0.99"} > 1
          for: 5m
          annotations:
            summary: "Slow API responses"
  ```
- [ ] Configure alert notifications (email, Slack, Discord)
- [ ] Document monitoring setup

**Estimated Effort:** 6-8 hours

**Benefits:**
- Real-time performance visibility
- Proactive issue detection
- Historical data for analysis
- Professional operations

---

## Issue 28: Create Deployment Documentation ✅

**Labels:** `documentation`, `deployment`, `priority:high`  
**Status:** ✅ **IMPLEMENTED**

**Implemented Files:**
- `docs/deployment/README.md` - Quick start guide, commands, troubleshooting
- `.env.example` - Environment variable template

**Description:**
Comprehensive guide for deploying the application to production.

**Tasks:**
- [x] Create deployment guide
  ```markdown
  # docs/deployment/production.md
  
  ## Prerequisites
  - Ubuntu 22.04 LTS server
  - Docker & Docker Compose installed
  - Domain with DNS configured
  - SSH access to server
  
  ## Initial Setup
  
  1. Clone repository
  2. Configure environment variables
  3. Set up SSL certificates
  4. Initialize database
  5. Start services
  
  ## Deployment Steps
  
  ## Monitoring
  
  ## Troubleshooting
  
  ## Rollback Procedure
  ```
- [ ] Create backup/restore documentation
  ```markdown
  # Backup
  ```bash
  # Database
  docker-compose exec web python scripts/backup_db.py
  
  # Files
  tar -czf backup-$(date +%Y%m%d).tar.gz data/
  ```
  
  # Restore
  ```bash
  docker-compose down
  tar -xzf backup-20240101.tar.gz
  docker-compose up -d
  ```
  ```
- [ ] Create update procedure
  ```markdown
  # Update to new version
  ```bash
  git pull
  docker-compose build
  docker-compose down
  docker-compose up -d
  ```
  ```
- [ ] Create security checklist
  - [ ] Firewall configured
  - [ ] SSL certificates valid
  - [ ] Secrets rotated
  - [ ] Backups tested
  - [ ] Monitoring active
- [x] Add troubleshooting guide

**Estimated Effort:** 4-5 hours ✅ **COMPLETED**

---

## Issue 29: Implement Automated Backups ✅

**Labels:** `infrastructure`, `priority:high`, `data-protection`  
**Status:** ✅ **IMPLEMENTED**

**Implemented Files:**
- `scripts/backup.py` - Full backup script with compression and cleanup
- `scripts/restore.py` - Interactive restore with safety confirmations

**Description:**
Set up automated backup system for database and critical files.

**Tasks:**
- [x] Create backup script
  ```python
  # scripts/backup.py
  import shutil
  import datetime
  import os
  
  BACKUP_DIR = '/backups'
  DATA_DIR = '/app/data'
  
  def backup_database():
      timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
      backup_file = f'{BACKUP_DIR}/database_{timestamp}.db'
      
      shutil.copy2(
          f'{DATA_DIR}/database.db',
          backup_file
      )
      
      # Compress
      shutil.make_archive(backup_file, 'gzip', backup_file)
      os.remove(backup_file)
      
      return f'{backup_file}.gz'
  
  def cleanup_old_backups(days=30):
      """Keep only last 30 days of backups"""
      cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
      
      for filename in os.listdir(BACKUP_DIR):
          filepath = os.path.join(BACKUP_DIR, filename)
          if os.path.getmtime(filepath) < cutoff.timestamp():
              os.remove(filepath)
  ```
- [ ] Add cron job for daily backups
  ```bash
  # /etc/cron.d/app-backup
  0 2 * * * root docker-compose exec -T web python scripts/backup.py
  ```
- [ ] Set up offsite backup storage
  ```python
  # Upload to S3/B2/etc.
  import boto3
  
  s3 = boto3.client('s3')
  s3.upload_file(
      backup_file,
      'your-backup-bucket',
      f'backups/{os.path.basename(backup_file)}'
  )
  ```
- [ ] Create restore script
  ```python
  # scripts/restore.py
  def restore_database(backup_file):
      # Stop application
      # Restore database
      # Restart application
      pass
  ```
- [ ] Test backup/restore procedure (manual)
- [x] Document backup strategy

**Estimated Effort:** 3-4 hours ✅ **COMPLETED**

**Benefits:**
- Data protection
- Disaster recovery
- Compliance requirements
```
