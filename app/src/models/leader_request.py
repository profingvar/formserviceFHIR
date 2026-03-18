"""Leader request model — professional requests group admin role, SU decides."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship

from src.db import Base


class LeaderRequest(Base):
    __tablename__ = 'leader_requests'

    id = Column(Integer, primary_key=True)
    guid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_guid = Column(String(36), ForeignKey('users.guid'), nullable=False)
    group_guid = Column(String(36), ForeignKey('groups.guid'), nullable=False)
    status = Column(Enum('pending', 'approved', 'rejected', name='proposal_status_enum',
                         create_type=False), nullable=False, default='pending')
    decided_by_guid = Column(String(36), ForeignKey('users.guid', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship('User', foreign_keys=[user_guid])
    group = relationship('Group')
    decided_by = relationship('User', foreign_keys=[decided_by_guid])

    def __repr__(self):
        return f'<LeaderRequest user={self.user_guid} group={self.group_guid} ({self.status})>'
