#!/usr/bin/env python3
"""Ticket #57 — groups ⟂ phases migration report.

Before #57, a user's `effective_phases` in the access blob was the union
of (direct UserPhase grants) and (the `group_type` of every approved
group membership). After #57 the union is gone: phases come *only* from
UserPhase. After #60 the column was renamed `group_type` → `category` and
loosened to a free-form varchar, so this script now walks rows where
`category` happens to still match a canonical phase name.

This script prints every user who, under the old model, would have had a
phase via an approved group membership but has **no** matching UserPhase
row — i.e. every user who will lose some phase access at the cutover
unless an SU explicitly grants it.

The policy (set 2026-04-15 by the user) is **SU-reviewed, explicit** — so
this script **does not** write anything. It is an audit artefact. Pipe it
to a file, walk through it with an SU, and grant each retained phase via
`POST /api/admin/users/<guid>/phases` on `sso.pdhc.se`.

Usage:
    cd app
    source venv/bin/activate
    python scripts/phases_migration_report.py

Output (stdout, TSV):
    user_guid<TAB>email<TAB>phase<TAB>via_group_guid<TAB>via_group_name
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.db import init_db, get_session
import src.models  # noqa: F401
from src.models.user import User
from src.models.membership import Membership
from src.models.group import Group
from src.models.user_phase import UserPhase, PHASE_NAMES


def main() -> int:
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print('ERROR: DATABASE_URL not set.', file=sys.stderr)
        return 1

    init_db(database_url)
    session = get_session()

    try:
        # (user_guid, phase) pairs already covered by direct grants.
        covered: set[tuple[str, str]] = {
            (up.user_guid, up.phase)
            for up in session.query(UserPhase).all()
        }

        # Walk every approved membership → implied phase.
        q = (
            session.query(Membership, Group, User)
            .join(Group, Group.guid == Membership.group_guid)
            .join(User, User.guid == Membership.user_guid)
            .filter(Membership.status == 'approved')
            .order_by(User.email, Group.category, Group.name)
        )

        header = ('user_guid', 'email', 'phase',
                  'via_group_guid', 'via_group_name')
        print('\t'.join(header))

        rows = 0
        seen: set[tuple[str, str]] = set()
        for membership, group, user in q:
            phase = group.category
            # Post-#60 `category` is free-form. Only rows whose category
            # happens to be a canonical phase name carry pre-#57 semantics.
            if phase not in PHASE_NAMES:
                continue
            key = (user.guid, phase)
            if key in covered:
                # SU already granted this phase directly — no action needed.
                continue
            if key in seen:
                # Don't list the same user+phase twice if they're in
                # multiple groups of that type; one grant covers all.
                continue
            seen.add(key)
            print('\t'.join([
                user.guid, user.email, phase,
                group.guid, group.name,
            ]))
            rows += 1

        print(f'# {rows} (user, phase) pairs need explicit SU grants',
              file=sys.stderr)
        return 0

    finally:
        session.close()


if __name__ == '__main__':
    sys.exit(main())
