"""Access request model — public onboarding for new professionals."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship

from src.db import Base


class AccessRequest(Base):
    __tablename__ = 'access_requests'

    id = Column(Integer, primary_key=True)
    guid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    first_name = Column(String(255), nullable=False)
    last_name = Column(String(255), nullable=False)
    professional_role = Column(Enum('doctor', 'nurse', 'other', name='professional_role_enum',
                                    create_type=False), nullable=False, default='other')
    organisation_guid = Column(String(36), ForeignKey('organisations.guid'), nullable=False)
    requested_phases = Column(JSON, nullable=False, default=list)
    chosen_leader_guid = Column(String(36), ForeignKey('users.guid'), nullable=False)
    status = Column(Enum('pending', 'endorsed', 'approved', 'rejected',
                         name='access_request_status_enum'), nullable=False, default='pending')
    decided_by_guid = Column(String(36), ForeignKey('users.guid', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    organisation = relationship('Organisation')
    chosen_leader = relationship('User', foreign_keys=[chosen_leader_guid])
    decided_by = relationship('User', foreign_keys=[decided_by_guid])

    def __repr__(self):
        return f'<AccessRequest {self.email} ({self.status})>'
