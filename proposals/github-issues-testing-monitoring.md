# 🧪 Testing & Monitoring

## Issue 19: Implement Unit Tests for Security Module

**Labels:** `testing`, `priority:high`, `security`, `enhancement`

**Description:**
Create comprehensive unit tests for all security functions to ensure they work correctly and prevent regressions.

**Current State:**
- No automated tests
- Security validation done manually
- Risk of breaking security features during refactoring

**Tasks:**
- [ ] Set up pytest framework
  ```bash
  pip install pytest pytest-cov pytest-flask
  ```
- [ ] Create test directory structure
  ```
  tests/
  ├── __init__.py
  ├── conftest.py           # Shared fixtures
  ├── unit/
  │   ├── test_security.py
  │   ├── test_sanitize.py
  │   └── test_validation.py
  └── integration/
      ├── test_auth.py
      └── test_rate_limiting.py
  ```
- [ ] Write security unit tests
  ```python
  # tests/unit/test_security.py
  import pytest
  from app.utils.security import (
      generate_csrf_token,
      validate_csrf_token,
      hash_ip,
      check_rate_limit_memory
  )
  
  def test_csrf_token_generation():
      token = generate_csrf_token()
      assert len(token) == 43  # 32 bytes base64
      assert token.isalnum() or '-' in token or '_' in token
  
  def test_csrf_token_validation(app):
      with app.test_request_context():
          token = generate_csrf_token()
          assert validate_csrf_token(token) is True
          assert validate_csrf_token('invalid') is False
          assert validate_csrf_token(None) is False
  
  def test_ip_hashing():
      ip = "192.168.1.1"
      hashed = hash_ip(ip)
      assert len(hashed) == 16
      assert hash_ip(ip) == hashed  # Deterministic
      assert hash_ip("192.168.1.2") != hashed  # Different IP
      assert hash_ip(None) is None
  
  def test_rate_limiting():
      ip = "test-ip"
      # Should allow first 10 requests
      for i in range(10):
          allowed, count = check_rate_limit_memory(ip, limit=10, window_seconds=60)
          assert allowed is True
          assert count == i + 1
      
      # 11th request should be denied
      allowed, count = check_rate_limit_memory(ip, limit=10, window_seconds=60)
      assert allowed is False
      assert count == 10
  ```
- [ ] Write sanitization tests
  ```python
  # tests/unit/test_sanitize.py
  from app.utils.sanitize import sanitize_text, sanitize_html
  
  def test_xss_prevention():
      malicious = '<script>alert("XSS")</script>'
      clean = sanitize_html(malicious)
      assert '<script>' not in clean
      assert 'alert' not in clean
  
  def test_sql_injection_prevention():
      malicious = "'; DROP TABLE users; --"
      clean = sanitize_text(malicious)
      assert clean == malicious  # Should be escaped, not removed
  ```
- [ ] Create test fixtures
  ```python
  # tests/conftest.py
  import pytest
  from app import create_app, db
  
  @pytest.fixture
  def app():
      app = create_app('testing')
      with app.app_context():
          db.create_all()
          yield app
          db.session.remove()
          db.drop_all()
  
  @pytest.fixture
  def client(app):
      return app.test_client()
  ```
- [ ] Achieve 80%+ code coverage
  ```bash
  pytest --cov=app --cov-report=html
  ```
- [ ] Add test documentation

**Estimated Effort:** 6-8 hours

**Benefits:**
- Catch security bugs early
- Safe refactoring
- Documentation through tests

---

## Issue 20: Add Integration Tests for Critical Flows

**Labels:** `testing`, `priority:high`, `enhancement`

**Description:**
Test complete user flows end-to-end, especially authentication and application submission.

**Tasks:**
- [ ] Test admin authentication flow
  ```python
  # tests/integration/test_auth.py
  def test_admin_login_flow(client):
      # Try with wrong credentials
      response = client.post('/api/admin/session', json={
          'username': 'wrong',
          'password': 'wrong'
      })
      assert response.status_code == 401
      
      # Try with correct credentials
      response = client.post('/api/admin/session', json={
          'username': 'admin',
          'password': 'correct'
      })
      assert response.status_code == 200
      assert 'admin_session_token' in response.headers.get('Set-Cookie', '')
  
  def test_rate_limiting_on_login(client):
      # Make 11 failed login attempts
      for _ in range(11):
          client.post('/api/admin/session', json={
              'username': 'wrong',
              'password': 'wrong'
          })
      
      # Next request should be rate limited
      response = client.post('/api/admin/session', json={
          'username': 'admin',
          'password': 'correct'
      })
      assert response.status_code == 429
  ```
- [ ] Test application submission flow
  ```python
  def test_application_submission(client):
      # Get CSRF token
      csrf_response = client.get('/api/csrf-token')
      csrf_token = csrf_response.json['csrf_token']
      
      # Submit application
      response = client.post('/api/bewerbung', 
          json={
              'roblox_username': 'TestUser',
              'discord_username': 'test#1234',
              # ... other fields
          },
          headers={'X-CSRF-Token': csrf_token}
      )
      assert response.status_code == 200
      assert response.json['success'] is True
  ```
- [ ] Test forum posting flow
  ```python
  def test_forum_post_creation(client, admin_session):
      csrf_token = get_csrf_token(client)
      
      response = client.post('/api/forum/posts',
          json={
              'title': 'Test Post',
              'content': 'Test content',
              'category': 'general'
          },
          headers={'X-CSRF-Token': csrf_token}
      )
      assert response.status_code == 201
  ```
- [ ] Test IP blacklist enforcement
  ```python
  def test_ip_blacklist_blocks_requests(client, blacklisted_ip):
      with client.application.test_request_context():
          client.environ_base['REMOTE_ADDR'] = blacklisted_ip
          
          response = client.get('/api/forum/posts')
          assert response.status_code == 403
  ```
- [ ] Run tests in CI pipeline
- [ ] Document test scenarios

**Estimated Effort:** 6-8 hours

---

## Issue 21: Create Health Check and Monitoring Endpoints

**Labels:** `monitoring`, `priority:high`, `enhancement`, `infrastructure`

**Description:**
Add health check endpoint for load balancers and monitoring systems, plus metrics endpoints for observability.

**Tasks:**
- [ ] Create comprehensive health check
  ```python
  # app/routes/monitoring.py
  from flask import Blueprint, jsonify
  import shutil
  from sqlalchemy import text
  
  monitoring_bp = Blueprint('monitoring', __name__)
  
  @monitoring_bp.route('/health')
  def health_check():
      """
      Health check endpoint for load balancers.
      Returns 200 if healthy, 503 if unhealthy.
      """
      health_status = {
          'status': 'healthy',
          'timestamp': time.time(),
          'checks': {}
      }
      
      # Database connectivity check
      try:
          db.session.execute(text('SELECT 1'))
          health_status['checks']['database'] = 'ok'
      except Exception as e:
          health_status['checks']['database'] = 'error'
          health_status['status'] = 'unhealthy'
          logger.error(f"Health check - DB failed: {e}")
      
      # Disk space check
      try:
          disk = shutil.disk_usage('/')
          disk_free_percent = (disk.free / disk.total) * 100
          
          if disk_free_percent < 10:
              health_status['checks']['disk'] = 'warning'
              health_status['status'] = 'degraded'
          else:
              health_status['checks']['disk'] = 'ok'
          
          health_status['checks']['disk_free_percent'] = round(disk_free_percent, 2)
      except Exception as e:
          health_status['checks']['disk'] = 'error'
          logger.error(f"Health check - Disk failed: {e}")
      
      # Memory check
      import psutil
      memory = psutil.virtual_memory()
      health_status['checks']['memory_percent'] = round(memory.percent, 2)
      
      if memory.percent > 90:
          health_status['status'] = 'degraded'
      
      status_code = 200 if health_status['status'] == 'healthy' else 503
      return jsonify(health_status), status_code
  
  @monitoring_bp.route('/health/live')
  def liveness():
      """Simple liveness check for Kubernetes."""
      return jsonify({'status': 'alive'}), 200
  
  @monitoring_bp.route('/health/ready')
  def readiness():
      """Readiness check - only healthy if can serve requests."""
      try:
          db.session.execute(text('SELECT 1'))
          return jsonify({'status': 'ready'}), 200
      except:
          return jsonify({'status': 'not ready'}), 503
  ```
- [ ] Add metrics endpoint
  ```python
  @monitoring_bp.route('/metrics')
  def metrics():
      """
      Prometheus-compatible metrics endpoint.
      """
      from app.utils.security import (
          CSRF_TOKENS, API_RATE_LIMITS,
          FAILED_LOGIN_ATTEMPTS
      )
      
      metrics_data = {
          'csrf_tokens_active': len(CSRF_TOKENS),
          'rate_limited_ips': len(API_RATE_LIMITS),
          'failed_login_attempts': len(FAILED_LOGIN_ATTEMPTS),
          'admin_sessions_active': AdminSession.query.filter(
              AdminSession.expires_at > time.time()
          ).count(),
          'applications_pending': Application.query.filter_by(
              status='pending'
          ).count(),
          'applications_total': Application.query.count(),
          'forum_posts_total': ForumPost.query.count(),
      }
      
      return jsonify(metrics_data), 200
  ```
- [ ] Document health check endpoints
- [ ] Configure monitoring system to use endpoints
- [ ] Set up alerts for unhealthy status

**Estimated Effort:** 3-4 hours

**Benefits:**
- Better uptime monitoring
- Faster incident detection
- Load balancer integration

---

## Issue 22: Implement Request Tracing

**Labels:** `monitoring`, `priority:medium`, `observability`, `enhancement`

**Description:**
Add distributed tracing to track requests through the system, especially useful for debugging performance issues.

**Tasks:**
- [ ] Add correlation IDs to all requests
  ```python
  import uuid
  from flask import g
  
  @app.before_request
  def set_correlation_id():
      g.correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4()))
      g.start_time = time.time()
  
  @app.after_request
  def add_correlation_header(response):
      response.headers['X-Correlation-ID'] = g.correlation_id
      return response
  ```
- [ ] Log request/response with correlation ID
  ```python
  @app.after_request
  def log_request(response):
      duration_ms = (time.time() - g.start_time) * 1000
      
      logger.info("Request completed", extra={
          'correlation_id': g.correlation_id,
          'method': request.method,
          'path': request.path,
          'status': response.status_code,
          'duration_ms': round(duration_ms, 2),
          'ip': request.remote_addr,
          'user_agent': request.user_agent.string
      })
      
      return response
  ```
- [ ] Add timing instrumentation
  ```python
  from functools import wraps
  import time
  
  def timed(operation_name):
      def decorator(f):
          @wraps(f)
          def wrapper(*args, **kwargs):
              start = time.time()
              result = f(*args, **kwargs)
              duration = time.time() - start
              
              logger.debug(f"{operation_name} completed", extra={
                  'operation': operation_name,
                  'duration_ms': round(duration * 1000, 2),
                  'correlation_id': g.get('correlation_id')
              })
              
              return result
          return wrapper
      return decorator
  
  # Usage:
  @timed('database_query')
  def get_applications():
      return Application.query.all()
  ```
- [ ] Create performance dashboard query
  ```sql
  -- Slow queries (> 100ms)
  SELECT 
      path,
      AVG(duration_ms) as avg_duration,
      MAX(duration_ms) as max_duration,
      COUNT(*) as request_count
  FROM logs
  WHERE duration_ms > 100
  GROUP BY path
  ORDER BY avg_duration DESC;
  ```
- [ ] Document tracing implementation

**Estimated Effort:** 3-4 hours

---

## Issue 23: Set up Automated Performance Testing

**Labels:** `testing`, `performance`, `priority:low`, `enhancement`

**Description:**
Create automated load tests to validate system performance under stress.

**Tasks:**
- [ ] Install load testing tool
  ```bash
  pip install locust
  ```
- [ ] Create load test scenarios
  ```python
  # locustfile.py
  from locust import HttpUser, task, between
  
  class WebsiteUser(HttpUser):
      wait_time = between(1, 3)
      
      def on_start(self):
          # Get CSRF token
          response = self.client.get("/api/csrf-token")
          self.csrf_token = response.json()["csrf_token"]
      
      @task(3)
      def view_forum(self):
          self.client.get("/api/forum/posts")
      
      @task(1)
      def create_post(self):
          self.client.post("/api/forum/posts",
              json={
                  "title": "Load Test Post",
                  "content": "Test content",
                  "category": "general"
              },
              headers={"X-CSRF-Token": self.csrf_token}
          )
      
      @task(2)
      def view_applications(self):
          self.client.get("/bewerbungen")
  ```
- [ ] Create performance benchmarks
  ```python
  # Define acceptable performance thresholds
  PERFORMANCE_TARGETS = {
      'api_response_time_p95': 200,  # 95th percentile < 200ms
      'api_response_time_p99': 500,  # 99th percentile < 500ms
      'requests_per_second': 100,     # Handle 100 req/s
      'error_rate': 0.01,             # < 1% errors
  }
  ```
- [ ] Run baseline tests
  ```bash
  locust -f locustfile.py --headless -u 100 -r 10 --run-time 5m --host http://localhost:5000
  ```
- [ ] Add to CI pipeline (performance regression tests)
- [ ] Create performance report template
- [ ] Document performance characteristics

**Estimated Effort:** 4-5 hours

**Benefits:**
- Validate system under load
- Catch performance regressions
- Capacity planning data
