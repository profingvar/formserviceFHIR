"""User model — base identity for all users."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship

from src.db import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    guid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    user_type = Column(Enum('patient', 'professional', name='user_type_enum'), nullable=False)
    is_su_admin = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    patient = relationship('Patient', back_populates='user', uselist=False, cascade='all, delete-orphan')
    professional = relationship('Professional', back_populates='user', uselist=False, cascade='all, delete-orphan')
    organisations = relationship('UserOrganisation', back_populates='user', cascade='all, delete-orphan')
    memberships = relationship('Membership', back_populates='user', foreign_keys='Membership.user_guid',
                               primaryjoin='User.guid == Membership.user_guid')

    def __repr__(self):
        return f'<User {self.email} ({self.user_type})>'
