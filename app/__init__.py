from flask import Flask, g
import os
import secrets
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_compress import Compress
from app.config import (
    SECRET_KEY, MAX_CONTENT_LENGTH, SQLALCHEMY_DATABASE_URI, 
    SQLALCHEMY_TRACK_MODIFICATIONS, SQLALCHEMY_ENGINE_OPTIONS,
    SEND_FILE_MAX_AGE_DEFAULT, COMPRESS_MIMETYPES, COMPRESS_LEVEL, COMPRESS_MIN_SIZE
)
from app.utils.admin_auth import rotate_admin_credentials
from app.utils.logger import setup_logger
from app.models import db

# Initialize Compress globally
compress = Compress()

def create_app():
    app = Flask(__name__, static_folder=None, template_folder=os.path.abspath('.'))
    
    # Initialize Logger immediately
    with app.app_context():
        setup_logger(app)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
    
    # Config
    app.config['SECRET_KEY'] = SECRET_KEY
    app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = SQLALCHEMY_ENGINE_OPTIONS
    
    # Static File Caching
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = SEND_FILE_MAX_AGE_DEFAULT
    
    # Response Compression Config
    app.config['COMPRESS_MIMETYPES'] = COMPRESS_MIMETYPES
    app.config['COMPRESS_LEVEL'] = COMPRESS_LEVEL
    app.config['COMPRESS_MIN_SIZE'] = COMPRESS_MIN_SIZE
    compress.init_app(app)
    
    # Pass computed configs
    from app.config import SECURE_COOKIES
    app.config['SECURE_COOKIES'] = SECURE_COOKIES
    
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

    # CSP Nonce & Security Headers
    from app.middleware.security_headers import add_security_headers

    @app.before_request
    def generate_csp_nonce():
        g.csp_nonce = secrets.token_urlsafe(16)

    @app.context_processor
    def inject_csp_nonce():
        return dict(csp_nonce=g.csp_nonce)

    @app.after_request
    def security_headers(response):
        return add_security_headers(response)

    # Global Error Handlers
    from flask import jsonify
    from app.exceptions import APIException

    @app.errorhandler(APIException)
    def handle_api_exception(error):
        """Handle all custom API exceptions with consistent JSON response."""
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        return response

    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 errors."""
        return jsonify({'error': 'Resource not found', 'status_code': 404}), 404

    @app.errorhandler(500)
    def handle_server_error(error):
        """Handle unexpected server errors."""
        app.logger.exception("Unexpected server error occurred")
        return jsonify({'error': 'Internal server error', 'status_code': 500}), 500

    # Initial setup
    with app.app_context():
        # Create database tables (if they don't exist)
        db.create_all()
        rotate_admin_credentials()

    return app
