from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
from app.config import SECRET_KEY, MAX_CONTENT_LENGTH, SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS
from app.utils.admin_auth import rotate_admin_credentials
from app.utils.logger import setup_logger
from app.models import db

def create_app():
    app = Flask(__name__, static_folder=None)
    
    # Initialize Logger immediately
    with app.app_context():
        setup_logger(app)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    
    # SQLAlchemy Configuration
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
    
    # Initialize Database
    db.init_app(app)

    # Register Blueprints
    from app.routes.main import main_bp
    from app.routes.applications import applications_bp
    from app.routes.forum import forum_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(applications_bp)
    app.register_blueprint(forum_bp)
    app.register_blueprint(admin_bp)

    # Initial setup
    with app.app_context():
        # Create database tables (if they don't exist)
        db.create_all()
        rotate_admin_credentials()

    # Security headers for all responses
    @app.after_request
    def add_security_headers(response):
        # Content Security Policy - only allows trusted sources
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        # Prevents MIME-Type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        # Prevents Clickjacking
        response.headers['X-Frame-Options'] = 'DENY'
        # Controls referrer information
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        # XSS protection (for older browsers)
        response.headers['X-XSS-Protection'] = '1; mode=block'
        return response

    return app

