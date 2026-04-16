"""Group model — FHIR resource type: Group.

After #57 (Groups ⟂ Phases) groups are organisational/category metadata only
and no longer participate in phase authorisation. #60 follows through on the
naming: the old column `group_type` is renamed to `category` and the former
four-value enum (planning/request/provider/analysis) is loosened to a plain
varchar so SU can invent new categories without a schema migration.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime

from src.db import Base


class Group(Base):
    __tablename__ = 'groups'

    FHIR_RESOURCE_TYPE = 'Group'

    id = Column(Integer, primary_key=True)
    guid = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    # #60: was `group_type` (enum). Now a free-form category label; downstream
    # consumers read `groups[*].category` from the access blob.
    category = Column(String(64), nullable=False)
    fhir_resource_type = Column(String(50), nullable=False, default='Group')
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f'<Group {self.name} ({self.category})>'
