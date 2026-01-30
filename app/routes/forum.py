"""
Forum Routes - Refactored

Handles forum posts and comments with proper rate limiting and security.
Rate limit is only applied AFTER successful validation to prevent penalizing
users for invalid submissions.
"""

from flask import Blueprint, request, jsonify, redirect
import time
from uuid import uuid4
from typing import Tuple, Optional, Dict

from app.config import MAX_FORUM_POST_RATE_LIMITS, MAX_FORUM_COMMENT_RATE_LIMITS
from app.utils.security import (
    get_client_ip_hash, validate_csrf_token, validate_admin_session,
    require_admin, limit_dict_size
)
from app.utils.moderation import is_ip_blacklisted, add_ip_warning, check_content_repetition, looks_like_spam
from app.utils.sanitize import sanitize_input
from app.models import db, ForumPost, ForumComment

forum_bp = Blueprint('forum', __name__)

# =============================================================================
# IN-MEMORY RATE LIMITS
# =============================================================================
# NOTE: These rate limits are stored in-memory and will be lost on server restart.
# For production multi-server deployments, consider using Redis:
#
# Redis Implementation (uncomment when Redis is enabled in security.py):
# from app.utils.security import redis_client
#
# def check_forum_rate_limit(ip: str, limit_seconds: int = 30) -> bool:
#     if redis_client:
#         key = f"forum_ratelimit:{ip}"
#         if redis_client.exists(key):
#             return False
#         redis_client.setex(key, limit_seconds, "1")
#         return True
#     # Fallback to in-memory
#     ...

FORUM_POST_RATE_LIMITS = {}
FORUM_COMMENT_RATE_LIMITS = {}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def check_rate_limit(rate_dict: dict, max_size: int, client_ip: str, limit_seconds: int = 30) -> Tuple[bool, Optional[Dict]]:
    """
    Check rate limit but DON'T update it yet.
    Returns (is_limited, error_response or None)
    """
    current_time = time.time()
    
    if client_ip in rate_dict:
        if current_time - rate_dict[client_ip] < limit_seconds:
            return True, {'error': f'Please wait {limit_seconds} seconds.'}
    
    return False, None


def apply_rate_limit(rate_dict: dict, max_size: int, client_ip: str) -> None:
    """Apply rate limit AFTER successful validation and DB commit."""
    limit_dict_size(rate_dict, max_size)
    rate_dict[client_ip] = time.time()


def perform_security_checks(ip_hash: str) -> Tuple[bool, Optional[Dict], int]:
    """
    Perform IP blacklist and CSRF validation.
    Returns (is_blocked, error_response or None, status_code)
    """
    # Check IP blacklist
    is_blocked, block_info = is_ip_blacklisted(ip_hash)
    if is_blocked:
        return True, {'error': 'IP blocked.'}, 403
    
    # Validate CSRF token
    csrf_token = request.headers.get('X-CSRF-Token')
    if not validate_csrf_token(csrf_token):
        return True, {'error': 'Invalid CSRF Token.'}, 403
    
    # NOTE: X-Requested-With header check removed.
    # This header provides no real security - any attacker can trivially set it:
    #   curl -H "X-Requested-With: DRP-Client" ...
    # Real protection comes from CSRF tokens and rate limiting.
    
    return False, None, 200


# =============================================================================
# PUBLIC ROUTES
# =============================================================================

@forum_bp.route('/forum')
def forum_redirect():
    return redirect('/forum/forum.html')


@forum_bp.route('/api/forum/check-admin', methods=['GET'])
def check_admin_status():
    """Check if current user has valid admin session"""
    try:
        session_token = request.cookies.get('admin_session_token')
        is_admin = validate_admin_session(session_token)
        return jsonify({'is_admin': is_admin})
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'Admin check failed: {e}')
        return jsonify({'is_admin': False})


@forum_bp.route('/api/forum/posts', methods=['GET'])
def get_forum_posts():
    """Get paginated forum posts with optional search and polling."""
    try:
        # Pagination & Polling
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search_query = request.args.get('q', '').strip()
        since_timestamp = request.args.get('since', 0.0, type=float)
        
        # Max per page to prevent abuse
        if per_page > 50:
            per_page = 50
        
        # Eager load comments to prevent N+1 problem
        from sqlalchemy.orm import joinedload
        query = ForumPost.query.options(joinedload(ForumPost.comments)).order_by(ForumPost.timestamp.desc())
        
        # Polling: Only get posts newer than X
        if since_timestamp > 0:
            query = query.filter(ForumPost.timestamp > since_timestamp)
        
        # Server-side Search
        if search_query:
            search_pattern = f"%{search_query}%"
            query = query.filter(
                (ForumPost.title.ilike(search_pattern)) |
                (ForumPost.content.ilike(search_pattern))
            )
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'posts': [post.to_dict() for post in pagination.items],
            'meta': {
                'page': page,
                'per_page': per_page,
                'total_posts': pagination.total,
                'total_pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        })
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'Failed to load forum posts: {type(e).__name__}', exc_info=True)
        return jsonify({'posts': [], 'meta': {}}), 500


@forum_bp.route('/api/forum/posts', methods=['POST'])
def create_forum_post():
    """
    Create a new forum post.
    
    Rate limit is applied AFTER successful validation and DB commit
    to prevent penalizing users for invalid submissions.
    """
    try:
        ip_hash = get_client_ip_hash()
        client_ip = request.remote_addr
        
        # 1. Security checks (IP blacklist, CSRF)
        is_blocked, error_response, status = perform_security_checks(ip_hash)
        if is_blocked:
            return jsonify(error_response), status
        
        # 2. Check rate limit (but don't apply yet)
        is_limited, error_response = check_rate_limit(
            FORUM_POST_RATE_LIMITS, MAX_FORUM_POST_RATE_LIMITS, client_ip, 30
        )
        if is_limited:
            return jsonify(error_response), 429
        
        # 3. Get and validate data
        post_data = request.json
        title = post_data.get('title', '').strip()
        content = post_data.get('content', '').strip()
        author = post_data.get('author', 'Anonym').strip()[:30]

        # DoS protection - check length before sanitization
        if len(title) > 500 or len(content) > 10000:
            return jsonify({'error': 'Content too long.'}), 400

        title = sanitize_input(title)
        content = sanitize_input(content)
        
        if not title or len(title) < 5 or not content or len(content) < 10:
            return jsonify({'error': 'Title/Content too short.'}), 400
        
        # 4. Content quality checks
        repetition, auto_blocked = check_content_repetition(ip_hash, content)
        if repetition or auto_blocked:
            return jsonify({'error': 'Duplicate content detected.'}), 403

        if looks_like_spam(content) or looks_like_spam(title):
            return jsonify({'error': 'Spam detected.'}), 403

        # 5. Create and save post
        new_post = ForumPost(
            id=str(uuid4()),
            title=title,
            content=content,
            author=author,
            ip_hash=ip_hash,
            timestamp=time.time()
        )
        
        db.session.add(new_post)
        db.session.commit()
        
        # 6. Apply rate limit ONLY after successful commit
        apply_rate_limit(FORUM_POST_RATE_LIMITS, MAX_FORUM_POST_RATE_LIMITS, client_ip)
        
        return jsonify({'success': True, 'post': new_post.to_dict()})
        
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'Failed to create forum post: {type(e).__name__}', exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Internal error.'}), 500


@forum_bp.route('/api/forum/posts/<post_id>/comments', methods=['GET'])
def get_post_comments(post_id):
    """Get all comments for a post."""
    try:
        post = ForumPost.query.get(post_id)
        if post:
            return jsonify([c.to_dict() for c in post.comments])
        return jsonify([])
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'Failed to load comments for post {post_id}: {type(e).__name__}', exc_info=True)
        return jsonify([]), 500


@forum_bp.route('/api/forum/posts/<post_id>/comments', methods=['POST'])
def add_post_comment(post_id):
    """
    Add a comment to a post.
    
    Rate limit is applied AFTER successful validation and DB commit.
    """
    try:
        ip_hash = get_client_ip_hash()
        client_ip = request.remote_addr
        
        # 1. Security checks
        is_blocked, _ = is_ip_blacklisted(ip_hash)
        if is_blocked:
            return jsonify({'error': 'Blocked'}), 403
        
        csrf_token = request.headers.get('X-CSRF-Token')
        if not validate_csrf_token(csrf_token):
            return jsonify({'error': 'CSRF'}), 403
        
        # 2. Check rate limit (but don't apply yet)
        is_limited, error_response = check_rate_limit(
            FORUM_COMMENT_RATE_LIMITS, MAX_FORUM_COMMENT_RATE_LIMITS, client_ip, 30
        )
        if is_limited:
            return jsonify(error_response), 429
        
        # 3. Check if post exists
        post = ForumPost.query.get(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        # 4. Validate data
        comment_data = request.json
        content = comment_data.get('content', '').strip()
        author = comment_data.get('author', 'Anonym').strip()[:30]

        # DoS protection
        if len(content) > 5000:
            return jsonify({'error': 'Content too long.'}), 400

        content = sanitize_input(content)
        
        if not content or len(content) < 2:
            return jsonify({'error': 'Short'}), 400
        
        # 5. Create and save comment
        new_comment = ForumComment(
            id=str(uuid4()),
            post_id=post_id,
            content=content,
            author=author,
            ip_hash=ip_hash,
            timestamp=time.time()
        )
        
        db.session.add(new_comment)
        db.session.commit()
        
        # 6. Apply rate limit ONLY after successful commit
        apply_rate_limit(FORUM_COMMENT_RATE_LIMITS, MAX_FORUM_COMMENT_RATE_LIMITS, client_ip)
        
        return jsonify({'success': True, 'comment': new_comment.to_dict()})
        
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'Failed to add comment to post {post_id}: {type(e).__name__}', exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Internal error.'}), 500


# =============================================================================
# ADMIN ROUTES (Protected with @require_admin decorator)
# =============================================================================

@forum_bp.route('/api/forum/posts/<post_id>', methods=['DELETE'])
@require_admin
def delete_forum_post(post_id):
    """Delete a forum post and all its comments."""
    try:
        post = ForumPost.query.get(post_id)
        if post:
            db.session.delete(post)
            db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'Failed to delete forum post {post_id}: {type(e).__name__}', exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Internal error.'}), 500


@forum_bp.route('/api/forum/posts/<post_id>/comments/<comment_id>', methods=['DELETE'])
@require_admin
def delete_forum_comment(post_id, comment_id):
    """Delete a specific comment."""
    try:
        comment = ForumComment.query.get(comment_id)
        if comment:
            db.session.delete(comment)
            db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'Failed to delete comment {comment_id}: {type(e).__name__}', exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Internal error.'}), 500
