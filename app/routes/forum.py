from flask import Blueprint, request, jsonify, redirect
import time
from app.config import MAX_FORUM_POST_RATE_LIMITS, MAX_FORUM_COMMENT_RATE_LIMITS
from app.utils.security import get_client_ip_hash, validate_csrf_token, validate_admin_session, limit_dict_size
from app.utils.moderation import is_ip_blacklisted, add_ip_warning, check_content_repetition, looks_like_spam
from app.utils.sanitize import sanitize_input
from app.models import db, ForumPost, ForumComment

forum_bp = Blueprint('forum', __name__)

# Keep track of rate limits for forum
FORUM_POST_RATE_LIMITS = {}
FORUM_COMMENT_RATE_LIMITS = {}

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
    try:
        # Pagination & Polling
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search_query = request.args.get('q', '').strip()
        since_timestamp = request.args.get('since', 0.0, type=float)
        
        # Max per page to prevent abuse
        if per_page > 50: per_page = 50
        
        # Eager load comments to prevent N+1 problem
        from sqlalchemy.orm import joinedload
        query = ForumPost.query.options(joinedload(ForumPost.comments)).order_by(ForumPost.timestamp.desc())
        
        # Polling: Only get posts newer than X
        if since_timestamp > 0:
            query = query.filter(ForumPost.timestamp > since_timestamp)
            # When polling, we might want all new posts, but let's still respect a (larger) limit or use pagination
            # For simplicity in this context, we return new posts. 
            # If there are TOO many, the client will just receive the latest 50 (due to pagination default if strictly applied, but logic below handles it)
        
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
    try:
        ip_hash = get_client_ip_hash()
        is_blocked, block_info = is_ip_blacklisted(ip_hash)
        
        if is_blocked:
            return jsonify({'error': 'IP blocked.'}), 403

        csrf_token = request.headers.get('X-CSRF-Token')
        if not validate_csrf_token(csrf_token):
            return jsonify({'error': 'Invalid CSRF Token.'}), 403
        
        if request.headers.get('X-Requested-With') != 'DRP-Client':
            return jsonify({'error': 'Access denied.'}), 403
        
        client_ip = request.remote_addr
        current_time = time.time()
        
        if client_ip in FORUM_POST_RATE_LIMITS:
            if current_time - FORUM_POST_RATE_LIMITS[client_ip] < 120:
                add_ip_warning(ip_hash, "Rate-Limit Abuse (Spamming Forum)")
                return jsonify({'error': 'Please wait 2 minutes.'}), 429
        
        limit_dict_size(FORUM_POST_RATE_LIMITS, MAX_FORUM_POST_RATE_LIMITS)
        FORUM_POST_RATE_LIMITS[client_ip] = current_time
        
        post_data = request.json
        title = post_data.get('title', '').strip()
        content = post_data.get('content', '').strip()
        author = post_data.get('author', 'Anonym').strip()[:30]

        # Backend length check (DoS protection)
        if len(title) > 500 or len(content) > 10000:
            return jsonify({'error': 'Content too long.'}), 400

        title = sanitize_input(title)
        content = sanitize_input(content)
        
        if not title or len(title) < 5 or not content or len(content) < 10:
            return jsonify({'error': 'Title/Content too short.'}), 400
        
        repetition, auto_blocked = check_content_repetition(ip_hash, content)
        if auto_blocked: return jsonify({'error': 'Blocked due to spam.'}), 403

        if looks_like_spam(content) or looks_like_spam(title):
            add_ip_warning(ip_hash, "Spam-Inhalt im Forum erkannt")
            return jsonify({'error': 'Spam detected.'}), 403

        new_post = ForumPost(
            id=str(int(time.time() * 1000)),
            title=title,
            content=content,
            author=author,
            ip_hash=ip_hash,
            timestamp=time.time()
        )
        
        db.session.add(new_post)
        db.session.commit()
        
        return jsonify({'success': True, 'post': new_post.to_dict()})
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'Failed to create forum post: {type(e).__name__}', exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Interner Fehler.'}), 500

@forum_bp.route('/api/forum/posts/<post_id>/comments', methods=['GET'])
def get_post_comments(post_id):
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
    try:
        ip_hash = get_client_ip_hash()
        is_blocked, _ = is_ip_blacklisted(ip_hash)
        if is_blocked: return jsonify({'error': 'Blocked'}), 403
        
        csrf_token = request.headers.get('X-CSRF-Token')
        if not validate_csrf_token(csrf_token): return jsonify({'error': 'CSRF'}), 403
        
        client_ip = request.remote_addr
        current_time = time.time()
        if client_ip in FORUM_COMMENT_RATE_LIMITS:
            if current_time - FORUM_COMMENT_RATE_LIMITS[client_ip] < 30:
                return jsonify({'error': 'Wait 30 sec.'}), 429
        
        limit_dict_size(FORUM_COMMENT_RATE_LIMITS, MAX_FORUM_COMMENT_RATE_LIMITS)
        FORUM_COMMENT_RATE_LIMITS[client_ip] = current_time
        
        # Check if post exists
        post = ForumPost.query.get(post_id)
        if not post:
            return jsonify({'error': 'Post not found'}), 404
        
        comment_data = request.json
        content = comment_data.get('content', '').strip()
        author = comment_data.get('author', 'Anonym').strip()[:30]

        # Backend length check (DoS protection)
        if len(content) > 5000:
            return jsonify({'error': 'Content too long.'}), 400

        content = sanitize_input(content)
        
        if not content or len(content) < 2: return jsonify({'error': 'Short'}), 400
        
        new_comment = ForumComment(
            id=str(int(time.time() * 1000)),
            post_id=post_id,
            content=content,
            author=author,
            ip_hash=ip_hash,
            timestamp=time.time()
        )
        
        db.session.add(new_comment)
        db.session.commit()
        
        return jsonify({'success': True, 'comment': new_comment.to_dict()})
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'Failed to add comment to post {post_id}: {type(e).__name__}', exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Interner Fehler.'}), 500

@forum_bp.route('/api/forum/posts/<post_id>', methods=['DELETE'])
def delete_forum_post(post_id):
    try:
        session_token = request.cookies.get('admin_session_token')
        if not validate_admin_session(session_token): return jsonify({'error': 'Unauthorized'}), 401
        
        post = ForumPost.query.get(post_id)
        if post:
            db.session.delete(post)
            db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'Failed to delete forum post {post_id}: {type(e).__name__}', exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Interner Fehler.'}), 500

@forum_bp.route('/api/forum/posts/<post_id>/comments/<comment_id>', methods=['DELETE'])
def delete_forum_comment(post_id, comment_id):
    try:
        session_token = request.cookies.get('admin_session_token')
        if not validate_admin_session(session_token): return jsonify({'error': 'Unauthorized'}), 401
        
        comment = ForumComment.query.get(comment_id)
        if comment:
            db.session.delete(comment)
            db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        from flask import current_app
        current_app.logger.error(f'Failed to delete comment {comment_id}: {type(e).__name__}', exc_info=True)
        db.session.rollback()
        return jsonify({'error': 'Interner Fehler.'}), 500
