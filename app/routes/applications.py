from flask import Blueprint, request, jsonify
import time
import re
from app.config import DATA_FILE
from app.utils.security import get_client_ip_hash, validate_csrf_token, validate_admin_session, RATE_LIMITS, limit_dict_size
from app.utils.moderation import (
    is_ip_blacklisted, add_ip_warning, check_content_repetition, 
    looks_like_spam, check_duplicate_fields, check_semantic_similarity
)
from app.utils.sanitize import sanitize_input
from app.utils.notifications import send_discord_notification
from app.models import db, Application, IPWarning

applications_bp = Blueprint('applications', __name__)

def validate_application_data(data):
    # Check age
    try:
        age = int(data.get('age', 0))
        if age < 1 or age > 99:
            return "Invalid age (1-99)."
    except:
        return "Age must be a number."

    # Roblox User
    roblox_user = data.get('roblox_user', '').strip()
    if len(roblox_user) < 3 or len(roblox_user) > 20:
        return "Roblox name must be 3-20 characters long."
    
    if not re.match(r'^[a-zA-Z0-9_]+$', roblox_user):
        return "Roblox name contains invalid characters (only letters, numbers, underscores)."
        
    if looks_like_spam(roblox_user):
        return "Please enter a real Roblox name."

    # Discord Name
    discord_name = data.get('discord_name', '').strip()
    if len(discord_name) < 2 or len(discord_name) > 32:
        return "Discord name must be 2-32 characters long."
        
    if looks_like_spam(discord_name):
        return "Please enter a real Discord name."

    # Text fields minimum length
    about_me = data.get('about_me', '').strip()
    if len(about_me) < 10:
         return "Please write a bit more about yourself."
         
    if looks_like_spam(about_me):
        return "Your text 'About me' was recognized as spam. Please write proper sentences."
        
    for field in ['motivation', 'why_us', 'strengths', 'weaknesses']:
        if field in data:
            val = str(data[field])
            if looks_like_spam(val):
                return f"Your text in '{field}' was recognized as spam."

    return None

@applications_bp.route('/api/applications', methods=['GET'])
def get_applications():
    try:
        session_token = request.cookies.get('admin_session_token')
        if not validate_admin_session(session_token):
             return jsonify({'error': 'Unauthorized'}), 401

        # Query parameters
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        status = request.args.get('status', '', type=str)
        search = request.args.get('q', '', type=str) # Search query
        
        # Base query
        query = Application.query

        # Filter by status
        if status and status != 'all':
            query = query.filter_by(status=status)
        
        # Search (Case-insensitive search in roblox_user or discord_name)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Application.roblox_user.ilike(search_term)) | 
                (Application.discord_name.ilike(search_term)) |
                (Application.id.like(search_term))
            )

        # Sorting: Newest first (uses index)
        query = query.order_by(Application.timestamp.desc())

        # Pagination
        pagination = query.paginate(page=page, per_page=limit, error_out=False)
        
        return jsonify({
            'apps': [app.to_dict() for app in pagination.items],
            'meta': {
                'total': pagination.total,
                'pages': pagination.pages,
                'current_page': page,
                'limit': limit
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@applications_bp.route('/api/applications/<id>', methods=['GET'])
def get_application(id):
    try:
        session_token = request.cookies.get('admin_session_token')
        if not validate_admin_session(session_token):
             return jsonify({'error': 'Unauthorized'}), 401

        application = Application.query.get(id)
        if not application:
            return jsonify({'error': 'Not found'}), 404
            
        app_dict = application.to_dict()
        
        # Moderation info
        is_banned, ban_info = is_ip_blacklisted(application.ip_hash)
        app_dict['is_banned'] = is_banned
        app_dict['ban_info'] = ban_info if is_banned else None
        
        warnings = IPWarning.query.filter_by(ip_hash=application.ip_hash).order_by(IPWarning.timestamp.desc()).all()
        app_dict['warnings'] = [w.to_dict() for w in warnings]
        
        return jsonify(app_dict)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@applications_bp.route('/api/applications', methods=['POST'])
def add_application():
    try:
        ip_hash = get_client_ip_hash()
        is_blocked, block_info = is_ip_blacklisted(ip_hash)
        
        if is_blocked:
            if block_info.get('expires_at'):
                hours_left = max(1, int((block_info['expires_at'] - time.time()) / 3600))
                return jsonify({
                    'error': f'Your IP is temporarily blocked. Reason: {block_info.get("reason", "Rule violation")}. Block expires in approx. {hours_left} hours.'
                }), 403
            else:
                return jsonify({
                    'error': f'Your IP is permanently blocked. Reason: {block_info.get("reason", "Serious violation")}'
                }), 403

        csrf_token = request.headers.get('X-CSRF-Token')
        if not validate_csrf_token(csrf_token):
            return jsonify({'error': 'Access denied (Invalid or expired CSRF token).'}), 403
        
        if request.headers.get('X-Requested-With') != 'DRP-Client':
            return jsonify({'error': 'Access denied (Invalid Header).'}), 403

        client_ip = request.remote_addr
        current_time = time.time()
        
        if client_ip in RATE_LIMITS:
            last_request_time = RATE_LIMITS[client_ip]
            if current_time - last_request_time < 60:
                warning_count, auto_blocked = add_ip_warning(ip_hash, "Rate-Limit Abuse (Spamming Applications)")
                if auto_blocked:
                    return jsonify({'error': 'Too many requests. Your IP has been blocked.'}), 403
                return jsonify({'error': 'Please wait a minute.'}), 429
        

        limit_dict_size(RATE_LIMITS, 10000)
        # Rate limit update moved to end of function


        new_app = request.json
        
        # 1. Honeypot check
        if new_app.get('website_url'):
            add_ip_warning(ip_hash, "Honeypot filled (Bot-Detection)")
            return jsonify({'error': 'Access denied (Automated detection).'}), 403
            
        # 2. Submit delay check (Min. 5 seconds)
        load_time = new_app.get('load_time', 0)
        if load_time > 0:
            if current_time - (load_time / 1000) < 5:
                add_ip_warning(ip_hash, "Submit too fast (Bot-Detection)")
                return jsonify({'error': 'Please take a bit more time to fill it out.'}), 400
        
        sanitized_data = {
            'application_type': new_app.get('applicationType'),
            'roblox_user': sanitize_input(new_app.get('roblox_user', '')),
            'discord_name': sanitize_input(new_app.get('discord_name', '')),
            'age': new_app.get('age'),
            'about_me': sanitize_input(new_app.get('about_me', '')),
            'daily_time': sanitize_input(new_app.get('daily_time', '')),
            'motivation': sanitize_input(new_app.get('motivation', '')) if 'motivation' in new_app else None,
            'ip_hash': ip_hash,
            'timestamp': new_app.get('timestamp', time.time())
        }
        
        # Hard length limits (DoS protection)
        if len(sanitized_data['about_me']) > 5000:
             return jsonify({'error': 'About me is too long (Max 5000 characters).'}), 400
        
        if sanitized_data.get('motivation') and len(sanitized_data['motivation']) > 5000:
             return jsonify({'error': 'Motivation is too long (Max 5000 characters).'}), 400

        about_me = sanitized_data.get('about_me', '').strip()
        if about_me:
            repetition, auto_blocked = check_content_repetition(ip_hash, about_me)
            if auto_blocked:
                return jsonify({'error': 'Application rejected: Automatic block due to repetitive spam.'}), 403

        if len(about_me) < 15:
            add_ip_warning(ip_hash, "Very short application")
            auto_blocked = False
        elif looks_like_spam(about_me):
            warning_count, auto_blocked = add_ip_warning(ip_hash, "Spam in 'About me'")
        elif looks_like_spam(sanitized_data.get('motivation', '')):
            warning_count, auto_blocked = add_ip_warning(ip_hash, "Spam in 'Motivation'")
        else:
            auto_blocked = False

        if auto_blocked:
            return jsonify({'error': 'Application rejected: Automatic block.'}), 403

        # For validation, we need the format with roblox_user etc.
        validation_data = {
            'roblox_user': sanitized_data['roblox_user'],
            'discord_name': sanitized_data['discord_name'],
            'age': sanitized_data['age'],
            'about_me': sanitized_data['about_me'],
            'motivation': sanitized_data.get('motivation'),
            'pasted_fields': new_app.get('pasted_fields', [])
        }
        
        # 3. Paste detection warning
        if 'about_me' in validation_data.get('pasted_fields', []):
            # We don't block immediately, but give a warning in the log / note
            # Or we could be stricter if the text is very long
            if len(validation_data['about_me']) > 500:
                add_ip_warning(ip_hash, "Extreme Paste detected in About-Me")
        
        # 4. Semantic similarity check (Copy-Paste from others)
        is_similar, field_name = check_semantic_similarity(validation_data['about_me'])
        if is_similar:
             return jsonify({'error': f'Your answer in "{field_name}" is too similar to an existing application. Please write your own text.'}), 400

        error_msg = validate_application_data(validation_data)
        if error_msg:
            if "Spam" in error_msg:
                add_ip_warning(ip_hash, f"Spam validation error: {error_msg}")
            return jsonify({'error': f'Validation error: {error_msg}'}), 400
        
        # Server-side duplicate field check
        has_duplicates, duplicate_fields = check_duplicate_fields(sanitized_data)
        if has_duplicates:
            add_ip_warning(ip_hash, f"Duplicate Fields: {duplicate_fields}")
            return jsonify({'error': 'Please write different texts in the various fields.'}), 400
        
        # Generate ID
        app_id = str(int(time.time() * 1000))
        
        # Save new application in DB
        application = Application(
            id=app_id,
            application_type=sanitized_data['application_type'],
            roblox_user=sanitized_data['roblox_user'],
            discord_name=sanitized_data['discord_name'],
            age=sanitized_data['age'],
            about_me=sanitized_data['about_me'],
            daily_time=sanitized_data.get('daily_time'),
            motivation=sanitized_data.get('motivation'),
            ip_hash=ip_hash,
            timestamp=sanitized_data['timestamp'],
            status='pending'
        )
        db.session.add(application)
        db.session.commit()
            
        
        # Rate limit update only on success
        RATE_LIMITS[client_ip] = time.time()
        
        send_discord_notification(application.to_dict())
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An internal error occurred.'}), 500

@applications_bp.route('/api/applications/<id>', methods=['PUT'])
def update_application(id):
    try:
        session_token = request.cookies.get('admin_session_token')
        if not validate_admin_session(session_token):
            return jsonify({'error': 'Unauthorized'}), 401
        
        update_data = request.json
        allowed_fields = {'status'}
        filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}
        
        if 'status' in filtered_data and filtered_data['status'] not in ['pending', 'accepted', 'rejected']:
            return jsonify({'error': 'Invalid status value'}), 400
        
        application = Application.query.get(id)
        if not application:
            return jsonify({'error': 'Application not found'}), 404
        
        if 'status' in filtered_data:
            application.status = filtered_data['status']
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An internal error occurred.'}), 500

@applications_bp.route('/api/applications/<id>', methods=['DELETE'])
def delete_application(id):
    try:
        session_token = request.cookies.get('admin_session_token')
        if not validate_admin_session(session_token):
            return jsonify({'error': 'Unauthorized'}), 401
        
        application = Application.query.get(id)
        if application:
            db.session.delete(application)
            db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An internal error occurred.'}), 500

@applications_bp.route('/api/applications', methods=['DELETE'])
def clear_applications():
    try:
        session_token = request.cookies.get('admin_session_token')
        if not validate_admin_session(session_token):
            return jsonify({'error': 'Unauthorized'}), 401
        
        Application.query.delete()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An internal error occurred.'}), 500
