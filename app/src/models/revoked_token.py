"""Revoked token model — JWT revocation list, pruned after expiry."""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime

from src.db import Base


class RevokedToken(Base):
    __tablename__ = 'revoked_tokens'

    id = Column(Integer, primary_key=True)
    token_guid = Column(String(36), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<RevokedToken {self.token_guid}>'
