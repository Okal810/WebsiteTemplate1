from flask import Blueprint, request, jsonify, redirect, send_from_directory, current_app, render_template
import os
import time
from app.config import START_TIME
from app.utils.security import (
    get_client_ip, generate_csrf_token, CSRF_TOKEN_RATE_LIMITS, 
    cleanup_memory_stores, validate_admin_session, hash_ip
)
from app.utils.roblox import resolve_roblox_user_logic
from app.utils.moderation import is_ip_blacklisted, load_warnings
from app.models import db, Application, Shift
from app.utils.updates import load_updates

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return redirect('/startseite/startseite.html')

@main_bp.route('/panel')
def panel_redirect():
    return redirect('/bewerbungspanel/bewerbungspanel.html')

@main_bp.route('/server')
def server_redirect():
    return redirect('/server/server.html')

@main_bp.route('/team')
def team_redirect():
    return redirect('/team/team.html')

@main_bp.route('/api/status', methods=['GET'])
def server_status():
    # Only log verbose status checks on DEBUG to avoid flooding logs
    # current_app.logger.debug(f"Status check from {request.remote_addr}")
    uptime = time.time() - START_TIME
    app_count = Application.query.count()
    return jsonify({'status': 'online', 'uptime': uptime, 'applications': app_count, 'version': '2.7.0'})

@main_bp.route('/api/updates', methods=['GET'])
def get_updates():
    return jsonify(load_updates())

@main_bp.route('/api/csrf-token', methods=['GET'])
def get_csrf_token_route():
    client_ip = get_client_ip()
    current_time = time.time()
    
    if client_ip in CSRF_TOKEN_RATE_LIMITS:
       requests_in_window = [t for t in CSRF_TOKEN_RATE_LIMITS[client_ip] if current_time - t < 60]
       if len(requests_in_window) >= 10:
           current_app.logger.warning(f"CSRF Rate Limit exceeded for IP: {client_ip}")
           return jsonify({'error': 'Too many requests'}), 429
       CSRF_TOKEN_RATE_LIMITS[client_ip] = requests_in_window + [current_time]
    else:
       CSRF_TOKEN_RATE_LIMITS[client_ip] = [current_time]
    
    cleanup_memory_stores()
    token = generate_csrf_token()
    return jsonify({'token': token})

@main_bp.route('/api/roblox/user', methods=['POST'])
def resolve_roblox_user_route():
    data = request.json
    username = data.get('username')
    if not username: return jsonify({'error': 'Username required'}), 400
    
    current_app.logger.info(f"Resolving Roblox user: {username}")
    user, error = resolve_roblox_user_logic(username)
    
    if error: 
        current_app.logger.error(f"Failed to resolve Roblox user {username}: {error}")
        return jsonify({'error': error}), 404 if "not found" in error else 500
    
    return jsonify(user)

@main_bp.route('/api/warning-status', methods=['GET'])
def get_warning_status():
    """Check if the current IP has warnings or is blacklisted"""
    try:
        client_ip = get_client_ip()
        ip_hash = hash_ip(client_ip)
        
        # Check if IP is blacklisted
        is_banned, ban_info = is_ip_blacklisted(ip_hash)
        
        # Check if IP has warnings
        all_warnings = load_warnings()
        ip_warnings = all_warnings.get(ip_hash, [])
        warning_count = len(ip_warnings)
        
        return jsonify({
            'has_warnings': warning_count > 0,
            'warning_count': warning_count,
            'is_banned': is_banned,
            'ban_reason': ban_info.get('reason') if is_banned else None
        })
    except Exception as e:
        current_app.logger.error(f"Error checking warning status: {e}")
        return jsonify({'has_warnings': False, 'warning_count': 0, 'is_banned': False})


@main_bp.route('/api/shifts/start', methods=['POST'])
def start_shift():
    try:
        session_token = request.headers.get('X-Session-Token')
        if not validate_admin_session(session_token):
            current_app.logger.warning(f"Unauthorized shift start attempt from {request.remote_addr}")
            return jsonify({'error': 'Unauthorized'}), 401

        new_shift = Shift(
            id=str(int(time.time() * 1000)),
            start_time=time.time(),
            status='active'
        )
        
        db.session.add(new_shift)
        db.session.commit()
        
        current_app.logger.info(f"Shift started: {new_shift.id} by admin (IP {request.remote_addr})")
        return jsonify({'success': True, 'shift': new_shift.to_dict()})
    except Exception as e:
        current_app.logger.exception("Error starting shift")
        db.session.rollback()
        return jsonify({'error': 'Interner Fehler.'}), 500

@main_bp.route('/api/shifts/end', methods=['POST'])
def end_shift():
    try:
        session_token = request.headers.get('X-Session-Token')
        if not validate_admin_session(session_token):
            current_app.logger.warning(f"Unauthorized shift end attempt from {request.remote_addr}")
            return jsonify({'error': 'Unauthorized'}), 401

        req_data = request.json
        shift_id = req_data.get('id')
        
        shift = Shift.query.get(shift_id)
        if not shift:
            current_app.logger.warning(f"Shift not found for ending: {shift_id}")
            return jsonify({'error': 'Shift not found'}), 404
        
        shift.end_time = time.time()
        shift.duration = shift.end_time - shift.start_time
        shift.status = 'ended'
        
        db.session.commit()
        
        current_app.logger.info(f"Shift ended: {shift_id}. Duration: {shift.duration:.2f}s")
        return jsonify({'success': True, 'shift': shift.to_dict()})
    except Exception as e:
        current_app.logger.exception(f"Error ending shift {shift_id if 'shift_id' in locals() else 'unknown'}")
        db.session.rollback()
        return jsonify({'error': 'Interner Fehler.'}), 500

@main_bp.route('/<path:path>')
def serve_static(path):
    """Serve static files from the project root.
    This ensures that URLs like /startseite/startseite.html correctly map to the
    corresponding file on disk. If the file (or its .html variant) does not exist,
    a 404 response with a clear message is returned.
    """
    # Determine the absolute base directory of the project (one level above this file)
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    # Resolve the requested path relative to the base directory
    file_path = os.path.join(base_dir, path)
    # If the exact file exists, serve it
    if os.path.isfile(file_path):
        return send_from_directory(base_dir, path)
    # If a .html version exists, serve that
    html_path = file_path + '.html'
    if os.path.isfile(html_path):
        rel_html = os.path.relpath(html_path, base_dir)
        return send_from_directory(base_dir, rel_html)
    # Otherwise, return a clear 404
    return render_template('404.html'), 404

@main_bp.app_errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@main_bp.app_errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500
