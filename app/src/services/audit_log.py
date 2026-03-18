"""File-based structured audit logging.

Logs: login attempts, admin actions, access decisions, token revocations.
Writes JSON lines to LOG_DIR with daily rotation.
"""
import json
import logging
import os
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler

_audit_logger = None


def init_audit_log(log_dir):
    """Initialise the audit logger with daily file rotation."""
    global _audit_logger

    os.makedirs(log_dir, exist_ok=True)

    _audit_logger = logging.getLogger('audit')
    _audit_logger.setLevel(logging.INFO)
    _audit_logger.propagate = False

    if not _audit_logger.handlers:
        log_path = os.path.join(log_dir, 'audit.log')
        handler = TimedRotatingFileHandler(
            log_path, when='midnight', interval=1, backupCount=90, utc=True,
        )
        handler.setFormatter(logging.Formatter('%(message)s'))
        _audit_logger.addHandler(handler)


def audit(event, user_guid=None, detail=None, ip=None):
    """Write a structured audit log entry.

    Args:
        event: Event type (e.g. 'login_success', 'admin_promote_su')
        user_guid: GUID of the acting user (if authenticated)
        detail: Dict with additional context
        ip: Client IP address
    """
    entry = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'event': event,
        'user_guid': user_guid,
        'ip': ip,
        'detail': detail or {},
    }

    if _audit_logger:
        _audit_logger.info(json.dumps(entry, default=str))
