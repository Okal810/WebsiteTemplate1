"""
Application Routes - Refactored

Handles application submissions and admin management.
Uses ApplicationDTO for clean data handling and helper functions for maintainability.
"""

from flask import Blueprint, request, jsonify
import time
import re
from uuid import uuid4
from typing import Optional, Tuple, Dict, Any

from app.config import DATA_FILE
from app.utils.security import (
    get_client_ip_hash, validate_csrf_token, require_admin,
    RATE_LIMITS, limit_dict_size
)
from app.utils.moderation import (
    is_ip_blacklisted, add_ip_warning, check_content_repetition,
    looks_like_spam, check_duplicate_fields, check_semantic_similarity
)
from app.utils.sanitize import sanitize_input
from app.utils.notifications import send_discord_notification
from app.utils.validation_config import ValidationConfig
from app.models import db, Application, IPWarning

applications_bp = Blueprint('applications', __name__)


# =============================================================================
# APPLICATION DATA TRANSFER OBJECT
# =============================================================================

class ApplicationDTO:
    """
    Data Transfer Object for application data.
    
    Handles sanitization, validation, and conversion to database model.
    Single source of truth for application data handling.
    """
    
    def __init__(self, request_data: Dict[str, Any]):
        """Initialize with raw request data and sanitize."""
        self.application_type = request_data.get('applicationType')
        self.roblox_user = sanitize_input(request_data.get('roblox_user', ''))
        self.discord_name = sanitize_input(request_data.get('discord_name', ''))
        self.age = request_data.get('age')
        self.about_me = sanitize_input(request_data.get('about_me', ''))
        self.daily_time = sanitize_input(request_data.get('daily_time', ''))
        self.motivation = sanitize_input(request_data.get('motivation', '')) if 'motivation' in request_data else None
        self.timestamp = request_data.get('timestamp', time.time())
        
        # Bot detection fields
        self.website_url = request_data.get('website_url')  # Honeypot
        self.load_time = request_data.get('load_time', 0)
        self.pasted_fields = request_data.get('pasted_fields', [])
    
    def validate(self) -> Optional[str]:
        """
        Validate all application data.
        
        Returns:
            Error message if validation fails, None if valid
        """
        cfg = ValidationConfig
        
        # Age validation
        try:
            age = int(self.age) if self.age else 0
            if age < cfg.MIN_AGE or age > cfg.MAX_AGE:
                return f"Invalid age ({cfg.MIN_AGE}-{cfg.MAX_AGE})."
        except (ValueError, TypeError):
            return "Age must be a number."
        
        # Roblox username
        if len(self.roblox_user) < cfg.MIN_ROBLOX_NAME_LENGTH or len(self.roblox_user) > cfg.MAX_ROBLOX_NAME_LENGTH:
            return f"Roblox name must be {cfg.MIN_ROBLOX_NAME_LENGTH}-{cfg.MAX_ROBLOX_NAME_LENGTH} characters long."
        
        if not re.match(cfg.ROBLOX_NAME_PATTERN, self.roblox_user):
            return "Roblox name contains invalid characters (only letters, numbers, underscores)."
        
        if looks_like_spam(self.roblox_user):
            return "Please enter a real Roblox name."
        
        # Discord username
        if len(self.discord_name) < cfg.MIN_DISCORD_NAME_LENGTH or len(self.discord_name) > cfg.MAX_DISCORD_NAME_LENGTH:
            return f"Discord name must be {cfg.MIN_DISCORD_NAME_LENGTH}-{cfg.MAX_DISCORD_NAME_LENGTH} characters long."
        
        if looks_like_spam(self.discord_name):
            return "Please enter a real Discord name."
        
        # About me
        if len(self.about_me) < cfg.MIN_ABOUT_ME_LENGTH:
            return "Please write a bit more about yourself."
        
        if len(self.about_me) > cfg.MAX_ABOUT_ME_LENGTH:
            return f"About me is too long (Max {cfg.MAX_ABOUT_ME_LENGTH} characters)."
        
        if looks_like_spam(self.about_me):
            return "Your text 'About me' was recognized as spam. Please write proper sentences."
        
        # Motivation (optional field)
        if self.motivation:
            if len(self.motivation) > cfg.MAX_ABOUT_ME_LENGTH:
                return f"Motivation is too long (Max {cfg.MAX_ABOUT_ME_LENGTH} characters)."
            if looks_like_spam(self.motivation):
                return "Your text in 'motivation' was recognized as spam."
        
        return None
    
    def to_db_model(self, app_id: str, ip_hash: str) -> Application:
        """Convert DTO to database model."""
        return Application(
            id=app_id,
            application_type=self.application_type,
            roblox_user=self.roblox_user,
            discord_name=self.discord_name,
            age=self.age,
            about_me=self.about_me,
            daily_time=self.daily_time,
            motivation=self.motivation,
            ip_hash=ip_hash,
            timestamp=self.timestamp,
            status='pending'
        )
    
    def to_sanitized_dict(self) -> Dict[str, Any]:
        """Return sanitized data as dictionary for duplicate checking."""
        return {
            'application_type': self.application_type,
            'roblox_user': self.roblox_user,
            'discord_name': self.discord_name,
            'age': self.age,
            'about_me': self.about_me,
            'daily_time': self.daily_time,
            'motivation': self.motivation
        }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def perform_security_checks(ip_hash: str) -> Tuple[bool, Optional[Dict]]:
    """
    Perform IP blacklist and CSRF validation.
    
    Returns:
        Tuple of (is_blocked, error_response or None)
    """
    # Check IP blacklist
    is_blocked, block_info = is_ip_blacklisted(ip_hash)
    
    if is_blocked:
        if block_info.get('expires_at'):
            hours_left = max(1, int((block_info['expires_at'] - time.time()) / 3600))
            return True, {
                'error': f'Your IP is temporarily blocked. Reason: {block_info.get("reason", "Rule violation")}. Block expires in approx. {hours_left} hours.'
            }
        else:
            return True, {
                'error': f'Your IP is permanently blocked. Reason: {block_info.get("reason", "Serious violation")}'
            }
    
    # Validate CSRF token
    csrf_token = request.headers.get('X-CSRF-Token')
    if not validate_csrf_token(csrf_token):
        return True, {'error': 'Access denied (Invalid or expired CSRF token).'}
    
    # NOTE: X-Requested-With header check removed.
    # This header provides no real security as it can be trivially spoofed by attackers.
    # Real protection comes from CSRF tokens and rate limiting.
    # For actual API authentication, consider implementing JWT or API keys.
    
    return False, None


def check_rate_limit(client_ip: str) -> Tuple[bool, Optional[Dict]]:
    """
    Check if client is rate limited.
    
    Returns:
        Tuple of (is_limited, error_response or None)
    """
    current_time = time.time()
    
    if client_ip in RATE_LIMITS:
        last_request_time = RATE_LIMITS[client_ip]
        if current_time - last_request_time < ValidationConfig.RATE_LIMIT_SECONDS:
            return True, {'error': 'Please wait a minute before submitting again.'}
    
    # Cleanup old entries (moved to start to prevent unbounded growth)
    limit_dict_size(RATE_LIMITS, 10000)
    
    return False, None


def perform_bot_detection(dto: ApplicationDTO, ip_hash: str) -> Tuple[bool, Optional[Dict]]:
    """
    Perform honeypot and timing-based bot detection.
    
    Returns:
        Tuple of (is_bot, error_response or None)
    """
    current_time = time.time()
    
    # Honeypot check
    if dto.website_url:
        add_ip_warning(ip_hash, "Honeypot filled (Bot-Detection)")
        return True, {'error': 'Access denied (Automated detection).'}
    
    # Submit delay check
    if dto.load_time > 0:
        if current_time - (dto.load_time / 1000) < ValidationConfig.MIN_SUBMIT_DELAY_SECONDS:
            add_ip_warning(ip_hash, "Submit too fast (Bot-Detection)")
            return True, {'error': 'Please take a bit more time to fill it out.'}
    
    return False, None


def check_content_quality(dto: ApplicationDTO, ip_hash: str) -> Tuple[bool, Optional[Dict]]:
    """
    Check for content repetition, paste detection, and semantic similarity.
    
    Returns:
        Tuple of (has_issues, error_response or None)
    """
    about_me = dto.about_me.strip()
    
    # Content repetition check
    if about_me:
        repetition, auto_blocked = check_content_repetition(ip_hash, about_me)
        if repetition or auto_blocked:
            return True, {'error': 'Application rejected: Duplicate content detected.'}
    
    # Paste detection warning
    if 'about_me' in dto.pasted_fields:
        if len(about_me) > ValidationConfig.PASTE_WARNING_THRESHOLD:
            add_ip_warning(ip_hash, "Extreme Paste detected in About-Me")
    
    # Semantic similarity check
    is_similar, field_name = check_semantic_similarity(about_me)
    if is_similar:
        return True, {'error': f'Your answer in "{field_name}" is too similar to an existing application. Please write your own text.'}
    
    # Duplicate fields check
    has_duplicates, duplicate_fields = check_duplicate_fields(dto.to_sanitized_dict())
    if has_duplicates:
        return True, {'error': 'Please write different texts in the various fields.'}
    
    return False, None


def save_application(dto: ApplicationDTO, ip_hash: str) -> Tuple[bool, Dict]:
    """
    Save application to database and send notification.
    
    Returns:
        Tuple of (success, response_dict)
    """
    try:
        # Generate UUID (guaranteed unique, no race conditions)
        app_id = str(uuid4())
        
        # Create and save application
        application = dto.to_db_model(app_id, ip_hash)
        db.session.add(application)
        db.session.commit()
        
        # Rate limit update only after successful commit
        RATE_LIMITS[request.remote_addr] = time.time()
        
        # Send notification (non-blocking)
        send_discord_notification(application.to_dict())
        
        return True, {'success': True}
        
    except Exception as e:
        db.session.rollback()
        raise


# =============================================================================
# PUBLIC APPLICATION ENDPOINT
# =============================================================================

@applications_bp.route('/api/applications', methods=['POST'])
def add_application():
    """
    Submit a new application.
    
    Performs in order:
    1. Security checks (IP blacklist, CSRF)
    2. Rate limiting
    3. Bot detection (honeypot, timing)
    4. Data validation
    5. Content quality checks
    6. Database persistence
    """
    try:
        ip_hash = get_client_ip_hash()
        
        # 1. Security checks
        is_blocked, error_response = perform_security_checks(ip_hash)
        if is_blocked:
            status = 403
            return jsonify(error_response), status
        
        # 2. Rate limiting
        is_limited, error_response = check_rate_limit(request.remote_addr)
        if is_limited:
            return jsonify(error_response), 429
        
        # 3. Create DTO and perform bot detection
        dto = ApplicationDTO(request.json)
        
        is_bot, error_response = perform_bot_detection(dto, ip_hash)
        if is_bot:
            status = 403 if 'Automated' in error_response.get('error', '') else 400
            return jsonify(error_response), status
        
        # 4. Validate application data
        validation_error = dto.validate()
        if validation_error:
            return jsonify({'error': f'Validation error: {validation_error}'}), 400
        
        # 5. Content quality checks
        has_issues, error_response = check_content_quality(dto, ip_hash)
        if has_issues:
            return jsonify(error_response), 400
        
        # 6. Save to database
        success, response = save_application(dto, ip_hash)
        return jsonify(response)
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An internal error occurred.'}), 500


# =============================================================================
# ADMIN ENDPOINTS (Protected with @require_admin decorator)
# =============================================================================

@applications_bp.route('/api/applications', methods=['GET'])
@require_admin
def get_applications():
    """Get paginated list of applications with optional filtering."""
    try:
        # Query parameters
        page = request.args.get('page', 1, type=int)
        limit = request.args.get('limit', 20, type=int)
        status = request.args.get('status', '', type=str)
        search = request.args.get('q', '', type=str)
        
        # Base query
        query = Application.query

        # Filter by status
        if status and status != 'all':
            query = query.filter_by(status=status)
        
        # Search (case-insensitive)
        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Application.roblox_user.ilike(search_term)) |
                (Application.discord_name.ilike(search_term)) |
                (Application.id.like(search_term))
            )

        # Sorting: Newest first (uses timestamp index)
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
@require_admin
def get_application(id):
    """Get a single application with moderation info."""
    try:
        application = Application.query.get(id)
        if not application:
            return jsonify({'error': 'Not found'}), 404
            
        app_dict = application.to_dict()
        
        # Add moderation info
        is_banned, ban_info = is_ip_blacklisted(application.ip_hash)
        app_dict['is_banned'] = is_banned
        app_dict['ban_info'] = ban_info if is_banned else None
        
        warnings = IPWarning.query.filter_by(ip_hash=application.ip_hash).order_by(IPWarning.timestamp.desc()).all()
        app_dict['warnings'] = [w.to_dict() for w in warnings]
        
        return jsonify(app_dict)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@applications_bp.route('/api/applications/<id>', methods=['PUT'])
@require_admin
def update_application(id):
    """Update application status."""
    try:
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
@require_admin
def delete_application(id):
    """Delete a single application."""
    try:
        application = Application.query.get(id)
        if application:
            db.session.delete(application)
            db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An internal error occurred.'}), 500


@applications_bp.route('/api/applications', methods=['DELETE'])
@require_admin
def clear_applications():
    """Delete all applications."""
    try:
        Application.query.delete()
        db.session.commit()
        return jsonify({'success': True})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An internal error occurred.'}), 500
