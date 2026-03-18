"""Professional model — FHIR resource type: Practitioner."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship

from src.db import Base


class Professional(Base):
    __tablename__ = 'professionals'

    FHIR_RESOURCE_TYPE = 'Practitioner'

    id = Column(Integer, primary_key=True)
    guid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    professional_role = Column(Enum('doctor', 'nurse', 'other', name='professional_role_enum'),
                               nullable=False, default='other')
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    fhir_resource_type = Column(String(50), nullable=False, default='Practitioner')
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship('User', back_populates='professional')

    def __repr__(self):
        return f'<Professional {self.guid} role={self.professional_role}>'
