import secrets
import hashlib
import time
from flask import request
from app.config import (
    IP_HASH_SALT, MAX_CSRF_TOKENS, MAX_ADMIN_SESSIONS, 
    MAX_FAILED_LOGINS, MAX_RATE_LIMITS
)

# In-memory stores (Admin Sessions now in DB)
CSRF_TOKENS = {} # token: {ip_hash, timestamp}
FAILED_LOGIN_ATTEMPTS = {} # ip: {count, lockout_until}
CSRF_TOKEN_RATE_LIMITS = {} # ip: [timestamps]
RATE_LIMITS = {} # ip: timestamp
API_RATE_LIMITS = {} # ip: [timestamps] for general API rate limiting

def get_client_ip():
    """Gets client IP safely (supports proxies if configured)"""
    # If ProxyFix is active (in app/__init__.py), remote_addr provides the real IP
    return request.remote_addr

def hash_ip(ip_address):
    """Secure hashing of IP addresses for data protection"""
    if not ip_address:
        return None
    return hashlib.sha256(f"{ip_address}:{IP_HASH_SALT}".encode()).hexdigest()[:16]

def get_client_ip_hash():
    """Gets and hashes client IP"""
    return hash_ip(get_client_ip())

def limit_dict_size(d, max_size):
    """Limits the size of a dict (removes oldest entries based on value or keys)."""
    if len(d) > max_size:
        # For dicts with timestamps as values (or in a sub-dict), we sort accordingly
        try:
            # Attempt to sort by 'timestamp' in sub-dicts or directly by value
            keys_to_remove = sorted(d.keys(), key=lambda k: d[k].get('timestamp', 0) if isinstance(d[k], dict) else d[k])
        except:
            # Fallback: Alphabetical (not ideal, but better than nothing on errors)
            keys_to_remove = list(d.keys())
        
        for k in keys_to_remove[:len(d) - max_size]:
            del d[k]

def generate_csrf_token():
    """Generate a new CSRF token bound to the client's IP"""
    token = secrets.token_urlsafe(32)
    ip_hash = get_client_ip_hash()
    current_time = time.time()
    
    CSRF_TOKENS[token] = {
        'ip_hash': ip_hash,
        'timestamp': current_time
    }
    
    cleanup_memory_stores()
    limit_dict_size(CSRF_TOKENS, MAX_CSRF_TOKENS)
    return token

def validate_csrf_token(token):
    """Validate CSRF token and check IP binding"""
    if not token or token not in CSRF_TOKENS:
        return False
    
    entry = CSRF_TOKENS[token]
    ip_hash = get_client_ip_hash()
    
    # Expiry Check (1 hour)
    if time.time() - entry['timestamp'] > 3600:
        del CSRF_TOKENS[token]
        return False
    
    # IP Binding Check
    if entry['ip_hash'] != ip_hash:
        return False
        
    return True

def validate_admin_session(token):
    """Validate admin panel session token (Persistent via DB)"""
    if not token:
        return False
        
    try:
        from app.models import AdminSession, db
        session = db.session.get(AdminSession, token)
        
        if not session:
            return False
            
        current_time = time.time()
        
        # Expiry Check
        if current_time > session.expires_at:
            db.session.delete(session)
            db.session.commit()
            return False
            
        # IP Binding disabled for local dev (localhost vs LAN IP mismatch)
        # To re-enable: uncomment below
        # ip_hash = get_client_ip_hash()
        # if session.ip_hash != ip_hash:
        #     return False
            
        return True
    except Exception as e:
        print(f"Session validation error: {e}")
        return False


def rate_limit(max_requests=10, window_seconds=60, authenticated_multiplier=5):
    """
    Adaptive rate limiting decorator with different limits for authenticated users.
    
    Args:
        max_requests: Base maximum requests for unauthenticated users
        window_seconds: Time window in seconds
        authenticated_multiplier: Multiplier for authenticated admin limits (default: 5x)
    
    Returns:
        Decorator function that enforces adaptive rate limiting
    
    Example:
        @rate_limit(max_requests=10, window_seconds=60, authenticated_multiplier=5)
        # Unauthenticated: 10 req/min
        # Authenticated Admin: 50 req/min
    """
    from functools import wraps
    from flask import jsonify, request
    
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            client_ip = get_client_ip()
            current_time = time.time()
            
            # Check if user is authenticated (has valid admin session)
            session_token = request.cookies.get('admin_session_token')
            is_authenticated = validate_admin_session(session_token)
            
            # Adaptive limit: Higher for authenticated admins
            effective_limit = max_requests * authenticated_multiplier if is_authenticated else max_requests
            
            # Initialize tracking for this IP
            if client_ip not in API_RATE_LIMITS:
                API_RATE_LIMITS[client_ip] = []
            
            # Remove timestamps outside the current window
            API_RATE_LIMITS[client_ip] = [
                ts for ts in API_RATE_LIMITS[client_ip] 
                if current_time - ts < window_seconds
            ]
            
            # Check if limit exceeded
            if len(API_RATE_LIMITS[client_ip]) >= effective_limit:
                return jsonify({
                    'error': 'Rate limit exceeded. Try again later.',
                    'limit': effective_limit,
                    'window_seconds': window_seconds
                }), 429
            
            # Add current request timestamp
            API_RATE_LIMITS[client_ip].append(current_time)
            
            # Cleanup: Limit memory usage
            if len(API_RATE_LIMITS) > 1000:
                # Remove oldest IPs
                sorted_ips = sorted(
                    API_RATE_LIMITS.items(), 
                    key=lambda x: max(x[1]) if x[1] else 0
                )
                for ip, _ in sorted_ips[:200]:
                    del API_RATE_LIMITS[ip]
            
            return f(*args, **kwargs)
        return wrapped
    return decorator

def cleanup_memory_stores():
    """Clean up in-memory stores to prevent memory DoS"""
    current_time = time.time()
    
    # 1. CSRF Tokens
    expired_csrf = [t for t, data in CSRF_TOKENS.items() if current_time - data['timestamp'] > 3600]
    for t in expired_csrf: del CSRF_TOKENS[t]
    
    # 2. Admin Sessions (Handled by DB now)
    # expired_sessions = [t for t, data in ADMIN_SESSION_TOKENS.items() if current_time - data['timestamp'] > 1800]
    # for t in expired_sessions: del ADMIN_SESSION_TOKENS[t]
    
    # 3. Rate Limits Cleanup (older than 10 mins)
    expired_rate = [ip for ip, ts in RATE_LIMITS.items() if current_time - ts > 600]
    for ip in expired_rate: del RATE_LIMITS[ip]
    
    # 4. Failed Logins Cleanup (older than 1 hour)
    expired_failed = [ip for ip, data in FAILED_LOGIN_ATTEMPTS.items() if current_time - data.get('lockout_until', 0) > 3600]
    for ip in expired_failed: del FAILED_LOGIN_ATTEMPTS[ip]

    # Enforcement of global limits
    limit_dict_size(CSRF_TOKENS, MAX_CSRF_TOKENS)
    # limit_dict_size(ADMIN_SESSION_TOKENS, MAX_ADMIN_SESSIONS)

    limit_dict_size(FAILED_LOGIN_ATTEMPTS, MAX_FAILED_LOGINS)
    limit_dict_size(RATE_LIMITS, MAX_RATE_LIMITS)
    limit_dict_size(CSRF_TOKEN_RATE_LIMITS, 1000) # Fixed limit for token requests
