"""Organisation model — FHIR resource type: Organization. Single source of truth."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime

from src.db import Base


class Organisation(Base):
    __tablename__ = 'organisations'

    FHIR_RESOURCE_TYPE = 'Organization'

    id = Column(Integer, primary_key=True)
    guid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), unique=True, nullable=False)
    fhir_resource_type = Column(String(50), nullable=False, default='Organization')
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Organisation {self.name}>'
