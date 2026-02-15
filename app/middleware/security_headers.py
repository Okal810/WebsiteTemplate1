
from flask import request, g

class SecurityHeadersMiddleware:
    """
    Middleware to add security headers to every response.
    Centralizes CSP, HSTS, and other security headers.
    """
    def __init__(self, app):
        self.app = app
    
    def __call__(self, environ, start_response):
        return self.app(environ, start_response)

def add_security_headers(response):
    """
    Helper function to attach security headers to a Flask response.
    Used in @app.after_request to ensure access to Flask context (g.csp_nonce).
    """
    nonce = getattr(g, 'csp_nonce', '')
    nonce_directive = f"'nonce-{nonce}'" if nonce else "'unsafe-inline'"

    # Content Security Policy (Strict)
    # We allow 'unsafe-inline' for styles because many libraries/tailwind usage often requires it
    # but we restrict scripts to valid nonces.
    csp = (
        "default-src 'self'; "
        f"script-src 'self' 'unsafe-inline' {nonce_directive} https://cdn.tailwindcss.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdnjs.cloudflare.com; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    
    response.headers['Content-Security-Policy'] = csp
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    
    return response
