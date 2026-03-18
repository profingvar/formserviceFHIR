"""CORS configuration — allows origins from config for cross-origin SSO."""
from flask_cors import CORS


def init_cors(app):
    """Initialise CORS with allowed origins from config."""
    origins = app.config.get('ALLOWED_ORIGINS', ['http://localhost:9000'])
    CORS(app, origins=origins, supports_credentials=True)
