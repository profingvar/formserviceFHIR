"""Invite model — time-limited token for group join."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from src.db import Base


class Invite(Base):
    __tablename__ = 'invites'

    id = Column(Integer, primary_key=True)
    guid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    group_guid = Column(String(36), ForeignKey('groups.guid', ondelete='CASCADE'), nullable=False)
    token = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_by_guid = Column(String(36), ForeignKey('users.guid'), nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    group = relationship('Group')
    created_by = relationship('User')

    def __repr__(self):
        return f'<Invite group={self.group_guid} expires={self.expires_at}>'
