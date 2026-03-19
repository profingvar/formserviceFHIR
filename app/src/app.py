"""Flask application factory — registers blueprints, DB, config, middleware."""
import time

from flask import Flask, jsonify

from src.config import Config, TestConfig
from src.db import init_db, close_db
import src.db as _db
from src.middleware.csrf import init_csrf
from src.middleware.cors import init_cors
from src.services.audit_log import init_audit_log

_start_time = None


def create_app(config_override=None):
    """Create and configure the Flask application."""
    global _start_time
    _start_time = time.time()

    app = Flask(__name__)

    # Load config
    if config_override and config_override.get('TESTING'):
        app.config.from_object(TestConfig())
    else:
        cfg = Config()
        Config.validate()
        app.config.from_mapping(
            SECRET_KEY=cfg.SECRET_KEY,
            DATABASE_URL=cfg.DATABASE_URL,
            SESSION_EXPIRY_HOURS=cfg.SESSION_EXPIRY_HOURS,
            FLASK_ENV=cfg.FLASK_ENV,
            LOG_DIR=cfg.LOG_DIR,
            ALLOWED_ORIGINS=cfg.ALLOWED_ORIGINS,
            ALLOWED_CALLBACK_URLS=cfg.ALLOWED_CALLBACK_URLS,
            SERVICE_CREDENTIALS=cfg.SERVICE_CREDENTIALS,
            WTF_CSRF_ENABLED=True,
            WTF_CSRF_SSL_STRICT=False,
        )

    # Apply overrides (for testing)
    if config_override:
        app.config.update(config_override)

    # Initialise database
    db_url = app.config.get('DATABASE_URL', '')
    if db_url:
        init_db(db_url)
        # Import models to register with Base.metadata
        import src.models  # noqa: F401
        if db_url == 'sqlite://':
            # In-memory SQLite for testing: create tables immediately
            from src.db import create_all_tables
            create_all_tables()

    # Teardown: commit/rollback session per request
    app.teardown_appcontext(close_db)

    # Trust reverse proxy headers (X-Forwarded-For, X-Forwarded-Proto)
    if not app.config.get('TESTING'):
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Cookie security
    if not app.config.get('TESTING'):
        is_dev = app.config.get('FLASK_ENV') == 'development'
        app.config['SESSION_COOKIE_SECURE'] = not is_dev
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # Security headers
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        if not app.config.get('TESTING'):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        return response

    # Max upload size (16 MB) to prevent CSV DoS
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    # Middleware
    init_csrf(app)
    init_cors(app)

    # Audit logging
    log_dir = app.config.get('LOG_DIR', './logs')
    init_audit_log(log_dir)

    # --- Register blueprints ---
    from src.routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from src.routes.patient import patient_bp
    app.register_blueprint(patient_bp)

    from src.routes.groups import groups_bp
    app.register_blueprint(groups_bp)

    from src.routes.admin import admin_bp
    app.register_blueprint(admin_bp)

    from src.routes.public import public_bp
    app.register_blueprint(public_bp)

    from src.routes.frontend import frontend_bp
    app.register_blueprint(frontend_bp)

    from src.fhir.capability_statement import fhir_bp
    app.register_blueprint(fhir_bp)

    # --- Health endpoint (Phase 3.j) ---
    @app.route('/api/health')
    def health():
        db_ok = False
        if _db.engine is not None:
            try:
                with _db.engine.connect() as conn:
                    conn.execute(conn.default_schema_name if False else __import__('sqlalchemy').text('SELECT 1'))
                db_ok = True
            except Exception:
                db_ok = False

        uptime = round(time.time() - _start_time, 1) if _start_time else 0

        status = 'ok' if db_ok or app.config.get('TESTING') else 'degraded'
        code = 200 if status == 'ok' else 503

        return jsonify({
            "status": status,
            "database": "connected" if db_ok else "unavailable",
            "uptime_seconds": uptime,
        }), code

    return app
