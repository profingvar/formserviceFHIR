"""User-Organisation junction — many-to-many relationship."""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from src.db import Base


class UserOrganisation(Base):
    __tablename__ = 'user_organisations'

    id = Column(Integer, primary_key=True)
    user_guid = Column(String(36), ForeignKey('users.guid'), nullable=False)
    organisation_guid = Column(String(36), ForeignKey('organisations.guid'), nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint('user_guid', 'organisation_guid', name='uq_user_organisation'),
    )

    # Relationships
    user = relationship('User', back_populates='organisations')
    organisation = relationship('Organisation')

    def __repr__(self):
        return f'<UserOrganisation user={self.user_guid} org={self.organisation_guid}>'
