"""In-memory rate limiting for public and login endpoints."""
import time
from functools import wraps
from collections import defaultdict

from flask import request, jsonify

# {ip: [(timestamp, ...),]}
_request_log = defaultdict(list)


def _cleanup(ip, window):
    """Remove entries older than window."""
    cutoff = time.time() - window
    _request_log[ip] = [t for t in _request_log[ip] if t > cutoff]


def rate_limit(max_requests=30, window_seconds=60):
    """Decorator: limit requests per IP within a time window."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            ip = request.remote_addr or '0.0.0.0'
            _cleanup(ip, window_seconds)

            if len(_request_log[ip]) >= max_requests:
                return jsonify({
                    "error": "rate_limit_exceeded",
                    "message": f"Too many requests. Limit: {max_requests} per {window_seconds}s",
                }), 429

            _request_log[ip].append(time.time())
            return f(*args, **kwargs)
        return decorated
    return decorator


def reset_rate_limits():
    """Clear all rate limit state. For testing only."""
    _request_log.clear()
