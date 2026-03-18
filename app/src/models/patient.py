"""Patient model — FHIR resource type: Patient."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from src.db import Base


class Patient(Base):
    __tablename__ = 'patients'

    FHIR_RESOURCE_TYPE = 'Patient'

    id = Column(Integer, primary_key=True)
    guid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    personnummer = Column(String(12), unique=True, nullable=False)
    organisation_guid = Column(String(36), ForeignKey('organisations.guid'), nullable=True)
    in_registry = Column(Boolean, nullable=False, default=False)
    registries = Column(JSON, default=list)
    fhir_resource_type = Column(String(50), nullable=False, default='Patient')
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship('User', back_populates='patient')
    organisation = relationship('Organisation', foreign_keys=[organisation_guid],
                                primaryjoin='Patient.organisation_guid == Organisation.guid')

    def __repr__(self):
        return f'<Patient {self.guid} pnr={self.personnummer}>'
