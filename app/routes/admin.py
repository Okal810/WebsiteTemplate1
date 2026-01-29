from flask import Blueprint, request, jsonify, current_app
import time
import secrets
import hmac  # Important for secure password comparison
from sqlalchemy import func

# Directly import models instead of old helper functions
from app.models import db, AdminSession, Blacklist, IPWarning, Warn
from app.utils.security import (
    validate_admin_session, get_client_ip, get_client_ip_hash, rate_limit
)
from app.utils.updates import save_update
from app.utils.admin_auth import ADMIN_CREDENTIALS

# In-Memory Cache for login attempts (sufficient for single-worker deployment)
FAILED_LOGIN_ATTEMPTS = {}

admin_bp = Blueprint('admin', __name__)

# ==================== AUTHENTICATION ====================

@admin_bp.route('/api/admin/session', methods=['POST'])
def create_admin_session():
    client_ip = get_client_ip()
    current_time = time.time()
    
    # 1. Brute-Force Protection Check
    if client_ip in FAILED_LOGIN_ATTEMPTS:
        attempt = FAILED_LOGIN_ATTEMPTS[client_ip]
        if current_time < attempt.get('lockout_until', 0):
            remaining = int(attempt['lockout_until'] - current_time)
            return jsonify({'error': f'Too many attempts. Wait {remaining}s.'}), 429

    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    # 2. Secure Comparison (Prevents Timing Attacks)
    # Standard '==' comparisons are measurably faster if the start matches.
    # compare_digest always takes the same amount of time.
    valid_user = hmac.compare_digest(username, ADMIN_CREDENTIALS['username'])
    valid_pass = hmac.compare_digest(password, ADMIN_CREDENTIALS['password'])

    if not (valid_user and valid_pass):
        # Fail Logic
        if client_ip not in FAILED_LOGIN_ATTEMPTS:
            FAILED_LOGIN_ATTEMPTS[client_ip] = {'count': 0, 'lockout_until': 0}
        
        FAILED_LOGIN_ATTEMPTS[client_ip]['count'] += 1
        
        if FAILED_LOGIN_ATTEMPTS[client_ip]['count'] >= 5:
            FAILED_LOGIN_ATTEMPTS[client_ip]['lockout_until'] = current_time + 900 # 15 Min
            return jsonify({'error': 'Too many attempts. 15 min lockout.'}), 429
            
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Success: Reset Fail Count
    if client_ip in FAILED_LOGIN_ATTEMPTS:
        del FAILED_LOGIN_ATTEMPTS[client_ip]
    
    # 3. Session Creation (DB)
    token = secrets.token_urlsafe(32)
    
    session = AdminSession(
        token=token,
        ip_hash=get_client_ip_hash(),
        expires_at=current_time + 1800  # 30 min
    )
    
    try:
        db.session.add(session)
        # Optional: Clean up old expired sessions
        AdminSession.query.filter(AdminSession.expires_at < current_time).delete()
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Database error during login'}), 500
    
    response = jsonify({'success': True})
    response.set_cookie(
        'admin_session_token', token,
        path='/', httponly=True, samesite='Lax', secure=False, max_age=1800
    )
    return response

@admin_bp.route('/api/admin/logout', methods=['POST'])
def logout_admin():
    token = request.cookies.get('admin_session_token')
    if token:
        # Only delete token if it exists
        AdminSession.query.filter_by(token=token).delete()
        db.session.commit()
            
    response = jsonify({'success': True})
    response.set_cookie('admin_session_token', '', path='/', expires=0)
    return response

# ==================== MODERATION (DB BASED) ====================

# Helper Decorator for Auth Check (DRY Principle)
def require_admin(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.cookies.get('admin_session_token')
        # Alternative Header Check for API Calls
        if not token: token = request.headers.get('X-Session-Token')
        
        if not validate_admin_session(token):
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/api/admin/blacklist', methods=['GET'])
@admin_bp.route('/api/moderation/blacklist', methods=['GET'])
@require_admin
@rate_limit(max_requests=60, window_seconds=60)
def get_blacklist():
    # OPTIMIZATION: Load directly from DB
    entries = Blacklist.query.order_by(Blacklist.timestamp.desc()).all()
    return jsonify([e.to_dict() for e in entries])

@admin_bp.route('/api/admin/blacklist', methods=['POST'])
@admin_bp.route('/api/moderation/blacklist', methods=['POST'])
@require_admin
def blacklist_ip():
    data = request.json
    ip_hash = data.get('ip_hash')
    
    if not ip_hash: return jsonify({'error': 'IP Hash missing'}), 400
    
    # Check if already exists
    existing = Blacklist.query.get(ip_hash)
    if existing:
        return jsonify({'success': True, 'message': 'Already banned'})

    duration = data.get('duration_hours')
    expires_at = (time.time() + (duration * 3600)) if duration else None

    entry = Blacklist(
        ip_hash=ip_hash,
        reason=data.get('reason', 'Manual Ban'),
        expires_at=expires_at,
        moderator='admin'
    )
    
    db.session.add(entry)
    db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/api/admin/blacklist/<ip_hash>', methods=['DELETE'])
@admin_bp.route('/api/moderation/blacklist/<ip_hash>', methods=['DELETE'])
@require_admin
def unblacklist_ip(ip_hash):
    entry = Blacklist.query.get(ip_hash)
    if entry:
        db.session.delete(entry)
        db.session.commit()
    return jsonify({'success': True})

@admin_bp.route('/api/admin/ip-warnings', methods=['GET'])
@admin_bp.route('/api/moderation/warnings', methods=['GET'])
@require_admin
def get_warnings():
    # OPTIMIZATION: Group warnings
    # We load all warnings and group them in Python
    warnings = IPWarning.query.order_by(IPWarning.timestamp.desc()).all()
    
    grouped = {}
    for w in warnings:
        if w.ip_hash not in grouped:
            grouped[w.ip_hash] = []
        grouped[w.ip_hash].append(w)
        
    result = []
    for ip, warns in grouped.items():
        result.append({
            'ip_hash': ip,
            'warning_count': len(warns),
            'recent_reasons': [x.reason for x in warns[:5]], # Last 5 reasons
            'last_warning': warns[0].timestamp
        })
        
    return jsonify({'success': True, 'warnings': result})

@admin_bp.route('/api/admin/warn', methods=['POST'])
@admin_bp.route('/api/moderation/warn', methods=['POST'])
@require_admin
def warn_ip():
    data = request.json
    ip_hash = data.get('ip_hash')
    
    if not ip_hash: return jsonify({'error': 'IP Hash missing'}), 400
    
    # 1. Create Warning
    warn = IPWarning(
        ip_hash=ip_hash,
        reason=data.get('reason', 'Manual Warning'),
        moderator='admin'
    )
    db.session.add(warn)
    
    # 2. Auto-Mod Check: How many warnings does he have NOW?
    # We count existing + 1 (the one we just added)
    count = IPWarning.query.filter_by(ip_hash=ip_hash).count() + 1
    
    auto_blocked = False
    if count >= 3:
        # Auto-Ban Logic
        existing_ban = Blacklist.query.get(ip_hash)
        if not existing_ban:
            ban = Blacklist(
                ip_hash=ip_hash,
                reason="Automatically banned (3 warnings)",
                expires_at=time.time() + 86400, # 24h
                moderator='auto_mod'
            )
            db.session.add(ban)
            auto_blocked = True
            
    db.session.commit()
    return jsonify({'success': True, 'warning_count': count, 'auto_blocked': auto_blocked})

@admin_bp.route('/api/admin/stats', methods=['GET'])
@admin_bp.route('/api/moderation/stats', methods=['GET'])
@require_admin
def get_stats():
    # OPTIMIZATION: Count queries are much faster than loading everything
    total_blacklisted = Blacklist.query.count()
    total_warned = db.session.query(IPWarning.ip_hash).distinct().count()
    
    # Active Bans (Expires > Now OR Expires is Null)
    now = time.time()
    active_blocks = Blacklist.query.filter(
        (Blacklist.expires_at == None) | (Blacklist.expires_at > now)
    ).count()
    
    return jsonify({
        'total_blacklisted': total_blacklisted,
        'total_warned_ips': total_warned,
        'active_blocks': active_blocks
    })

@admin_bp.route('/api/admin/updates', methods=['POST'])
@require_admin
def add_update_route():
    data = request.json
    content = data.get('content')
    tag = data.get('tag', 'UPDATE')
    color = data.get('color', '#3388ff')
    
    if not content: return jsonify({'error': 'Content missing'}), 400
    
    entry = save_update(content, tag, color)
    if entry:
        return jsonify({'success': True, 'entry': entry})
    return jsonify({'error': 'Failed to save'}), 500

# ==================== APPLICATION WARNS (User based) ====================

@admin_bp.route('/api/warns', methods=['GET', 'POST'])
@require_admin
def handle_user_warns():
    if request.method == 'GET':
        warns = Warn.query.order_by(Warn.timestamp.desc()).all()
        return jsonify([w.to_dict() for w in warns])
    
    if request.method == 'POST':
        data = request.json
        new_warn = Warn(
            id=str(int(time.time() * 1000)),
            roblox_user=data.get('roblox_user'),
            reason=data.get('reason'),
            timestamp=time.time()
        )
        db.session.add(new_warn)
        db.session.commit()
        return jsonify({'success': True, 'warn': new_warn.to_dict()})

@admin_bp.route('/api/warns/<id>', methods=['DELETE'])
@require_admin
def delete_user_warn(id):
    Warn.query.filter_by(id=id).delete()
    db.session.commit()
    return jsonify({'success': True})
