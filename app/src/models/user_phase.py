"""User-Phase junction — direct phase grants, independent of Group membership.

Tickets #46 + #57: phases are a first-class access criterion and they are
**orthogonal to group membership**. The `UserPhase` table is the **sole**
source of phase access after #57 — an approved membership in a
`planning`-typed group does NOT confer the `planning` phase on its own.
SU grants phases explicitly via `POST /api/admin/users/<guid>/phases`.

Phase name values stay stable (`planning`, `request`, `provider`,
`analysis`) so the `'planning' in effective_phases` check every downstream
service already does keeps working unchanged; only the source of that
list changed.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, UniqueConstraint

from src.db import Base


# The canonical phase names. After #60 `Group.category` is a free-form
# varchar, so it no longer constrains this list — phases live in their own
# enum here and are granted directly via UserPhase regardless of what
# categories SU invents for groups.
PHASE_NAMES = ('planning', 'request', 'provider', 'analysis')


class UserPhase(Base):
    __tablename__ = 'user_phases'

    id = Column(Integer, primary_key=True)
    user_guid = Column(String(36), ForeignKey('users.guid'), nullable=False)
    phase = Column(Enum(*PHASE_NAMES, name='phase_enum'), nullable=False)
    # NULL = system backfill (from pre-existing group-derived access).
    granted_by_guid = Column(String(36), ForeignKey('users.guid'), nullable=True)
    granted_at = Column(DateTime, nullable=False,
                        default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint('user_guid', 'phase', name='uq_user_phase'),
    )

    def __repr__(self):
        return f'<UserPhase user={self.user_guid} phase={self.phase}>'
