"""Group model — FHIR resource type: Group. Maps to phase authorization."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, Enum

from src.db import Base


class Group(Base):
    __tablename__ = 'groups'

    FHIR_RESOURCE_TYPE = 'Group'

    id = Column(Integer, primary_key=True)
    guid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    group_type = Column(Enum('planning', 'request', 'provider', 'analysis', name='group_type_enum'),
                        nullable=False)
    fhir_resource_type = Column(String(50), nullable=False, default='Group')
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Group {self.name} ({self.group_type})>'
