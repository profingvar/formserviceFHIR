"""Group proposal model — professional suggests new group, SU decides."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship

from src.db import Base


class GroupProposal(Base):
    __tablename__ = 'group_proposals'

    id = Column(Integer, primary_key=True)
    guid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    proposed_name = Column(String(255), nullable=False)
    group_type = Column(Enum('planning', 'request', 'provider', 'analysis', name='group_type_enum',
                             create_type=False), nullable=False)
    requested_by_guid = Column(String(36), ForeignKey('users.guid'), nullable=False)
    status = Column(Enum('pending', 'approved', 'rejected', name='proposal_status_enum'),
                    nullable=False, default='pending')
    decided_by_guid = Column(String(36), ForeignKey('users.guid', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    requested_by = relationship('User', foreign_keys=[requested_by_guid])
    decided_by = relationship('User', foreign_keys=[decided_by_guid])

    def __repr__(self):
        return f'<GroupProposal {self.proposed_name} ({self.status})>'
