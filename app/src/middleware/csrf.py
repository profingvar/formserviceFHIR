"""CSRF protection — wraps Flask-WTF CSRFProtect.
Active on all form POST endpoints. API endpoints using Bearer tokens
are exempt (stateless auth does not need CSRF)."""
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()


def init_csrf(app):
    """Initialise CSRF protection on the Flask app.
    Exempts API blueprint routes that use Bearer token auth."""
    csrf.init_app(app)

    # Exempt JSON API routes — they use Bearer tokens, not cookies
    @app.before_request
    def csrf_exempt_api():
        from flask import request
        if request.path.startswith('/api/'):
            # Skip CSRF for API endpoints (Bearer token auth)
            request.csrf_valid = True
