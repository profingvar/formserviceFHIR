"""JWT service — issue, decode, validate tokens. Checks revocation."""
import uuid
from datetime import datetime, timedelta, timezone

import jwt


class TokenExpiredError(Exception):
    pass


class TokenInvalidError(Exception):
    pass


class TokenRevokedError(Exception):
    pass


def issue_token(user_guid, secret_key, expiry_hours=24):
    """Issue a JWT with user_guid as subject and a unique token_guid (jti)."""
    now = datetime.now(timezone.utc)
    payload = {
        'sub': user_guid,
        'jti': str(uuid.uuid4()),
        'iat': now,
        'exp': now + timedelta(hours=expiry_hours),
    }
    return jwt.encode(payload, secret_key, algorithm='HS256')


def decode_token(token, secret_key):
    """Decode and validate a JWT. Returns payload dict.
    Raises TokenExpiredError or TokenInvalidError."""
    try:
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise TokenInvalidError(f"Invalid token: {e}")


def validate_token(token, secret_key, session):
    """Full validation: decode + check revocation. Returns payload.
    Raises TokenExpiredError, TokenInvalidError, or TokenRevokedError."""
    payload = decode_token(token, secret_key)

    from src.models.revoked_token import RevokedToken
    token_guid = payload.get('jti')
    if token_guid:
        revoked = session.query(RevokedToken).filter_by(token_guid=token_guid).first()
        if revoked:
            raise TokenRevokedError("Token has been revoked")

    return payload


def revoke_token(token_guid, expires_at, session):
    """Add token to revocation list."""
    from src.models.revoked_token import RevokedToken
    revoked = RevokedToken(token_guid=token_guid, expires_at=expires_at)
    session.add(revoked)


def prune_expired_tokens(session):
    """Remove revoked tokens that have passed their expiry."""
    from src.models.revoked_token import RevokedToken
    now = datetime.now(timezone.utc)
    session.query(RevokedToken).filter(RevokedToken.expires_at < now).delete()
